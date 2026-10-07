"""
python3 test_posture.py  (flask 필요, 카메라/mediapipe 불필요)

[필요 환경]
  Python : 3.9 ~ 3.12 (3.11 권장, posture.py와 같은 버전)
  flask  : 버전 제한 없음
  ※ 카메라 없이 계산·서버 부분만 테스트하므로 mediapipe·OpenCV는 없어도 됨
"""
import os, json, threading, tempfile, urllib.request
import app, posture
from werkzeug.serving import make_server

cfg = {"warning_pct": 10, "danger_pct": 20}
base = {"neck": 1.0, "mouth": 0.5, "face": 0.4}
assert posture.worse_pct({"neck": 1.0, "mouth": 0.5, "face": 0.4}, base) == 0
assert round(posture.worse_pct({"neck": 0.85, "mouth": 0.5, "face": 0.4}, base)) == 15
assert posture.raw_status(15, cfg) == "경고" and posture.raw_status(25, cfg) == "위험"

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
assert len(posture.pending) == 1
threading.Thread(target=srv.serve_forever, daemon=True).start()
posture.send(rec, url + "/api/record")
assert not posture.pending
rows = json.load(urllib.request.urlopen(url + "/api/results"))
assert len(rows) == 2 and rows[0]["angle"] == 15.0 and rows[0]["status"] == "경고"
stats = json.load(urllib.request.urlopen(url + "/api/stats?date=2026-10-07"))
assert stats["counts"]["경고"] == 2
assert "악화율" in urllib.request.urlopen(url + "/").read().decode()
srv.shutdown()
print("OK")
