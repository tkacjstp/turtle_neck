r"""
========================================================================
 거북목 판별기 (posture.py)   담당: 임진혁 - 로직 / 각도·자세 계산
========================================================================

[이 프로그램이 하는 일]
  웹캠으로 앞모습을 찍어서 귀·입·어깨 위치를 찾고,
  처음에 잡은 "바른 자세"보다 얼마나 나빠졌는지(%) 계산해서
  정상 / 경고 / 위험을 판정한 뒤 서버(app.py)로 보낸다.

  웹캠 -> 귀·입·어깨 찾기 -> 바른 자세와 비교 -> 나쁜 자세가 10초 이상 계속되면 경고/위험
       -> 5초마다 서버로 전송 -> 웹 페이지(http://서버IP:5050)에서 결과 확인


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
  □ 카메라 화면에 양쪽 귀, 입, 양쪽 어깨가 모두 보이는가? (의자를 조금 뒤로)
  □ 카메라를 옮겼거나 다른 컴퓨터로 바꿨다면 baseline.json을 지웠는가?


[실행]
  윈도우: venv\Scripts\python posture.py      맥/라즈베리파이: python posture.py
  종료  : 카메라 창에서 q 키, 또는 명령 창에서 Ctrl+C

  1) 처음 실행하면 사람이 보인 뒤 5초 동안 "바른 자세"를 측정함 (화면: CALIBRATING)
     -> 이때 자세가 나쁘면 그 자세가 기준이 되어 판정이 이상해짐. 꼭 바르게 앉을 것!
  2) 기준자세는 baseline.json에 저장되고, 다음 실행부터는 이 값을 계속 사용함
  3) 처음 실행할 때 모델을 인터넷에서 받느라 몇 초 걸릴 수 있음 (막혀도 자동으로 다른 모델 사용)


[카메라 창 글자 뜻]  (OpenCV는 한글을 못 써서 영어로 표시)
  NO PERSON           : 사람이 안 보임
  MOVE BACK - ...     : 사람은 보이는데 귀·입·어깨 중 일부가 화면 밖 -> 뒤로 물러나기
  CALIBRATING         : 바른 자세 측정 중 -> 5초간 바르게 앉아 있기
  NORMAL  (초록)      : 정상
  WARNING (주황)      : 경고 - 바른 자세보다 10% 이상 나빠진 상태가 10초 이상
  DANGER  (빨강)      : 위험 - 바른 자세보다 20% 이상 나빠진 상태가 10초 이상
  ※ 숫자(%)는 바른 자세보다 얼마나 나빠졌는지. 0%에 가까울수록 좋음


[주의사항]
  - 카메라는 반드시 "정면"에 둘 것. 옆이나 위에서 찍으면 판정이 틀림
  - 판정이 너무 예민하거나 둔하면 config.json의 warning_pct, danger_pct, hold_sec 숫자를 조절
  - config.json을 바꾸면 프로그램을 껐다 켜야 반영됨
  - 기준자세를 다시 잡고 싶으면 baseline.json을 지우고 다시 실행
  - 서버가 꺼져 있어도 판별은 계속되고, 결과는 최대 1000개까지 보관했다가 서버가 켜지면 한꺼번에 전송
  - 카메라 창은 모니터가 있을 때만 뜸. 라즈베리파이를 SSH로 접속하거나 부팅 시 자동 실행(systemd)하면
    창 없이 실행됨 (오류 아님). 창을 일부러 끄려면 config.json에 "show_window": false
  - 실행 기록은 posture.log 파일에 남음. 문제가 생기면 이 파일을 확인


[자주 나오는 메시지와 해결]
  "전송 실패 ... timed out"            -> server_url의 IP가 틀렸거나, 서버와 다른 네트워크에 있음
  "전송 실패 ... Connection refused"   -> 서버(app.py)가 꺼져 있음
  "카메라 연결 실패, 5초 후 재시도"     -> 웹캠 연결 확인 / 다른 프로그램이 카메라 사용 중
                                         윈도우: 설정 > 개인 정보 > 카메라 > 데스크톱 앱 허용
  "config.json 형식 오류: N번째 줄"     -> 그 줄 근처의 쉼표, 따옴표 확인
                                         (한글 따옴표 “ ”, 마지막 줄 끝 쉼표, True 대문자 등)
  "가벼운 모델 다운로드 실패, 기본 모델로 실행" -> 인터넷이 막힌 것. 자동 해결되니 그대로 사용
  "has no attribute 'solutions'"       -> mediapipe 버전이 너무 최신. pip install mediapipe==0.10.18
  "DLL load failed" (윈도우)           -> Visual C++ 재배포 패키지 설치 필요 (관리자 권한 필요)
  "No module named ..."               -> 가상환경(venv)의 python으로 실행했는지 확인
"""
import os
import sys
import math
import json
import time
import signal
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

SMOOTH_N = 15        # 최근 N프레임 평균
PENDING_MAX = 1000   # 전송 실패 시 보관할 최대 개수

# MediaPipe Pose 랜드마크 번호
LEFT_EAR, RIGHT_EAR, MOUTH_LEFT, MOUTH_RIGHT, LEFT_SHOULDER, RIGHT_SHOULDER = 7, 8, 9, 10, 11, 12

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
pending = deque(maxlen=PENDING_MAX)
send_lock = threading.Lock()


def send(rec, url):
    """서버로 전송. 실패한 데이터는 보관했다가 다음에 다시 보냄"""
    pending.append(rec)
    if not send_lock.acquire(blocking=False):
        return   # 이전 전송이 아직 진행 중이면 보관만
    try:
        _flush(url)
    finally:
        send_lock.release()


def _flush(url):
    sent = 0
    while pending:
        try:
            req = urllib.request.Request(
                url, data=json.dumps(pending[0], ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=1).close()  # 4xx/5xx는 예외 발생
        except Exception as e:
            log.warning(f"전송 실패, 보관 중 {len(pending)}개: {e}")
            break
        pending.popleft()
        sent += 1
    if sent > 1:
        log.info(f"밀린 데이터 {sent}개 전송 완료")


# ======================== 지표 계산 ========================
def get_metrics(lm, w, h):
    """앞모습에서 지표 4개 계산. 필요한 점이 안 보이면 None"""
    need = (LEFT_EAR, RIGHT_EAR, MOUTH_LEFT, MOUTH_RIGHT, LEFT_SHOULDER, RIGHT_SHOULDER)
    if min(lm[i].visibility for i in need) < 0.5:
        return None

    p = lambda i: (lm[i].x * w, lm[i].y * h)
    le, re = p(LEFT_EAR), p(RIGHT_EAR)
    lmo, rmo = p(MOUTH_LEFT), p(MOUTH_RIGHT)
    ls, rs = p(LEFT_SHOULDER), p(RIGHT_SHOULDER)

    sw = math.dist(ls, rs)
    if sw < 1:
        return None
    sh_y = (ls[1] + rs[1]) / 2

    return {
        "neck": (sh_y - (le[1] + re[1]) / 2) / sw,      # 귀~어깨: 거북목이면 짧아짐
        "mouth": (sh_y - (lmo[1] + rmo[1]) / 2) / sw,   # 입~어깨: 고개 숙이면 짧아짐
        "face": math.dist(le, re) / sw,                 # 얼굴 크기: 머리가 앞으로 오면 커짐
        "tilt": math.degrees(math.atan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0]))),  # 어깨 기울기
    }


def worse_pct(m, base):
    """기준자세 대비 가장 많이 나빠진 지표의 %"""
    neck = (base["neck"] - m["neck"]) / base["neck"] * 100
    mouth = (base["mouth"] - m["mouth"]) / base["mouth"] * 100
    face = (m["face"] - base["face"]) / base["face"] * 100
    return max(neck, mouth, face, 0.0)


def raw_status(pct, cfg):
    if pct < cfg["warning_pct"]:
        return "정상"
    return "경고" if pct < cfg["danger_pct"] else "위험"


def hold(raw, bad_since, hold_sec, now):
    """나쁜 자세가 hold_sec 이상 이어져야 확정. (확정 상태, bad_since, 지속시간)"""
    if raw == "정상":
        return "정상", None, 0.0
    bad_since = bad_since or now
    duration = now - bad_since
    return (raw if duration >= hold_sec else "정상"), bad_since, duration


def on_status_change(old, new):
    """상태가 바뀔 때 호출. 로컬 피드백(LED/부저/진동) 담당이 여기에 연결.
    예) from gpiozero import LED, Buzzer 로 핀 제어"""
    log.info(f"상태 변경: {old} -> {new}")


# ======================== 화면 표시 ========================
STATUS_EN = {"정상": "NORMAL", "경고": "WARNING", "위험": "DANGER"}   # cv2.putText는 한글 미지원
STATUS_COLOR = {"정상": (0, 200, 0), "경고": (0, 165, 255), "위험": (0, 0, 255)}  # BGR


def has_display():
    """창을 띄울 화면이 있는지. systemd·SSH 실행처럼 화면이 없으면 False"""
    if not sys.platform.startswith("linux"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def draw(cv2, mp, frame, result, text, color):
    """관절점과 상태를 그려서 창에 표시. q 키를 누르면 종료"""
    global running
    if result.pose_landmarks:
        mp.solutions.drawing_utils.draw_landmarks(
            frame, result.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
    cv2.putText(frame, text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    cv2.imshow("turtle_neck", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        log.info("q 키 입력, 종료")
        running = False


def make_pose(mp):
    """가벼운 모델(0)은 첫 실행 때 인터넷에서 다운로드함.
    네트워크가 막혀 실패하면 설치 파일에 들어 있는 모델(1)로 실행"""
    for c in (0, 1):
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
    calib, calib_start = [], None
    history = deque(maxlen=SMOOTH_N)
    status, bad_since, last_save = "정상", None, time.time()
    pct = 0.0
    show = cfg.get("show_window", True) and has_display()
    if not show:
        log.info("카메라 창 없이 실행 (모니터 없음 또는 show_window=false)")

    try:
        with make_pose(mp) as pose:
            while running:
                ok, frame = cap.read()
                if not ok:
                    log.warning("프레임 읽기 실패, 카메라 재연결")
                    cap.release()
                    cap = open_camera(cv2)
                    if cap is None:
                        break
                    continue

                h, w = frame.shape[:2]
                result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                m = get_metrics(result.pose_landmarks.landmark, w, h) \
                    if result.pose_landmarks else None

                if show:
                    if result.pose_landmarks and m is None:   # 사람은 있는데 귀·입·어깨가 다 안 보임
                        text, color = "MOVE BACK - show ears & shoulders", (160, 160, 160)
                    elif m is None:
                        text, color = "NO PERSON", (160, 160, 160)
                    elif base is None:
                        text, color = "CALIBRATING - sit up straight", (255, 200, 0)
                    else:
                        text, color = f"{STATUS_EN[status]}  {pct:.1f}%", STATUS_COLOR[status]
                    draw(cv2, mp, frame, result, text, color)

                if m is None:
                    # 자리 비움: 보정·지속시간 초기화, 경고 끄기
                    calib, calib_start, bad_since = [], None, None
                    history.clear()
                    if status != "정상":
                        on_status_change(status, "정상")
                        status = "정상"
                    time.sleep(0.2)
                    continue

                now = time.time()

                # 1) 기준자세 측정
                if base is None:
                    if calib_start is None:
                        calib_start = now
                        log.info("사람 감지, 기준자세 측정 시작")
                    calib.append(m)
                    if now - calib_start >= cfg["calib_sec"]:
                        base = {k: sum(c[k] for c in calib) / len(calib) for k in m}
                        with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                            json.dump(base, f)
                        log.info(f"기준값 저장: {base}")
                    continue

                # 2) 거북목 판별 (평균 + 지속시간)
                history.append(worse_pct(m, base))
                pct = sum(history) / len(history)
                new_status, bad_since, duration = hold(raw_status(pct, cfg), bad_since,
                                                       cfg["hold_sec"], now)
                if new_status != status:
                    on_status_change(status, new_status)
                    status = new_status

                # 3) 어깨 기울기 판별
                shoulder = "틀어짐" if m["tilt"] - base["tilt"] >= cfg["shoulder_tilt_deg"] else "정상"

                # 4) 전송
                if now - last_save >= cfg["save_interval"]:
                    threading.Thread(target=send, daemon=True, args=({
                        "user_id": cfg["user_id"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "worse_pct": round(pct, 1),
                        "status": status,
                        "shoulder_status": shoulder,
                        "shoulder_tilt": round(m["tilt"], 1),
                        "bad_duration": round(duration, 1),
                    }, cfg["server_url"])).start()   # 백그라운드 전송: 서버가 느려도 화면이 안 멈춤
                    last_save = now
    finally:
        if cap is not None:
            cap.release()
        if show:
            cv2.destroyAllWindows()


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    cfg = load_json(CONFIG_FILE)
    if cfg is None:
        log.error(f"설정 파일 없음 또는 형식 오류: {CONFIG_FILE}")
        return
    log.info("프로그램 시작")
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
