# 거북목 판별기 (turtle_neck)

웹캠으로 앉은 자세를 보고 거북목을 판별해, 결과를 서버에 저장하고 웹 페이지로 보여줍니다.

```
[라즈베리파이 / 노트북]                         [서버 컴퓨터]
웹캠 → posture.py ──POST /api/record──→ app.py → turtle_neck.db
                                                  ↑
                                   브라우저 (index.html, 2초마다 갱신)
```

## 파일 구성

| 파일 | 실행 위치 | 역할 |
|---|---|---|
| `posture.py` | 라즈베리파이 | 카메라로 자세를 판별하고 결과를 서버로 전송 |
| `config.json` | 라즈베리파이 | 서버 주소와 판별 기준값 |
| `app.py` | 서버 | 측정값 저장, 조회 API, 웹 페이지 |
| `templates/index.html` | 브라우저 | 최근 측정 결과 표 |
| `test_posture.py` | 개발용 | 판별 로직과 서버 연동 확인 |

실행하면 자동으로 생기는 파일(git에 올리지 않음):
`baseline.json`(기준자세), `posture.log`(판별기 로그), `turtle_neck.db`(서버 DB)

## 0. 코드 받기와 가상환경 (서버·판별기 기기 모두)

```bash
git clone -b develop https://github.com/tkacjstp/turtle_neck.git
cd turtle_neck
python3 -m venv venv
source venv/bin/activate
```

- 윈도우는 `venv\Scripts\activate` 입니다. 프롬프트 앞에 `(venv)`가 보이면 성공입니다.
- 새 터미널을 열 때마다 `source venv/bin/activate`를 다시 실행하세요.
- 라즈베리파이 최신 OS는 가상환경 없이 `pip install` 하면 `externally-managed-environment` 오류가 납니다.
- **Python은 3.9~3.12**여야 합니다(3.11 권장). 3.13 이상이면 판별기용 `mediapipe`가 설치되지 않으니 `python3.11 -m venv venv`처럼 버전을 지정해 가상환경을 만드세요. 버전 확인은 `python3 --version`. 라즈베리파이는 64비트 OS가 필요합니다.

## 1. 서버 실행

```bash
pip install flask
python3 app.py
```

- `http://<서버 IP>:5050` 에 접속하면 결과 표가 보입니다.
- 서버 IP 확인: macOS `ipconfig getifaddr en0`, Windows `ipconfig`, Linux `hostname -I`

## 2. 판별기 실행

```bash
pip install mediapipe==0.10.18
```

- **mediapipe는 반드시 0.10.18**로 설치하세요. 버전을 지정하지 않으면 최신 버전이 설치되는데, 0.10.30 이상은 이 코드가 쓰는 `mp.solutions`가 없어 실행되지 않습니다. 0.10.20·0.10.21은 라즈베리파이용 설치 파일이 없습니다.
- OpenCV는 mediapipe와 함께 설치됩니다. `opencv-python`을 따로 설치하면 충돌할 수 있습니다.

`config.json`의 `server_url`을 **서버 컴퓨터의 IP**로 바꾼 뒤 실행합니다.

```bash
python3 posture.py
```

1. 카메라가 사용자 **정면**을 보도록 둡니다. 양쪽 귀·입·양쪽 어깨가 모두 화면에 나와야 합니다.
2. 처음 실행하면 사람이 감지된 뒤 `calib_sec`초 동안 **바른 자세**로 앉아 있으세요. 이 자세가 기준값(`baseline.json`)으로 저장됩니다.
3. 이후 기준보다 자세가 나빠진 상태가 `hold_sec`초 이상 이어지면 경고/위험으로 판정합니다.
4. `save_interval`초마다 결과를 서버로 보냅니다. 서버가 꺼져 있어도 최대 1000개까지 보관했다가 연결되면 한꺼번에 보냅니다.

종료는 `Ctrl+C`입니다. 카메라 창이 떠 있으면 창에서 `q`를 눌러도 됩니다.

**카메라 창**: 실행하면 카메라 화면에 관절점과 현재 상태(`NORMAL`/`WARNING`/`DANGER`, 악화율)가 표시됩니다. 모니터가 없는 환경(systemd 자동 실행, SSH 접속)에서는 자동으로 창 없이 실행됩니다.

## 3. 설정 (config.json)

| 키 | 의미 | 기본값 |
|---|---|---|
| `server_url` | 서버 주소 | `http://<서버 IP>:5050/api/record` |
| `user_id` | 사용자 구분 | `user1` |
| `calib_sec` | 기준자세 측정 시간(초) | 5 |
| `warning_pct` | 경고 기준 악화율(%) | 10 |
| `danger_pct` | 위험 기준 악화율(%) | 20 |
| `hold_sec` | 경고/위험 확정까지 지속시간(초) | 10 |
| `shoulder_tilt_deg` | 어깨 틀어짐 기준(°) | 5 |
| `save_interval` | 서버 전송 주기(초) | 5 |
| `show_window` | 카메라 창 표시 (모니터 없으면 자동으로 끔) | true |

- 설정을 바꾸면 판별기를 **재시작**해야 반영됩니다.
- 판별이 너무 민감하면 `warning_pct`, `danger_pct`, `hold_sec`를 올리고, 둔하면 내리세요.
- **기준자세 다시 잡기**: `baseline.json`을 지우고 재시작합니다. 카메라 위치를 바꿨거나 다른 기기로 옮겼을 때도 꼭 지우세요.

## 4. 판별 방식

MediaPipe Pose로 귀·입·어깨 좌표를 찾아 지표 4개를 계산합니다. 모두 **어깨 너비로 나눈 비율**이라 카메라와의 거리가 달라져도 값이 유지됩니다.

| 지표 | 계산 | 나빠지면 |
|---|---|---|
| `neck` | 귀~어깨 높이 | 줄어듦 (거북목) |
| `mouth` | 입~어깨 높이 | 줄어듦 (고개 숙임) |
| `face` | 양쪽 귀 사이 거리 | 커짐 (머리가 앞으로) |
| `tilt` | 어깨 기울기 | 커짐 (어깨 틀어짐) |

기준자세 대비 **가장 많이 나빠진 지표의 %(악화율)** 를 최근 15프레임 평균으로 구해 정상/경고/위험을 정합니다.

LED·부저를 연결하려면 `posture.py`의 `on_status_change()`에 코드를 넣으면 됩니다. 상태가 바뀔 때마다 호출됩니다.

## 5. 라즈베리파이 부팅 시 자동 실행 (systemd)

`/etc/systemd/system/turtle.service` 파일을 만듭니다. 경로와 사용자 이름은 환경에 맞게 바꾸세요.
`ExecStart`는 **가상환경 안의 python**을 가리켜야 설치한 라이브러리를 찾습니다.

```ini
[Unit]
Description=Turtle neck detector
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/turtle_neck
ExecStart=/home/pi/turtle_neck/venv/bin/python /home/pi/turtle_neck/posture.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now turtle
```

- 상태 확인: `systemctl status turtle`
- 로그 보기: `journalctl -u turtle -f` 또는 `posture.log`
- 설정 변경 후 재시작: `sudo systemctl restart turtle`

## 6. API

| 경로 | 설명 |
|---|---|
| `POST /api/record` | 측정값 저장. `status`는 `정상`/`경고`/`위험`만 허용 |
| `GET /api/results?limit=20` | 최근 측정값 (최대 500개) |
| `GET /api/stats?date=YYYY-MM-DD` | 그날 상태별 개수와 비율 |

`/api/record` 요청 예시:

```json
{
  "user_id": "user1",
  "timestamp": "2026-10-07 10:00:00",
  "worse_pct": 15.0,
  "status": "경고",
  "shoulder_status": "정상",
  "shoulder_tilt": 1.0,
  "bad_duration": 12.0
}
```

`worse_pct`는 DB의 `angle` 컬럼에도 저장됩니다(예전 형식과의 호환용).

## 7. 테스트

카메라 없이 판별 로직과 서버 연동을 확인합니다(`flask`만 있으면 됩니다).

```bash
python3 test_posture.py
```

마지막에 `OK`가 나오면 통과입니다.

## 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `전송 실패 ... timed out` | `server_url`의 IP가 틀렸거나, 두 기기가 다른 네트워크에 있거나, 서버 방화벽이 막고 있음. 판별기 기기에서 `curl http://<서버 IP>:5050/api/results`로 확인 |
| `전송 실패 ... Connection refused` | 서버(`app.py`)가 꺼져 있음 |
| macOS에서 서버 포트 충돌 | 5000번은 AirPlay 수신이 사용하므로 이 프로젝트는 5050번을 씀 |
| `카메라 연결 실패` 반복 | 카메라 연결 확인. 0번 카메라(처음 인식된 카메라)를 사용함. 맥은 시스템 설정 → 개인정보 보호 → 카메라에서 터미널/VS Code 허용 |
| `pip install mediapipe==0.10.18` 실패 | Python 3.9~3.12인지 확인(3.11로 가상환경 다시 만들기). 라즈베리파이는 64비트 OS 확인 |
| `module 'mediapipe' has no attribute 'solutions'` | mediapipe 버전이 너무 최신. `pip install mediapipe==0.10.18`로 다시 설치 |
| 카메라 창이 안 뜸 | 모니터 없이(SSH·systemd) 실행 중이거나 `show_window`가 false. `opencv-python-headless`가 설치돼 있으면 삭제 |
| systemd 실행 시 `ModuleNotFoundError` | `ExecStart`가 가상환경 python(`venv/bin/python`)을 가리키는지 확인 |
| 라즈베리파이 카메라 모듈(리본 케이블)이 안 열림 | 최신 라즈베리파이 OS는 `cv2.VideoCapture`로 바로 안 열릴 수 있음. USB 웹캠을 쓰거나 `picamera2` 사용 |
| 판정이 이상함 | `baseline.json`을 지우고 바른 자세로 기준값을 다시 측정 |
