r"""
========================================================================
 DB 전달기 (forward.py)
========================================================================

[이 프로그램이 하는 일]
  이 서버(app.py)의 turtle_neck.db에 저장된 측정 결과를
  다른 서버(FORWARD_URL)로 보낸다. 이미 보낸 데이터는 다시 보내지 않는다.

  posture.py -> app.py -> turtle_neck.db -> forward.py -> 다른 서버

[실행]  app.py와 같은 폴더에서, app.py와 따로 창을 하나 더 열어서 실행
  윈도우: venv\Scripts\python forward.py      맥/라즈베리파이: python forward.py
  한 번만 보내고 끝내기: 뒤에 --once  (예: python forward.py --once)
  종료: Ctrl+C

[체크리스트]
  □ 아래 FORWARD_URL을 받는 서버 주소로 바꿨는가?
  □ 받는 서버가 켜져 있고, 이 컴퓨터에서 브라우저로 접속되는가?
  □ 받는 서버가 app.py의 /api/record와 같은 JSON 형식을 받는가?
      {"user_id", "timestamp", "worse_pct", "status", "shoulder_status",
       "shoulder_tilt", "bad_duration", "angle"}
    형식이 다르면 make_payload() 안의 이름만 바꾸면 됨

[주의사항]
  - 어디까지 보냈는지는 forward_state.json에 저장됨 (자동 생성)
    -> 처음부터 전부 다시 보내고 싶으면 이 파일을 삭제
  - 받는 서버가 꺼져 있으면 보내지 않고 기다렸다가, 켜지면 밀린 것부터 순서대로 보냄
  - 받는 서버가 데이터를 거부(4xx 오류)하면 그 데이터에서 멈추고 오류를 남김
    -> 형식 문제이므로 make_payload()를 고쳐야 함
  - turtle_neck.db를 지웠다면 forward_state.json도 같이 지울 것
    (안 지우면 새로 쌓인 데이터를 이미 보낸 것으로 착각함)

[필요 환경]  Python 3.9 이상, 추가 설치 없음 (기본 모듈만 사용)
"""
import os
import sys
import json
import time
import sqlite3
import logging
import urllib.request
import urllib.error

# ======================== 설정 ========================
FORWARD_URL = "http://받는서버IP:5050/api/record"   # ← 받는 서버 주소로 바꾸기
INTERVAL = 10       # 몇 초마다 새 데이터를 확인할지
BATCH = 200         # 한 번에 최대 몇 개 보낼지

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "turtle_neck.db")
STATE_FILE = os.path.join(BASE_DIR, "forward_state.json")   # 마지막으로 보낸 id

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("forward")


def load_last_id():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)["last_id"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return 0


def save_last_id(last_id):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"last_id": last_id}, f)
    os.replace(tmp, STATE_FILE)   # 저장 중 꺼져도 파일이 깨지지 않게


def make_payload(row):
    """DB 한 줄 -> 받는 서버로 보낼 JSON. 받는 서버 형식이 다르면 여기만 고치기"""
    keys = ["user_id", "timestamp", "worse_pct", "status", "shoulder_status",
            "shoulder_tilt", "bad_duration", "angle"]
    return {k: row[k] for k in keys if k in row.keys()}


def forward_once():
    """아직 안 보낸 데이터를 보냄. 보낸 개수를 돌려줌"""
    if not os.path.exists(DB_FILE):
        log.warning("turtle_neck.db 없음 (app.py를 먼저 실행해서 데이터를 받아야 함)")
        return 0
    last_id = load_last_id()
    conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)   # 읽기 전용
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM measurements WHERE id > ? ORDER BY id LIMIT ?",
                            (last_id, BATCH)).fetchall()
    finally:
        conn.close()

    sent = 0
    for row in rows:
        req = urllib.request.Request(
            FORWARD_URL, data=json.dumps(make_payload(row), ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=3).close()
        except urllib.error.HTTPError as e:
            log.error(f"받는 서버가 거부함 (id={row['id']}, {e.code}): 형식 확인 필요 -> make_payload()")
            break
        except Exception as e:
            log.warning(f"전송 실패, {INTERVAL}초 후 다시 시도: {e}")
            break
        save_last_id(row["id"])   # 한 개 보낼 때마다 기록 -> 중간에 꺼져도 중복 전송 없음
        sent += 1
    if sent:
        log.info(f"{sent}개 전송 완료 (마지막 id={load_last_id()})")
    return sent


def main():
    if "받는서버IP" in FORWARD_URL:
        log.error("forward.py 위쪽의 FORWARD_URL을 받는 서버 주소로 바꾸세요")
        return
    log.info(f"전달 시작: {DB_FILE} -> {FORWARD_URL}")
    if "--once" in sys.argv:
        while forward_once() == BATCH:   # 밀린 게 많으면 다 보낼 때까지
            pass
        return
    try:
        while True:
            if forward_once() < BATCH:   # 다 보냈으면 잠깐 쉬고, 밀려 있으면 바로 이어서
                time.sleep(INTERVAL)
    except KeyboardInterrupt:
        log.info("종료")


if __name__ == "__main__":
    main()
