r"""
========================================================================
 라즈베리파이 알림·센서 (rpi_device.py)
========================================================================

[이 프로그램이 하는 일]
  1) 알림: 노트북 서버(app.py)의 /api/status를 0.3초마다 확인해서
           경고/위험이면 LED·부저를 켬 (상태가 바뀌고 0.5초 안에 반응)
  2) 센서: read_sensors()로 센서값을 읽어 SENSOR_SEC초마다 서버 /api/sensor로 보냄

  [노트북] 카메라 -> posture.py -> app.py(서버) <-> rpi_device.py [라즈베리파이]

[필요 환경]  라즈베리파이 OS 기본 python3 + gpiozero (기본 설치됨). mediapipe 필요 없음

[실행]  python3 rpi_device.py      종료: Ctrl+C
  노트북 없이 시험(가짜 GPIO): GPIOZERO_PIN_FACTORY=mock python3 rpi_device.py

[체크리스트]
  □ 아래 SERVER를 노트북 IP로 바꿨는가? (노트북에서: ipconfig getifaddr en0)
  □ 노트북 서버(app.py)와 판별기(posture.py)가 켜져 있는가?
  □ 라즈베리파이에서 브라우저나 curl로 http://노트북IP:5050 이 열리는가?
  □ 핀 번호(BCM 번호)가 실제 배선과 같은가?

[동작]
  정상 : 모두 꺼짐
  경고 : LED 켜짐
  위험 : LED 깜빡임 + 부저 삐- 삐-
  (진동 모터를 달면 VIBRATION_PIN에 핀 번호를 넣으면 상태가 바뀔 때 짧게 한 번 울림)
  서버 연결이 끊기거나, 판별기가 STALE_SEC초 넘게 소식이 없으면 모두 끔
"""
import json
import time
import logging
import urllib.request
from datetime import datetime
from collections import deque

# ======================== 설정 ========================
SERVER = "http://노트북IP:5050"   # ← 노트북 IP로 바꾸기
POLL_SEC = 0.3      # 상태 확인 주기 (1초 안에 반응하려면 0.5 이하)
SENSOR_SEC = 5      # 센서값 전송 주기
STALE_SEC = 15      # 판별기 소식이 이 시간 넘게 없으면 알림 끔
LED_PIN, BUZZER_PIN, VIBRATION_PIN = 17, 27, None   # BCM 번호. 없는 장치는 None (진동 모터 미사용)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rpi")


def read_sensors():
    """센서 담당이 채우는 곳. {"이름": 숫자} 를 돌려주면 서버에 저장됨. 읽을 게 없으면 {}
    예) 초음파 거리센서:  from gpiozero import DistanceSensor
                         sensor = DistanceSensor(echo=24, trigger=23)  (파일 위쪽에서 한 번만 만들 것)
                         return {"distance_cm": sensor.distance * 100}"""
    return {}


# ======================== 서버 통신 ========================
def http(method, path, body=None):
    req = urllib.request.Request(
        SERVER + path, method=method, headers={"Content-Type": "application/json"},
        data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None)
    with urllib.request.urlopen(req, timeout=1) as res:
        return json.load(res)


def get_status():
    """서버의 지금 상태. 연결이 안 되거나 판별기 소식이 오래 없으면 '정상'(알림 끔)"""
    try:
        r = http("GET", "/api/status")
    except Exception as e:
        log.warning(f"서버 연결 실패: {e}")
        return "정상"
    if r.get("age") is None or r["age"] > STALE_SEC:
        return "정상"
    return r["status"]


pending = deque(maxlen=1000)   # 서버가 꺼져 있을 때 센서값 보관


def send_sensors():
    values = read_sensors()
    if values:
        pending.append({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "values": values})
    while pending:
        try:
            http("POST", "/api/sensor", pending[0])
        except Exception as e:
            log.warning(f"센서값 전송 실패, 보관 중 {len(pending)}개: {e}")
            return
        pending.popleft()


# ======================== 알림 출력 ========================
def make_devices():
    from gpiozero import LED, Buzzer, DigitalOutputDevice
    return (LED(LED_PIN) if LED_PIN is not None else None,
            Buzzer(BUZZER_PIN) if BUZZER_PIN is not None else None,
            DigitalOutputDevice(VIBRATION_PIN) if VIBRATION_PIN is not None else None)


def apply(status, led, buzzer, vib):
    """상태에 맞게 LED·부저·진동 켜고 끄기"""
    for d in (led, buzzer, vib):
        if d:
            d.off()
    if status == "정상":
        return
    if vib:
        vib.blink(on_time=0.4, n=1)            # 진동 짧게 한 번
    if status == "경고":
        if led:
            led.on()
    else:   # 위험
        if led:
            led.blink(on_time=0.3, off_time=0.3)
        if buzzer:
            buzzer.beep(on_time=0.2, off_time=0.8)


def main():
    if "노트북IP" in SERVER:
        log.error("rpi_device.py 위쪽의 SERVER를 노트북 IP로 바꾸세요")
        return
    devices = make_devices()
    log.info(f"시작: {SERVER}")
    shown, last_sensor = None, 0.0
    try:
        while True:
            status = get_status()
            if status != shown:
                log.info(f"알림: {shown} -> {status}")
                apply(status, *devices)
                shown = status
            if time.time() - last_sensor >= SENSOR_SEC:
                send_sensors()
                last_sensor = time.time()
            time.sleep(POLL_SEC)
    except KeyboardInterrupt:
        log.info("종료")
    finally:
        apply("정상", *devices)


if __name__ == "__main__":
    main()
