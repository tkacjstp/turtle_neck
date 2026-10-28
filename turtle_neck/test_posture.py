"""
python3 test_posture.py  (flask 필요, 카메라/mediapipe 불필요)

[필요 환경]
  Python : 3.9 ~ 3.12 (3.11 권장, posture.py와 같은 버전)
  flask  : 버전 제한 없음
  ※ 카메라 없이 계산·서버 부분만 테스트. numpy 필요 (mediapipe 설치 시 함께 설치됨)
"""
import os, json, threading, tempfile, urllib.request
import app, posture
posture.LOCAL_DB = os.path.join(tempfile.mkdtemp(), "posture_data.db")
from werkzeug.serving import make_server

import random
cfg = {"warning_pct": 50, "danger_pct": 80}
assert posture.raw_status(60, cfg) == "경고" and posture.raw_status(90, cfg) == "위험"
assert posture.raw_status(47, cfg, prev="경고") == "경고"    # 경계 근처에서 깜빡이지 않음
assert posture.raw_status(44, cfg, prev="경고") == "정상"

# 개인 맞춤 학습(LDA): 바른 자세 0점, 나쁜 자세 100점, 흔들림만 큰 값은 무시
random.seed(0)
f = lambda pitch, dist, y: {"face": [pitch + random.gauss(0, 1), dist + random.gauss(0, .01), y + random.gauss(0, .005)],
                            "shoulder": None, "tilt": None}
good = [f(0, 6.0, 0.00) for _ in range(40)]
bad = [f(3, 5.9, 0.04) for _ in range(40)]        # 나쁜 자세: 머리가 가까워지고(dist↓) 내려감(y↑)
model, sep = posture.train(good, bad)
assert sep > posture.MIN_SEPARATION
assert abs(posture.score(model["face"], [0, 6.0, 0.00])) < 10
assert abs(posture.score(model["face"], [3, 5.9, 0.04]) - 100) < 10
assert posture.train(good, [f(0, 6.0, 0.00) for _ in range(40)])[1] < posture.MIN_SEPARATION   # 차이 없으면 실패

# 지속시간: 10초 미만이면 정상, 이상이면 확정, 정상 들어오면 리셋
s, since, d = posture.hold("위험", None, 10, now=100)
assert (s, since) == ("정상", 100)
s, since, d = posture.hold("위험", since, 10, now=111)
assert (s, d) == ("위험", 11)
assert posture.hold("정상", since, 10, now=112) == ("정상", None, 0.0)

# 서버 연동: 꺼져 있으면 보관, 켜지면 밀린 것까지 전송
app.DB_FILE = os.path.join(tempfile.mkdtemp(), "t.db"); app.init_db()
srv = make_server("127.0.0.1", 0, app.app)
url = f"http://127.0.0.1:{srv.port}"
rec = {"user_id": "u", "timestamp": "2026-10-07 10:00:00", "worse_pct": 15.0,
       "status": "경고", "shoulder_status": "정상", "shoulder_tilt": 1.0, "bad_duration": 12.0}
posture.send(rec, "http://127.0.0.1:1/api/record")
assert posture.unsent_count() == 1
threading.Thread(target=srv.serve_forever, daemon=True).start()
posture.send(rec, url + "/api/record")
assert posture.unsent_count() == 0
rows = json.load(urllib.request.urlopen(url + "/api/results"))
assert len(rows) == 2 and rows[0]["angle"] == 15.0 and rows[0]["status"] == "경고"
stats = json.load(urllib.request.urlopen(url + "/api/stats?date=2026-10-07"))
assert stats["counts"]["경고"] == 2
assert "악화율" in urllib.request.urlopen(url + "/").read().decode()

# 라즈베리파이 연동: 판별기 상태 알림 -> RPi가 가져감, RPi 센서값 저장
import time
import rpi_device
rpi_device.SERVER = url
assert rpi_device.get_status() == "정상"            # 판별기 소식이 아직 없으면 알림 끔
posture.STATUS_URL = url + "/api/status"
posture.post_status("위험")
time.sleep(0.3)
assert rpi_device.get_status() == "위험"
rpi_device.read_sensors = lambda: {"distance_cm": 42.5}
rpi_device.send_sensors()
assert json.load(urllib.request.urlopen(url + "/api/sensor"))[0]["value"] == 42.5
srv.shutdown()
rpi_device.SERVER = "http://127.0.0.1:1"
assert rpi_device.get_status() == "정상"            # 서버가 꺼지면 알림 끔
try:   # GPIO 출력 (gpiozero가 있을 때만, 가짜 핀으로 확인)
    os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
    led, buzzer, vib = rpi_device.make_devices()
except ImportError:
    pass
else:
    rpi_device.apply("경고", led, buzzer, vib)
    assert led.is_lit and not buzzer.is_active
    rpi_device.apply("정상", led, buzzer, vib)
    assert not led.is_lit
print("OK")
