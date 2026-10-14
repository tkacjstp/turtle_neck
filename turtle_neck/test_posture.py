"""
python3 test_posture.py  (flask 필요, 카메라/mediapipe 불필요)

[필요 환경]
  Python : 3.9 ~ 3.12 (3.11 권장, posture.py와 같은 버전)
  flask  : 버전 제한 없음
  ※ 카메라 없이 계산·서버 부분만 테스트하므로 mediapipe·OpenCV는 없어도 됨
"""
import os, json, threading, tempfile, urllib.request
import app, posture
posture.LOCAL_DB = os.path.join(tempfile.mkdtemp(), "posture_data.db")
from werkzeug.serving import make_server

cfg = {"warning_pct": 10, "danger_pct": 20}
base = {"forward": 0.25, "height": 0.60, "tilt": 1.0}
assert posture.worse_pct({"forward": 0.25, "height": 0.60}, base) == 0
assert round(posture.worse_pct({"forward": 0.2875, "height": 0.60}, base)) == 15   # 머리가 앞으로 15%
assert round(posture.worse_pct({"forward": 0.25, "height": 0.48}, base)) == 20     # 머리가 20% 내려감
assert posture.worse_pct({"forward": 0.22, "height": 0.66}, base) == 0             # 뒤로 기대면 정상
assert posture.raw_status(15, cfg) == "경고" and posture.raw_status(25, cfg) == "위험"
assert posture.raw_status(9, cfg, prev="경고") == "경고"    # 경계 근처에서 깜빡이지 않음
assert posture.raw_status(7, cfg, prev="경고") == "정상"

# 카메라 거리 보정: 같은 비율 변화라도 카메라가 멀수록 % 큼 (60cm 기준 환산)
b60 = {**base, "dist": 60.0}
assert round(posture.worse_pct({"forward": 0.275, "height": 0.60, "dist": 60 / 1.1}, b60)) == 10
assert round(posture.worse_pct({"forward": 0.275, "height": 0.60, "dist": 30 / 1.1},
                               {**b60, "dist": 30.0})) == 5
# 몸통만 돌림: 어깨만 좁아져 forward가 커져도 눈 거리(dist)가 그대로면 정상
assert posture.worse_pct({"forward": 0.30, "height": 0.60, "dist": 60.0}, b60) == 0

# 지표 계산: 다른 사람 얼굴이 잡히면 무시, 정상이면 dist 추정
P = lambda x, y, v=1.0: type("P", (), {"x": x, "y": y, "visibility": v})()
pose = [P(0, 0)] * 33
pose[11], pose[12] = P(0.7, 0.8), P(0.3, 0.8)
face = [P(0, 0)] * 468
face[33], face[263], face[1] = P(0.45, 0.4), P(0.55, 0.4), P(0.5, 0.45)
m, why = posture.get_metrics(pose, face, 640, 480, fov_deg=65)
assert why is None and 60 < m["dist"] < 80 and round(m["forward"], 2) == 0.25
face[1] = P(0.9, 0.45)   # 코가 어깨 밖 -> 다른 사람
assert posture.get_metrics(pose, face, 640, 480)[1] == "ONE PERSON ONLY"

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
