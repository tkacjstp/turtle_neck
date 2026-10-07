"""
라즈베리파이 거북목 판별기 (담당: 임진혁 - 로직 / 각도·자세 계산)

전원 ON -> systemd 자동 실행 -> 웹캠(앞모습) -> MediaPipe로 귀·입·어깨 좌표 추출
-> 기준자세 대비 변화율 계산 -> 일정 시간 지속되면 경고/위험 확정
-> 서버(app.py) POST /api/record 로 전송

기준자세 다시 잡기: baseline.json 삭제 후 재시작
설정 변경: config.json 수정 후 재시작 (sudo systemctl restart <서비스명>)
"""
import os
import math
import json
import time
import signal
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
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ======================== 전송 ========================
pending = deque(maxlen=PENDING_MAX)


def send(rec, url):
    """서버로 전송. 실패한 데이터는 보관했다가 다음에 다시 보냄"""
    pending.append(rec)
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

    try:
        with mp.solutions.pose.Pose(model_complexity=0,
                                    min_detection_confidence=0.5,
                                    min_tracking_confidence=0.5) as pose:
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
                    send({
                        "user_id": cfg["user_id"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "worse_pct": round(pct, 1),
                        "status": status,
                        "shoulder_status": shoulder,
                        "shoulder_tilt": round(m["tilt"], 1),
                        "bad_duration": round(duration, 1),
                    }, cfg["server_url"])
                    last_save = now
    finally:
        if cap is not None:
            cap.release()


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
            time.sleep(10)
    log.info("프로그램 종료")


if __name__ == "__main__":
    main()
