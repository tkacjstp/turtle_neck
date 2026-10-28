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

import math, random
import numpy as np
cv2 = None
try:
    import cv2
except ImportError:
    pass

# 판정: 경고 50%, 위험 80%, 경고에 들어간 뒤에는 5% 낮은 곳에서 해제 (깜빡임 방지)
cfg = {"warning_pct": 50, "danger_pct": 80}
assert posture.raw_status(60, cfg) == "경고" and posture.raw_status(90, cfg) == "위험"
assert posture.raw_status(47, cfg, prev="경고") == "경고"
assert posture.raw_status(44, cfg, prev="경고") == "정상"

# 개인 맞춤 학습(LDA): 바른 자세 0%, 거북목 100%, 흔들림만 큰 값(높이)은 점수에 거의 영향 없음
random.seed(1)
feat = lambda pitch, dist, y: {"face": [pitch, math.log(dist), y], "shoulder": None, "tilt": None}
good = [feat(random.gauss(0, 1), random.gauss(60, 0.5), random.gauss(0, 0.05)) for _ in range(60)]
bad = [feat(random.gauss(20, 1), random.gauss(55, 0.5), random.gauss(0, 0.05)) for _ in range(60)]
model, sep = posture.train(good, bad)
assert model["version"] == posture.MODEL_VERSION and sep > posture.MIN_SEPARATION
assert abs(posture.posture_score(model, feat(0, 60, 0))) < 15
assert 85 < posture.posture_score(model, feat(20, 55, 0)) < 115
assert abs(posture.posture_score(model, feat(0, 60, 0.1))) < 15      # 높이만 흔들림 -> 무시
assert posture.train(good, good)[1] < posture.MIN_SEPARATION          # 두 자세가 같으면 학습 실패

# 어깨: 팔꿈치·손목이 어깨 위로 올라가거나, 어깨가 화면 아래 끝이면 믿지 않음
P = lambda x, y, v=1.0: type("P", (), {"x": x, "y": y, "visibility": v})()
pose = [P(0.5, 0.95, 0.2)] * 33
pose[11], pose[12] = P(0.7, 0.8), P(0.3, 0.8)
pose[13], pose[14] = P(0.75, 0.95), P(0.25, 0.95)   # 팔꿈치는 어깨 아래 (타자 치는 자세)
assert posture.shoulders_ok(pose)
pose[15] = P(0.6, 0.5)                                 # 손을 머리 위로 듦
assert not posture.shoulders_ok(pose)
pose[15] = P(0.6, 0.95, 0.2)
pose[11] = P(0.7, 0.97)                                # 어깨가 화면 아래 끝
assert not posture.shoulders_ok(pose)
pose[11] = P(0.7, 0.8)

# 머리 자세(solvePnP, OpenCV가 있을 때만): 알고 있는 거리·각도로 얼굴을 그려서 그대로 되찾는지
if cv2 is not None:
    def fake_face(z, pitch, w=640, h=480):
        f, a = (w / 2) / math.tan(math.radians(65) / 2), math.radians(pitch)
        R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        lm = [P(0.5, 0.5)] * 468
        for i, pt in zip(posture.FACE_IDX, posture.FACE_3D):
            c = R @ pt + (0, 0, z)
            lm[i] = P((f * c[0] / c[2] + w / 2) / w, (f * c[1] / c[2] + h / 2) / h)
        return lm
    hp = posture.head_pose(cv2, fake_face(55, 20), 640, 480, 65)
    assert round(hp["dist"]) == 55 and round(hp["pitch"]) == 20 and abs(hp["yaw"]) < 1
    feats, why = posture.get_features(cv2, pose, fake_face(60, 0), 640, 480)
    assert why is None and feats["shoulder"] is not None              # 어깨 사용
    pose[16] = P(0.4, 0.5)                                            # 팔을 듦 -> 얼굴만
    assert posture.get_features(cv2, pose, fake_face(60, 0), 640, 480)[0]["shoulder"] is None
    pose[16] = P(0.5, 0.95, 0.2)
    assert posture.get_features(cv2, pose, fake_face(60, 0), 640, 480, use_shoulders=False)[0]["shoulder"] is None

# 지속시간: hold_sec 미만이면 정상, 이상이면 확정, 정상 들어오면 리셋
s, since, d = posture.hold("위험", None, 1, now=100)
assert (s, since) == ("정상", 100)
s, since, d = posture.hold("위험", since, 1, now=101.5)
assert (s, d) == ("위험", 1.5)
assert posture.hold("정상", since, 1, now=102) == ("정상", None, 0.0)

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
