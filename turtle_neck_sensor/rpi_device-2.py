"""Run on Raspberry Pi alongside app.py. BCM numbering; GPIO imported lazily.

쓰레드 구조 (라즈베리파이 부하를 줄이도록 나눔)
  - 상태 확인 쓰레드 : 서버에 지금 자세 상태를 물어봄 (poll_interval마다). 상태가 '바뀔 때만' 게시판에 알림
  - LED 쓰레드      : 상태가 바뀔 때 색을 바꾸고 잠듦. 경고일 때만 0.5초마다 깨어나 깜빡임
  - 부저 쓰레드     : 상태가 바뀔 때만 켜고 끔. 그 밖에는 계속 잠듦
  - 메인 쓰레드     : 0.5초마다 상태 확인 쓰레드가 멈추지 않았는지만 확인 (멈췄으면 모두 끔)
  예전에는 메인 쓰레드가 0.02초마다(초당 50번) 깨어나 출력을 확인했는데,
  이제는 바뀔 때만 일해서 CPU를 거의 쓰지 않음. 네트워크가 느려도 LED·부저는 기다리지 않음.
  색·소리 패턴과 설정 파일(sensor_config.json), 실행 방법(--config, --dry-run)은 그대로.
"""
import argparse
import json
import logging
from pathlib import Path
import signal
import threading
import time
import urllib.request

log = logging.getLogger(__name__)

BLINK_SEC = .5        # 경고: 0.5초 켜짐, 0.5초 꺼짐 (output_pattern과 같은 박자)
STALE_SEC = 2         # 상태 확인이 이 시간 넘게 멈추면 모두 끔
WATCH_SEC = .5        # 메인 쓰레드가 확인하는 간격


def read_config(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    rgb_pins = cfg.get('rgb_pins')
    if rgb_pins is not None and (not isinstance(rgb_pins, list) or len(rgb_pins) != 3 or None in rgb_pins):
        raise ValueError('rgb_pins must specify three BCM numbers in R, G, B order')
    pins = [*(rgb_pins or []), cfg.get('buzzer_pin')]
    if any(p is not None and (type(p) is not int or not 0 <= p <= 27) for p in pins):
        raise ValueError('GPIO pins must be BCM integers 0..27, or null to disable')
    used = [pin for pin in pins if pin is not None]
    if len(set(used)) != len(used):
        raise ValueError('RGB channels and buzzer must use different GPIO pins')
    if cfg.get('buzzer_type', 'active') not in ('active', 'passive'):
        raise ValueError('buzzer_type must be active or passive')
    for key, default in [('poll_interval', .25), ('request_timeout', 1), ('tone_hz', 880)]:
        value = cfg.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < float('inf'):
            raise ValueError(key + ' must be a positive finite number')
    return cfg


def output_pattern(status, elapsed):
    if status == '정상':
        return (0, 0, 1), False
    if status == '경고' and elapsed % 1 < .5:
        return (1, 0, 0), False
    if status == '위험':
        return (1, 1, 0), True
    return (0, 0, 0), False


class StatusBoard:
    """지금 자세 상태를 쓰레드들이 함께 보는 게시판. 상태가 바뀔 때만 기다리는 쓰레드를 깨움"""
    def __init__(self):
        self.cond = threading.Condition()
        self.status, self.changed_at, self.version, self.closing = None, time.monotonic(), 0, False

    def publish(self, status):
        with self.cond:
            if status == self.status:
                return
            self.status, self.changed_at, self.version = status, time.monotonic(), self.version + 1
            self.cond.notify_all()
        log.info('Posture: %s', status or 'offline')

    def wait_change(self, version, timeout=None):
        """version 이후 상태가 바뀌거나 timeout이 지날 때까지 잠듦. (version, 상태, 바뀐 시각, 종료 여부)"""
        with self.cond:
            self.cond.wait_for(lambda: self.version != version or self.closing, timeout)
            return self.version, self.status, self.changed_at, self.closing

    def close(self):
        with self.cond:
            self.closing = True
            self.cond.notify_all()


class LedOutput:
    def __init__(self, cfg, dry_run=False):
        self.led, self.last = None, None
        if dry_run or not cfg.get('rgb_pins'):
            return
        from gpiozero import RGBLED
        self.led = RGBLED(*cfg['rgb_pins'], active_high=cfg.get('rgb_active_high', True),
                          initial_value=(0, 0, 0), pwm=False)

    def set(self, color):
        if self.last == color:   # 바뀔 때만 핀을 건드림
            return
        if self.led is not None:
            self.led.value = color
        else:
            log.info('Outputs LED=%s', color)
        self.last = color

    def close(self):
        if self.led is not None:
            try:
                self.led.off()
            finally:
                self.led.close()


class BuzzerOutput:
    def __init__(self, cfg, dry_run=False):
        self.buzzer, self.last = None, None
        self.passive = cfg.get('buzzer_type', 'active') == 'passive'
        self.tone = cfg.get('tone_hz', 880)
        if dry_run or cfg.get('buzzer_pin') is None:
            return
        from gpiozero import Buzzer, TonalBuzzer
        if self.passive:
            self.buzzer = TonalBuzzer(cfg['buzzer_pin'])
        else:
            self.buzzer = Buzzer(cfg['buzzer_pin'], active_high=cfg.get('buzzer_active_high', True), initial_value=False)

    def set(self, on):
        if self.last == on:
            return
        if self.buzzer is not None:
            if self.passive:
                self.buzzer.play(self.tone) if on else self.buzzer.stop()
            else:
                self.buzzer.on() if on else self.buzzer.off()
        else:
            log.info('Outputs buzzer=%s', on)
        self.last = on

    def close(self):
        if self.buzzer is not None:
            try:
                self.buzzer.stop() if self.passive else self.buzzer.off()
            finally:
                self.buzzer.close()


class LedWorker(threading.Thread):
    """LED만 맡는 쓰레드. 상태가 바뀔 때와 경고 깜빡임 박자(0.5초)에만 깨어남"""
    def __init__(self, board, led):
        super().__init__(daemon=True, name='led')
        self.board, self.led = board, led

    def run(self):
        version, timeout = -1, None
        while True:
            version, status, changed_at, closing = self.board.wait_change(version, timeout)
            if closing:
                break
            elapsed = time.monotonic() - changed_at
            color, _ = output_pattern(status, elapsed)
            try:
                self.led.set(color)
            except Exception as e:
                log.warning('LED error: %s', e)
            # 경고일 때만 다음 깜빡임 시각까지 잠듦, 나머지는 상태가 바뀔 때까지 계속 잠듦
            timeout = BLINK_SEC - elapsed % BLINK_SEC + .005 if status == '경고' else None
        self.led.set((0, 0, 0))


class BuzzerWorker(threading.Thread):
    """부저만 맡는 쓰레드. 상태가 바뀔 때만 깨어나 켜고 끔 (LED와 서로 기다리지 않음)"""
    def __init__(self, board, buzzer):
        super().__init__(daemon=True, name='buzzer')
        self.board, self.buzzer = board, buzzer

    def run(self):
        version = -1
        while True:
            version, status, _, closing = self.board.wait_change(version)
            if closing:
                break
            _, on = output_pattern(status, 0)
            try:
                self.buzzer.set(on)
            except Exception as e:
                log.warning('Buzzer error: %s', e)
        self.buzzer.set(False)


class StatusPoller:
    """Network requests cannot delay buzzer off transitions.
    서버에 상태를 물어보는 일만 하는 쓰레드. 상태가 바뀔 때만 게시판에 알림"""
    def __init__(self, cfg, stop, board):
        self.cfg, self.stop, self.board = cfg, stop, board
        self.lock = threading.Lock()
        self.received = -float('inf')
        self.thread = threading.Thread(target=self.run, daemon=True, name='poller')

    def age(self):
        """마지막으로 응답을 처리한 뒤 지난 시간(초)"""
        with self.lock:
            return time.monotonic() - self.received

    def run(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while not self.stop.is_set():
            status = None
            try:
                req = urllib.request.Request(self.cfg['status_url'], headers={'Cache-Control': 'no-cache'})
                with opener.open(req, timeout=self.cfg.get('request_timeout', 1)) as response:
                    data = json.loads(response.read(8193))
                if data.get('online') is True and data.get('status') in ('정상', '경고', '위험'):
                    status = data['status']
            except (OSError, ValueError, TypeError, AttributeError):
                pass
            with self.lock:
                self.received = time.monotonic()
            self.board.publish(status)
            self.stop.wait(self.cfg.get('poll_interval', .25))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(Path(__file__).with_name('sensor_config.json')))
    parser.add_argument('--dry-run', action='store_true', help='Log outputs without touching GPIO')
    args = parser.parse_args()
    cfg = read_config(args.config)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    led = buzzer = None
    try:
        led = LedOutput(cfg, args.dry_run)
        buzzer = BuzzerOutput(cfg, args.dry_run)
        board = StatusBoard()
        workers = [LedWorker(board, led), BuzzerWorker(board, buzzer)]
        poller = StatusPoller(cfg, stop, board)
        for t in workers:
            t.start()
        poller.thread.start()
        while not stop.wait(WATCH_SEC):
            if poller.age() > STALE_SEC:   # Also turn off when the polling thread stalls.
                board.publish(None)
        board.close()
        for t in workers:
            t.join(timeout=2)
        poller.thread.join(timeout=2)
    finally:
        stop.set()
        for device in (buzzer, led):
            if device is not None:
                device.close()


if __name__ == '__main__':
    main()
