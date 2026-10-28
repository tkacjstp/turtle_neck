r"""
========================================================================
 거북목 판별기 - 얼굴만 사용 (posture_face.py)
========================================================================

[posture.py와 다른 점]
  어깨를 쓰지 않음 -> 팔을 들거나 움직여도 판정이 흔들리지 않음
  Face Mesh 6점(코끝·턱·눈 끝 2개·입꼬리 2개) + OpenCV solvePnP로
  머리의 3D 위치(cm)와 숙인 각도(°)를 직접 계산해서 기준자세와 비교
    - 앞으로 나옴(cm) : 기준자세보다 머리가 카메라(화면) 쪽으로 다가온 거리
    - 고개 숙임(°)    : 기준자세보다 고개를 숙인 각도
  둘 중 더 나쁜 쪽으로 판정.
  서버·DB·라즈베리파이 연동, config.json, 설치 방법은 posture.py와 같음 (posture.py의 함수를 그대로 씀)

[한계]
  정면 카메라 하나로는 "머리만 나온 것"과 "상체 전체가 화면 쪽으로 기운 것"을 구분 못 함.
  둘 다 화면에 다가가는 나쁜 자세라서 경고로 처리함.

[실행]  윈도우: venv\Scripts\python posture_face.py      맥/라즈베리파이: python posture_face.py
  처음 5초(calib_sec) 동안 바른 자세로 앉아 기준자세 측정 -> baseline_face.json에 저장
  카메라 창에서 c: 기준자세 다시 측정, q: 종료

[config.json에 추가된 값]  (없으면 괄호 안 기본값 사용)
  face_warning_cm (3)  / face_danger_cm (6)   : 머리가 이만큼 앞으로 나오면 경고 / 위험
  face_warning_deg (15) / face_danger_deg (25) : 고개를 이만큼 숙이면 경고 / 위험
  ※ 시작값임. posture.log의 "앞으로 ?cm, 숙임 ?°"를 보고 내 자세에 맞게 조절
"""
import os
import json
import math
import time
import signal
import statistics
import threading
from collections import deque
from datetime import datetime

import posture as P
from posture import log

BASELINE_FILE = os.path.join(P.BASE_DIR, "baseline_face.json")

# Face Mesh 번호와 평균 성인 얼굴의 3D 좌표(cm). 코끝 기준, x 오른쪽, y 위쪽, z 카메라 쪽
FACE_IDX = (1, 152, 33, 263, 61, 291)   # 코끝, 턱 끝, 눈 바깥 끝(화면 왼쪽·오른쪽), 입꼬리(왼쪽·오른쪽)
FACE_3D = [(0, 0, 0), (0, -6.6, -1.3), (-4.5, 3.4, -2.7), (4.5, 3.4, -2.7), (-3.0, -3.0, -2.5), (3.0, -3.0, -2.5)]
MAX_YAW = 25   # 고개를 이보다 옆으로 돌린 순간은 판정에서 제외


def head_pose(cv2, np, face_lm, w, h, fov_deg=65):
    """얼굴 6점 -> {"z": 카메라~코끝 거리(cm), "y": 코끝 높이(cm, 아래가 +),
                    "pitch": 숙임 각도(°, 숙이면 +), "yaw": 돌림 각도(°)}. 계산 실패 시 None"""
    f = (w / 2) / math.tan(math.radians(fov_deg) / 2)
    cam = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]], dtype=float)
    img = np.array([(face_lm[i].x * w, face_lm[i].y * h) for i in FACE_IDX], dtype=float)
    ok, rvec, tvec = cv2.solvePnP(np.array(FACE_3D, dtype=float), img, cam, None,
                                  flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok or tvec[2][0] <= 0:
        return None
    face_dir = cv2.Rodrigues(rvec)[0] @ np.array([0.0, 0.0, 1.0])   # 얼굴 정면 방향. 카메라를 보면 (0, 0, -1)
    return {"z": float(tvec[2][0]), "y": float(tvec[1][0]),
            "pitch": math.degrees(math.atan2(face_dir[1], -face_dir[2])),
            "yaw": math.degrees(math.atan2(face_dir[0], -face_dir[2]))}


def to_pct(v, warn, danger, cfg):
    """cm·° -> 악화율(%). warn이면 warning_pct, danger면 danger_pct가 되게 맞춤
    -> posture.py의 판정(raw_status·hysteresis)과 서버 저장 형식을 그대로 씀"""
    lo, hi = cfg["warning_pct"], cfg["danger_pct"]
    if v <= warn:
        return max(v, 0.0) / warn * lo
    return lo + (v - warn) / (danger - warn) * (hi - lo)


def worse(m, base, cfg):
    """(악화율 %, 앞으로 나온 cm, 숙인 °)"""
    fwd = base["z"] - m["z"]
    pitch = m["pitch"] - base["pitch"]
    pct = max(to_pct(fwd, cfg.get("face_warning_cm", 3), cfg.get("face_danger_cm", 6), cfg),
              to_pct(pitch, cfg.get("face_warning_deg", 15), cfg.get("face_danger_deg", 25), cfg))
    return pct, fwd, pitch


def run(cfg):
    import cv2
    import numpy as np
    import mediapipe as mp

    cap = P.open_camera(cv2)
    if cap is None:
        return
    base = P.load_json(BASELINE_FILE)
    calib, calib_start, still_msg_until = [], None, 0
    history = deque()   # (시각, 악화율, 앞으로 cm, 숙임 °) 최근 smooth_sec초
    status, raw, bad_since = "정상", "정상", None
    last_save = last_valid = time.time()
    last_proc, interval = 0.0, 1 / cfg.get("analysis_fps", 10)
    face_lm, text, color = None, "STARTING", P.GRAY
    show = cfg.get("show_window", True) and P.has_display()

    def reset_state():
        nonlocal calib, calib_start, bad_since, raw, status
        calib, calib_start, bad_since, raw = [], None, None, "정상"
        history.clear()
        if status != "정상":
            P.on_status_change(status, "정상")
            status = "정상"

    try:
        with mp.solutions.face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.5,
                                             min_tracking_confidence=0.5) as face_mesh:
            while P.running:
                ok, frame = cap.read()
                if not ok:
                    log.warning("프레임 읽기 실패, 카메라 재연결")
                    cap.release()
                    cap = P.open_camera(cv2)
                    if cap is None:
                        break
                    continue
                now = time.time()

                if now - last_proc >= interval:
                    last_proc = now
                    h, w = frame.shape[:2]
                    faces = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).multi_face_landmarks
                    face_lm = faces[0].landmark if faces else None
                    m = head_pose(cv2, np, face_lm, w, h, cfg.get("camera_fov_deg", 65)) if face_lm else None
                    reason = "NO FACE - look at camera" if m is None else \
                        "TURN TO CAMERA" if abs(m["yaw"]) > MAX_YAW else None

                    if reason:
                        text, color = reason, P.GRAY
                        if now - last_valid > P.ABSENT_SEC:
                            reset_state()

                    elif base is None:
                        # 1) 기준자세 측정: 측정 중 거리 2cm 또는 각도 5° 넘게 움직이면 처음부터 다시
                        last_valid = now
                        if calib_start is None:
                            calib_start = now
                            log.info("얼굴 감지, 기준자세 측정 시작")
                        calib.append(m)
                        if len(calib) >= 5 and (statistics.pstdev(c["z"] for c in calib) > 2
                                                or statistics.pstdev(c["pitch"] for c in calib) > 5):
                            log.info("기준자세 측정 중 움직임 감지, 다시 측정")
                            calib, calib_start, still_msg_until = [], now, now + 2
                        elif now - calib_start >= cfg["calib_sec"]:
                            base = {k: statistics.median(c[k] for c in calib) for k in m}
                            with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                                json.dump(base, f)
                            log.info(f"기준값 저장: 거리 {base['z']:.1f}cm, 각도 {base['pitch']:.1f}°")
                        text = "HOLD STILL - measuring again" if now < still_msg_until \
                            else "CALIBRATING - sit up straight"
                        color = (255, 200, 0)

                    else:
                        # 2) 판별: 최근 smooth_sec초 중간값 + 지속시간 (posture.py와 같은 방식)
                        last_valid = now
                        history.append((now, *worse(m, base, cfg)))
                        while history[0][0] < now - cfg.get("smooth_sec", 3):
                            history.popleft()
                        pct, fwd, pitch = (statistics.median(r[i] for r in history) for i in (1, 2, 3))
                        raw = P.raw_status(pct, cfg, raw)
                        new_status, bad_since, duration = P.hold(raw, bad_since, cfg["hold_sec"], now)
                        if new_status != status:
                            P.on_status_change(status, new_status)
                            status = new_status
                            last_save = 0   # 상태가 바뀌면 바로 기록
                        text = f"{P.STATUS_EN[status]}  {pct:.0f}%  fwd {fwd:+.1f}cm  down {pitch:+.0f}deg"
                        color = P.STATUS_COLOR[status]

                        # 3) 전송
                        if now - last_save >= cfg["save_interval"]:
                            log.info(f"{status} 악화율 {pct:.1f}% (앞으로 {fwd:+.1f}cm, 숙임 {pitch:+.1f}°)")
                            threading.Thread(target=P.send, daemon=True, args=({
                                "user_id": cfg["user_id"],
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "worse_pct": round(pct, 1),
                                "status": status,
                                "bad_duration": round(duration, 1),
                            }, cfg["server_url"])).start()
                            P.post_status(status)
                            last_save = now

                if show and P.draw(cv2, mp, frame, None, face_lm, text, color) == ord("c"):
                    log.info("c 키 입력, 기준자세 다시 측정")
                    base = None
                    reset_state()
                    if os.path.exists(BASELINE_FILE):
                        os.remove(BASELINE_FILE)
                elif not show:
                    time.sleep(max(0.0, interval - (time.time() - now)))
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()


def main():
    signal.signal(signal.SIGTERM, P.stop)
    signal.signal(signal.SIGINT, P.stop)
    cfg = P.load_json(P.CONFIG_FILE)
    if cfg is None:
        log.error(f"설정 파일 없음 또는 형식 오류: {P.CONFIG_FILE}")
        return
    P.STATUS_URL = cfg["server_url"].rsplit("/", 1)[0] + "/status"
    log.info("프로그램 시작 (얼굴만 사용)")
    while P.running:
        try:
            run(cfg)
        except Exception as e:
            log.exception(f"오류 발생, 10초 후 재시작: {e}")
            for _ in range(10):
                if P.running:
                    time.sleep(1)
    log.info("프로그램 종료")


if __name__ == "__main__":
    main()
