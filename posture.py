r"""
========================================================================
 거북목 판별기 (posture.py)   담당: 임진혁 - 로직 / 각도·자세 계산
========================================================================

[이 프로그램이 하는 일]
  정면 웹캠으로 얼굴과 어깨를 찾고, 처음에 그 사람의 "바른 자세"와 "거북목 자세"를
  직접 보여 달라고 해서 학습한 뒤, 지금 자세가 둘 중 어디에 가까운지 점수(%)로 판정한다.
  작품 전시용으로 관람객이 바뀌면 자동으로 새로 학습하고, 격하게 움직여도 바로 반응한다.

  웹캠 -> 자세 학습(바른 자세 2초 + 거북목 2초) -> 실시간 점수 -> 정상/경고/위험
       -> 3초마다(상태가 바뀌면 바로) 서버로 전송 -> 웹 페이지(http://서버IP:5050)에서 결과 확인


[판별 방식]  모니터 위(또는 노트북) 웹캠 1개로 정면에서 찍음
  1) 귀 위치를 3D로 계산
     Face Mesh(얼굴 468점) 중 표정이 바뀌어도 안 움직이는 33점(콧등·눈 끝·광대·이마)을
     MediaPipe 표준 얼굴 3D 모형에 맞춰서(solvePnP) 머리의 3D 위치를 구하고, 그중 "귀" 위치를 씀.
     -> 코가 아니라 귀를 보므로 고개만 숙이거나 끄덕이는 건(키보드 보기 등) 거의 영향 없음
  2) 몸통 움직임 빼기 (가장 중요)
     고관절을 축으로 몸을 숙이면(척추 중립) 고관절-어깨-귀가 한 직선처럼 같이 돌아서,
     귀는 어깨가 다가온 만큼의 (몸통+목)/몸통 배(약 1.3배)만큼 움직임 -> 그만큼을 빼면
     "목만 앞으로 나온 거리(cm)"가 남음. 이게 거북목.
     어깨(몸통)가 카메라 쪽으로 다가온 거리는 두 가지 단서로 잼:
       ① 어깨 너비: 가까워지면 넓게 보임      ② 어깨 높이: 가까워지면 화면에서 아래로 내려감
     두 단서가 둘 다 "다가왔다"고 할 때만 인정 -> 한쪽만 틀리게 잡혀도 걸러짐
     보정은 "빼는 쪽"으로만 함 -> 어깨만 움직여서는 점수가 절대 올라가지 않음
     -> 어깨 으쓱(얼굴 고정), 몸 비틀기, 뒤로 기대기, 고관절로 숙이기, 의자째 다가가기는 거북목으로 안 봄
     -> 숙인 상태에서 목까지 빼면 그건 거북목으로 잡음
     ※ 한계: 뒤로 기댄 채로 목만 뺀 자세는 못 잡음 (어깨 으쓱과 구분할 수 없어서, 오판을 막는 쪽을 택함)
  3) 개인 맞춤 학습: 바른 자세 2초 + 거북목 2초를 보여 주면, 거북목일 때 목이 몸통 기준으로
     앞으로·아래로 몇 cm 움직이는지 학습. 점수 = 지금 목 움직임을 그 방향에 비춘 비율
     (바른 자세 0%, 학습한 거북목 100%, 화면·전송은 0~100%로 제한)
     10% 이상이면 바로 경고, 20% 이상인 상태가 2.5초(danger_after_sec) 이어지면 위험
     점수는 초당 rise_per_sec(기본 40%)까지만 올라감 -> 뚝뚝 끊기지 않고 차오르듯 오름 (내려갈 때는 바로)
  4) 어깨를 못 쓰게 되면(팔을 듦, 어깨가 화면 밖, 잠깐 안 잡힘): 직전의 어깨를 기억해서 30초 동안 계속 판정
     사람은 있는데 잴 수 없으면(고개를 많이 숙여 얼굴이 안 잡힘, 얼굴 가림 등. 노란 선이 더 움직이지 않음):
     판별을 멈추지 않고 "마지막으로 잰 점수"로 계속 진행 (최대 30초)
     -> 점수 막대가 그 점수까지 계속 올라가고, 위험 판정(2.5초)과 서버 기록도 계속됨
     몸통 값 고정: 귀가 가만히 있는 동안에는 어깨로 잰 몸통 값을 바꾸지 않음
     -> 거북목 자세로 가만히 있을 때 어깨 측정이 흔들려도 점수가 흔들리다 정상으로 떨어지지 않음
     고개를 20도 넘게 돌리면(옆 사람과 대화 등): 머리 위치 계산이 부정확해져서 점수를 올리지 않음
  5) 한 사람만 따라가기: 처음 잡은 사람(가장 크게 보이는 얼굴)만 계속 따라감. 판정 중에 다른 사람이
     화면에 들어와도 무시하고, 어깨도 그 사람 주변만 잘라서 계산. 5초 넘게 안 보이면 다음 사람을 새로 잡고
     새로 학습

  빠른 반응을 위한 처리 (전시용)
  - 경고는 기다리지 않고 바로 표시 (자세가 바뀌고 약 0.3초 안에 반영)
  - 귀와 어깨 측정값을 똑같은 방식으로 부드럽게 함: 움직일 때는 0.25초(smooth_sec), 가만히 있을 때는
    0.6초로 더 부드럽게 (둘이 똑같이 늦어져야 빨리 움직여도 서로 어긋나지 않음)
  - 점수는 최근 3번의 가운데 값(한 번 튀는 값 무시) -> One Euro 필터
  - 얼굴(초당 30번)과 어깨(초당 10번)는 계산 속도가 달라서, 판정할 때는 "같은 화면"에서 나온
    얼굴과 어깨를 짝지어 씀 (안 그러면 빨리 숙일 때 귀만 먼저 움직인 것처럼 보여 순간 오판)
  - 경고에 들어간 뒤에는 기준을 3%(hysteresis_pct) 낮춰 경계에서 깜빡이지 않게 함
  - 자리를 떠나면 1초 안에 정상으로, 5초 이상 비면 다음 관람객을 위해 학습을 처음부터

  부하를 줄이기 위한 처리 (라즈베리파이용, 쓰레드 4개로 나눔)
  - 카메라 쓰레드 : 카메라 읽기만 함(camera_fps, 기본 30fps). 항상 "가장 최근 화면" 하나만 보관
  - 얼굴 쓰레드   : Face Mesh(얼굴)만 계산, 초당 analysis_fps번
  - 어깨 쓰레드   : Pose(어깨)만 계산, 초당 pose_fps번 (가장 무거운 계산. 어깨는 천천히 움직여서 충분)
  - 메인 쓰레드   : 화면 표시(카메라 속도 그대로) + 판정(새 어깨 결과가 나올 때마다, 계산량 아주 적음)
  -> MediaPipe는 계산하는 동안 파이썬 잠금(GIL)을 풀어 줘서, 얼굴·어깨 계산이 라즈베리파이의
     서로 다른 CPU 코어에서 동시에 돎. 무거운 계산이 늦어져도 화면은 끊기지 않음
  - 정해진 횟수만 계산하고 남는 시간은 쉬어서 CPU를 다 쓰지 않음 (같은 기기의 서버 app.py도 여유 있게)
  - 화면 오른쪽 아래에 cam/screen/face/pose 초당 처리 횟수(fps) 표시, 로그에도 10초마다 기록
  ※ 라즈베리파이에서는 자동으로 가벼운 설정을 씀 (config.json "profile": "auto"):
     얼굴 분석 초당 15회, 화면 표시 초당 20회, 가벼운 어깨 모델(0) -> 남는 CPU로 어깨를 더 자주 계산해 반응이 빨라짐
     가벼운 어깨 모델은 첫 실행 때 인터넷에서 받음 (실패하면 기본 모델로 실행되고 조금 느림)
     화면의 pose 숫자가 점수 막대의 반응 속도 (초당 판정 횟수). 판정이 드물어도 막대는 그 사이를 이어서 움직임
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

  관람객 진행 순서 (화면에 영어로 안내가 나옴. 전체 약 8초, 다시 시키지 않음)
  1) 카메라 앞에 앉으면 자동 시작
  2) "1/2 SIT UP STRAIGHT 2,1" -> 바르게 앉아서 2초 유지 ("HOLD STRAIGHT...")
  3) "2/2 NOW TURTLE NECK! 2,1" -> 평소 나쁜 자세처럼 머리를 앞으로 빼고 2초 유지 ("HOLD IT...")
     -> 화면에 "head forward +O.Ocm"로 목이 앞으로 나온 거리가 실시간으로 보임
     -> 거북목은 한 번만 잼. 목이 앞으로 0.7cm 이상 나왔으면 그 방향을 배우고(크기는 3~9cm로 맞춤),
        제대로 안 잡혔으면 다시 시키지 않고 기본값(목 앞 5cm, 아래 2cm)으로 바로 시작
     -> 학습 중 잠깐(3초 이내) 얼굴이 안 보이면 측정만 멈췄다가 이어서 함
     -> 준비·측정 시간은 config.json의 ready_sec, calib_sec로 조절
  4) 이후 실시간 판정. 화면 아래 막대가 점수, 흰 선 두 개가 경고(10)·위험(20) 기준
  5) 자리를 떠나 5초가 지나면 다음 사람을 위해 1)부터 다시

  ※ 개인용으로 쓸 때: config.json의 new_person_reset_sec을 0으로 하면
     학습 결과를 baseline.json에 저장해 두고 다음 실행에도 그대로 사용
  ※ 어깨를 아예 안 쓰려면 config.json에 "use_shoulders": false (얼굴만으로 판정)


[카메라 창 글자 뜻]  (OpenCV는 한글을 못 써서 영어로 표시)
  NO PERSON           : 사람이 안 보임
  FACE NOT FOUND      : 얼굴 인식 안 됨 -> 정면 보기, 조명 확인 (마스크·손으로 가리면 안 됨)
  TURN TO CAMERA      : 고개를 옆으로 많이(35도 이상) 돌림 -> 정면 보기
  head turned - score held : 고개를 20도 넘게 돌림 -> 그동안은 점수를 올리지 않음 (정면을 보면 다시 판정)
  ... - using last measurement : 사람은 있는데 잴 수 없음 -> 마지막으로 잰 점수로 판별을 계속함 (최대 30초)
  MOVE BACK - show both shoulders : 어깨가 화면 밖 -> 뒤로 물러나거나 카메라 각도 조절
  LOWER YOUR ARMS     : 팔을 10초 넘게 들고 있어서 어깨 위치를 알 수 없음 -> 팔 내리기
  FACE THE CAMERA     : 몸을 크게 비튼 상태가 10초 넘게 이어짐 -> 카메라 쪽으로 앉기
  face hidden - using last measurement : 몸은 보이는데 얼굴이 안 잡힘(고개를 많이 숙임, 손으로 가림 등)
                        ※ 사람이 아예 안 보이면 1초 뒤 상태를 정상으로 돌림
  1/2 ..., 2/2 ...    : 자세 학습 중 (위 [실행] 순서 참고)
  NORMAL  (초록)      : 정상
  WARNING (주황)      : 경고 - 점수 10%(warning_pct) 이상 (바로 표시)
  DANGER  (빨강)      : 위험 - 점수 20%(danger_pct) 이상이 2.5초(danger_after_sec) 이상 이어짐
  ※ 점수 0% = 학습한 바른 자세, 100% = 학습한 거북목 자세 (0~100%로 제한)
  ※ 하늘색 점 = 코·눈 끝·턱, 흰 선 = 어깨·팔, 노란 선 = 귀(추정)~어깨 가운데 (거북목이면 앞으로 기울어짐)
  ※ 화면은 거울처럼 좌우 반전해서 보여줌 (mirror: false로 끌 수 있음)


[주의사항]
  - 카메라는 정면, 눈높이 근처에 둘 것. 학습한 뒤 카메라(노트북 화면 각도 포함)를 움직이면
    판정이 틀어지므로 c 키로 다시 학습할 것
  - 거북목 자세를 너무 과장해서 학습하면 평소 자세에 둔해짐. "평소 하는 나쁜 자세" 정도로 보여줄 것
  - 학습할 때 어깨가 잘 안 보였으면 몸통 보정 없이 판정함 (로그에 경고가 남음) -> 몸을 숙이면 거북목으로 볼 수 있으니
    어깨까지 나오게 하고 c 키로 다시 학습할 것
  - 몸을 아주 크게(30도 넘게) 숙이면 계산 오차를 봐주는 만큼 그 상태의 거북목은 점수가 조금 낮게 나옴
  - 점수가 오르는 속도는 config.json의 rise_per_sec로 조절 (낮추면 천천히·덜 예민, 높이면 빨리 반응)
  - 숙일 때 오판이 남으면 로그의 "몸통 단서 너비·높이" 값을 보고 config.json의 torso_cue를 바꿀 것
    ("both" 기본 / "height" 높이만 / "width" 너비만 / "either" 둘 중 큰 쪽)
  - 안경은 괜찮지만, 마스크나 손으로 얼굴을 가리면 인식이 안 됨
  - model_complexity: 1(기본)이 더 정확. 라즈베리파이가 너무 느리면 0으로 (대신 첫 실행 때 다운로드)
  - 판정이 너무 예민하거나 둔하면 config.json의 warning_pct, danger_pct, danger_after_sec 숫자를 조절
    (기준 점수는 "학습한 거북목의 몇 %만큼 목이 나왔나". 학습 때 거북목을 크게 하면 둔해지고 작게 하면 예민해짐)
  - config.json을 바꾸면 프로그램을 껐다 켜야 반영됨
  - 모든 측정값은 판별기 쪽 posture_data.db에 먼저 저장되고, 그다음 서버 포트(server_url)로 전송됨
    서버가 꺼져 있거나 연결이 안 되면 DB에 남겨 두었다가, 연결되면 오래된 것부터 자동 전송
    (프로그램을 껐다 켜도 남아 있고, 측정 시각도 원래 시각 그대로 저장됨)
  - posture_data.db는 보낸 기록도 계속 쌓임 (save_interval 3초면 하루 약 2.9만 개, 약 6MB)
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
  "거북목 측정: ... -> 기본값 사용"     -> 거북목 자세에서 목이 거의 안 나옴. 그대로 써도 되고,
                                         개인 맞춤으로 하려면 c 키로 다시 학습 (머리를 더 앞으로, 몸통은 그대로)
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
import urllib.error
from datetime import datetime
from collections import deque
import uuid
from video_stream import FramePublisher
import numpy as np   # mediapipe 설치 시 함께 설치됨

VERSION = "2026-11-13"   # 실행 중인 판별기가 최신인지 로그 첫 줄에서 확인
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BASELINE_FILE = os.path.join(BASE_DIR, "baseline.json")
LOG_FILE = os.path.join(BASE_DIR, "posture.log")

# 시간 간격은 모두 time.monotonic()으로 잼: 라즈베리파이는 부팅 직후 인터넷 시간 맞추기로 시계가
# 몇 시간씩 바뀔 수 있는데, 그래도 측정 시간·카운트다운이 꼬이지 않음 (기록 시각만 datetime.now 사용)
VIS_MIN = 0.5        # 관절점이 이 값 이상 확실하게 보여야 사용
ABSENT_SEC = 1       # 판정할 수 없는 화면이 이만큼 이어지면 자리 비움으로 처리 (빠른 반응)
LOCAL_DB = os.path.join(BASE_DIR, "posture_data.db")   # 측정 기록 저장 + 전송 대기 (자동 생성)

# 어깨는 Pose(몸 33점)의 11, 12번 / 얼굴은 Face Mesh(얼굴 468점) 사용
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
ARM_POINTS = (13, 14)   # 양쪽 팔꿈치: 어깨보다 위로 올라가면 팔을 든 것
                        # (손목만 올라간 턱 괴기·안경 만지기는 어깨 점이 거의 안 움직여서 그대로 사용)
EDGE_Y = 1.0    # 어깨가 화면 아래 끝을 넘어가면 화면 밖을 추측한 위치라 사용 안 함 (가까이 앉아도 쓰도록 끝까지 허용)

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
MAX_RECORDS = 500
record_generation = 0
reset_requested = threading.Event()
# 서버로 보낼 때 프록시 설정(http_proxy 환경변수)을 무시하고 직접 연결.
# 라즈베리파이(리눅스)에 프록시가 설정돼 있으면 127.0.0.1로 보내는 것까지 프록시로 가서 실패하기 때문
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SEND_TIMEOUT = 5   # 라즈베리파이는 판별 계산으로 바빠서 서버 응답이 1초를 넘기기도 함


def _local_db():
    """Keep at most 500 local measurements, including pending uploads."""
    conn = sqlite3.connect(LOCAL_DB, timeout=5)
    conn.execute("CREATE TABLE IF NOT EXISTS records "
                 "(id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, sent INTEGER DEFAULT 0)")
    conn.execute('CREATE TABLE IF NOT EXISTS record_settings (key TEXT PRIMARY KEY, value TEXT)')
    conn.execute(f"""CREATE TRIGGER IF NOT EXISTS keep_latest_records
        AFTER INSERT ON records BEGIN
        DELETE FROM records WHERE id NOT IN
            (SELECT id FROM records ORDER BY id DESC LIMIT {MAX_RECORDS});
        END""")
    conn.execute('DELETE FROM records WHERE id NOT IN '
                 '(SELECT id FROM records ORDER BY id DESC LIMIT ?)', (MAX_RECORDS,))
    conn.commit()
    return conn


def ensure_remote_reset(url):
    """Called under send_lock; retry a pending reset before sending new records."""
    conn = _local_db()
    try:
        pending = conn.execute("SELECT value FROM record_settings WHERE key = 'pending_reset'").fetchone()
        if pending is None:
            return True
        req = urllib.request.Request(
            url.rsplit('/', 1)[0] + '/reset_records',
            data=json.dumps({'reset_id': pending[0]}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            _opener.open(req, timeout=SEND_TIMEOUT).close()
        except Exception as exc:
            log.warning('기록 초기화 전송 대기: %s', exc)
            return False
        conn.execute("DELETE FROM record_settings WHERE key = 'pending_reset'")
        conn.commit()
        return True
    finally:
        conn.close()


def reset_measurements(url):
    global record_generation
    # Stop an existing backlog upload, and invalidate sends queued before C.
    record_generation += 1
    reset_requested.set()
    with send_lock:
        conn = _local_db()
        try:
            conn.execute('DELETE FROM records')
            conn.execute("INSERT OR REPLACE INTO record_settings VALUES ('pending_reset', ?)",
                         (uuid.uuid4().hex,))
            conn.commit()
        finally:
            conn.close()
        reset_requested.clear()
        synced = ensure_remote_reset(url)
    log.info('캘리브레이션: 측정 기록 초기화%s', '' if synced else ' (웹 서버 연결 후 재시도)')


def unsent_count():
    """아직 서버로 못 보낸 개수"""
    conn = _local_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM records WHERE sent = 0").fetchone()[0]
    finally:
        conn.close()


def send(rec, url, generation=None):
    if generation is None:
        generation = record_generation
    with send_lock:
        if generation != record_generation or reset_requested.is_set():
            return
        conn = _local_db()
        try:
            conn.execute('INSERT INTO records (data) VALUES (?)',
                         (json.dumps(rec, ensure_ascii=False),))
            conn.commit()
        finally:
            conn.close()
        if ensure_remote_reset(url):
            _flush(url)


def clamp_record(data):
    """기록의 점수(worse_pct)를 0~100%로 맞춤 (예전 버전은 100%를 넘는 값을 저장했음)"""
    try:
        rec = json.loads(data)
        if isinstance(rec.get("worse_pct"), (int, float)):
            rec["worse_pct"] = round(min(max(rec["worse_pct"], 0.0), 100.0), 1)
        return json.dumps(rec, ensure_ascii=False)
    except (ValueError, TypeError, AttributeError):
        return data


def _flush(url):
    conn = _local_db()
    sent = 0
    try:
        rows = conn.execute("SELECT id, data FROM records WHERE sent = 0 ORDER BY id").fetchall()
        for rid, data in rows:
            if reset_requested.is_set():
                break
            data = clamp_record(data)   # 예전 버전이 남긴 100% 넘는 값도 0~100%로
            try:
                req = urllib.request.Request(url, data=data.encode("utf-8"),
                                             headers={"Content-Type": "application/json"}, method="POST")
                _opener.open(req, timeout=SEND_TIMEOUT).close()  # 4xx/5xx는 예외 발생
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:   # 서버가 형식 문제로 거부: 다시 보내도 안 되므로 건너뜀 (뒤 데이터가 막히지 않게)
                    log.error(f"서버가 데이터를 거부해 건너뜀 ({e.code}): {data}")
                    conn.execute("UPDATE records SET sent = 2 WHERE id = ?", (rid,))
                    conn.commit()
                    continue
                log.warning(f"전송 실패, DB에 보관 중 {len(rows) - sent}개: {e}")
                break
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
TORSO_CUE = "both"        # 몸통이 다가온 것을 어깨의 무엇으로 볼지. main()에서 config의 torso_cue로 바꿈
TORSO_LEN = 50.0           # 고관절~어깨 길이(cm). 성인 평균 근사 (몸통 기울기 계산에 사용)
SHOULDER_MEMORY_SEC = 30   # 팔을 들어 어깨 점을 못 믿을 때, 마지막으로 믿을 수 있던 어깨를 이 시간 동안 사용
FACE_HIDDEN_HOLD = 3       # 학습 중 얼굴이 잠깐 안 보일 때 기다려 주는 시간(초)
PRESENT_HOLD_SEC = 30      # 판정 중: 사람은 있는데 얼굴·어깨를 못 재는 동안 마지막 판정(점수 막대 포함)을 유지하는 시간(초)
                           # (거북목이 심해 얼굴이 어깨 아래로 내려가거나 어깨가 화면 밖으로 나가도 판정이 사라지지 않게)
YAW_TRUST = 20             # 고개를 이보다 많이 돌리면(도) 머리 위치 계산이 부정확해져서 점수를 올리지 않음 (옆 사람과 대화 등)
MEMORY_TRUST_SEC = 1.0     # 기억한 어깨를 쓰는 동안에는 점수가 이 시간 이상 계속 높아야 올림
                           # (팔을 내리면서 몸을 숙이는 순간처럼, 기억한 어깨와 실제 몸통이 어긋나는 짧은 순간의 오판 방지)


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
    "arms"  : 팔꿈치가 어깨보다 위 (팔을 들면 어깨 점이 팔을 따라 움직임)
    "twist" : 몸이 거의 옆으로 돌아감 (어깨 너비로 거리를 재는데 비틀면 좁아 보임)"""
    shoulders = (LEFT_SHOULDER, RIGHT_SHOULDER)
    if min(pose_lm[i].visibility for i in shoulders) < VIS_MIN:
        return "hidden"
    if max(pose_lm[i].y for i in shoulders) > EDGE_Y:
        return "hidden"
    top = min(pose_lm[i].y for i in shoulders) - 0.05   # 어깨보다 화면 높이의 5% 이상 위여야 '든 것'
    if any(pose_lm[i].visibility >= 0.5 and pose_lm[i].y < top for i in ARM_POINTS):   # (어깨 높이쯤은 무시)
        return "arms"
    ls, rs = pose_lm[LEFT_SHOULDER], pose_lm[RIGHT_SHOULDER]
    if abs(ls.z - rs.z) >= 1.5 * abs(ls.x - rs.x):   # z(앞뒤)는 실제 사진에서도 크게 흔들려서, 거의 옆으로 돌았을 때만
        return "twist"                                # (조금 비튼 건 neck_offset에서 '높이가 맞아야 기대기'로 걸러짐)
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
            feats["tilt"] = math.degrees(math.atan2(abs(ls[1] - rs[1]), abs(ls[0] - rs[0])))   # 어깨 기울기
        else:
            feats["sh_problem"] = "hidden"
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


def torso_forward(sh, base, f, c):
    """몸통(어깨)이 바른 자세보다 카메라 쪽으로 다가온 거리(cm, 0 이상)와 아래로 내려간 거리(cm, 0 이상),
    그리고 두 단서 각각의 값(로그용)을 돌려줌. 단서는 두 가지:
      ① 어깨 너비: 가까워지면 넓게 보임
      ② 어깨 높이: 카메라가 어깨보다 위에 있으면, 가까워질수록 화면에서 아래로 내려감
    두 단서가 '둘 다' 다가왔다고 할 때만 인정함 (TORSO_CUE = "both", 기본):
      높이로 잰 값을 쓰되, 너비로 잰 값의 2배를 넘지 못하게 함
      -> 너비가 조금 덜 반응해도 높이가 채워 주고, 한쪽만 엉뚱하게 튀면 걸러짐
    실제 Pose는 가만히 있어도 어깨 너비를 10~20% 넓게 잡을 때가 있는데(너비만 믿으면 몸통이 다가온 줄 알고
    진짜 거북목을 놓침), 그때 높이는 그대로라서 걸러짐. 반대로 구부정해서 어깨만 내려간 것도 너비가 그대로라 걸러짐.
    현장에서 로그의 "몸통 단서 너비 ·높이" 값을 보고 config.json의 torso_cue로 바꿀 수 있음:
      "height"(높이만), "width"(너비만), "either"(둘 중 큰 쪽: 숙일 때 오판이 남으면)
    '다가온' 쪽만 계산: 어깨 으쓱(위로), 몸 비틀기(좁아 보임), 뒤로 기대기는 0 -> 이런 동작이 점수를 올릴 수 없음"""
    sh0 = np.array(base["sh"])
    z0 = sh0[2]
    by_width = z0 - z0 * base["sw0"] / sh["sw"]
    by_height = None
    y0, y = f * sh0[1] / z0, sh["y"] - c[1]          # 화면 가운데에서 어깨까지 세로 거리(픽셀): 바른 자세, 지금
    if y0 > 0.12 * 2 * c[1]:                         # 어깨가 화면 가운데보다 충분히 아래(화면 높이의 12%)일 때만 쓸 수 있음
        # 몸통을 고관절 축으로 t만큼 숙이면 어깨는 앞으로 L·sin t, 아래로 L·(1-cos t) 움직임.
        # 카메라가 tilt만큼 내려다볼 때 그 어깨가 화면 어디에 보일지 계산해서, 지금 높이 y와 맞는 t를 찾음
        tilt, L = math.radians(CAMERA_TILT), TORSO_LEN
        def seen(t):   # 숙인 각도 t일 때 (화면 높이, 카메라까지 거리)
            fw, dn = L * math.sin(t), L * (1 - math.cos(t))
            zz = z0 - fw * math.cos(tilt) + dn * math.sin(tilt)
            return f * (sh0[1] + fw * math.sin(tilt) + dn * math.cos(tilt)) / zz, zz
        if y <= y0:
            by_height = z0 * (y / y0 - 1)        # 어깨가 위로 올라감: 다가온 게 아님(음수)
        else:
            lo, hi = 0.0, math.radians(60)
            for _ in range(20):                  # 반씩 좁혀 가며 찾기
                mid = (lo + hi) / 2
                if seen(mid)[0] < y:
                    lo = mid
                else:
                    hi = mid
            by_height = z0 - seen((lo + hi) / 2)[1]
    fwd = max(combine_cues(by_width, by_height), 0.0)
    down = max((sh["y"] - c[1]) / f * (z0 - fwd) - sh0[1], 0.0) if fwd > 0 else 0.0
    return fwd, down, by_width, by_height


def combine_cues(by_width, by_height):
    """두 단서(어깨 너비·높이로 잰 '다가온 거리')를 하나로. 둘 다 같은 쪽을 가리킬 때만 인정"""
    if by_height is None or TORSO_CUE == "width":
        return by_width
    if TORSO_CUE == "height":
        return by_height
    if TORSO_CUE == "either":
        return max(by_width, by_height)
    if by_width > 0 and by_height > 0:        # "both": 높이 값을 쓰되 너비 값의 2배를 넘지 못함
        return min(by_height, 2.0 * by_width)
    if by_width < 0 and by_height < 0:
        return max(by_height, 2.0 * by_width)
    return 0.0


class TorsoHold:
    """몸통이 다가온 거리를 안정적으로 따라감 (실행 중에만 사용).
    몸통이 움직이면 귀도 반드시 같이 움직임. 그러니 귀는 가만히 있는데 어깨로 잰 값만 오르내리면
    그건 측정 흔들림 -> 그대로 두면 거북목 자세로 가만히 있을 때 점수가 흔들리다 정상으로 떨어짐.
    - 귀가 가만히 있는 동안: 몸통 값을 고정하고, 그때의 어깨 단서 값을 '기준'으로 기억
    - 귀가 MOVE(cm) 이상 움직이면 그때부터 SETTLE초 동안: 어깨 단서가 '기준에서 변한 만큼'만 몸통 값에 반영
      (가만히 있을 때 이미 틀어져 있던 값은 서로 상쇄되어 영향을 주지 않음)
    - 반영하는 양은 귀가 움직인 거리 이하 (몸통이 귀보다 더 많이 움직일 수는 없음)"""
    MOVE, SETTLE = 0.7, 0.8

    def __init__(self, fwd=None):
        self.fwd, self.down, self.anchor = fwd, 0.0, None
        self.budget, self.moved_at = 0.0, -1e9

    def __call__(self, ear, by_width, by_height, down, now):
        ear = np.asarray(ear, dtype=np.float64)
        if self.anchor is None:
            if self.fwd is None:                      # 처음 보는 자세(자리 비움 뒤 등): 잰 값 그대로 시작
                self.fwd, self.down = combine_cues(by_width, by_height), down
            self.anchor, self.start = ear, (self.fwd, self.down)
            self.ref = (by_width, by_height, down)
            return max(self.fwd, 0.0), max(self.down, 0.0)
        moved = float(np.linalg.norm(ear - self.anchor))
        if moved >= self.MOVE:                        # 귀가 움직임: 반영할 수 있는 양을 그만큼 늘림
            self.budget, self.moved_at, self.anchor = self.budget + moved, now, ear
        if now - self.moved_at <= self.SETTLE:        # 움직이는 중(+측정이 뒤따라오는 시간): 기준에서 변한 만큼 반영
            dh = None if by_height is None or self.ref[1] is None else by_height - self.ref[1]
            change = combine_cues(by_width - self.ref[0], dh)
            change = min(max(change, -self.budget), self.budget)
            # 지금 잰 값보다 크게는 안 봄(다른 동작이 겹쳐 어긋나는 것 방지), 0보다 작게도 안 봄(빼는 쪽으로만 보정)
            self.fwd = max(min(self.start[0] + change, max(combine_cues(by_width, by_height), 0.0)), 0.0)
            self.down = max(self.start[1] + (down - self.ref[2]), 0.0)
        else:                                         # 가만히 있음: 값 고정, 지금 어깨 단서를 새 기준으로
            self.budget, self.start = 0.0, (self.fwd, self.down)
            self.ref = (by_width, by_height, down)
        return max(self.fwd, 0.0), max(self.down, 0.0)


def neck_offset(feats, base):
    """귀가 바른 자세보다 앞으로/아래로 움직인 거리(cm) 중에서 '몸통이 다가와서 생긴 만큼'을 뺀 값과,
    몸통 숙임 각도(도, 참고용)를 돌려줌.
    고관절을 축으로 몸통을 숙이면(척추 중립) 고관절-어깨-귀가 한 직선처럼 같이 돌아서,
    귀는 어깨가 움직인 만큼의 (몸통+목)/몸통 배(약 1.3배) 움직임. 그만큼 빼면 '목만 움직인 양'이 남음.
    보정은 '빼는 쪽'으로만 함: 어깨 측정이 틀리거나 어깨만 움직여도(으쓱·비틀기) 점수가 올라가지 않음"""
    ear, ear0 = np.array(feats["pose"]["ear"]), np.array(base["ear"])
    fwd, down, lean = float(ear0[2] - ear[2]), float(ear[1] - ear0[1]), 0.0   # 앞으로(카메라 쪽), 아래로
    sh = feats.get("sh_use")
    if sh is not None and "sw0" in base:
        k = (TORSO_LEN + base["neck"]) / TORSO_LEN
        if "torso" in feats:   # 실행 중: 안정화한 값 (TorsoHold)
            t_fwd, t_down = feats["torso"]
        else:
            t_fwd, t_down, _, _ = torso_forward(sh, base, feats["pose"]["f"], feats["c"])
        lean = math.degrees(math.asin(min(1.0, t_fwd / TORSO_LEN)))
        # 몸통 길이·카메라 각도는 사람마다 달라서 계산이 조금 틀릴 수 있음 -> 몸통이 움직인 양의 12%는 오차로 봐줌
        margin = 0.12 * k * math.hypot(t_fwd, t_down)
        fwd -= k * t_fwd
        down -= k * t_down
        fwd = max(fwd - margin, 0.0) if fwd > 0 else fwd
        down = max(down - margin / 2, 0.0) if down > 0 else down
    return fwd, down, lean


# ======================== 개인 맞춤 학습 ========================
MIN_SEPARATION = 1.5   # 두 자세 차이가 같은 자세 안에서의 흔들림의 몇 배 이상이어야 학습 성공
MIN_MOVE_CM = 0.7      # 거북목 자세에서 목이 앞으로 최소 이만큼(cm)은 나와야 학습 성공
DELTA_RANGE = (3.0, 9.0)     # 학습한 거북목 크기를 이 범위(cm)로 맞춤
DEFAULT_DELTA = [5.0, 2.0]   # 거북목이 거의 안 잡혔을 때 쓰는 기본 거북목(목이 앞 5cm, 아래 2cm). 다시 시키지 않음
MODEL_VERSION = 3      # 저장된 학습 결과(baseline.json) 형식. 바뀌면 예전 파일은 다시 학습


def train(good, bad):
    """바른 자세로 기준을 만들고, 거북목 자세에서 목이 몸통 기준으로 얼마나(cm) 움직였는지 학습.
    점수 = 지금 목의 움직임을 '학습한 거북목 방향'에 비춰 본 비율 (바른 자세 0, 학습한 거북목 100).
    반환: (모델 또는 None, 구분 정도, 목 움직임 [앞 cm, 아래 cm], 흔들림 cm)
    None이면 거북목이 거의 안 잡힌 것 -> train_default()로 기본값 사용"""
    base = make_base(good)
    G = np.array([neck_offset(g, base)[:2] for g in good])
    B = np.array([neck_offset(b, base)[:2] for b in bad])
    # 평균 대신 가운데 값: 실행 중에도 '최근 3번의 가운데 값'으로 점수를 내므로 같은 방식이어야
    # 바른 자세가 0%에 맞음 (평균을 쓰면 가끔 튀는 값 때문에 바른 자세가 5~10%로 치우침)
    mg, mb = np.median(G, axis=0), np.median(B, axis=0)
    delta = mb - mg
    size = float(np.linalg.norm(delta))
    if size < 1e-6:
        return None, 0.0, delta.tolist(), 0.0
    proj = np.vstack([G - mg, B - mb]) @ delta / size        # 같은 자세 안에서의 흔들림
    noise = max(float(proj.std()), 0.3)                       # 흔들림 최소 0.3cm로 봄
    sep = size / noise
    # 거북목은 목이 앞으로 나와야 함. 기준은 느슨하게: 앞으로 0.7cm 이상, 흔들림의 1.5배 이상이면 성공
    if not (delta[0] >= MIN_MOVE_CM and sep >= MIN_SEPARATION):
        return None, sep, delta.tolist(), noise
    # 방향은 배운 대로, 크기는 3~9cm로 맞춤: 너무 작게 보여 주면 조금만 움직여도 경고(예민),
    # 너무 과장하면 평소 자세에 둔해지므로
    scale = min(max(size, DELTA_RANGE[0]), DELTA_RANGE[1]) / size
    base.update(good=mg.tolist(), delta=(delta * scale).tolist())
    return base, sep, delta.tolist(), noise


def train_default(good):
    """거북목 자세가 제대로 안 잡혔을 때: 바른 자세는 그대로 쓰고, 거북목은 평균적인 값으로 정함
    (사용자에게 다시 시키지 않기 위해)"""
    base = make_base(good)
    G = np.array([neck_offset(g, base)[:2] for g in good])
    base.update(good=np.median(G, axis=0).tolist(), delta=list(DEFAULT_DELTA), default=True)
    return base


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
    귀와 어깨가 똑같이 늦어져야 서로 어긋나지 않아서, 몸을 움직이는 순간에 점수가 튀지 않음.
    가만히 있을 때는 더 많이(still_tau) 부드럽게 해서 흔들림을 줄이고, 움직이면 빠르게(tau) 따라감.
    (귀와 어깨에 항상 같은 값을 쓰므로 둘이 어긋나지 않음)"""
    def __init__(self, tau=0.25, still_tau=0.6):
        self.fast, self.still = tau, max(still_tau, tau)
        self.tau, self.v, self.t = tau, {}, {}

    def adapt(self, ear):
        """귀가 부드럽게 한 위치에서 얼마나 벗어났는지(cm)로 이번에 쓸 tau를 정함"""
        if "ear" not in self.v:
            self.tau = self.fast
            return
        dev = float(np.linalg.norm(np.asarray(ear) - self.v["ear"]))
        self.tau = self.fast + (self.still - self.fast) * math.exp(-dev / 0.6)   # 0.6cm 이상 움직이면 거의 빠르게

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
    sm.adapt(feats["pose"]["ear"])
    out["pose"]["ear"] = sm("ear", feats["pose"]["ear"], now).tolist()
    sh = feats["shoulder"]
    cx, cy = feats["c"]
    # 어깨는 (1/너비, 가로위치/너비, 세로위치/너비)를 부드럽게 함 = 어깨의 3D 위치를 부드럽게 하는 것과 같음.
    # 귀도 3D 위치를 부드럽게 하므로 둘이 정확히 같은 방식으로 늦어져서, 빨리 움직여도 서로 어긋나지 않음
    if sh is not None:
        v = sm("sh", [1 / sh["sw"], (sh["x"] - cx) / sh["sw"], (sh["y"] - cy) / sh["sw"]], now)
    elif "sh" in sm.v and now - sm.t["sh"] < SHOULDER_MEMORY_SEC:
        # 팔을 들었거나, 어깨가 화면 밖으로 나갔거나, 잠깐 안 보일 때: 마지막으로 본 어깨를 대신 사용.
        # (어깨가 화면 밖으로 나가기 직전의 값이라 그때까지 몸이 다가온 만큼은 이미 들어 있음)
        v, out["sh_from_memory"] = sm.v["sh"], True
    else:
        out["sh_use"] = None
        return out
    sw = 1 / v[0]
    out["sh_use"] = {"x": v[1] * sw + cx, "y": v[2] * sw + cy, "sw": sw}
    return out


class OneEuro:
    """빠르게 움직일 땐 바로 따라가고, 가만히 있을 땐 떨림만 잡는 필터 (One Euro Filter)"""
    def __init__(self, min_cutoff=1.5, beta=0.02):
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


UPPER_BODY = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]   # 화면에 그릴 선: 어깨, 팔
FACE_DOTS = (1, 33, 263, 152)                                       # 화면에 그릴 얼굴 점: 코, 눈 끝, 턱


def neck_points(feats):
    """화면에 그릴 귀(추정)와 어깨 가운데 위치(픽셀). 거북목이면 이 선이 앞으로 기울어짐"""
    sh = feats.get("sh_use")
    if sh is None:
        return None
    ex, ey, ez = feats["pose"]["ear"]
    f, (cx, cy) = feats["pose"]["f"], feats["c"]
    return (int(cx + f * ex / ez), int(cy + f * ey / ez)), (int(sh["x"]), int(sh["y"]))


def draw(cv2, mp, frame, pose_res, face_lm, text, color, sub, pct, cfg, fps_text="", neck_line=None, publisher=None, show_window=True):
    """어깨·팔 선, 얼굴 점, 귀-어깨 선, 상태, 점수 막대를 그려서 창에 표시. q: 종료, 누른 키를 돌려줌"""
    global running
    h, w = frame.shape[:2]
    if pose_res is not None and pose_res.pose_landmarks:   # 상체만 (다리·얼굴 점은 판정에 안 써서 생략)
        lm = pose_res.pose_landmarks.landmark
        pt = lambda i: (int(lm[i].x * w), int(lm[i].y * h))
        for a, b in UPPER_BODY:
            if lm[a].visibility > 0.5 and lm[b].visibility > 0.5:
                cv2.line(frame, pt(a), pt(b), (255, 255, 255), 2)
        for i in (11, 12):
            if lm[i].visibility > 0.5:
                cv2.circle(frame, pt(i), 5, (0, 0, 255), -1)
    if face_lm is not None:
        for i in FACE_DOTS:
            cv2.circle(frame, (int(face_lm[i].x * w), int(face_lm[i].y * h)), 3, (255, 255, 0), -1)
    if neck_line is not None:
        cv2.line(frame, neck_line[0], neck_line[1], (0, 255, 255), 2)
        cv2.circle(frame, neck_line[0], 6, (0, 255, 255), -1)
    if cfg.get("mirror", True):
        frame = cv2.flip(frame, 1)   # 거울처럼 보여주기 (글자는 뒤집기 후에 씀)

    cv2.putText(frame, text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)
    if sub:
        cv2.putText(frame, sub, (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if pct is not None:   # 점수 막대: 0(바른 자세) ~ 100(학습한 나쁜 자세)
        x0, x1, y0 = 10, w - 10, h - 45
        cv2.rectangle(frame, (x0, y0), (x1, y0 + 15), (80, 80, 80), -1)
        fill = x0 + int((x1 - x0) * min(max(pct, 0), 100) / 100)
        cv2.rectangle(frame, (x0, y0), (fill, y0 + 15), color, -1)
        for th in (cfg["warning_pct"], cfg["danger_pct"]):   # 경고·위험 기준선
            tx = x0 + int((x1 - x0) * th / 100)
            cv2.line(frame, (tx, y0 - 3), (tx, y0 + 18), (255, 255, 255), 2)
    cv2.putText(frame, "c: recalibrate  q: quit", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    if fps_text:
        cv2.putText(frame, fps_text, (w - 360, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    if publisher is not None:
        publisher.submit(frame)
    if not show_window:
        return -1
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
        self.n, self.t0, self.value = 0, time.monotonic(), 0.0

    def tick(self):
        self.n += 1
        dt = time.monotonic() - self.t0
        if dt >= 2:
            self.value, self.n, self.t0 = self.n / dt, 0, time.monotonic()


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
                    opened_at = time.monotonic()
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
                if not checked and time.monotonic() - opened_at > 5:   # 실제로 나오는 속도 한 번 확인
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
    def __init__(self, name, cv2, make_model, pick, camera, fps, stop_event, prep=None):
        super().__init__(daemon=True, name=name)
        self.cv2, self.make_model, self.pick, self.camera = cv2, make_model, pick, camera
        self.prep = prep or (lambda frame: (frame, None))   # 계산 전에 화면을 잘라내는 등 (기본: 그대로)
        self.interval, self.stop_event = 1 / max(fps, 0.5), stop_event
        self.cond = threading.Condition()
        self.result, self.stamp, self.id, self.rate = None, 0.0, 0, Rate()
        self.frame_seq, self.history = -1, deque(maxlen=90)   # 결과가 나온 화면 번호, 최근 결과들

    def run(self):
        try:
            with self.make_model() as model:
                last_seq = -1
                while running and not self.stop_event.is_set():
                    start = time.monotonic()
                    seq, frame = self.camera.wait_new(last_seq, 0.5)
                    if frame is None:
                        continue
                    last_seq = seq
                    img, meta = self.prep(frame)
                    rgb = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False   # 복사 없이 넘겨서 조금 더 빠르게
                    out = self.pick(model.process(rgb), meta)
                    with self.cond:
                        self.result, self.stamp, self.id, self.frame_seq = out, time.monotonic(), self.id + 1, seq
                        self.history.append((seq, out))
                        self.cond.notify_all()
                    self.rate.tick()
                    self.stop_event.wait(max(0.0, self.interval - (time.monotonic() - start)))   # 남는 시간은 쉼
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


class Target:
    """처음 잡은 한 사람만 계속 따라감. 판정 중에 다른 사람이 화면에 들어와도 무시.
    - 처음에는 가장 크게(가깝게) 보이는 얼굴을 고름
    - 그다음부터는 바로 전 위치에서 가장 가까운 얼굴만 같은 사람으로 봄 (너무 멀리 있으면 다른 사람)
    - release_sec 동안 안 보이면 놓아줌 (다음 사람을 새로 잡을 수 있게)
    - 어깨(Pose)는 이 사람 주변만 잘라서 계산 -> 다른 사람의 어깨를 잡지 않음"""
    def __init__(self, release_sec=5):
        self.release_sec = release_sec
        self.center, self.size, self.seen, self.face_seen = None, 0.0, 0.0, 0.0
        self.box = None          # 어깨 계산용으로 잘라낼 영역 (픽셀, 어깨 쓰레드가 읽음)
        self.lock_id = 0         # 새 사람을 잡을 때마다 1씩 늘어남 (사람이 바뀌었는지 확인용)

    @staticmethod
    def _measure(lm, w, h):
        a, b = lm[33], lm[263]   # 양쪽 눈 바깥 끝
        return ((a.x + b.x) / 2 * w, (a.y + b.y) / 2 * h), max(math.hypot((a.x - b.x) * w, (a.y - b.y) * h), 1.0)

    def keep_alive(self, now):
        """얼굴은 안 보이지만 몸(어깨)은 보일 때: 같은 사람이 그대로 있는 것으로 봄 (얼굴을 마지막으로 본 뒤 30초까지)"""
        if self.center is not None and now - self.face_seen < PRESENT_HOLD_SEC:
            self.seen = now

    def pick(self, faces, w, h, now):
        """얼굴 여러 개 중 따라가는 사람의 얼굴. 없으면 None"""
        if self.center is not None and now - self.seen > self.release_sec:
            log.info("따라가던 사람이 안 보임 -> 다음 사람을 새로 잡음")
            self.center, self.box = None, None
        if not faces:
            return None
        cands = [(self._measure(f, w, h), f) for f in faces]
        if self.center is None:                         # 처음: 가장 크게 보이는(가까운) 사람
            (c, size), face = max(cands, key=lambda x: x[0][1])
            self.lock_id += 1
            log.info(f"따라갈 사람을 잡음 ({self.lock_id}번째)")
        else:
            (c, size), face = min(cands, key=lambda x: math.dist(x[0][0], self.center))
            if math.dist(c, self.center) > max(3 * self.size, 0.15 * w):
                return None                             # 다른 사람 -> 무시
        self.center, self.size, self.seen, self.face_seen = c, size, now, now
        # 어깨·팔까지 들어가는 영역: 눈 사이 거리(s)의 가로 ±5배, 위 5배(팔 들기), 아래 7배
        s_ = size
        box = (max(0, c[0] - 5 * s_), max(0, c[1] - 5 * s_), min(w, c[0] + 5 * s_), min(h, c[1] + 7 * s_))
        if self.box is None or max(abs(a - b) for a, b in zip(box, self.box)) > 0.5 * s_:
            self.box = box                              # 조금씩 흔들릴 때는 그대로 (어깨 추적이 안정적)
        return face


def pose_prep(target):
    """어깨 계산 전: 따라가는 사람 주변만 잘라냄 (아직 아무도 안 잡았으면 화면 전체)"""
    def prep(frame):
        box = target.box
        if box is None:
            return frame, None
        x0, y0, x1, y1 = (int(v) for v in box)
        if x1 - x0 < 32 or y1 - y0 < 32:
            return frame, None
        return frame[y0:y1, x0:x1], (x0, y0, x1 - x0, y1 - y0, frame.shape[1], frame.shape[0])
    return prep


def pose_pick(result, meta):
    """잘라낸 화면 기준 어깨 좌표를 전체 화면 기준으로 되돌림"""
    if meta is None or not result.pose_landmarks:
        return result
    from mediapipe.framework.formats import landmark_pb2
    x0, y0, cw, ch, w, h = meta
    out = landmark_pb2.NormalizedLandmarkList()
    for p in result.pose_landmarks.landmark:
        out.landmark.add(x=(p.x * cw + x0) / w, y=(p.y * ch + y0) / h, z=p.z * cw / w, visibility=p.visibility)
    result.pose_landmarks = out
    return result


# ======================== 메인 루프 ========================
BAR_SMOOTH_SEC = 0.15   # 점수 막대가 새 점수까지 부드럽게 움직이는 시간 (판정은 초당 5번이라 그대로 그리면 뚝뚝 끊김)


def run(cfg):
    global running
    import cv2
    import mediapipe as mp

    stop_event = threading.Event()   # run()이 끝나면 쓰레드들도 같이 끝내기 위한 신호
    camera = CameraThread(cv2, cfg, stop_event)
    face_thread = ModelThread(
        "face", cv2,
        lambda: mp.solutions.face_mesh.FaceMesh(max_num_faces=3, min_detection_confidence=0.5,
                                                min_tracking_confidence=0.5),   # 여러 명 중 따라갈 사람을 고르려고 3명까지
        lambda r, meta: [f.landmark for f in r.multi_face_landmarks] if r.multi_face_landmarks else [],
        camera, cfg.get("analysis_fps", 30), stop_event)
    target = Target(cfg.get("new_person_reset_sec", 5) or 5)
    pose_thread = None
    if cfg.get("use_shoulders", True):   # 어깨를 안 쓰면 가장 무거운 계산을 아예 안 함
        pose_thread = ModelThread("pose", cv2, lambda: make_pose(mp, cfg.get("model_complexity", 1)),
                                  pose_pick, camera, cfg.get("pose_fps", 10), stop_event, prep=pose_prep(target))
    threads = [t for t in (camera, face_thread, pose_thread) if t is not None]
    for t in threads:
        t.start()
    screen_rate, last_fps_log, fps_text = Rate(), time.monotonic(), ""

    reset_sec = cfg.get("new_person_reset_sec", 5)
    model_lock = 0   # 지금 학습·판정 중인 사람 번호 (Target.lock_id)
    model = load_json(BASELINE_FILE) if reset_sec == 0 else None   # 전시회 모드면 매번 새로 학습
    if model and model.get("version") != MODEL_VERSION:
        model = None   # 예전 버전 파일 (거리 단위 등이 달라서 다시 학습)
    phase = "run" if model else "wait"   # wait -> good_ready -> good_rec -> bad_ready -> bad_rec -> run
    phase_start, good, bad = 0.0, [], []
    temp_base = None   # 바른 자세 기준 (학습 중 '목이 앞으로 몇 cm' 안내용)
    ready_sec, calib_sec = cfg.get("ready_sec", 2), cfg.get("calib_sec", 2)   # 준비 카운트다운, 측정 시간(초)
    filt = OneEuro()
    status, raw, bad_since = "정상", "정상", None
    last_save = last_valid = time.monotonic()
    last_seen = 0.0
    sm = Smooth(cfg.get("smooth_sec", 0.25))   # 귀·어깨를 같은 정도로 부드럽게 (+ 팔 들 때 어깨 기억)
    rise_since = None                           # 기억한 어깨로 점수가 오르기 시작한 시각
    recent = deque(maxlen=3)                    # 최근 점수 3개 (튀는 값 걸러내기)
    goal = None                                 # 가장 최근에 잰 점수 (점수 막대가 향하는 목표)
    torso_hold = TorsoHold()                    # 몸통이 다가온 거리 안정화
    pct, duration, pct_time = None, 0.0, 0.0
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

    def advance(now):
        """점수를 목표(goal) 쪽으로 움직이고(올라갈 때는 속도 제한) 정상/경고/위험과 위험 타이머를 진행.
        잴 수 없는 동안에도(얼굴이 안 잡힘 등) 마지막으로 잰 목표를 향해 계속 진행하려고 따로 뺌"""
        nonlocal pct, pct_time, raw, bad_since, duration, text, color
        if pct is None:   # 처음(학습 직후·자리 비움 뒤)은 0%에서 시작
            pct, pct_time = 0.0, now
        new_pct = goal
        if new_pct > pct:   # 올라가는 속도 제한: 초당 rise_per_sec %까지만 (내려갈 때는 바로)
            new_pct = min(new_pct, pct + cfg.get("rise_per_sec", 40) * max(now - pct_time, 0.0))
        pct, pct_time = new_pct, now
        raw = raw_status(pct, cfg, raw)
        new_status, bad_since, duration = hold(raw, bad_since, cfg.get("danger_after_sec", 2.5), now)
        set_status(new_status)
        text, color = f"{STATUS_EN[status]}  {pct:.0f}%", STATUS_COLOR[status]

    def record(now, shoulder=None, tilt=None):
        """측정 기록을 서버로 보냄 (백그라운드: 서버가 느려도 화면이 안 멈춤)"""
        threading.Thread(target=send, daemon=True, args=({
            "user_id": cfg["user_id"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "worse_pct": round(pct, 1),
            "status": status,
            "shoulder_status": shoulder,
            "shoulder_tilt": round(tilt, 1) if shoulder else None,
            "bad_duration": round(duration, 1),
        }, cfg["server_url"], record_generation)).start()
        post_status(status)   # 살아 있다는 신호 겸 상태 재전송

    def restart_calibration(why):
        nonlocal model, phase, good, bad, pct, bad_since, raw, filt, temp_base, sm, rise_since, goal, torso_hold
        log.info(f"{why} -> 자세 학습 다시 시작")
        model, phase, good, bad, pct, bad_since, raw, filt = None, "wait", [], [], None, None, "정상", OneEuro()
        temp_base, sm, rise_since = None, Smooth(cfg.get("smooth_sec", 0.25)), None
        goal, torso_hold = None, TorsoHold()
        recent.clear()
        set_status("정상")

    publisher = FramePublisher(cfg) if cfg.get("web_video", True) else None
    try:
        cam_seq, face_id, pose_id = -1, 0, 0
        show_pose, neck_line = None, None   # 화면에 그릴 최신 어깨, 귀-어깨 선
        bar_val, bar_t = None, 0.0          # 화면 점수 막대에 보여 줄 값 (부드럽게 움직임)
        judge_dt, last_judge = 0.1, 0.0     # 판정 간격(초)의 평균, 마지막 판정 시각
        last_draw, draw_interval = 0.0, 1 / max(cfg.get("display_fps", 30), 1) - 0.004   # 화면 표시 속도 제한
        while running:
            command = publisher.take_command() if publisher is not None else None
            if command == 'quit':
                running = False
                break
            if command == 'calibrate':
                if os.path.exists(BASELINE_FILE):
                    os.remove(BASELINE_FILE)
                reset_measurements(cfg['server_url'])
                restart_calibration('web C command')
            if not camera.is_alive() or not face_thread.is_alive() or (pose_thread and not pose_thread.is_alive()):
                log.warning("카메라·얼굴·어깨 쓰레드 중 하나가 멈춤 -> 다시 시작")
                break
            if show or publisher is not None:   # 화면은 카메라 속도(최대 camera_fps) 그대로 부드럽게 갱신
                cam_seq, frame = camera.wait_new(cam_seq, 0.5)
                if frame is None:
                    continue
                fid, new_face, _ = face_thread.latest()
            else:      # 창이 없으면 새 얼굴 결과가 나올 때만 깨어나서 CPU를 아낌
                fid, new_face, _ = face_thread.wait_new(face_id, 0.5)

            # 판정할 때는 '같은 화면'에서 나온 얼굴과 어깨를 짝지어 씀.
            # (어깨는 초당 10번, 얼굴은 30번 계산해서, 최신 결과끼리 쓰면 빨리 움직일 때 서로 다른 순간이 섞여
            #  몸통만 숙여도 귀만 먼저 앞으로 간 것처럼 보임) -> 어깨 결과가 새로 나올 때마다 판정
            h, w = camera.shape
            new_face_result = fid != face_id
            if new_face_result:   # 여러 얼굴 중 따라가는 사람의 얼굴만 (화면에 그리는 얼굴 점은 항상 최신)
                face_id, face_lm = fid, target.pick(new_face or [], w, h, time.monotonic())
            judge, pose_res, judge_face = False, None, face_lm
            if pose_thread is None:
                judge = new_face_result
            else:
                pid, res, stamp, pseq = pose_thread.latest_full()
                show_pose = res if res is not None and time.monotonic() - stamp < POSE_MAX_AGE else None
                if pid != pose_id:
                    pose_id, judge, pose_res = pid, True, res
                    faces = face_thread.find(pseq) or []   # 어깨와 같은 화면의 얼굴 (따라가는 사람 것만)
                    judge_face = min(faces, key=lambda f: math.dist(Target._measure(f, w, h)[0], target.center),
                                     default=None) if target.center is not None and faces else face_lm
                    if judge_face is not None and target.center is not None and math.dist(
                            Target._measure(judge_face, w, h)[0], target.center) > max(3 * target.size, 0.15 * w):
                        judge_face = None
                elif new_face_result and time.monotonic() - stamp > POSE_MAX_AGE:
                    judge = True                         # 어깨 계산이 멈췄으면 얼굴만으로

            if judge:   # 판정 자체는 계산량이 아주 적음
                now = time.monotonic()
                pose_lm = pose_res.pose_landmarks.landmark if pose_res and pose_res.pose_landmarks else None
                feats, reason = get_features(cv2, pose_lm, judge_face, w, h, cfg.get("camera_fov_deg", 65),
                                             cfg.get("use_shoulders", True))
                if pose_lm is not None and judge_face is None:
                    target.keep_alive(now)               # 얼굴은 안 보여도 몸이 보이면 같은 사람
                if judge_face is not None or (pose_lm is not None and now - target.seen < 1.0):
                    last_seen = now                      # 따라가는 사람이 보임 (다른 사람 몸은 제외)
                if target.lock_id != model_lock and reset_sec and phase != "wait":
                    restart_calibration("다른 사람으로 바뀜")   # 새 사람은 새로 학습
                model_lock = target.lock_id
                if feats is not None:
                    feats = prepare(sm, feats, now)
                    neck_line = neck_points(feats) or neck_line   # 어깨를 잠깐 몰라도 선은 마지막 위치에 유지
                    if phase == "run" and feats["sh_use"] and "sw0" in model:
                        _, _, bw, bh = torso_forward(feats["sh_use"], model, feats["pose"]["f"], feats["c"])
                        t_down = max((feats["sh_use"]["y"] - feats["c"][1]) / feats["pose"]["f"] * model["sh"][2]
                                     - model["sh"][1], 0.0)   # 어깨가 내려간 거리(cm, 대략)
                        feats["torso"] = torso_hold(feats["pose"]["ear"], bw, bh, t_down, now)
                    if phase == "run" and not can_judge(model, feats):
                        feats, reason = None, {"arms": "LOWER YOUR ARMS", "twist": "FACE THE CAMERA"}.get(
                            feats["sh_problem"], "MOVE BACK - show both shoulders")

                # 사람은 있는데 잴 수 없는 경우(얼굴이 어깨 아래로 내려감, 손으로 가림, 어깨가 화면 밖 등):
                # 판정 중이면 마지막 결과와 점수 막대를 그대로 유지 (사라지지 않게)
                hidden = feats is None and phase == "run" and (pose_lm is not None or judge_face is not None)
                if hidden and now - last_valid <= PRESENT_HOLD_SEC:
                    # 판별은 멈추지 않음: 마지막으로 잰 점수를 향해 막대가 계속 움직이고, 위험 타이머(2.5초)와 기록도 계속 진행
                    if goal is not None:
                        advance(now)
                        if now - last_save >= cfg["save_interval"]:
                            log.info(f"{status} 점수 {pct:.0f}% (잴 수 없어 마지막 측정값으로 진행: {reason})")
                            record(now)
                            last_save = now
                    sub = "face hidden - using last measurement" if judge_face is None else f"{reason} - using last measurement"
                elif feats is None:
                    text, sub, color = ("NO PERSON" if now - last_seen > 0.3 else reason), "", GRAY
                    neck_line = None
                    if now - last_valid > (PRESENT_HOLD_SEC if hidden else ABSENT_SEC):   # 판정 불가가 이어지면 자리 비움
                        bad_since, raw = None, "정상"
                        set_status("정상")
                        recent.clear()                     # 예전 점수를 비워서, 돌아왔을 때 경고가 잠깐 뜨지 않게
                        filt, pct, rise_since, goal, torso_hold = OneEuro(), None, None, None, TorsoHold()
                    # 학습 중에는 잠깐(3초 이내) 안 보이는 건 기다림 (그동안은 측정만 멈춤). 오래 안 보이면 처음부터
                    if phase not in ("wait", "run") and now - last_valid > FACE_HIDDEN_HOLD:
                        log.info(f"학습 중 사람이 {FACE_HIDDEN_HOLD}초 넘게 안 보임 -> 처음부터 다시")
                        phase, good, bad = "wait", [], []
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
                        left = ready_sec - (now - phase_start)
                        step = "1/2  SIT UP STRAIGHT" if phase == "good_ready" else "2/2  NOW TURTLE NECK!"
                        text, color = f"{step}  {math.ceil(max(left, 0))}", YELLOW
                        sub = "Sit tall, chin in" if phase == "good_ready" \
                            else "Push your head forward like usual bad posture"
                        if phase == "bad_ready" and temp_base is not None:
                            sub += f"  (head forward {neck_offset(feats, temp_base)[0]:+.1f}cm)"
                        if left <= 0:
                            phase = "good_rec" if phase == "good_ready" else "bad_rec"
                            phase_start = now
                    elif phase in ("good_rec", "bad_rec"):
                        (good if phase == "good_rec" else bad).append(feats)
                        text = "1/2  HOLD STRAIGHT..." if phase == "good_rec" else "2/2  HOLD IT..."
                        sub, color = f"recording {max(calib_sec - (now - phase_start), 0):.1f}s", YELLOW
                        if phase == "bad_rec" and temp_base is not None:
                            sub += f"  (head forward {neck_offset(feats, temp_base)[0]:+.1f}cm)"
                        if now - phase_start >= calib_sec:
                            if phase == "good_rec":
                                phase, phase_start, bad = "bad_ready", now, []
                                temp_base = make_base(good)
                                log.info(f"바른 자세 측정 완료 ({len(good)}개, 어깨 사용: {'sw0' in temp_base})")
                            else:
                                # 거북목 측정은 한 번만. 제대로 안 잡혔으면 다시 시키지 않고 기본값으로 바로 시작
                                model, sep, delta, noise = train(good, bad)
                                log.info(f"거북목 측정: 목 앞 {delta[0]:+.1f}cm, 아래 {delta[1]:+.1f}cm, "
                                         f"흔들림 {noise:.1f}cm, 구분 정도 {sep:.1f} -> {'성공' if model else '기본값 사용'}")
                                if model is None:
                                    model = train_default(good)
                                phase, filt = "run", OneEuro()
                                goal, torso_hold = None, TorsoHold(0.0)   # 학습 직후 몸통은 기준 그대로
                                log.info(f"자세 학습 완료 ({'기본값 사용' if model.get('default') else f'구분 정도 {sep:.1f}'}, "
                                         f"어깨 사용: {'sw0' in model}, "
                                         f"거북목 기준: 목이 앞으로 {model['delta'][0]:.1f}cm, 아래로 {model['delta'][1]:.1f}cm)")
                                if "sw0" not in model:
                                    log.warning("어깨가 잘 안 보여서 몸통 보정 없이 판정 -> 몸을 숙이면 거북목으로 볼 수 있음")
                                with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                                    json.dump(model, f)

                    # ---------- 판별 ----------
                    else:
                        recent.append(posture_score(model, feats))
                        # 최근 3번의 가운데 값 -> 한 번 튀는 값은 무시, 그다음 One Euro로 부드럽게, 0~100%로 제한
                        new_pct = min(max(filt(statistics.median(recent), now), 0.0), 100.0)
                        if feats["sh_from_memory"] and pct is not None and new_pct > pct + 1:
                            rise_since = rise_since or now
                            if now - rise_since < MEMORY_TRUST_SEC:
                                new_pct = pct   # 기억한 어깨로는 점수가 1초 넘게 높아야 올림 (짧은 어긋남 무시)
                        else:
                            rise_since = None
                        turned = abs(feats["pose"]["yaw"]) > YAW_TRUST
                        if turned and pct is not None and new_pct > pct:
                            new_pct = pct   # 고개를 많이 돌린 동안은 점수를 올리지 않음 (내려가는 건 허용)
                        goal = new_pct
                        advance(now)
                        sub = "head turned - score held" if turned else (
                            "" if "sw0" not in model or feats["sh_use"] else "shoulders not visible")

                        shoulder, tilt = None, feats["tilt"]
                        if tilt is not None and "tilt" in model:
                            shoulder = "틀어짐" if tilt - model["tilt"] >= cfg["shoulder_tilt_deg"] else "정상"
                        if now - last_save >= cfg["save_interval"]:
                            hp = feats["pose"]
                            fwd, down, lean = neck_offset(feats, model)
                            cue = ""
                            if feats["sh_use"] and "sw0" in model:   # 몸통이 다가온 거리: 어깨 너비로 / 높이로 잰 값
                                _, _, bw, bh = torso_forward(feats["sh_use"], model, hp["f"], feats["c"])
                                cue = f", 몸통 단서 너비 {bw:+.0f}cm·높이 " + ("없음" if bh is None else f"{bh:+.0f}cm")
                            log.info(f"{status} 점수 {pct:.0f}% (목 앞으로 {fwd:+.1f}cm, 아래로 {down:+.1f}cm, "
                                     f"몸통 숙임 {lean:+.0f}°{cue}, 고개 {hp['pitch']:+.0f}°, 거리 {hp['dist']:.0f}cm, "
                                     f"어깨 {'기억' if feats['sh_from_memory'] else ('사용' if feats['sh_use'] else '안 씀')})")
                            record(now, shoulder, tilt)
                            last_save = now

                fps_text = (f"cam {camera.rate.value:.0f} / screen {screen_rate.value:.0f} / "
                            f"face {face_thread.rate.value:.0f} / pose "
                            + (f"{pose_thread.rate.value:.0f} fps" if pose_thread else "off"))
                if now - last_fps_log >= 10:
                    log.info(f"처리 속도: {fps_text}")
                    last_fps_log = now

            if judge:   # 판정이 나오는 간격 (느린 기기일수록 김)
                if last_judge:
                    judge_dt += 0.3 * (min(now - last_judge, 1.0) - judge_dt)
                last_judge = now
            if (show or publisher is not None) and time.monotonic() - last_draw >= draw_interval:
                last_draw = time.monotonic()
                screen_rate.tick()
                shown_pct = None
                if phase == "run" and pct is not None:
                    t_now = time.monotonic()
                    if bar_val is None:
                        bar_val = pct
                    else:   # 부드럽게 다가감 (화면 표시만 바뀜, 판정·알림·기록은 그대로).
                        # 판정 간격이 길면(라즈베리파이) 그만큼 천천히 움직여서, 계단처럼 끊기지 않고 이어지게 함
                        tau = max(BAR_SMOOTH_SEC, 0.8 * judge_dt)
                        bar_val += (pct - bar_val) * (1 - math.exp(-(t_now - bar_t) / tau))
                    bar_t, shown_pct = t_now, bar_val
                    text = f"{STATUS_EN[status]}  {bar_val:.0f}%"
                else:
                    bar_val = None
                # 그림은 복사본에 그림 (얼굴·어깨 쓰레드가 같은 화면을 읽는 중일 수 있어서)
                if draw(cv2, mp, frame.copy(), show_pose, face_lm, text, color, sub, shown_pct, cfg,
                        fps_text, neck_line, publisher, show) == ord("c"):
                    if os.path.exists(BASELINE_FILE):
                        os.remove(BASELINE_FILE)
                    reset_measurements(cfg["server_url"])
                    restart_calibration("c 키 입력")
    finally:
        if publisher is not None:
            publisher.close()
        stop_event.set()   # 카메라·얼굴·어깨 쓰레드 모두 종료
        for t in threads:
            t.join(timeout=3)
        if show:
            cv2.destroyAllWindows()


PI_PROFILE = {"analysis_fps": 15, "pose_fps": 10, "model_complexity": 0, "display_fps": 20}


def apply_profile(cfg):
    """라즈베리파이(ARM)에서는 CPU가 모자라 화면이 끊기므로, profile이 "auto"(기본)면 가벼운 값으로 낮춤.
    - 얼굴 분석 초당 15회, 화면 표시 초당 20회 -> 남는 CPU를 어깨 계산에 줘서 점수 반응이 빨라짐
    - 어깨 모델은 가벼운 것(0) -> 어깨 계산이 약 2배 빨라짐 (첫 실행 때 인터넷에서 받고, 실패하면 기본 모델)
    profile을 "pc"로 하면 config.json 값을 그대로, "pi"로 하면 어디서든 가벼운 값을 씀"""
    import platform
    profile = cfg.get("profile", "auto")
    arm = platform.machine().lower() in ("aarch64", "arm64", "armv7l", "armv6l") and sys.platform.startswith("linux")
    if profile == "pi" or (profile == "auto" and arm):
        cfg = dict(cfg)
        for k, v in PI_PROFILE.items():
            cfg[k] = min(cfg.get(k, v), v) if k != "pose_fps" else v
        log.info(f"라즈베리파이용 가벼운 설정 적용: {PI_PROFILE} (끄려면 config.json에 \"profile\": \"pc\")")
    return cfg


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    global STATUS_URL
    cfg = load_json(CONFIG_FILE)
    if cfg is None:
        log.error(f"설정 파일 없음 또는 형식 오류: {CONFIG_FILE}")
        return
    if os.environ.get('POSTURE_WEB_LAUNCH') == '1':
        cfg['show_window'] = False
        cfg['web_video'] = True
        cfg['server_url'] = os.environ.get('POSTURE_SERVER_URL', cfg['server_url'])
    STATUS_URL = cfg["server_url"].rsplit("/", 1)[0] + "/status"
    global CAMERA_TILT, TORSO_CUE
    CAMERA_TILT = cfg.get("camera_tilt_deg", CAMERA_TILT)
    TORSO_CUE = cfg.get("torso_cue", TORSO_CUE)
    cfg = apply_profile(cfg)
    log.info(f"프로그램 시작 (판별기 버전 {VERSION}, 점수는 0~100%)")
    left = unsent_count()
    if left:
        log.info(f"지난번에 못 보낸 데이터 {left}개 있음 -> 서버 연결되면 자동 전송")
    while running:
        try:
            run(cfg)
            for _ in range(2):   # 쓰레드가 멈춰서 끝난 경우: 2초 쉬고 다시 시작
                if running:
                    time.sleep(1)
        except Exception as e:
            log.exception(f"오류 발생, 10초 후 재시작: {e}")
            for _ in range(10):   # 대기 중에도 Ctrl+C 바로 반영
                if running:
                    time.sleep(1)
    log.info("프로그램 종료")


def acquire_instance_lock():
    """Hold an OS lock until exit, including when started manually."""
    handle = open(os.path.join(BASE_DIR, 'posture.lock'), 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


if __name__ == "__main__":
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        log.error('posture.py가 이미 실행 중입니다. 기존 측정을 종료한 뒤 다시 시작하세요.')
        sys.exit(1)
    try:
        main()
    finally:
        instance_lock.close()
