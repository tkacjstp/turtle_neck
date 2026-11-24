"""Run on Raspberry Pi alongside app.py. BCM numbering; GPIO imported lazily."""
import argparse
import json
import logging
from pathlib import Path
import signal
import threading
import time
import urllib.request

log = logging.getLogger(__name__)


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


class Outputs:
    def __init__(self, cfg, dry_run=False, threaded_buzzer=False):
        self.led = self.buzzer = None
        self.buzzer_thread = None
        self.buzzer_condition = threading.Condition()
        self.buzzer_requested = False
        self.closing = False
        self.passive = cfg.get('buzzer_type', 'active') == 'passive'
        self.tone = cfg.get('tone_hz', 880)
        self.last = None
        if dry_run:
            return
        from gpiozero import RGBLED, Buzzer, PWMOutputDevice
        try:
            if cfg.get('rgb_pins'):
                self.led = RGBLED(*cfg['rgb_pins'], active_high=cfg.get('rgb_active_high', True),
                                  initial_value=(0, 0, 0), pwm=False)
            if cfg.get('buzzer_pin') is not None:
                if self.passive:
                    self.buzzer = PWMOutputDevice(
                        cfg['buzzer_pin'], active_high=cfg.get('buzzer_active_high', True),
                        initial_value=0, frequency=self.tone)
                else:
                    self.buzzer = Buzzer(cfg['buzzer_pin'], active_high=cfg.get('buzzer_active_high', True), initial_value=False)
        except Exception:
            self.close()
            raise
        if threaded_buzzer and self.buzzer is not None:
            self.buzzer_thread = threading.Thread(target=self.run_buzzer, name='posture-buzzer')
            self.buzzer_thread.start()

    def drive_buzzer(self, enabled):
        if self.passive:
            self.buzzer.value = 0.5 if enabled else 0
        else:
            self.buzzer.on() if enabled else self.buzzer.off()

    def run_buzzer(self):
        applied = False
        while True:
            with self.buzzer_condition:
                self.buzzer_condition.wait_for(
                    lambda: self.closing or self.buzzer_requested != applied)
                if self.closing:
                    return
                applied = self.buzzer_requested
            try:
                self.drive_buzzer(applied)
            except Exception:
                log.exception('Buzzer output failed')

    def set(self, led, buzzer):
        if self.last == (led, buzzer):
            return
        if self.led is not None:
            self.led.value = led
        if self.buzzer is not None and (self.last is None or self.last[1] != buzzer):
            if self.buzzer_thread is None:
                self.drive_buzzer(buzzer)
            else:
                with self.buzzer_condition:
                    self.buzzer_requested = buzzer
                    self.buzzer_condition.notify()
        if self.led is None and self.buzzer is None:
            log.info('Outputs LED=%s buzzer=%s', led, buzzer)
        self.last = (led, buzzer)

    def close(self):
        if self.buzzer_thread is not None:
            with self.buzzer_condition:
                self.closing = True
                self.buzzer_condition.notify()
            self.buzzer_thread.join()
        for device in (self.buzzer, self.led):
            if device is not None:
                try:
                    if hasattr(device, 'stop'):
                        device.stop()
                    else:
                        device.off()
                finally:
                    device.close()


class StatusPoller:
    """Network requests cannot delay buzzer off transitions."""
    def __init__(self, cfg, stop):
        self.cfg, self.stop = cfg, stop
        self.lock = threading.Lock()
        self.status, self.received = None, -float('inf')
        self.thread = threading.Thread(target=self.run, daemon=True)

    def current(self):
        with self.lock:
            # Also turn off when the polling thread stalls.
            return self.status if time.monotonic() - self.received < 2 else None

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
                self.status, self.received = status, time.monotonic()
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
    outputs = Outputs(cfg, args.dry_run, threaded_buzzer=True)
    poller = StatusPoller(cfg, stop)
    previous, changed = None, time.monotonic()
    try:
        poller.thread.start()
        while not stop.is_set():
            status = poller.current()
            now = time.monotonic()
            if status != previous:
                log.info('Posture: %s', status or 'offline')
                previous, changed = status, now
            outputs.set(*output_pattern(status, now - changed))
            stop.wait(.02)
    finally:
        stop.set()
        outputs.close()
        poller.thread.join(timeout=2)


if __name__ == '__main__':
    main()
