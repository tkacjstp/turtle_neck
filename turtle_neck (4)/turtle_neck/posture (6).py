r"""
========================================================================
 거북목 판별기 (posture.py)   담당: 임진혁 - 로직 / 각도·자세 계산
========================================================================

[이 프로그램이 하는 일]
  정면 웹캠으로 얼굴과 어깨를 찾고, 처음에 그 사람의 "바른 자세"와 "거북목 자세"를
  직접 보여 달라고 해서 학습한 뒤, 지금 자세가 둘 중 어디에 가까운지 점수(%)로 판정한다.
  작품 전시용으로 관람객이 바뀌면 자동으로 새로 학습하고, 격하게 움직여도 바로 반응한다.

  웹캠 -> 자세 학습(바른 자세 3초 + 거북목 3초) -> 실시간 점수 -> 정상/경고/위험
       -> 2초마다(상태가 바뀌면 바로) 서버로 전송 -> 웹 페이지(http://서버IP:5050)에서 결과 확인


[판별 방식]  모니터 위(또는 노트북) 웹캠 1개로 정면에서 찍음
  1) 귀 위치를 3D로 계산
     Face Mesh(얼굴 468점) 중 표정이 바뀌어도 안 움직이는 33점(콧등·눈 끝·광대·이마)을
     MediaPipe 표준 얼굴 3D 모형에 맞춰서(solvePnP) 머리의 3D 위치를 구하고, 그중 "귀" 위치를 씀.
     -> 코가 아니라 귀를 보므로 고개만 숙이거나 끄덕이는 건(키보드 보기 등) 거의 영향 없음
  2) 몸통 움직임 빼기 (가장 중요)
     어깨(Pose)의 3D 위치도 구함: 어깨가 카메라에 가까워지면 넓게 보이는 것으로 앞뒤 거리를,
     화면 속 높이로 위아래를 계산.
     고관절을 축으로 몸을 숙이면(척추 중립) 고관절-어깨-귀가 한 직선처럼 같이 돌아서,
     귀는 어깨가 움직인 만큼의 (몸통+목)/몸통 배(약 1.3배)만큼 움직임 -> 그만큼을 빼면
     "목만 앞으로 나온 거리(cm)"가 남음. 이게 거북목.
     -> 고관절로 숙이기, 뒤로 기대기, 의자째 다가가기, 몸 비틀기, 어깨 으쓱은 거북목으로 안 봄
        (어깨가 멀어져 보일 때는 화면 속 높이도 같이 올라가야 '뒤로 기댐'으로 인정. 높이 그대로면 비틀기)
     -> 숙인 상태에서 목까지 빼면 그건 거북목으로 잡음
  3) 개인 맞춤 학습: 바른 자세 3초 + 거북목 3초를 보여 주면, 거북목일 때 목이 몸통 기준으로
     앞으로·아래로 몇 cm 움직이는지 학습. 점수 = 지금 목 움직임을 그 방향에 비춘 비율
     (바른 자세 0%, 학습한 거북목 100%, 화면·전송은 0~100%로 제한)
     30% 이상이면 바로 경고, 60% 이상인 상태가 2.5초(danger_after_sec) 이어지면 위험
  4) 팔을 들면: Pose의 어깨 점이 팔을 따라 올라가서 못 믿음 -> 팔을 들기 직전의 어깨를 기억해서 사용(10초)
     손으로 얼굴을 가려 잠깐 얼굴이 안 보이면: 3초 동안 마지막 판정 유지
     어깨가 화면 밖으로 나가면: 몸통 움직임을 뺄 수 없어서 판정하지 않음 ("MOVE BACK")

  빠른 반응을 위한 처리 (전시용)
  - 경고는 기다리지 않고 바로 표시 (자세가 바뀌고 약 0.3초 안에 반영)
  - 귀와 어깨 측정값을 똑같은 방식으로 0.25초(smooth_sec)만큼 부드럽게 함 + One Euro 필터
    (둘이 똑같이 늦어져야 빨리 움직여도 서로 어긋나지 않음)
  - 얼굴(초당 30번)과 어깨(초당 5번)는 계산 속도가 달라서, 판정할 때는 "같은 화면"에서 나온
    얼굴과 어깨를 짝지어 씀 (안 그러면 빨리 숙일 때 귀만 먼저 움직인 것처럼 보여 순간 오판)
  - 경고에 들어간 뒤에는 기준을 5%(hysteresis_pct) 낮춰 경계에서 깜빡이지 않게 함
  - 자리를 떠나면 1초 안에 정상으로, 5초 이상 비면 다음 관람객을 위해 학습을 처음부터

  부하를 줄이기 위한 처리 (라즈베리파이용, 쓰레드 4개로 나눔)
  - 카메라 쓰레드 : 카메라 읽기만 함(최대 60fps). 항상 "가장 최근 화면" 하나만 보관
  - 얼굴 쓰레드   : Face Mesh(얼굴)만 계산, 초당 analysis_fps번
  - 어깨 쓰레드   : Pose(어깨)만 계산, 초당 pose_fps번 (가장 무거운 계산. 어깨는 천천히 움직여서 충분)
  - 메인 쓰레드   : 화면 표시(카메라 속도 그대로) + 판정(새 어깨 결과가 나올 때마다, 계산량 아주 적음)
  -> MediaPipe는 계산하는 동안 파이썬 잠금(GIL)을 풀어 줘서, 얼굴·어깨 계산이 라즈베리파이의
     서로 다른 CPU 코어에서 동시에 돎. 무거운 계산이 늦어져도 화면은 끊기지 않음
  - 정해진 횟수만 계산하고 남는 시간은 쉬어서 CPU를 다 쓰지 않음 (같은 기기의 서버 app.py도 여유 있게)
  - 화면 오른쪽 아래에 cam/screen/face/pose 초당 처리 횟수(fps) 표시, 로그에도 10초마다 기록
  ※ 라즈베리파이 추천 설정: "analysis_fps": 15, "pose_fps": 5, "model_complexity": 0
  ※ 웹캠 60fps: 웹캠이 60fps를 지원해야 하고(대부분 MJPG 방식에서만), 조명이 밝아야 함
     (어두우면 웹캠이 스스로 노출 시간을 늘려서 15~30fps로 떨어짐). 실제 값은 로그로 확인


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
  □ 웹캠을 모니터 위 가운데에 두고, 화면에 얼굴과 양쪽 어깨(가슴 위쪽까지)가 보이는가?
      어깨가 안 보이면 몸통 움직임을 못 빼서 몸을 숙이면 거북목으로 보일 수 있음
  □ config.json의 camera_tilt_deg가 웹캠이 아래로 기울어진 각도와 비슷한가?
      (모니터 위에서 사람을 내려다보면 보통 10~15, 노트북 화면 웹캠이면 0~5. 대충 맞으면 됨)
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
     -> 화면에 "head forward +O.Ocm"로 목이 앞으로 나온 거리가 실시간으로 보임 (2cm 이상이면 충분)
     -> 목이 1.5cm도 안 움직였으면 "Head moved only ..."가 뜨고 3)을 다시 함 (최대 3번)
     -> 3번 해도 안 되면 "Let's start again from step 1"이 뜨고 2)부터 다시 (무한 반복 안 함)
     -> 학습 중 잠깐(3초 이내) 얼굴이 안 보이면 측정만 멈췄다가 이어서 함
  4) 이후 실시간 판정. 화면 아래 막대가 점수, 흰 선 두 개가 경고(30)·위험(60) 기준
  5) 자리를 떠나 5초가 지나면 다음 사람을 위해 1)부터 다시

  ※ 개인용으로 쓸 때: config.json의 new_person_reset_sec을 0으로 하면
     학습 결과를 baseline.json에 저장해 두고 다음 실행에도 그대로 사용
  ※ 어깨를 아예 안 쓰려면 config.json에 "use_shoulders": false (얼굴만으로 판정)


[카메라 창 글자 뜻]  (OpenCV는 한글을 못 써서 영어로 표시)
  NO PERSON           : 사람이 안 보임
  FACE NOT FOUND      : 얼굴 인식 안 됨 -> 정면 보기, 조명 확인 (마스크·손으로 가리면 안 됨)
  TURN TO CAMERA      : 고개를 옆으로 많이(35도 이상) 돌림 -> 정면 보기
  MOVE BACK - show both shoulders : 어깨가 화면 밖 -> 뒤로 물러나거나 카메라 각도 조절
  face hidden - keeping last result : 몸은 보이는데 얼굴이 가려짐(손 등) -> 3초 동안 마지막 판정 유지
                        ※ 판정할 수 없는 상태가 1초(얼굴만 가려졌으면 3초) 넘게 이어지면 상태를 정상으로 돌림
  1/2 ..., 2/2 ...    : 자세 학습 중 (위 [실행] 순서 참고)
  NORMAL  (초록)      : 정상
  WARNING (주황)      : 경고 - 점수 30%(warning_pct) 이상 (바로 표시)
  DANGER  (빨강)      : 위험 - 점수 60%(danger_pct) 이상이 2.5초(danger_after_sec) 이상 이어짐
  ※ 점수 0% = 학습한 바른 자세, 100% = 학습한 거북목 자세 (0~100%로 제한)
  ※ 하늘색 점 = 머리 위치 계산에 쓰는 얼굴 점 33개
  ※ 화면은 거울처럼 좌우 반전해서 보여줌 (mirror: false로 끌 수 있음)


[주의사항]
  - 카메라는 정면, 눈높이 근처에 둘 것. 학습한 뒤 카메라(노트북 화면 각도 포함)를 움직이면
    판정이 틀어지므로 c 키로 다시 학습할 것
  - 거북목 자세를 너무 과장해서 학습하면 평소 자세에 둔해짐. "평소 하는 나쁜 자세" 정도로 보여줄 것
  - 학습할 때 어깨가 잘 안 보였으면 몸통 보정 없이 판정함 (로그에 경고가 남음) -> 몸을 숙이면 거북목으로 볼 수 있으니
    어깨까지 나오게 하고 c 키로 다시 학습할 것
  - 몸을 아주 크게(30도 넘게) 숙이면 계산 오차를 봐주는 만큼 그 상태의 거북목은 점수가 조금 낮게 나옴
  - 경고 기준을 너무 낮추면(예: 10%) 측정 흔들림만으로도 경고가 깜빡일 수 있음. 30% 이상 권장
  - 안경은 괜찮지만, 마스크나 손으로 얼굴을 가리면 인식이 안 됨
  - model_complexity: 1(기본)이 더 정확. 라즈베리파이가 너무 느리면 0으로 (대신 첫 실행 때 다운로드)
  - 판정이 너무 예민하거나 둔하면 config.json의 warning_pct, danger_pct, danger_after_sec 숫자를 조절
    (기준 점수는 "학습한 거북목의 몇 %만큼 목이 나왔나". 학습 때 거북목을 크게 하면 둔해지고 작게 하면 예민해짐)
  - config.json을 바꾸면 프로그램을 껐다 켜야 반영됨
  - 모든 측정값은 판별기 쪽 posture_data.db에 먼저 저장되고, 그다음 서버 포트(server_url)로 전송됨
    서버가 꺼져 있거나 연결이 안 되면 DB에 남겨 두었다가, 연결되면 오래된 것부터 자동 전송
    (프로그램을 껐다 켜도 남아 있고, 측정 시각도 원래 시각 그대로 저장됨)
  - posture_data.db는 보낸 기록도 계속 쌓임 (save_interval 2초면 하루 약 4.3만 개, 약 8MB)
    -> 정리하고 싶으면 프로그램을 끄고 삭제. 단, 아직 못 보낸 데이터도 같이 사라짐
  - 카메라 창은 모니터가 있을 때만 뜸. 라즈베리파이를 SSH로 접속하거나 부팅 시 자동 실행(systemd)하면
    창 없이 실행됨 (오류 아님). 창을 일부러 끄려면 config.json에 "show_window": false
  - 실행 기록은 posture.log 파일에 남음. 문제가 생기면 이 파일을 확인
    (전송할 때마다 점수·목이 앞/아래로 나온 거리·몸통 숙임·어깨 사용 여부가 남아서 오판 원인을 볼 수 있음)


[자주 나오는 메시지와 해결]
  "전송 실패, DB에 보관 중 N개"         -> 데이터는 posture_data.db에 안전하게 저장 중. 아래 원인 해결하면 자동 전송
  "전송 실패 ... timed out"            -> server_url의 IP가 틀렸거나, 서버와 다른 네트워크에 있음
  "전송 실패 ... Connection refused"   -> 서버(app.py)가 꺼져 있음
  "카메라 연결 실패, 5초 후 재시도"     -> 웹캠 연결 확인 / 다른 프로그램이 카메라 사용 중
                                         윈도우: 설정 > 개인 정보 > 카메라 > 데스크톱 앱 허용
  "config.json 형식 오류: N번째 줄"     -> 그 줄 근처의 쉼표, 따옴표 확인
                                         (한글 따옴표 “ ”, 마지막 줄 끝 쉼표, True 대문자 등)
  "가벼운 모델 다운로드 실패, 기본 모델로 실행" -> (model_complexity 0일 때) 인터넷이 막힌 것. 자동 해결됨
  "거북목 측정 N번째: 목 앞 Xcm ... -> 부족" -> 거북목 자세에서 목이 거의 안 움직임. 머리를 더 앞으로 (몸통은 그대로)
                                         "흔들림"이 크게 나오면 측정하는 3초 동안 가만히 있기
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
ARM_POINTS = (13, 14, 15, 16)   # 양쪽 팔꿈치, 손목: 어깨보다 위로 올라가면 팔을 든 것
EDGE_Y = 0.95   # 어깨가 화면 높이의 이 비율보다 아래면 화면 밖을 추측한 위치라 사용 안 함

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
# 서버로 보낼 때 프록시 설정(http_proxy 환경변수)을 무시하고 직접 연결.
# 라즈베리파이(리눅스)에 프록시가 설정돼 있으면 127.0.0.1로 보내는 것까지 프록시로 가서 실패하기 때문
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SEND_TIMEOUT = 5   # 라즈베리파이는 판별 계산으로 바빠서 서버 응답이 1초를 넘기기도 함


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
                _opener.open(req, timeout=SEND_TIMEOUT).close()  # 4xx/5xx는 예외 발생
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
# 얼굴 3D 모형(cm): MediaPipe 표준 얼굴 모형(canonical_face_model, Apache 2.0)에서
# 표정이 바뀌어도 거의 안 움직이는 33점(콧등·콧볼·눈 끝·광대·이마)만 골라 씀.
# 점이 많을수록 흔들림이 평균되어 머리 위치·거리가 훨씬 안정적 (예전 6점 -> 33점)
# 좌표 방향: x 오른쪽, y 아래, z 카메라에서 멀어지는 쪽, 원점은 코끝
FACE_MODEL = {
    1: (0.0, -0.0, -0.0),
    4: (0.0, -0.66, -0.11),
    5: (0.0, -1.49, 0.23),
    195: (0.0, -2.19, 0.7),
    197: (0.0, -2.86, 1.16),
    6: (0.0, -3.6, 1.69),
    168: (0.0, -4.4, 2.24),
    8: (0.0, -5.15, 2.19),
    9: (0.0, -6.01, 2.09),
    151: (0.0, -7.67, 2.45),
    10: (0.0, -9.39, 2.99),
    98: (-1.41, 0.59, 2.23),
    327: (1.41, 0.59, 2.23),
    129: (-1.79, -0.15, 2.63),
    358: (1.79, -0.15, 2.63),
    33: (-4.45, -3.79, 4.3),
    263: (4.45, -3.79, 4.3),
    133: (-1.86, -3.71, 3.72),
    362: (1.86, -3.71, 3.72),
    116: (-6.47, -2.06, 5.79),
    345: (6.47, -2.06, 5.79),
    123: (-6.34, -0.6, 5.59),
    352: (6.34, -0.6, 5.59),
    50: (-4.77, -0.43, 3.94),
    280: (4.77, -0.43, 3.94),
    54: (-6.28, -7.74, 6.05),
    284: (6.28, -7.74, 6.05),
    103: (-5.13, -8.61, 4.82),
    332: (5.13, -8.61, 4.82),
    67: (-3.52, -9.13, 3.75),
    297: (3.52, -9.13, 3.75),
    109: (-1.89, -9.36, 3.2),
    338: (1.89, -9.36, 3.2),
}
FACE_IDX = list(FACE_MODEL)
FACE_3D = np.array([FACE_MODEL[i] for i in FACE_IDX], dtype=np.float64)
# 귀(양쪽 귀 앞 가운데) 위치: 코끝보다 1.8cm 위, 9.9cm 뒤.
# 거북목 판정은 코가 아니라 귀 위치로 함 -> 고개만 숙이거나 끄덕일 때는 귀가 거의 안 움직여서 오판이 줄어듦
EAR_3D = np.array([0.0, -1.8, 9.9])

CAMERA_TILT = 10          # 카메라가 아래로 기울어진 각도(도). main()에서 config의 camera_tilt_deg로 바꿈
TORSO_LEN = 50.0           # 고관절~어깨 길이(cm). 성인 평균 근사 (몸통 기울기 계산에 사용)
SHOULDER_MEMORY_SEC = 10   # 팔을 들어 어깨 점을 못 믿을 때, 마지막으로 믿을 수 있던 어깨를 이 시간 동안 사용
FACE_HIDDEN_HOLD = 3       # 사람은 보이는데 얼굴만 가려졌을 때(손 등) 마지막 판정을 유지하는 시간(초)


def head_pose(cv2, face_lm, w, h, fov_deg=65):
    """얼굴 33점을 3D 모형에 맞춰(solvePnP) 고개 각도·카메라까지 거리(cm)·귀의 3D 위치를 구함.
    fov_deg: 카메라 가로 화각. 노트북·모니터 웹캠은 보통 60~78도"""
    pts = np.array([(face_lm[i].x * w, face_lm[i].y * h) for i in FACE_IDX], dtype=np.float64)
    f = (w / 2) / math.tan(math.radians(fov_deg) / 2)   # 화각으로 구한 초점거리(픽셀)
    cam = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]], dtype=np.float64)
    flag = getattr(cv2, "SOLVEPNP_SQPNP", cv2.SOLVEPNP_ITERATIVE)
    ok, rvec, tvec = cv2.solvePnP(FACE_3D, pts, cam, None, flags=flag)
    if not ok or tvec[2, 0] <= 0:
        return None
    R = cv2.Rodrigues(rvec)[0]
    fx, fy, fz = R @ np.array([0.0, 0.0, -1.0])   # 얼굴이 향한 방향
    ear = R @ EAR_3D + tvec[:, 0]
    return {"pitch": math.degrees(math.atan2(fy, -fz)),   # +: 고개 숙임
            "yaw": math.degrees(math.atan2(fx, -fz)),     # 좌우로 돌린 각도
            "dist": tvec[2, 0],                           # 카메라까지 거리 (cm)
            "ear": ear.tolist(),                          # 귀의 3D 위치 (cm, 카메라 기준)
            "f": f}


def shoulder_problem(pose_lm):
    """어깨 점을 못 믿는 이유. 믿을 수 있으면 None
    "hidden": 잘 안 보이거나 화면 아래 끝에 걸림(Pose가 추측한 위치)
    "arms"  : 팔꿈치·손목이 어깨보다 위 (팔을 들면 어깨 점이 팔을 따라 움직임)
    "twist" : 몸을 45도 이상 비틂 (어깨 너비로 거리를 재는데 비틀면 좁아 보임)"""
    shoulders = (LEFT_SHOULDER, RIGHT_SHOULDER)
    if min(pose_lm[i].visibility for i in shoulders) < VIS_MIN:
        return "hidden"
    if max(pose_lm[i].y for i in shoulders) > EDGE_Y:
        return "hidden"
    top = min(pose_lm[i].y for i in shoulders)
    if any(pose_lm[i].visibility >= 0.5 and pose_lm[i].y < top for i in ARM_POINTS):
        return "arms"
    ls, rs = pose_lm[LEFT_SHOULDER], pose_lm[RIGHT_SHOULDER]
    if abs(ls.z - rs.z) >= 1.0 * abs(ls.x - rs.x):   # z(앞뒤)는 흔들림이 커서 아주 크게 비틀었을 때만 판단
        return "twist"
    return None


def get_features(cv2, pose_lm, face_lm, w, h, fov_deg=65, use_shoulders=True):
    """({"pose": head_pose 결과, "shoulder": 어깨(픽셀) 또는 None, "tilt": 어깨 기울기 또는 None, ...}, None)
    또는 판정할 수 없을 때 (None, 화면에 띄울 이유)"""
    if face_lm is None:
        return None, "FACE NOT FOUND - look at camera"
    hp = head_pose(cv2, face_lm, w, h, fov_deg)
    if hp is None:
        return None, "FACE NOT FOUND - look at camera"
    if abs(hp["yaw"]) > 35:
        return None, "TURN TO CAMERA"
    feats = {"pose": hp, "c": (w / 2, h / 2), "shoulder": None, "tilt": None, "sh_problem": "hidden"}

    # 어깨: 믿을 수 있고, 얼굴이 두 어깨 사이에 있을 때만(같은 사람인지 확인) 사용
    if use_shoulders and pose_lm is not None:
        feats["sh_problem"] = shoulder_problem(pose_lm)
    if feats["sh_problem"] is None:
        ls = (pose_lm[LEFT_SHOULDER].x * w, pose_lm[LEFT_SHOULDER].y * h)
        rs = (pose_lm[RIGHT_SHOULDER].x * w, pose_lm[RIGHT_SHOULDER].y * h)
        nose_x, sw = face_lm[1].x * w, math.dist(ls, rs)
        if sw > 1 and min(ls[0], rs[0]) < nose_x < max(ls[0], rs[0]):
            feats["shoulder"] = {"x": (ls[0] + rs[0]) / 2, "y": (ls[1] + rs[1]) / 2, "sw": sw}
        else:
            feats["sh_problem"] = "hidden"
            feats["tilt"] = math.degrees(math.atan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0])))
    return feats, None


def shoulder_3d(sh, f, c, z):
    """어깨 가운데(픽셀)와 거리(cm) -> 카메라 기준 3D 위치(cm)"""
    return np.array([(sh["x"] - c[0]) / f * z, (sh["y"] - c[1]) / f * z, z])


def make_base(good):
    """바른 자세 측정값으로 기준을 만듦: 귀 위치, 어깨 위치, 귀~어깨 거리.
    어깨 실제 너비는 모르므로 '바른 자세에서는 어깨가 귀와 같은 거리에 있다'고 보고 정함"""
    ear0 = np.median([g["pose"]["ear"] for g in good], axis=0)
    base = {"version": MODEL_VERSION, "ear": ear0.tolist()}
    with_sh = [g for g in good if g.get("sh_use")]
    if len(with_sh) >= 0.7 * len(good):
        f, c = good[0]["pose"]["f"], good[0]["c"]
        sh = {k: statistics.median(g["sh_use"][k] for g in with_sh) for k in ("x", "y", "sw")}
        # 바른 자세에서 어깨는 귀 바로 아래. 카메라가 camera_tilt_deg만큼 내려다보면
        # 어깨가 귀보다 (귀~어깨 높이 x sin 기울기)만큼 카메라에서 더 멀리 있음
        z0 = ear0[2]
        for _ in range(3):
            gap = shoulder_3d(sh, f, c, z0)[1] - ear0[1]     # 화면 기준 귀~어깨 높이 차이(cm)
            z0 = ear0[2] + gap * math.tan(math.radians(CAMERA_TILT))
        sh0 = shoulder_3d(sh, f, c, z0)
        base.update(sw0=sh["sw"], sh=sh0.tolist(), neck=float(np.linalg.norm(ear0 - sh0)))
        tilts = [g["tilt"] for g in with_sh if g["tilt"] is not None]
        if tilts:
            base["tilt"] = statistics.median(tilts)
    return base


def neck_offset(feats, base):
    """귀가 바른 자세보다 앞으로/아래로 움직인 거리(cm) 중에서 '몸통이 움직여서 생긴 만큼'을 뺀 값과,
    몸통 숙임 각도(도, 참고용)를 돌려줌.
    고관절을 축으로 몸통을 숙이면(척추 중립) 고관절-어깨-귀가 한 직선처럼 같이 돌아서,
    귀는 어깨가 움직인 만큼의 (몸통+목)/몸통 배(약 1.3배) 움직임. 그만큼 빼면 '목만 움직인 양'이 남음
    -> 고관절로 숙이기, 뒤로 기대기, 의자째 다가가기는 거북목으로 안 봄
    어깨 앞뒤 위치는 어깨 너비로(가까워지면 넓게 보임), 위아래는 화면 속 어깨 높이로 구함"""
    ear, ear0 = np.array(feats["pose"]["ear"]), np.array(base["ear"])
    move = ear - ear0
    lean = 0.0
    sh = feats.get("sh_use")
    if sh is not None and "sw0" in base:
        sh0 = np.array(base["sh"])
        z = sh0[2] * base["sw0"] / sh["sw"]                 # 어깨까지 거리
        sh_move = shoulder_3d(sh, feats["pose"]["f"], feats["c"], z) - sh0
        sh_move[0] = 0.0                                    # 좌우 이동은 거북목과 상관없음
        # 어깨가 멀어져 보이면(좁아 보임) 뒤로 기대기 또는 몸 비틀기.
        # 뒤로 기대면 어깨가 화면에서 위로도 올라가고, 비틀면 높이는 그대로 -> 높이가 맞는 만큼만 '기대기'로 인정
        # (비틀기를 기대기로 잘못 보면 귀가 앞으로 나온 것처럼 계산되기 때문)
        if sh_move[2] > 0:
            f = feats["pose"]["f"]
            expect = f * sh0[1] / (sh0[2] + sh_move[2]) - f * sh0[1] / sh0[2]   # 기댔다면 화면 높이 변화(픽셀)
            actual = (sh["y"] - feats["c"][1]) - f * sh0[1] / sh0[2]
            agree = min(max(actual / expect, 0.0), 1.0) if expect < -2 else 0.0
            sh_move[2] *= agree
        # 어깨가 앞뒤로는 거의 안 움직이고 위로만 움직이면 몸통 숙임이 아니라 어깨 으쓱 -> 그만큼은 무시
        sh_move[1] = max(sh_move[1], -0.6 * abs(sh_move[2]) - 1.0)
        body = (TORSO_LEN + base["neck"]) / TORSO_LEN * sh_move   # 몸통이 움직여서 생긴 귀 이동
        move = move - body
        lean = math.degrees(math.asin(max(-1.0, min(1.0, -sh_move[2] / TORSO_LEN))))
        # 몸통 길이·카메라 각도는 사람마다 달라서 위 계산이 조금 틀릴 수 있음 ->
        # 몸통이 많이 움직였을 때는 그 12%만큼은 '오차'로 보고 봐줌 (몸을 크게 숙여도 오판 안 하게)
        margin = 0.12 * float(np.linalg.norm(body))
        fwd, down = -move[2], move[1]
        fwd = max(fwd - margin, 0.0) if fwd > 0 else fwd
        down = max(down - margin / 2, 0.0) if down > 0 else down
        return fwd, down, lean
    return -move[2], move[1], lean                          # 앞으로(카메라 쪽), 아래로, 몸통 숙임


# ======================== 개인 맞춤 학습 ========================
MIN_SEPARATION = 2.0   # 두 자세 차이가 같은 자세 안에서의 흔들림의 몇 배 이상이어야 학습 성공
MIN_MOVE_CM = 1.5      # 거북목 자세에서 목이 최소 이만큼(cm)은 움직여야 학습 성공
MAX_TRIES = 3          # 거북목 측정을 이만큼 해도 부족하면 기준을 낮춰 보고, 그래도 안 되면 바른 자세부터 다시
MODEL_VERSION = 3      # 저장된 학습 결과(baseline.json) 형식. 바뀌면 예전 파일은 다시 학습


def train(good, bad, force=False):
    """바른 자세로 기준을 만들고, 거북목 자세에서 목이 몸통 기준으로 얼마나(cm) 움직였는지 학습.
    점수 = 지금 목의 움직임을 '학습한 거북목 방향'에 비춰 본 비율 (바른 자세 0, 학습한 거북목 100).
    force: 여러 번 다시 측정했으면 기준을 낮춤 (1cm 이상 움직였으면 학습)
    반환: (모델 또는 None, 구분 정도, 목 움직임 [앞 cm, 아래 cm], 흔들림 cm)"""
    base = make_base(good)
    G = np.array([neck_offset(g, base)[:2] for g in good])
    B = np.array([neck_offset(b, base)[:2] for b in bad])
    mg, mb = G.mean(axis=0), B.mean(axis=0)
    delta = mb - mg
    size = float(np.linalg.norm(delta))
    if size < 1e-6:
        return None, 0.0, delta.tolist(), 0.0
    proj = np.vstack([G - mg, B - mb]) @ delta / size        # 같은 자세 안에서의 흔들림
    noise = max(float(proj.std()), 0.3)                       # 흔들림 최소 0.3cm로 봄
    sep = size / noise
    ok = size >= MIN_MOVE_CM and sep >= MIN_SEPARATION and delta[0] > -0.5   # 뒤로 간 건 거북목 아님
    if force:   # 여러 번 했으면 기준을 조금 낮춰 줌 (그래도 흔들림 수준이면 실패)
        ok = size >= 1.0 and sep >= 1.5 and delta[0] > -0.5
    if not ok:
        return None, sep, delta.tolist(), noise
    base.update(good=mg.tolist(), delta=delta.tolist())
    return base, sep, delta.tolist(), noise


def can_judge(model, feats):
    """어깨까지 써서 학습했는데 지금 어깨를 모르면, 몸통 움직임을 뺄 수 없어서 판정하지 않음"""
    return "sw0" not in model or feats.get("sh_use") is not None


def posture_score(model, feats):
    """0 = 바른 자세, 100 = 학습한 거북목.
    지금 목의 움직임(앞으로, 아래로 cm)을 '학습한 거북목 방향'에 비춰 본 비율.
    학습 때보다 숙이지 않고 머리만 내밀어도 앞으로 나온 만큼 점수가 오름"""
    fwd, down, _ = neck_offset(feats, model)
    x = np.array([fwd, down]) - np.array(model["good"])
    d = np.array(model["delta"])
    return float(x @ d / (d @ d)) * 100


class Smooth:
    """귀·어깨 측정값을 모두 '같은 시간(tau초)만큼' 부드럽게 함.
    귀와 어깨가 똑같이 늦어져야 서로 어긋나지 않아서, 몸을 움직이는 순간에 점수가 튀지 않음"""
    def __init__(self, tau=0.15):
        self.tau, self.v, self.t = tau, {}, {}

    def __call__(self, key, x, now):
        x = np.asarray(x, dtype=np.float64)
        if key not in self.v or now - self.t[key] > 0.5:   # 처음이거나 한동안 없었으면 새로 시작
            self.v[key] = x
        else:
            a = 1 - math.exp(-(now - self.t[key]) / self.tau)
            self.v[key] = self.v[key] + a * (x - self.v[key])
        self.t[key] = now
        return self.v[key]


def prepare(sm, feats, now):
    """판정 전 준비: 귀·어깨를 같은 정도로 부드럽게 하고,
    지금 어깨를 믿을 수 없으면(팔을 듦 등) 최근에 믿을 수 있던 어깨(부드럽게 한 값)를 대신 사용"""
    out = dict(feats, pose=dict(feats["pose"]), sh_from_memory=False)
    out["pose"]["ear"] = sm("ear", feats["pose"]["ear"], now).tolist()
    sh = feats["shoulder"]
    cx, cy = feats["c"]
    # 어깨는 (1/너비, 가로위치/너비, 세로위치/너비)를 부드럽게 함 = 어깨의 3D 위치를 부드럽게 하는 것과 같음.
    # 귀도 3D 위치를 부드럽게 하므로 둘이 정확히 같은 방식으로 늦어져서, 빨리 움직여도 서로 어긋나지 않음
    if sh is not None:
        v = sm("sh", [1 / sh["sw"], (sh["x"] - cx) / sh["sw"], (sh["y"] - cy) / sh["sw"]], now)
    elif feats["sh_problem"] in ("arms", "twist") and "sh" in sm.v and now - sm.t["sh"] < SHOULDER_MEMORY_SEC:
        # 팔을 들거나 잠깐 비틀었을 때만 기억 사용 (몸통은 그대로라고 볼 수 있음).
        # 어깨가 화면 밖으로 나간 건 몸이 크게 움직인 것이라 기억을 쓰면 안 됨
        v, out["sh_from_memory"] = sm.v["sh"], True
    else:
        out["sh_use"] = None
        return out
    sw = 1 / v[0]
    out["sh_use"] = {"x": v[1] * sw + cx, "y": v[2] * sw + cy, "sw": sw}
    return out


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
    """점수 -> 정상/경고/위험. 이미 경고/위험이면 기준을 hysteresis_pct만큼 낮춰 경계에서 깜빡이지 않게"""
    gap = cfg.get("hysteresis_pct", 2)
    warn = cfg["warning_pct"] - (gap if prev != "정상" else 0)
    danger = cfg["danger_pct"] - (gap if prev == "위험" else 0)
    if pct < warn:
        return "정상"
    return "경고" if pct < danger else "위험"


def hold(raw, since, danger_after_sec, now):
    """경고 기준을 넘으면 바로 경고, 위험 기준을 넘은 상태가 danger_after_sec 이어지면 위험.
    since: (나쁜 자세 시작 시각, 위험 기준 넘은 시각) 또는 None. 반환: (상태, since, 나쁜 자세 지속시간)"""
    if raw == "정상":
        return "정상", None, 0.0
    bad, danger = since or (None, None)
    bad = bad or now
    danger = (danger or now) if raw == "위험" else None
    status = "위험" if danger is not None and now - danger >= danger_after_sec else "경고"
    return status, (bad, danger), now - bad


STATUS_URL = None   # main()에서 server_url로 정함. 예) http://127.0.0.1:5050/api/status


def post_status(status):
    """지금 상태를 서버 /api/status로 바로 보냄 -> 라즈베리파이(rpi_device.py)가 가져가서 LED/부저/진동 제어.
    실패해도 다음 상태 변경이나 save_interval마다 다시 보내므로 기록만 남김"""
    def _post():
        try:
            req = urllib.request.Request(
                STATUS_URL, data=json.dumps({"status": status}, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST")
            _opener.open(req, timeout=SEND_TIMEOUT).close()
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


def draw(cv2, mp, frame, pose_res, face_lm, text, color, sub, pct, cfg, fps_text=""):
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
        for th in (cfg["warning_pct"], cfg["danger_pct"]):   # 경고·위험 기준선
            tx = x0 + int((x1 - x0) * th / 120)
            cv2.line(frame, (tx, y0 - 3), (tx, y0 + 18), (255, 255, 255), 2)
    cv2.putText(frame, "c: recalibrate  q: quit", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    if fps_text:
        cv2.putText(frame, fps_text, (w - 360, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
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
def open_camera(cv2, cfg, stop_event):
    """카메라 열기. 60fps를 쓰려면 대부분의 웹캠이 MJPG 방식이어야 해서 먼저 MJPG로 요청.
    안 열리면 5초마다 다시 시도"""
    api = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY   # 라즈베리파이는 V4L2
    want_w, want_h = cfg.get("camera_width", 640), cfg.get("camera_height", 480)
    want_fps, fourcc = cfg.get("camera_fps", 60), cfg.get("camera_fourcc", "MJPG")
    while running and not stop_event.is_set():
        cap = cv2.VideoCapture(cfg.get("camera_index", 0), api)
        if cap.isOpened():
            if fourcc:   # 해상도보다 먼저 정해야 적용되는 카메라가 많음
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, want_w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, want_h)
            cap.set(cv2.CAP_PROP_FPS, want_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # 오래된 화면을 쌓아 두지 않음 (지원하는 카메라만)
            log.info(f"카메라 연결 성공 (요청 {want_w}x{want_h} {want_fps}fps -> 카메라 응답 "
                     f"{cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f} "
                     f"{cap.get(cv2.CAP_PROP_FPS):.0f}fps)")
            return cap
        cap.release()
        log.warning("카메라 연결 실패, 5초 후 재시도")
        stop_event.wait(5)
    return None


class Rate:
    """초당 처리 횟수(fps) 측정"""
    def __init__(self):
        self.n, self.t0, self.value = 0, time.time(), 0.0

    def tick(self):
        self.n += 1
        dt = time.time() - self.t0
        if dt >= 2:
            self.value, self.n, self.t0 = self.n / dt, 0, time.time()


class CameraThread(threading.Thread):
    """카메라 읽기 전용 쓰레드. 항상 '가장 최근 화면' 하나만 보관해서,
    분석이 느려도 오래된 화면이 쌓이지 않음. 새 화면이 오면 기다리는 쓰레드들을 깨움"""
    def __init__(self, cv2, cfg, stop_event):
        super().__init__(daemon=True, name="camera")
        self.cv2, self.cfg, self.stop_event = cv2, cfg, stop_event
        self.cond = threading.Condition()
        self.frame, self.seq, self.shape, self.rate = None, 0, (480, 640), Rate()

    def run(self):
        cap, checked = None, False
        try:
            while running and not self.stop_event.is_set():
                if cap is None:
                    cap = open_camera(self.cv2, self.cfg, self.stop_event)
                    if cap is None:
                        break
                    opened_at = time.time()
                ok, frame = cap.read()
                if not ok:
                    log.warning("프레임 읽기 실패, 카메라 재연결")
                    cap.release()
                    cap = None
                    continue
                with self.cond:
                    self.frame, self.seq, self.shape = frame, self.seq + 1, frame.shape[:2]
                    self.cond.notify_all()
                self.rate.tick()
                if not checked and time.time() - opened_at > 5:   # 실제로 나오는 속도 한 번 확인
                    checked, want = True, self.cfg.get("camera_fps", 60)
                    log.info(f"카메라 실제 속도 {self.rate.value:.0f}fps (요청 {want}fps)")
                    if self.rate.value < want * 0.8:
                        log.warning("카메라가 요청한 속도보다 느림 -> 웹캠이 이 속도를 지원하지 않거나, "
                                    "조명이 어두워 노출 시간이 길어진 것 (조명을 밝게)")
        except Exception:
            log.exception("카메라 쓰레드 오류")
        finally:
            if cap is not None:
                cap.release()
            with self.cond:
                self.cond.notify_all()

    def latest(self):
        with self.cond:
            return self.seq, self.frame

    def wait_new(self, last_seq, timeout):
        """last_seq 다음 화면이 올 때까지 기다림 (계속 확인하며 CPU를 쓰지 않음). 시간 초과면 (last_seq, None)"""
        with self.cond:
            self.cond.wait_for(lambda: self.seq != last_seq or self.stop_event.is_set(), timeout)
            return (self.seq, self.frame) if self.seq != last_seq else (last_seq, None)


class ModelThread(threading.Thread):
    """MediaPipe 모델 하나만 전담하는 쓰레드 (얼굴용 1개, 어깨용 1개).
    - MediaPipe는 계산하는 동안 파이썬 잠금(GIL)을 풀어 줘서, 쓰레드마다 다른 CPU 코어에서 동시에 계산됨
    - 새 화면이 왔을 때만, 초당 fps번까지만 계산하고 남는 시간은 쉼 -> CPU를 다 쓰지 않음"""
    def __init__(self, name, cv2, make_model, pick, camera, fps, stop_event):
        super().__init__(daemon=True, name=name)
        self.cv2, self.make_model, self.pick, self.camera = cv2, make_model, pick, camera
        self.interval, self.stop_event = 1 / max(fps, 0.5), stop_event
        self.cond = threading.Condition()
        self.result, self.stamp, self.id, self.rate = None, 0.0, 0, Rate()
        self.frame_seq, self.history = -1, deque(maxlen=90)   # 결과가 나온 화면 번호, 최근 결과들

    def run(self):
        try:
            with self.make_model() as model:
                last_seq = -1
                while running and not self.stop_event.is_set():
                    start = time.time()
                    seq, frame = self.camera.wait_new(last_seq, 0.5)
                    if frame is None:
                        continue
                    last_seq = seq
                    rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False   # 복사 없이 넘겨서 조금 더 빠르게
                    out = self.pick(model.process(rgb))
                    with self.cond:
                        self.result, self.stamp, self.id, self.frame_seq = out, time.time(), self.id + 1, seq
                        self.history.append((seq, out))
                        self.cond.notify_all()
                    self.rate.tick()
                    self.stop_event.wait(max(0.0, self.interval - (time.time() - start)))   # 남는 시간은 쉼
        except Exception:
            log.exception(f"{self.name} 쓰레드 오류")
        finally:
            with self.cond:
                self.cond.notify_all()

    def latest(self):
        with self.cond:
            return self.id, self.result, self.stamp

    def latest_full(self):
        with self.cond:
            return self.id, self.result, self.stamp, self.frame_seq

    def find(self, seq):
        """화면 번호 seq와 같은(없으면 가장 가까운) 화면의 결과. 없으면 가장 최근 결과"""
        with self.cond:
            if not self.history:
                return self.result
            return min(self.history, key=lambda h: abs(h[0] - seq))[1]

    def wait_new(self, last_id, timeout):
        """새 결과가 나올 때까지 기다림. 시간 초과면 예전 결과 그대로"""
        with self.cond:
            self.cond.wait_for(lambda: self.id != last_id or self.stop_event.is_set(), timeout)
            return self.id, self.result, self.stamp


POSE_MAX_AGE = 1.0   # 어깨 결과가 이보다 오래됐으면 쓰지 않음(초)


# ======================== 메인 루프 ========================
READY_SEC = 3   # 보정 단계마다 준비 카운트다운(초)


def run(cfg):
    import cv2
    import mediapipe as mp

    stop_event = threading.Event()   # run()이 끝나면 쓰레드들도 같이 끝내기 위한 신호
    camera = CameraThread(cv2, cfg, stop_event)
    face_thread = ModelThread(
        "face", cv2,
        lambda: mp.solutions.face_mesh.FaceMesh(max_num_faces=1, min_detection_confidence=0.5,
                                                min_tracking_confidence=0.5),
        lambda r: r.multi_face_landmarks[0].landmark if r.multi_face_landmarks else None,
        camera, cfg.get("analysis_fps", 30), stop_event)
    pose_thread = None
    if cfg.get("use_shoulders", True):   # 어깨를 안 쓰면 가장 무거운 계산을 아예 안 함
        pose_thread = ModelThread("pose", cv2, lambda: make_pose(mp, cfg.get("model_complexity", 1)),
                                  lambda r: r, camera, cfg.get("pose_fps", 5), stop_event)
    threads = [t for t in (camera, face_thread, pose_thread) if t is not None]
    for t in threads:
        t.start()
    screen_rate, last_fps_log, fps_text = Rate(), time.time(), ""

    reset_sec = cfg.get("new_person_reset_sec", 5)
    model = load_json(BASELINE_FILE) if reset_sec == 0 else None   # 전시회 모드면 매번 새로 학습
    if model and model.get("version") != MODEL_VERSION:
        model = None   # 예전 버전 파일 (거리 단위 등이 달라서 다시 학습)
    phase = "run" if model else "wait"   # wait -> good_ready -> good_rec -> bad_ready -> bad_rec -> run
    phase_start, good, bad, retry_msg_until = 0.0, [], [], 0.0
    tries, temp_base, retry_msg = 0, None, ""   # 거북목 측정 횟수, 바른 자세 기준(학습 중 안내용), 다시 측정 이유
    filt = OneEuro()
    status, raw, bad_since = "정상", "정상", None
    last_save = last_valid = time.time()
    last_seen = 0.0
    sm = Smooth(cfg.get("smooth_sec", 0.25))   # 귀·어깨를 같은 정도로 부드럽게 (+ 팔 들 때 어깨 기억)
    pct, duration = None, 0.0
    pose_res, face_lm, text, sub, color = None, None, "STARTING", "", GRAY
    show = cfg.get("show_window", True) and has_display()
    if not show:
        log.info("카메라 창 없이 실행 (모니터 없음 또는 show_window=false)")

    def set_status(new):
        nonlocal status, last_save
        if new != status:
            on_status_change(status, new)
            status = new
            last_save = 0   # 상태가 바뀌면 전송 주기를 기다리지 않고 바로 기록

    def restart_calibration(why):
        nonlocal model, phase, good, bad, pct, bad_since, raw, filt
        log.info(f"{why} -> 자세 학습 다시 시작")
        model, phase, good, bad, pct, bad_since, raw, filt = None, "wait", [], [], None, None, "정상", OneEuro()
        set_status("정상")

    try:
        cam_seq, face_id, pose_id = -1, 0, 0
        while running:
            if not camera.is_alive() or not face_thread.is_alive():
                log.warning("카메라 또는 얼굴 쓰레드가 멈춤 -> 다시 시작")
                break
            if show:   # 화면은 카메라 속도(최대 camera_fps) 그대로 부드럽게 갱신
                cam_seq, frame = camera.wait_new(cam_seq, 0.5)
                if frame is None:
                    continue
                fid, new_face, _ = face_thread.latest()
            else:      # 창이 없으면 새 얼굴 결과가 나올 때만 깨어나서 CPU를 아낌
                fid, new_face, _ = face_thread.wait_new(face_id, 0.5)

            # 판정할 때는 '같은 화면'에서 나온 얼굴과 어깨를 짝지어 씀.
            # (어깨는 초당 5번, 얼굴은 30번 계산해서, 최신 결과끼리 쓰면 빨리 움직일 때 서로 다른 순간이 섞여
            #  몸통만 숙여도 귀만 먼저 앞으로 간 것처럼 보임) -> 어깨 결과가 새로 나올 때마다 판정
            new_face_result = fid != face_id
            if new_face_result:
                face_id, face_lm = fid, new_face        # 화면에 그리는 얼굴 점은 항상 최신
            judge, pose_res, judge_face = False, None, new_face
            if pose_thread is None:
                judge = new_face_result
            else:
                pid, res, stamp, pseq = pose_thread.latest_full()
                if pid != pose_id:
                    pose_id, judge = pid, True
                    pose_res, judge_face = res, face_thread.find(pseq)
                elif new_face_result and time.time() - stamp > POSE_MAX_AGE:
                    judge = True                         # 어깨 계산이 멈췄으면 얼굴만으로

            if judge:   # 판정 자체는 계산량이 아주 적음
                now = time.time()
                h, w = camera.shape
                pose_lm = pose_res.pose_landmarks.landmark if pose_res and pose_res.pose_landmarks else None
                feats, reason = get_features(cv2, pose_lm, judge_face, w, h, cfg.get("camera_fov_deg", 65),
                                             cfg.get("use_shoulders", True))
                if judge_face is not None or pose_lm is not None:
                    last_seen = now
                if feats is not None:
                    feats = prepare(sm, feats, now)
                    if phase == "run" and not can_judge(model, feats):
                        feats, reason = None, "MOVE BACK - show both shoulders"

                # 사람(몸)은 보이는데 얼굴만 가려진 경우(손으로 가림 등): 판정 중이면 잠깐 마지막 결과 유지
                hidden = feats is None and pose_lm is not None and phase == "run"
                if hidden and now - last_valid <= FACE_HIDDEN_HOLD:
                    sub = "face hidden - keeping last result"
                elif feats is None:
                    text, sub, color = ("NO PERSON" if now - last_seen > 0.3 else reason), "", GRAY
                    if now - last_valid > (FACE_HIDDEN_HOLD if hidden else ABSENT_SEC):   # 판정 불가가 이어지면 자리 비움
                        bad_since, raw = None, "정상"
                        set_status("정상")
                    # 학습 중에는 잠깐(3초 이내) 안 보이는 건 기다림 (그동안은 측정만 멈춤). 오래 안 보이면 처음부터
                    if phase not in ("wait", "run") and now - last_valid > FACE_HIDDEN_HOLD:
                        log.info(f"학습 중 사람이 {FACE_HIDDEN_HOLD}초 넘게 안 보임 -> 처음부터 다시")
                        phase, good, bad, tries = "wait", [], [], 0
                    if model and reset_sec and now - last_seen > reset_sec:
                        restart_calibration("사람이 떠남(새 관람객 대비)")
                else:
                    if phase in ("good_rec", "bad_rec") and now - last_valid > 0.5:
                        phase_start += now - last_valid   # 잠깐 안 보였던 시간만큼 측정 시간을 늘려 줌
                    last_valid = now
                    if phase == "wait":
                        phase, phase_start = "good_ready", now
                        log.info("사람 감지, 자세 학습 시작")

                    # ---------- 자세 학습: 바른 자세 -> 나쁜 자세 ----------
                    if phase in ("good_ready", "bad_ready"):
                        left = READY_SEC - (now - phase_start)
                        step = "1/2  SIT UP STRAIGHT" if phase == "good_ready" else "2/2  NOW TURTLE NECK!"
                        text, color = f"{step}  {math.ceil(max(left, 0))}", YELLOW
                        sub = retry_msg if now < retry_msg_until \
                            else ("Sit tall, chin in" if phase == "good_ready"
                                  else "Push your head forward like usual bad posture")
                        if phase == "bad_ready" and temp_base is not None and now >= retry_msg_until:
                            sub += f"  (head forward {neck_offset(feats, temp_base)[0]:+.1f}cm)"
                        if left <= 0:
                            phase = "good_rec" if phase == "good_ready" else "bad_rec"
                            phase_start = now
                    elif phase in ("good_rec", "bad_rec"):
                        (good if phase == "good_rec" else bad).append(feats)
                        text = "1/2  HOLD STRAIGHT..." if phase == "good_rec" else "2/2  HOLD IT..."
                        sub, color = f"recording {max(cfg['calib_sec'] - (now - phase_start), 0):.1f}s", YELLOW
                        if phase == "bad_rec" and temp_base is not None:
                            sub += f"  (head forward {neck_offset(feats, temp_base)[0]:+.1f}cm)"
                        if now - phase_start >= cfg["calib_sec"]:
                            if phase == "good_rec":
                                phase, phase_start, bad, tries = "bad_ready", now, [], 0
                                temp_base = make_base(good)
                                log.info(f"바른 자세 측정 완료 ({len(good)}개, 어깨 사용: {'sw0' in temp_base})")
                            else:
                                tries += 1
                                model, sep, delta, noise = train(good, bad, force=tries >= MAX_TRIES)
                                log.info(f"거북목 측정 {tries}번째: 목 앞 {delta[0]:+.1f}cm, 아래 {delta[1]:+.1f}cm, "
                                         f"흔들림 {noise:.1f}cm, 구분 정도 {sep:.1f} -> {'성공' if model else '부족'}")
                                if model is None and tries >= MAX_TRIES:
                                    # 여러 번 해도 목이 거의 안 움직임 -> 바른 자세부터 다시 (무한 반복 방지)
                                    log.info("거북목 자세가 바른 자세와 거의 같음 -> 바른 자세부터 다시")
                                    phase, phase_start, good, bad, tries = "good_ready", now, [], [], 0
                                    retry_msg, retry_msg_until = "Let's start again from step 1", now + READY_SEC
                                elif model is None:
                                    phase, phase_start, bad = "bad_ready", now, []
                                    retry_msg_until = now + READY_SEC
                                    retry_msg = (f"Head moved only {math.hypot(*delta):.1f}cm - push it further forward"
                                                 if math.hypot(*delta) < MIN_MOVE_CM else
                                                 "Too shaky - hold still while recording")
                                else:
                                    phase, filt = "run", OneEuro()
                                    log.info(f"자세 학습 완료 (구분 정도 {sep:.1f}, 어깨 사용: {'sw0' in model}, "
                                             f"거북목 때 목이 앞으로 {model['delta'][0]:.1f}cm, 아래로 {model['delta'][1]:.1f}cm)")
                                    if "sw0" not in model:
                                        log.warning("어깨가 잘 안 보여서 몸통 보정 없이 판정 -> 몸을 숙이면 거북목으로 볼 수 있음")
                                    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                                        json.dump(model, f)

                    # ---------- 판별 ----------
                    else:
                        pct = min(max(filt(posture_score(model, feats), now), 0.0), 100.0)   # 0~100%로 제한
                        raw = raw_status(pct, cfg, raw)
                        new_status, bad_since, duration = hold(raw, bad_since, cfg.get("danger_after_sec", 2.5), now)
                        set_status(new_status)
                        text, color = f"{STATUS_EN[status]}  {pct:.0f}%", STATUS_COLOR[status]
                        sub = "" if "sw0" not in model or feats["sh_use"] else "shoulders not visible"

                        shoulder, tilt = None, feats["tilt"]
                        if tilt is not None and "tilt" in model:
                            shoulder = "틀어짐" if tilt - model["tilt"] >= cfg["shoulder_tilt_deg"] else "정상"
                        if now - last_save >= cfg["save_interval"]:
                            hp = feats["pose"]
                            fwd, down, lean = neck_offset(feats, model)
                            log.info(f"{status} 점수 {pct:.0f}% (목 앞으로 {fwd:+.1f}cm, 아래로 {down:+.1f}cm, "
                                     f"몸통 숙임 {lean:+.0f}°, 고개 {hp['pitch']:+.0f}°, 거리 {hp['dist']:.0f}cm, "
                                     f"어깨 {'기억' if feats['sh_from_memory'] else ('사용' if feats['sh_use'] else '안 씀')})")
                            threading.Thread(target=send, daemon=True, args=({
                                "user_id": cfg["user_id"],
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "worse_pct": round(pct, 1),
                                "status": status,
                                "shoulder_status": shoulder,
                                "shoulder_tilt": round(tilt, 1) if shoulder else None,
                                "bad_duration": round(duration, 1),
                            }, cfg["server_url"])).start()   # 백그라운드 전송: 서버가 느려도 화면이 안 멈춤
                            post_status(status)   # 살아 있다는 신호 겸 상태 재전송
                            last_save = now

                fps_text = (f"cam {camera.rate.value:.0f} / screen {screen_rate.value:.0f} / "
                            f"face {face_thread.rate.value:.0f} / pose "
                            + (f"{pose_thread.rate.value:.0f} fps" if pose_thread else "off"))
                if now - last_fps_log >= 10:
                    log.info(f"처리 속도: {fps_text}")
                    last_fps_log = now

            if show:
                screen_rate.tick()
                shown_pct = pct if phase == "run" else None
                # 그림은 복사본에 그림 (얼굴·어깨 쓰레드가 같은 화면을 읽는 중일 수 있어서)
                if draw(cv2, mp, frame.copy(), pose_res, face_lm, text, color, sub, shown_pct, cfg,
                        fps_text) == ord("c"):
                    if os.path.exists(BASELINE_FILE):
                        os.remove(BASELINE_FILE)
                    restart_calibration("c 키 입력")
    finally:
        stop_event.set()   # 카메라·얼굴·어깨 쓰레드 모두 종료
        for t in threads:
            t.join(timeout=3)
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
    global CAMERA_TILT
    CAMERA_TILT = cfg.get("camera_tilt_deg", CAMERA_TILT)
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