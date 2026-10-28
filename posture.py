r"""
========================================================================
 거북목 판별기 (posture.py)   담당: 임진혁 - 로직 / 각도·자세 계산
========================================================================

[이 프로그램이 하는 일]
  정면 웹캠으로 얼굴과 어깨를 찾고, 처음에 그 사람의 "바른 자세"와 "거북목 자세"를
  직접 보여 달라고 해서 학습한 뒤, 지금 자세가 둘 중 어디에 가까운지 점수(%)로 판정한다.
  작품 전시용으로 관람객이 바뀌면 자동으로 새로 학습하고, 격하게 움직여도 바로 반응한다.

  웹캠 -> 자세 학습(바른 자세 3초 + 거북목 3초) -> 실시간 점수 -> 정상/경고/위험
       -> 5초마다 서버로 전송 -> 웹 페이지(http://서버IP:5050)에서 결과 확인


[판별 방식]  노트북·모니터 위 웹캠 같은 "정면" 카메라용
  1) 머리 3D 자세 추정
     Face Mesh(얼굴 468점) 중 6점(코끝·턱·양 눈끝·양 입꼬리)을 사람 얼굴 3D 모형에 맞춰서(solvePnP)
     고개 숙인 각도, 카메라까지 거리, 머리 높이를 계산. 어깨(Pose)는 확실히 보일 때만 보조로 사용
  2) 개인 맞춤 학습 (선형판별분석, LDA)
     바른 자세와 거북목 자세를 3초씩 측정해서, "이 사람·이 카메라에서 거북목이 되면
     어떤 값이 어느 방향으로 변하는지"를 학습. 흔들림이 큰 값은 자동으로 비중이 낮아짐
     -> 키보드 내려다보기, 어깨 으쓱, 몸 전체가 다가오기처럼 거북목이 아닌 동작은 점수가 거의 안 오름
     -> 보조로 "머리가 어깨보다 앞으로 나온 정도"도 따로 봐서, 숙이지 않고 머리만 내밀어도 잡아냄
  3) 점수: 바른 자세 = 0%, 학습한 거북목 자세 = 100%
     경고 50%, 위험 80% (사람·카메라가 달라도 같은 의미)

  빠른 반응을 위한 처리 (전시용)
  - 초당 30번 분석, 판정 확정까지 1초(hold_sec)
  - One Euro 필터: 빠르게 움직일 땐 바로 따라가고, 가만히 있을 땐 떨림만 잡음
  - 경고에 들어간 뒤에는 기준을 5%(hysteresis_pct) 낮춰 경계에서 깜빡이지 않게 함
  - 자리를 떠나면 1초 안에 정상으로, 5초 이상 비면 다음 관람객을 위해 학습을 처음부터


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
  □ config.json을 고칠 때 숫자만 바꿨는가? (쉼표·따옴표를 건드리면 실행 안 됨)
  □ 웹캠이 연결되어 있고, 다른 프로그램(줌, 카메라 앱 등)이 쓰고 있지 않은가?
  □ 카메라가 정면에 있고, 얼굴과 양쪽 어깨가 보이는가? (어깨가 안 보여도 얼굴만으로 동작은 함)
  □ 얼굴이 밝게 보이는가? (뒤에 창문이 있어 역광이면 얼굴 인식이 잘 안 됨)
  □ 카메라 뒤쪽(화면 안)에 다른 사람 얼굴이 크게 잡히지 않는가? (전시장에서는 배경 쪽 주의)


[실행]
  윈도우: venv\Scripts\python posture.py      맥/라즈베리파이: python posture.py
  종료  : 카메라 창에서 q 키, 또는 명령 창에서 Ctrl+C
  다시 학습 : 카메라 창에서 c 키

  관람객 진행 순서 (화면에 영어로 안내가 나옴)
  1) 카메라 앞에 앉으면 자동 시작
  2) "1/2 SIT UP STRAIGHT 3,2,1" -> 바르게 앉아서 3초 유지 ("HOLD STRAIGHT...")
  3) "2/2 NOW TURTLE NECK! 3,2,1" -> 평소 나쁜 자세처럼 머리를 앞으로 빼고 3초 유지 ("HOLD IT...")
     -> 두 자세 차이가 너무 작으면 "Too similar"가 뜨고 3)을 다시 함
  4) 이후 실시간 판정. 화면 아래 막대가 점수, 흰 선 두 개가 경고(50)·위험(80) 기준
  5) 자리를 떠나 5초가 지나면 다음 사람을 위해 1)부터 다시

  ※ 개인용으로 쓸 때: config.json의 new_person_reset_sec을 0으로 하면
     학습 결과를 baseline.json에 저장해 두고 다음 실행에도 그대로 사용


[카메라 창 글자 뜻]  (OpenCV는 한글을 못 써서 영어로 표시)
  NO PERSON           : 사람이 안 보임
  FACE NOT FOUND      : 얼굴 인식 안 됨 -> 정면 보기, 조명 확인 (마스크·손으로 가리면 안 됨)
  TURN TO CAMERA      : 고개를 옆으로 많이(35도 이상) 돌림 -> 정면 보기
                        ※ 위 경우가 1초 넘게 이어지면 상태를 정상으로 돌림
  1/2 ..., 2/2 ...    : 자세 학습 중 (위 [실행] 순서 참고)
  NORMAL  (초록)      : 정상
  WARNING (주황)      : 경고 - 점수 50% 이상이 1초 이상
  DANGER  (빨강)      : 위험 - 점수 80% 이상이 1초 이상
  ※ 점수 0% = 학습한 바른 자세, 100% = 학습한 거북목 자세 (100%를 넘을 수도 있음)
  ※ 하늘색 점 6개 = 머리 각도 계산에 쓰는 얼굴 점
  ※ 화면은 거울처럼 좌우 반전해서 보여줌 (mirror: false로 끌 수 있음)


[주의사항]
  - 카메라는 정면, 눈높이 근처에 둘 것. 학습한 뒤 카메라(노트북 화면 각도 포함)를 움직이면
    판정이 틀어지므로 c 키로 다시 학습할 것
  - 거북목 자세를 너무 과장해서 학습하면 평소 자세에 둔해짐. "평소 하는 나쁜 자세" 정도로 보여줄 것
  - 어깨가 안 보이면 얼굴만으로 판정함. 이때는 "숙이지 않고 머리만 내미는" 자세는 잘 못 잡으니
    가능하면 어깨까지 나오게 앉을 것
  - 안경은 괜찮지만, 마스크나 손으로 얼굴을 가리면 인식이 안 됨
  - model_complexity: 1(기본)이 더 정확. 라즈베리파이가 너무 느리면 0으로 (대신 첫 실행 때 다운로드)
  - 판정이 너무 예민하거나 둔하면 config.json의 warning_pct, danger_pct, hold_sec 숫자를 조절
  - config.json을 바꾸면 프로그램을 껐다 켜야 반영됨
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
  "두 자세 구분 부족, 나쁜 자세 다시 측정" -> 거북목 자세를 조금 더 확실하게 (머리를 앞으로)
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
import numpy as np   # mediapipe 설치 시 함께 설치됨

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BASELINE_FILE = os.path.join(BASE_DIR, "baseline.json")
LOG_FILE = os.path.join(BASE_DIR, "posture.log")

VIS_MIN = 0.6        # 관절점이 이 값 이상 확실하게 보여야 사용
ABSENT_SEC = 1       # 판정할 수 없는 화면이 이만큼 이어지면 자리 비움으로 처리 (빠른 반응)
LOCAL_DB = os.path.join(BASE_DIR, "posture_data.db")   # 측정 기록 저장 + 전송 대기 (자동 생성)

# 어깨는 Pose(몸 33점)의 11, 12번 / 얼굴은 Face Mesh(얼굴 468점) 사용
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12

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



# ======================== 특징값 계산 ========================
# 얼굴 3D 표준 모형 (카메라와 같은 방향: x 오른쪽, y 아래, z 카메라에서 멀어지는 쪽)
# Face Mesh 번호: 코끝 1, 턱 152, 양쪽 눈 바깥 끝 33/263, 양쪽 입꼬리 61/291
FACE_IDX = [1, 152, 33, 263, 61, 291]
FACE_3D = np.array([(0, 0, 0), (0, 330, 65), (-225, -170, 135), (225, -170, 135),
                    (-150, 150, 125), (150, 150, 125)], dtype=np.float64)


def head_pose(cv2, face_lm, w, h):
    """얼굴 6점을 3D 표준 모형에 맞춰(solvePnP) 고개 각도·카메라까지 거리·높이를 구함"""
    pts = np.array([(face_lm[i].x * w, face_lm[i].y * h) for i in FACE_IDX], dtype=np.float64)
    cam = np.array([[w, 0, w / 2], [0, w, h / 2], [0, 0, 1]], dtype=np.float64)   # 초점거리 ≈ 화면 폭
    flag = getattr(cv2, "SOLVEPNP_SQPNP", cv2.SOLVEPNP_ITERATIVE)
    ok, rvec, tvec = cv2.solvePnP(FACE_3D, pts, cam, None, flags=flag)
    if not ok or tvec[2, 0] <= 0:
        return None
    fx, fy, fz = cv2.Rodrigues(rvec)[0] @ np.array([0.0, 0.0, -1.0])   # 얼굴이 향한 방향
    return {"pitch": math.degrees(math.atan2(fy, -fz)),   # +: 고개 숙임
            "yaw": math.degrees(math.atan2(fx, -fz)),     # 좌우로 돌린 각도
            "dist": tvec[2, 0],                           # 카메라까지 거리 (상대값)
            "y": tvec[1, 0] / tvec[2, 0]}                 # 카메라 중심 대비 머리 높이


def get_features(cv2, pose_lm, face_lm, w, h):
    """({"face": [..], "shoulder": [..] 또는 None, "tilt": 도 또는 None}, None)
    또는 판정할 수 없을 때 (None, 화면에 띄울 이유)"""
    if face_lm is None:
        return None, "FACE NOT FOUND - look at camera"
    hp = head_pose(cv2, face_lm, w, h)
    if hp is None:
        return None, "FACE NOT FOUND - look at camera"
    if abs(hp["yaw"]) > 35:
        return None, "TURN TO CAMERA"
    feats = {"face": [hp["pitch"], math.log(hp["dist"]), hp["y"]], "shoulder": None, "tilt": None}

    # 어깨: 확실히 보이고, 얼굴이 두 어깨 사이에 있을 때만(같은 사람인지 확인) 보조로 사용
    if pose_lm is not None and min(pose_lm[i].visibility for i in (LEFT_SHOULDER, RIGHT_SHOULDER)) >= VIS_MIN:
        ls = (pose_lm[LEFT_SHOULDER].x * w, pose_lm[LEFT_SHOULDER].y * h)
        rs = (pose_lm[RIGHT_SHOULDER].x * w, pose_lm[RIGHT_SHOULDER].y * h)
        nose_x, sw = face_lm[1].x * w, math.dist(ls, rs)
        if sw > 1 and min(ls[0], rs[0]) < nose_x < max(ls[0], rs[0]):
            feats["shoulder"] = [((ls[1] + rs[1]) / 2 - h / 2) / w, math.log(sw)]
            feats["tilt"] = math.degrees(math.atan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0])))
    return feats, None


def vector(feats, kind):
    return feats["face"] + feats["shoulder"] if kind == "full" else feats["face"]


# ======================== 개인 맞춤 학습 (LDA) ========================
MIN_SEPARATION = 3.0   # 바른 자세와 나쁜 자세가 이 정도 이상 구분돼야 학습 성공


def fit_lda(good, bad):
    """바른 자세·나쁜 자세 측정값에서 '나빠지는 방향'을 학습 (선형판별분석, LDA).
    흔들림이 큰 값은 비중이 낮아지고, 두 자세 차이가 확실한 값은 비중이 높아짐.
    반환: (모델, 구분 정도). 모델 점수는 바른 자세 평균 0, 나쁜 자세 평균 100"""
    G, B = np.array(good, dtype=np.float64), np.array(bad, dtype=np.float64)
    mg, mb = G.mean(axis=0), B.mean(axis=0)
    resid = np.vstack([G - mg, B - mb])              # 같은 자세 안에서의 흔들림
    sd = resid.std(axis=0) + 1e-6
    cov = np.atleast_2d(np.cov((resid / sd).T))
    cov = 0.8 * cov + 0.2 * np.eye(len(sd))          # 측정 개수가 적어도 안정적으로 (수축 보정)
    w = np.linalg.solve(cov, (mb - mg) / sd) / sd
    span = float((mb - mg) @ w)
    spread = math.sqrt(max(float(w @ np.atleast_2d(np.cov(resid.T)) @ w), 1e-12))
    if span <= 0:
        return None, 0.0
    return {"mean": mg.tolist(), "w": (w / span * 100).tolist()}, span / spread


def score(model, x):
    return float((np.array(x) - model["mean"]) @ np.array(model["w"]))


def train(good, bad):
    """얼굴만 쓰는 모델(face) + 어깨까지 쓰는 모델(full, 어깨가 충분히 보였을 때만)"""
    model, sep = fit_lda([vector(f, "face") for f in good], [vector(f, "face") for f in bad])
    if model is None:
        return None, 0.0
    result = {"face": model}
    g = [f for f in good if f["shoulder"]]
    b = [f for f in bad if f["shoulder"]]
    if len(g) >= 0.7 * len(good) and len(b) >= 0.7 * len(bad):
        full, full_sep = fit_lda([vector(f, "full") for f in g], [vector(f, "full") for f in b])
        if full is not None:
            result["full"] = full
            sep = max(sep, full_sep)
            result["tilt"] = statistics.median(f["tilt"] for f in g)
        # 보조 판단: 머리가 어깨보다 앞으로 나온 정도 하나만 따로 기억
        # (학습한 자세와 조금 다르게, 숙이지 않고 머리만 내밀어도 잡기 위해)
        rg, rb = [forward_rel(f) for f in g], [forward_rel(f) for f in b]
        noise = statistics.pstdev([x - statistics.median(rg) for x in rg] + [x - statistics.median(rb) for x in rb])
        if statistics.median(rg) - statistics.median(rb) > 3 * noise:
            result["forward"] = {"good": statistics.median(rg), "bad": statistics.median(rb)}
    return result, sep


def forward_rel(feats):
    """머리가 어깨보다 카메라 쪽으로 나온 정도 = log(머리까지 거리) + log(어깨 너비).
    몸 전체가 다가오면 거리는 줄고 어깨 너비는 커져서 합이 그대로, 머리만 나오면 작아짐"""
    return feats["face"][1] + feats["shoulder"][1]


def posture_score(model, feats):
    """0 = 바른 자세, 100 = 학습한 나쁜 자세. 어깨가 보이면 어깨까지 쓰는 모델 사용"""
    if not feats["shoulder"] or "full" not in model:
        return score(model["face"], vector(feats, "face"))
    s = score(model["full"], vector(feats, "full"))
    if "forward" in model:   # 학습한 자세 점수와 '머리만 앞으로 나온 정도' 중 큰 쪽
        fw = model["forward"]
        s = max(s, (fw["good"] - forward_rel(feats)) / (fw["good"] - fw["bad"]) * 100)
    return s


class OneEuro:
    """빠르게 움직일 땐 바로 따라가고, 가만히 있을 땐 떨림만 잡는 필터 (One Euro Filter)"""
    def __init__(self, min_cutoff=1.0, beta=0.02):
        self.min_cutoff, self.beta, self.t = min_cutoff, beta, None

    def __call__(self, x, t):
        if self.t is None:
            self.x, self.dx, self.t = x, 0.0, t
            return x
        dt = max(t - self.t, 1e-3)
        self.t = t
        a = lambda fc: 1 / (1 + 1 / (2 * math.pi * fc * dt))
        self.dx += a(1.0) * ((x - self.x) / dt - self.dx)
        self.x += a(self.min_cutoff + self.beta * abs(self.dx)) * (x - self.x)
        return self.x


def raw_status(pct, cfg, prev="정상"):
    """점수 -> 상태. 이미 경고/위험이면 기준을 hysteresis_pct만큼 낮춰 경계에서 깜빡이지 않게"""
    gap = cfg.get("hysteresis_pct", 5)
    warn = cfg["warning_pct"] - (gap if prev != "정상" else 0)
    danger = cfg["danger_pct"] - (gap if prev == "위험" else 0)
    if pct < warn:
        return "정상"
    return "경고" if pct < danger else "위험"


def hold(raw, bad_since, hold_sec, now):
    """나쁜 자세가 hold_sec 이상 이어져야 확정. (확정 상태, bad_since, 지속시간)"""
    if raw == "정상":
        return "정상", None, 0.0
    bad_since = bad_since or now
    duration = now - bad_since
    return (raw if duration >= hold_sec else "정상"), bad_since, duration


STATUS_URL = None   # main()에서 server_url로 정함. 예) http://127.0.0.1:5050/api/status


def post_status(status):
    """지금 상태를 서버 /api/status로 바로 보냄 -> 라즈베리파이(rpi_device.py)가 가져가서 LED/부저/진동 제어.
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
GRAY, YELLOW = (160, 160, 160), (0, 220, 255)


def has_display():
    """창을 띄울 화면이 있는지. systemd·SSH 실행처럼 화면이 없으면 False"""
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def draw(cv2, mp, frame, pose_res, face_lm, text, color, sub, pct, cfg):
    """관절점·얼굴 점, 상태, 점수 막대를 그려서 창에 표시. q: 종료, 누른 키를 돌려줌"""
    global running
    h, w = frame.shape[:2]
    if pose_res is not None and pose_res.pose_landmarks:
        mp.solutions.drawing_utils.draw_landmarks(
            frame, pose_res.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
    if face_lm is not None:
        for i in FACE_IDX:
            cv2.circle(frame, (int(face_lm[i].x * w), int(face_lm[i].y * h)), 4, (255, 255, 0), -1)
    if cfg.get("mirror", True):
        frame = cv2.flip(frame, 1)   # 거울처럼 보여주기 (글자는 뒤집기 후에 씀)

    cv2.putText(frame, text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)
    if sub:
        cv2.putText(frame, sub, (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if pct is not None:   # 점수 막대: 0(바른 자세) ~ 100(학습한 나쁜 자세)
        x0, x1, y0 = 10, w - 10, h - 45
        cv2.rectangle(frame, (x0, y0), (x1, y0 + 15), (80, 80, 80), -1)
        fill = x0 + int((x1 - x0) * min(max(pct, 0), 120) / 120)
        cv2.rectangle(frame, (x0, y0), (fill, y0 + 15), color, -1)
        for th in (cfg["warning_pct"], cfg["danger_pct"]):
            tx = x0 + int((x1 - x0) * th / 120)
            cv2.line(frame, (tx, y0 - 3), (tx, y0 + 18), (255, 255, 255), 2)
    cv2.putText(frame, "c: recalibrate  q: quit", (10, h - 12),
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
READY_SEC = 3   # 보정 단계마다 준비 카운트다운(초)


def run(cfg):
    import cv2
    import mediapipe as mp

    cap = open_camera(cv2)
    if cap is None:
        return

    reset_sec = cfg.get("new_person_reset_sec", 5)
    model = load_json(BASELINE_FILE) if reset_sec == 0 else None   # 전시회 모드면 매번 새로 학습
    if model and "face" not in model:
        model = None   # 예전 버전 파일
    phase = "run" if model else "wait"   # wait -> good_ready -> good_rec -> bad_ready -> bad_rec -> run
    phase_start, good, bad, retry_msg_until = 0.0, [], [], 0.0
    filt = OneEuro()
    status, raw, bad_since = "정상", "정상", None
    last_save = last_valid = time.time()
    last_seen = 0.0
    last_proc, interval = 0.0, 1 / cfg.get("analysis_fps", 30)
    pct, duration = None, 0.0
    pose_res, face_lm, text, sub, color = None, None, "STARTING", "", GRAY
    show = cfg.get("show_window", True) and has_display()
    if not show:
        log.info("카메라 창 없이 실행 (모니터 없음 또는 show_window=false)")

    def set_status(new):
        nonlocal status
        if new != status:
            on_status_change(status, new)
            status = new

    def restart_calibration(why):
        nonlocal model, phase, good, bad, pct, bad_since, raw, filt
        log.info(f"{why} -> 자세 학습 다시 시작")
        model, phase, good, bad, pct, bad_since, raw, filt = None, "wait", [], [], None, None, "정상", OneEuro()
        set_status("정상")

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

                if now - last_proc >= interval:
                    last_proc = now
                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pose_res = pose.process(rgb)
                    faces = face_mesh.process(rgb).multi_face_landmarks
                    face_lm = faces[0].landmark if faces else None
                    pose_lm = pose_res.pose_landmarks.landmark if pose_res.pose_landmarks else None
                    feats, reason = get_features(cv2, pose_lm, face_lm, w, h)
                    if face_lm is not None or pose_lm is not None:
                        last_seen = now

                    if feats is None:
                        text, sub, color = ("NO PERSON" if now - last_seen > 0.3 else reason), "", GRAY
                        if now - last_valid > ABSENT_SEC:            # 판정 불가가 이어지면 자리 비움
                            bad_since, raw = None, "정상"
                            set_status("정상")
                            if phase not in ("wait", "run"):
                                phase, good, bad = "wait", [], []     # 보정 중이었으면 처음부터
                        if model and reset_sec and now - last_seen > reset_sec:
                            restart_calibration("사람이 떠남(새 관람객 대비)")
                    else:
                        last_valid = now
                        if phase == "wait":
                            phase, phase_start = "good_ready", now
                            log.info("사람 감지, 자세 학습 시작")

                        # ---------- 자세 학습: 바른 자세 -> 나쁜 자세 ----------
                        if phase in ("good_ready", "bad_ready"):
                            left = READY_SEC - (now - phase_start)
                            step = "1/2  SIT UP STRAIGHT" if phase == "good_ready" else "2/2  NOW TURTLE NECK!"
                            text, color = f"{step}  {math.ceil(max(left, 0))}", YELLOW
                            sub = "Too similar - push your head forward more" if now < retry_msg_until \
                                else ("Sit tall, chin in" if phase == "good_ready"
                                      else "Push your head forward like usual bad posture")
                            if left <= 0:
                                phase = "good_rec" if phase == "good_ready" else "bad_rec"
                                phase_start = now
                        elif phase in ("good_rec", "bad_rec"):
                            (good if phase == "good_rec" else bad).append(feats)
                            text = "1/2  HOLD STRAIGHT..." if phase == "good_rec" else "2/2  HOLD IT..."
                            sub, color = f"recording {cfg['calib_sec'] - (now - phase_start):.1f}s", YELLOW
                            if now - phase_start >= cfg["calib_sec"]:
                                if phase == "good_rec":
                                    phase, phase_start, bad = "bad_ready", now, []
                                else:
                                    model, sep = train(good, bad)
                                    if model is None or sep < MIN_SEPARATION:
                                        log.info(f"두 자세 구분 부족(구분 정도 {sep:.1f}), 나쁜 자세 다시 측정")
                                        model, phase, phase_start, bad = None, "bad_ready", now, []
                                        retry_msg_until = now + READY_SEC
                                    else:
                                        phase, filt = "run", OneEuro()
                                        log.info(f"자세 학습 완료 (구분 정도 {sep:.1f}, 어깨 사용: {'full' in model})")
                                        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                                            json.dump(model, f)

                        # ---------- 판별 ----------
                        else:
                            pct = filt(posture_score(model, feats), now)
                            raw = raw_status(pct, cfg, raw)
                            new_status, bad_since, duration = hold(raw, bad_since, cfg["hold_sec"], now)
                            set_status(new_status)
                            text, sub, color = f"{STATUS_EN[status]}  {max(pct, 0):.0f}%", "", STATUS_COLOR[status]

                            shoulder, tilt = None, feats["tilt"]
                            if tilt is not None and "tilt" in model:
                                shoulder = "틀어짐" if tilt - model["tilt"] >= cfg["shoulder_tilt_deg"] else "정상"
                            if now - last_save >= cfg["save_interval"]:
                                threading.Thread(target=send, daemon=True, args=({
                                    "user_id": cfg["user_id"],
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "worse_pct": round(max(pct, 0), 1),
                                    "status": status,
                                    "shoulder_status": shoulder,
                                    "shoulder_tilt": round(tilt, 1) if shoulder else None,
                                    "bad_duration": round(duration, 1),
                                }, cfg["server_url"])).start()   # 백그라운드 전송: 서버가 느려도 화면이 안 멈춤
                                post_status(status)   # 살아 있다는 신호 겸 상태 재전송
                                last_save = now

                if show:
                    shown_pct = pct if phase == "run" else None
                    if draw(cv2, mp, frame, pose_res, face_lm, text, color, sub, shown_pct, cfg) == ord("c"):
                        if os.path.exists(BASELINE_FILE):
                            os.remove(BASELINE_FILE)
                        restart_calibration("c 키 입력")
                else:
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