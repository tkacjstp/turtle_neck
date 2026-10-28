r"""
========================================================================
 거북목 판별기 (posture.py)   담당: 임진혁 - 로직 / 각도·자세 계산
========================================================================

[이 프로그램이 하는 일]
  웹캠으로 사람을 찍어서 귀·어깨 위치를 찾고,
  처음에 잡은 "바른 자세"보다 얼마나 나빠졌는지(%) 계산해서
  정상 / 경고 / 위험을 판정한 뒤 서버(app.py)로 보낸다.

  웹캠 -> 귀·어깨 찾기 -> 바른 자세와 비교 -> 나빠진 상태가 경고 5초·위험 3초 이상 계속되면 확정
       -> 5초마다 서버로 전송 -> 웹 페이지(http://서버IP:5050)에서 결과 확인


[판별 방식]  노트북·모니터 위 웹캠처럼 "정면" 카메라용
  - 어깨는 Pose(몸 33점), 눈·코는 Face Mesh(얼굴 468점)로 찾음
    -> 예전처럼 귀 위치(흔들림 큼) 대신 훨씬 정밀한 눈 위치를 사용
  - 머리가 앞으로 나옴 : 카메라에 가까운 물체는 크게 보이는 원리 이용
                         "눈 사이 거리 / 어깨 너비"가 커지면 머리만 앞으로 나온 것
                         (몸 전체가 다가오거나 뒤로 기대면 둘 다 같이 변해서 값이 그대로)
  - 머리가 내려감      : "어깨선~눈 높이 / 어깨 너비"가 작아지면 목을 빼고 숙이거나 구부정한 것
  - 두 값 중 기준자세보다 더 많이 나빠진 쪽(%)으로 판정 + 어깨 기울기는 따로 판정

  정확도를 위한 처리
  - 최근 2초(smooth_sec)의 "중간값" 사용 -> 순간적으로 튀는 값 무시
  - 경고에 들어간 뒤에는 기준을 2%(hysteresis_pct) 낮춰서 경계에서 깜빡이지 않게 함
  - 기준자세 측정 중 많이 움직이면 처음부터 다시 측정
  - 고개를 옆으로 돌린 순간은 판정에서 제외 (잠깐이면 상태 유지)
  - 카메라 거리를 눈 사이 거리로 추정해서, 카메라가 가깝든 멀든 같은 기준(60cm 기준 %)으로 판정
  - 몸통만 돌려 어깨가 좁아 보이는 것은 머리가 나온 것으로 치지 않음 (눈이 실제로 가까워진 만큼만 인정)
  - 화면에 다른 사람 얼굴이 잡히면 무시 (어깨 사이에 있는 얼굴만 사용)

  효율을 위한 처리
  - 자세는 천천히 변하므로 분석은 초당 10번(analysis_fps)만, 화면은 계속 갱신 -> CPU 사용량 감소


[필요 환경]  ※ 버전이 다르면 설치가 안 되거나 실행 중 오류가 남
  Python    : 3.9 ~ 3.12 (3.11 권장)
              - mediapipe 0.10.18이 3.9~3.12만 지원. 3.13 이상, 3.8 이하는 설치 불가
              - 라즈베리파이 OS Bookworm은 기본이 3.11이라 그대로 사용 가능
              - 3.13 이상이면 3.11을 따로 설치해서 가상환경을 만들 것
              - 버전 확인: python3 --version (윈도우는 py --version)
  mediapipe : 0.10.18 (조원 모두 이 버전으로 통일)
              - 이 코드는 예전 방식인 mp.solutions.pose 를 사용함
              - mp.solutions 는 0.10.30 이상(최신 1.x 포함)에서 삭제됨
                -> 버전 지정 없이 설치하면 "has no attribute 'solutions'" 오류로 실행 안 됨
              - 0.10.20, 0.10.21은 라즈베리파이(ARM 64비트)용 설치 파일이 없음
                -> 라즈베리파이에서도 설치되는 마지막 버전이 0.10.18
  OpenCV    : mediapipe 설치 시 opencv-contrib-python 이 함께 설치됨 (따로 설치 불필요)
              - opencv-python 을 따로 설치하면 OpenCV가 두 개라 충돌할 수 있음
              - opencv-python-headless 가 설치돼 있으면 카메라 창이 안 뜸 -> 삭제할 것
  numpy     : mediapipe 설치 시 1.x 버전이 함께 설치됨 (numpy 2.x 와 호환 안 됨)
  기기      : 웹캠 필수 (데스크톱 PC는 USB 웹캠을 꽂아야 함)
              라즈베리파이는 64비트 OS 필요


[설치]  처음 한 번만. turtle_neck 폴더 안에서 실행
  윈도우 (명령 프롬프트 cmd 사용, PowerShell 말고)
      py -3.11 -m venv venv
      venv\Scripts\python -m pip install flask mediapipe==0.10.18
  맥 / 라즈베리파이
      python3.11 -m venv venv
      source venv/bin/activate
      pip install flask mediapipe==0.10.18
  설치 확인: 테스트 실행 후 마지막에 OK가 나오면 성공
      윈도우: venv\Scripts\python test_posture.py     맥/라즈베리파이: python test_posture.py


[실행 전 체크리스트]  하나라도 안 되면 제대로 동작하지 않음
  □ 서버(app.py)를 먼저 켰는가?  (판별기보다 먼저, 창을 닫지 말고 켜 둘 것)
  □ config.json의 server_url이 맞는가?
      - 내 컴퓨터 하나로 테스트할 때 : "http://127.0.0.1:5050/api/record"
      - 서버가 다른 컴퓨터일 때      : "http://서버컴퓨터IP:5050/api/record"
        (두 컴퓨터가 같은 와이파이/네트워크에 있어야 함)
  □ config.json을 고칠 때 IP 숫자만 바꿨는가? (쉼표·따옴표를 건드리면 실행 안 됨)
  □ 웹캠이 연결되어 있고, 다른 프로그램(줌, 카메라 앱 등)이 쓰고 있지 않은가?
  □ 카메라가 정면에 있고, 화면에 얼굴과 양쪽 어깨가 모두 보이는가? (의자를 조금 뒤로)
  □ 얼굴이 밝게 보이는가? (뒤에 창문이 있어 역광이면 얼굴 인식이 잘 안 됨)
  □ 카메라를 옮겼거나 다른 컴퓨터로 바꿨다면 기준자세를 다시 잡았는가? (카메라 창에서 c 키)


[실행]
  윈도우: venv\Scripts\python posture.py      맥/라즈베리파이: python posture.py
  종료  : 카메라 창에서 q 키, 또는 명령 창에서 Ctrl+C
  기준자세 다시 잡기 : 카메라 창에서 c 키 (또는 baseline.json 삭제 후 재시작)

  1) 처음 실행하면 사람이 보인 뒤 5초 동안 "바른 자세"를 측정함 (화면: CALIBRATING)
     -> 이때 자세가 나쁘면 그 자세가 기준이 되어 판정이 이상해짐. 꼭 바르게 앉을 것!
     -> 측정 중 많이 움직이면 "HOLD STILL"이 뜨고 처음부터 다시 측정함
  2) 기준자세는 baseline.json에 저장되고, 다음 실행부터는 이 값을 계속 사용함
     (예전 버전의 baseline.json이면 자동으로 다시 측정)


[카메라 창 글자 뜻]  (OpenCV는 한글을 못 써서 영어로 표시)
  NO PERSON           : 사람이 안 보임
  MOVE BACK - ...     : 사람은 보이는데 어깨가 화면 밖 -> 뒤로 물러나기
  FACE NOT FOUND      : 얼굴 인식 안 됨 -> 정면 보기, 조명 확인 (마스크·손으로 가리면 안 됨)
  TURN TO CAMERA      : 고개를 옆으로 돌림 -> 정면 보기
                        ※ 위 경우들이 잠깐(3초 이내)이면 판정만 건너뛰고 상태는 유지
  CALIBRATING         : 바른 자세 측정 중 -> 5초간 바르게 앉아 있기
  HOLD STILL          : 측정 중 움직여서 다시 측정 -> 가만히 바르게 앉아 있기
  NORMAL  (초록)      : 정상
  WARNING (주황)      : 경고 - 바른 자세보다 10% 이상 나빠진 상태가 5초 이상
  DANGER  (빨강)      : 위험 - 바른 자세보다 20% 이상 나빠진 상태가 3초 이상
  ※ 숫자(%)는 바른 자세보다 얼마나 나빠졌는지. 0%에 가까울수록 좋음
  ※ 노란 점 3개 = 판정에 쓰는 양쪽 눈 끝과 코끝


[주의사항]
  - 카메라는 정면, 눈높이 근처에 둘 것. 기준자세를 잡은 뒤 카메라(노트북 화면 각도 포함)를 움직이면
    판정이 틀어지므로 c 키로 기준자세를 다시 잡을 것
  - 안경은 괜찮지만, 마스크나 손으로 얼굴을 가리면 인식이 안 됨
  - model_complexity: 1(기본)이 더 정확. 라즈베리파이가 너무 느리면 0으로 (대신 첫 실행 때 다운로드)
  - 판정이 너무 예민하거나 둔하면 config.json의 warning_pct, danger_pct, warning_hold_sec, danger_hold_sec 숫자를 조절
  - config.json을 바꾸면 프로그램을 껐다 켜야 반영됨
  - 기준자세를 다시 잡고 싶으면 baseline.json을 지우고 다시 실행
  - 모든 측정값은 판별기 쪽 posture_data.db에 먼저 저장되고, 그다음 서버 포트(server_url)로 전송됨
    서버가 꺼져 있거나 연결이 안 되면 DB에 남겨 두었다가, 연결되면 오래된 것부터 자동 전송
    (프로그램을 껐다 켜도 남아 있고, 측정 시각도 원래 시각 그대로 저장됨)
  - posture_data.db는 보낸 기록도 계속 쌓임 (하루 약 1.7만 개, 약 3MB)
    -> 정리하고 싶으면 프로그램을 끄고 삭제. 단, 아직 못 보낸 데이터도 같이 사라짐
  - 카메라 창은 모니터가 있을 때만 뜸. 라즈베리파이를 SSH로 접속하거나 부팅 시 자동 실행(systemd)하면
    창 없이 실행됨 (오류 아님). 창을 일부러 끄려면 config.json에 "show_window": false
  - 실행 기록은 posture.log 파일에 남음. 문제가 생기면 이 파일을 확인


[자주 나오는 메시지와 해결]
  "전송 실패, DB에 보관 중 N개"         -> 데이터는 posture_data.db에 안전하게 저장 중. 아래 원인 해결하면 자동 전송
  "전송 실패 ... timed out"            -> server_url의 IP가 틀렸거나, 서버와 다른 네트워크에 있음
  "전송 실패 ... Connection refused"   -> 서버(app.py)가 꺼져 있음
  "카메라 연결 실패, 5초 후 재시도"     -> 웹캠 연결 확인 / 다른 프로그램이 카메라 사용 중
                                         윈도우: 설정 > 개인 정보 > 카메라 > 데스크톱 앱 허용
  "config.json 형식 오류: N번째 줄"     -> 그 줄 근처의 쉼표, 따옴표 확인
                                         (한글 따옴표 “ ”, 마지막 줄 끝 쉼표, True 대문자 등)
  "가벼운 모델 다운로드 실패, 기본 모델로 실행" -> (model_complexity 0일 때) 인터넷이 막힌 것. 자동 해결됨
  "기준자세 측정 중 움직임 감지, 다시 측정" -> 측정하는 몇 초 동안 가만히 앉아 있기
  "has no attribute 'solutions'"       -> mediapipe 버전이 너무 최신. pip install mediapipe==0.10.18
  "DLL load failed" (윈도우)           -> Visual C++ 재배포 패키지 설치 필요 (관리자 권한 필요)
  "No module named ..."               -> 가상환경(venv)의 python으로 실행했는지 확인
"""
import os
import sys
import math
import statistics
import json
import time
import signal
import sqlite3
import threading
import logging
import logging.handlers
import urllib.request
from datetime import datetime
from collections import deque

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BASELINE_FILE = os.path.join(BASE_DIR, "baseline.json")
LOG_FILE = os.path.join(BASE_DIR, "posture.log")

VIS_MIN = 0.6        # 관절점이 이 값 이상 확실하게 보여야 사용
ABSENT_SEC = 3       # 판정할 수 없는 화면이 이만큼 이어지면 자리 비움으로 처리
EYE_W_CM = 9.0       # 양쪽 눈 바깥 끝 사이 실제 거리(성인 평균). 카메라 거리 추정용
REF_DIST_CM = 60     # warning_pct·danger_pct는 카메라가 이 거리에 있을 때 기준
LOCAL_DB = os.path.join(BASE_DIR, "posture_data.db")   # 측정 기록 저장 + 전송 대기 (자동 생성)

# 랜드마크 번호: 어깨는 Pose, 눈·코는 Face Mesh(얼굴 468점, Pose보다 훨씬 정밀)
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
EYE_OUT_1, EYE_OUT_2, NOSE_TIP = 33, 263, 1     # 양쪽 눈 바깥 끝, 코끝

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000,
                                                   backupCount=3, encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger("posture")

running = True


def stop(signum, frame):
    global running
    log.info("종료 신호 받음")
    running = False


def load_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:   # -sig: 메모장 BOM 저장도 읽음
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        log.error(f"{os.path.basename(path)} 형식 오류: {e.lineno}번째 줄 {e.colno}번째 칸 근처 ({e.msg})")
        return None


# ======================== 전송 ========================
send_lock = threading.Lock()


def _local_db():
    """판별기 쪽 DB(posture_data.db). 모든 측정값을 저장하고, sent=1이면 서버로 보낸 것"""
    conn = sqlite3.connect(LOCAL_DB, timeout=5)
    conn.execute("CREATE TABLE IF NOT EXISTS records "
                 "(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, sent INTEGER DEFAULT 0)")
    return conn


def unsent_count():
    """아직 서버로 못 보낸 개수"""
    conn = _local_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM records WHERE sent = 0").fetchone()[0]
    finally:
        conn.close()


def send(rec, url):
    """측정값을 posture_data.db에 저장한 뒤, 안 보낸 것을 오래된 순서로 서버 포트(server_url)에 전송.
    서버가 꺼져 있으면 DB에 남겨 두었다가 다음 전송 때(프로그램을 다시 켠 뒤에도) 보냄"""
    conn = _local_db()
    try:
        conn.execute("INSERT INTO records (data) VALUES (?)", (json.dumps(rec, ensure_ascii=False),))
        conn.commit()
    finally:
        conn.close()
    if not send_lock.acquire(blocking=False):
        return   # 이전 전송이 아직 진행 중이면 저장만
    try:
        _flush(url)
    finally:
        send_lock.release()


def _flush(url):
    conn = _local_db()
    sent = 0
    try:
        rows = conn.execute("SELECT id, data FROM records WHERE sent = 0 ORDER BY id").fetchall()
        for rid, data in rows:
            try:
                req = urllib.request.Request(url, data=data.encode("utf-8"),
                                             headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=1).close()  # 4xx/5xx는 예외 발생
            except Exception as e:
                log.warning(f"전송 실패, DB에 보관 중 {len(rows) - sent}개: {e}")
                break
            conn.execute("UPDATE records SET sent = 1 WHERE id = ?", (rid,))
            conn.commit()
            sent += 1
    finally:
        conn.close()
    if sent > 1:
        log.info(f"밀린 데이터 {sent}개 전송 완료")


# ======================== 지표 계산 ========================
def get_metrics(pose_lm, face_lm, w, h, fov_deg=65):
    """(지표, None) 또는 판정할 수 없을 때 (None, 화면에 띄울 이유)

    forward : 눈 사이 거리 / 어깨 너비
              카메라에 가까울수록 크게 보이므로, 머리만 앞으로 나오면 이 값이 커짐
              (몸 전체가 다가오거나 멀어지면 둘 다 같이 변해서 값이 그대로 -> 거리 영향 없음)
    height  : 어깨선~눈 높이 / 어깨 너비 -> 목을 빼고 숙이거나 구부정하면 작아짐
    tilt    : 어깨 기울기(도)
    dist    : 카메라~눈 거리 추정(cm). 화면 속 눈 사이 거리와 카메라 화각(fov_deg)으로 계산"""
    if face_lm is None:
        return None, "FACE NOT FOUND - look at camera"
    if min(pose_lm[i].visibility for i in (LEFT_SHOULDER, RIGHT_SHOULDER)) < VIS_MIN:
        return None, "MOVE BACK - show both shoulders"

    p = lambda lm, i: (lm[i].x * w, lm[i].y * h)
    ls, rs = p(pose_lm, LEFT_SHOULDER), p(pose_lm, RIGHT_SHOULDER)
    e1, e2, nose = p(face_lm, EYE_OUT_1), p(face_lm, EYE_OUT_2), p(face_lm, NOSE_TIP)
    sw, eye_d = math.dist(ls, rs), math.dist(e1, e2)
    if sw < 1 or eye_d < 1:
        return None, "MOVE BACK - show both shoulders"
    if not min(ls[0], rs[0]) < nose[0] < max(ls[0], rs[0]):
        return None, "ONE PERSON ONLY"         # 잡힌 얼굴이 이 사람 어깨 사이에 없음 (다른 사람 얼굴)
    if abs(nose[0] - (e1[0] + e2[0]) / 2) / eye_d > 0.15:
        return None, "TURN TO CAMERA"          # 고개를 옆으로 돌린 순간은 판정에서 제외

    # ponytail: 눈 너비를 성인 평균으로 가정 -> 사람마다 ±10% 오차. 정확도가 더 필요하면 개인별 측정
    focal = (w / 2) / math.tan(math.radians(fov_deg) / 2)
    return {
        "forward": eye_d / sw,
        "height": ((ls[1] + rs[1]) / 2 - (e1[1] + e2[1]) / 2) / sw,
        "tilt": math.degrees(math.atan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0]))),
        "dist": focal * EYE_W_CM / eye_d,
    }, None


def worse_pct(m, base):
    """기준자세보다 몇 % 나빠졌는지 (머리가 앞으로 나온 정도, 내려간 정도 중 큰 쪽)"""
    forward = (m["forward"] - base["forward"]) / base["forward"] * 100
    if "dist" in m and "dist" in base:
        # 몸통만 돌리면 어깨만 좁아지고 눈은 그대로 -> 머리가 실제로 카메라에 가까워진 만큼만 인정
        forward = min(forward, (base["dist"] / m["dist"] - 1) * 100)
        # 같은 %라도 카메라가 멀수록 머리가 실제로 많이 나온 것 -> REF_DIST_CM 기준으로 환산
        forward *= base["dist"] / REF_DIST_CM
    drop = (base["height"] - m["height"]) / base["height"] * 100
    return max(forward, drop, 0.0)


def raw_status(pct, cfg, prev="정상"):
    """악화율 -> 상태. 이미 경고/위험이면 기준을 hysteresis_pct만큼 낮춰 경계에서 깜빡이지 않게"""
    gap = cfg.get("hysteresis_pct", 2)
    warn = cfg["warning_pct"] - (gap if prev != "정상" else 0)
    danger = cfg["danger_pct"] - (gap if prev == "위험" else 0)
    if pct < warn:
        return "정상"
    return "경고" if pct < danger else "위험"


def hold(raw, since, cfg, now):
    """경고는 warning_hold_sec초, 위험은 danger_hold_sec초 이상 이어져야 확정.
    since = (나빠지기 시작한 시각, 위험 수준이 시작된 시각). 반환: (확정 상태, since, 나쁜 자세 지속시간)"""
    if raw == "정상":
        return "정상", (None, None), 0.0
    bad = since[0] or now
    danger = (since[1] or now) if raw == "위험" else None
    duration = now - bad
    if danger is not None and now - danger >= cfg["danger_hold_sec"]:
        status = "위험"
    elif duration >= cfg["warning_hold_sec"]:
        status = "경고"
    else:
        status = "정상"
    return status, (bad, danger), duration


STATUS_URL = None   # main()에서 server_url로 정함. 예) http://127.0.0.1:5050/api/status


def post_status(status):
    """지금 상태를 서버 /api/status로 바로 보냄 -> 라즈베리파이가 가져가서 LED/부저 제어.
    실패해도 다음 상태 변경이나 save_interval마다 다시 보내므로 기록만 남김"""
    def _post():
        try:
            req = urllib.request.Request(
                STATUS_URL, data=json.dumps({"status": status}, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=1).close()
        except Exception as e:
            log.warning(f"상태 알림 실패: {e}")
    threading.Thread(target=_post, daemon=True).start()


def on_status_change(old, new):
    """상태가 바뀔 때 호출. 서버를 거쳐 라즈베리파이(rpi_device.py)가 1초 안에 알림"""
    log.info(f"상태 변경: {old} -> {new}")
    post_status(new)


# ======================== 화면 표시 ========================
STATUS_EN = {"정상": "NORMAL", "경고": "WARNING", "위험": "DANGER"}   # cv2.putText는 한글 미지원
STATUS_COLOR = {"정상": (0, 200, 0), "경고": (0, 165, 255), "위험": (0, 0, 255)}  # BGR
GRAY = (160, 160, 160)


def has_display():
    """창을 띄울 화면이 있는지. systemd·SSH 실행처럼 화면이 없으면 False"""
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def draw(cv2, mp, frame, pose_res, face_lm, text, color):
    """관절점·눈·코와 상태를 그려서 창에 표시. q: 종료, 누른 키를 돌려줌"""
    global running
    h, w = frame.shape[:2]
    if pose_res is not None and pose_res.pose_landmarks:
        mp.solutions.drawing_utils.draw_landmarks(
            frame, pose_res.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
    if face_lm is not None:
        for i in (EYE_OUT_1, EYE_OUT_2, NOSE_TIP):
            cv2.circle(frame, (int(face_lm[i].x * w), int(face_lm[i].y * h)), 4, (255, 255, 0), -1)
    cv2.putText(frame, text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    cv2.putText(frame, "c: recalibrate  q: quit", (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imshow("turtle_neck", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        log.info("q 키 입력, 종료")
        running = False
    return key


def make_pose(mp, complexity=1):
    """1: 정확(기본, 설치 파일에 포함) / 0: 가벼움(라즈베리파이용, 첫 실행 때 다운로드).
    0이 다운로드에 실패하면 1로 실행"""
    for c in dict.fromkeys((complexity, 1)):
        try:
            return mp.solutions.pose.Pose(model_complexity=c,
                                          min_detection_confidence=0.5,
                                          min_tracking_confidence=0.5)
        except Exception as e:
            if c == 1:
                raise
            log.warning(f"가벼운 모델 다운로드 실패, 기본 모델로 실행: {e}")


# ======================== 카메라 ========================
def open_camera(cv2):
    while running:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)    # 라즈베리파이 부담 줄이기
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            log.info("카메라 연결 성공")
            return cap
        cap.release()
        log.warning("카메라 연결 실패, 5초 후 재시도")
        time.sleep(5)
    return None


# ======================== 메인 루프 ========================
def run(cfg):
    import cv2
    import mediapipe as mp

    cap = open_camera(cv2)
    if cap is None:
        return

    base = load_json(BASELINE_FILE)
    if base and "dist" not in base:
        log.info("예전 방식의 기준자세라 다시 측정")
        base = None
    calib, calib_start, still_msg_until = [], None, 0
    history = deque()   # (시각, 악화율, 어깨 기울기) 최근 smooth_sec초
    status, raw, bad_since = "정상", "정상", (None, None)
    last_save = last_valid = time.time()
    last_proc, interval = 0.0, 1 / cfg.get("analysis_fps", 10)
    n_proc, fps_since = 0, time.time()   # 실제 분석 속도 기록용 (라즈베리파이 성능 확인)
    pct, duration = 0.0, 0.0
    pose_res, face_lm, text, color = None, None, "STARTING", GRAY
    show = cfg.get("show_window", True) and has_display()
    if not show:
        log.info("카메라 창 없이 실행 (모니터 없음 또는 show_window=false)")

    def reset_state():
        nonlocal calib, calib_start, bad_since, raw, status
        calib, calib_start, bad_since, raw = [], None, (None, None), "정상"
        history.clear()
        if status != "정상":
            on_status_change(status, "정상")
            status = "정상"

    try:
        with make_pose(mp, cfg.get("model_complexity", 1)) as pose, \
                mp.solutions.face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.5,
                                                min_tracking_confidence=0.5) as face_mesh:
            while running:
                ok, frame = cap.read()
                if not ok:
                    log.warning("프레임 읽기 실패, 카메라 재연결")
                    cap.release()
                    cap = open_camera(cv2)
                    if cap is None:
                        break
                    continue
                now = time.time()

                # 분석은 초당 analysis_fps번만 (자세는 천천히 변하므로 CPU 절약), 화면은 매번 갱신
                if now - last_proc >= interval:
                    last_proc = now
                    n_proc += 1
                    if now - fps_since >= 60:
                        log.info(f"분석 속도: 초당 {n_proc / (now - fps_since):.1f}회 "
                                 f"(목표 {cfg.get('analysis_fps', 10)}회)")
                        n_proc, fps_since = 0, now
                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pose_res = pose.process(rgb)
                    faces = face_mesh.process(rgb).multi_face_landmarks
                    face_lm = faces[0].landmark if faces else None
                    if pose_res.pose_landmarks:
                        m, reason = get_metrics(pose_res.pose_landmarks.landmark, face_lm, w, h,
                                                cfg.get("camera_fov_deg", 65))
                    else:
                        m, reason = None, "NO PERSON"

                    if m is None:
                        # 사람이 없거나, 판정할 수 없는 화면이 ABSENT_SEC 이상이면 자리 비움 처리
                        text, color = reason, GRAY
                        if (not pose_res.pose_landmarks and face_lm is None) or now - last_valid > ABSENT_SEC:
                            reset_state()

                    elif base is None:
                        # 1) 기준자세 측정: 중간값 사용, 측정 중 많이 움직이면 처음부터 다시
                        last_valid = now
                        if calib_start is None:
                            calib_start = now
                            log.info("사람 감지, 기준자세 측정 시작")
                        calib.append(m)
                        vals = [c["forward"] for c in calib]
                        if len(vals) >= 5 and statistics.pstdev(vals) > statistics.median(vals) * 0.05:
                            log.info("기준자세 측정 중 움직임 감지, 다시 측정")
                            calib, calib_start, still_msg_until = [], now, now + 2
                        elif now - calib_start >= cfg["calib_sec"]:
                            base = {k: statistics.median(c[k] for c in calib) for k in m}
                            with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                                json.dump(base, f)
                            log.info(f"기준값 저장: {base}")
                        text = "HOLD STILL - measuring again" if now < still_msg_until \
                            else "CALIBRATING - sit up straight"
                        color = (255, 200, 0)

                    else:
                        # 2) 거북목 판별: 최근 smooth_sec초 중간값 + 지속시간
                        last_valid = now
                        history.append((now, worse_pct(m, base), m["tilt"]))
                        while history[0][0] < now - cfg.get("smooth_sec", 2):
                            history.popleft()
                        pct = statistics.median(v for _, v, _ in history)
                        raw = raw_status(pct, cfg, raw)
                        new_status, bad_since, duration = hold(raw, bad_since, cfg, now)
                        if new_status != status:
                            on_status_change(status, new_status)
                            status = new_status
                        text, color = f"{STATUS_EN[status]}  {pct:.1f}%", STATUS_COLOR[status]

                        # 3) 어깨 기울기
                        tilt = statistics.median(t for _, _, t in history)
                        shoulder = "틀어짐" if tilt - base["tilt"] >= cfg["shoulder_tilt_deg"] else "정상"

                        # 4) 전송
                        if now - last_save >= cfg["save_interval"]:
                            threading.Thread(target=send, daemon=True, args=({
                                "user_id": cfg["user_id"],
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "worse_pct": round(pct, 1),
                                "status": status,
                                "shoulder_status": shoulder,
                                "shoulder_tilt": round(tilt, 1),
                                "bad_duration": round(duration, 1),
                            }, cfg["server_url"])).start()   # 백그라운드 전송: 서버가 느려도 화면이 안 멈춤
                            post_status(status)   # 살아 있다는 신호 겸 상태 재전송
                            last_save = now

                if show and draw(cv2, mp, frame, pose_res, face_lm, text, color) == ord("c"):
                    log.info("c 키 입력, 기준자세 다시 측정")
                    base = None
                    reset_state()
                    if os.path.exists(BASELINE_FILE):
                        os.remove(BASELINE_FILE)
                elif not show:
                    time.sleep(max(0.0, interval - (time.time() - now)))   # 창이 없으면 분석 사이에 쉼
    finally:
        if cap is not None:
            cap.release()
        if show:
            cv2.destroyAllWindows()


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    global STATUS_URL
    cfg = load_json(CONFIG_FILE)
    if cfg is None:
        log.error(f"설정 파일 없음 또는 형식 오류: {CONFIG_FILE}")
        return
    STATUS_URL = cfg["server_url"].rsplit("/", 1)[0] + "/status"
    log.info("프로그램 시작")
    left = unsent_count()
    if left:
        log.info(f"지난번에 못 보낸 데이터 {left}개 있음 -> 서버 연결되면 자동 전송")
    while running:
        try:
            run(cfg)
        except Exception as e:
            log.exception(f"오류 발생, 10초 후 재시작: {e}")
            for _ in range(10):   # 대기 중에도 Ctrl+C 바로 반영
                if running:
                    time.sleep(1)
    log.info("프로그램 종료")


if __name__ == "__main__":
    main()
