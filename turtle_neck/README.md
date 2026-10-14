# 거북목 판별기 (turtle_neck)

노트북 카메라로 앉은 자세를 보고 거북목을 판별해, 결과를 서버에 저장하고 웹 페이지로 보여줍니다.
라즈베리파이는 판정 결과를 받아 LED·부저·진동으로 알리고, 센서값을 서버로 보냅니다.

```
[노트북]  카메라 → posture.py ──POST /api/record──→ app.py → turtle_neck.db
                       └─POST /api/status (상태 변경 즉시)─┘ │   ↑
                                                             │   브라우저 (index.html)
[라즈베리파이]  rpi_device.py ── GET /api/status (0.3초마다) ─┘
                (LED·부저·진동)   POST /api/sensor (센서값)
```

## 파일 구성

| 파일 | 실행 위치 | 역할 |
|---|---|---|
| `posture.py` | 노트북 | 카메라로 자세를 판별하고 결과를 서버로 전송 |
| `config.json` | 노트북 | 서버 주소와 판별 기준값 |
| `app.py` | 노트북 | 측정값·센서값 저장, 지금 상태 전달, 조회 API, 웹 페이지 |
| `rpi_device.py` | 라즈베리파이 | 상태에 따라 LED·부저·진동, 센서값 전송 |
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
4. `save_interval`초마다 결과를 판별기 쪽 `posture_data.db`에 저장한 뒤 서버로 보냅니다. 서버가 꺼져 있으면 DB에 남겨 두었다가 연결되면 자동으로 보냅니다.

**판별 방식**: 정면 웹캠으로 어깨(Pose)와 눈·코(Face Mesh, 얼굴 468점)를 찾아, "눈 사이 거리 / 어깨 너비"로 머리가 앞으로 나온 정도를, "어깨선~눈 높이 / 어깨 너비"로 머리가 내려간 정도를 잽니다. 몸 전체가 카메라에 다가오거나 멀어져도 값이 그대로라 거리 영향을 받지 않습니다. 카메라 창에서 `c` 키를 누르면 기준자세를 다시 잡습니다.

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
| `model_complexity` | 1: 정확 / 0: 가벼움(라즈베리파이가 느릴 때) | 1 |
| `smooth_sec` | 최근 몇 초의 중간값으로 판정할지 | 2 |
| `hysteresis_pct` | 경고 진입 후 해제 기준을 몇 % 낮출지 (깜빡임 방지) | 2 |
| `analysis_fps` | 초당 분석 횟수 (낮추면 CPU 절약). 실제 속도는 1분마다 로그에 `분석 속도`로 남음 | 10 |
| `camera_fov_deg` | 카메라 가로 화각(°). 카메라 거리 추정용 — 제품 사양에 있으면 그 값으로 | 65 |

- 설정을 바꾸면 판별기를 **재시작**해야 반영됩니다.
- 판별이 너무 민감하면 `warning_pct`, `danger_pct`, `hold_sec`를 올리고, 둔하면 내리세요.
- **기준자세 다시 잡기**: `baseline.json`을 지우고 재시작합니다. 카메라 위치를 바꿨거나 다른 기기로 옮겼을 때도 꼭 지우세요.

## 4. 판별 방식

Pose로 어깨, Face Mesh로 양쪽 눈 끝·코끝을 찾아 지표를 계산합니다. 모두 **어깨 너비로 나눈 비율**입니다.

| 지표 | 계산 | 나빠지면 |
|---|---|---|
| `forward` | 눈 사이 거리 / 어깨 너비 | 커짐 (머리만 카메라 쪽으로 나옴) |
| `height` | 어깨선~눈 높이 / 어깨 너비 | 작아짐 (목을 빼고 숙임, 구부정함) |
| `tilt` | 어깨 기울기(°) | 커짐 (어깨 틀어짐, 따로 판정) |
| `dist` | 카메라~눈 거리 추정(cm) | 판정 보정용 |

- 기준자세 대비 **더 많이 나빠진 쪽의 %(악화율)** 를 최근 `smooth_sec`초 중간값으로 구해 정상/경고/위험을 정합니다.
- `forward`는 카메라 거리(`dist`)로 **60cm 기준 %로 환산**해서, 카메라가 가깝든 멀든 같은 기준으로 판정합니다.
- 몸통만 돌려 어깨가 좁아 보이는 경우는 머리가 나온 것으로 치지 않습니다(눈이 실제로 가까워진 만큼만 인정).
- 고개를 옆으로 돌렸거나 다른 사람 얼굴이 잡힌 순간은 판정에서 뺍니다.

## 5. 라즈베리파이 알림·센서 (rpi_device.py)

라즈베리파이에는 `rpi_device.py` 하나만 있으면 됩니다. 기본 `python3`와 `gpiozero`(라즈베리파이 OS에 기본 설치)만 쓰므로 **가상환경·mediapipe 설치가 필요 없습니다.**

**1) 설정** — `rpi_device.py` 위쪽

| 항목 | 의미 | 기본값 |
|---|---|---|
| `SERVER` | 노트북 서버 주소 (노트북에서 `ipconfig getifaddr en0`) | `http://노트북IP:5050` |
| `LED_PIN`, `BUZZER_PIN`, `VIBRATION_PIN` | BCM 핀 번호. 없는 장치는 `None` | 17, 27, 22 |
| `POLL_SEC` | 상태 확인 주기(초) | 0.3 |
| `SENSOR_SEC` | 센서값 전송 주기(초) | 5 |
| `STALE_SEC` | 판별기 소식이 이 시간 넘게 없으면 알림 끔 | 15 |

**2) 센서 연결** — `read_sensors()`가 `{"이름": 숫자}`를 돌려주면 서버 DB(`sensor_readings`)에 저장됩니다.

```python
from gpiozero import DistanceSensor
sonar = DistanceSensor(echo=24, trigger=23)   # 파일 위쪽에서 한 번만 만들기

def read_sensors():
    return {"distance_cm": sonar.distance * 100}
```

**3) 실행** (노트북에서 `app.py`, `posture.py`를 먼저 켠 뒤)

```bash
python3 rpi_device.py
```

| 판정 | 동작 |
|---|---|
| 정상 | 모두 꺼짐 |
| 경고 | LED 켜짐 + 진동 짧게 한 번 |
| 위험 | LED 깜빡임 + 부저 삐- 삐- + 진동 짧게 한 번 |
| 서버 연결 끊김 / 판별기 꺼짐 | 모두 꺼짐 |

상태가 바뀌고 약 0.2~0.5초 안에 반응합니다. 연결이 안 되면 라즈베리파이에서 `curl http://노트북IP:5050/api/status`로 확인하세요(같은 와이파이, 맥 방화벽).

배선 없이 동작만 시험하려면 가짜 GPIO로 실행합니다: `GPIOZERO_PIN_FACTORY=mock python3 rpi_device.py`

**4) 부팅 시 자동 실행 (systemd)** — `/etc/systemd/system/turtle.service` (경로·사용자 이름은 환경에 맞게)

```ini
[Unit]
Description=Turtle neck RPi alerts and sensors
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/turtle_neck
ExecStart=/usr/bin/python3 /home/pi/turtle_neck/rpi_device.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now turtle
```

- 상태 확인: `systemctl status turtle`
- 로그 보기: `journalctl -u turtle -f`
- 설정 변경 후 재시작: `sudo systemctl restart turtle`

## 6. API

| 경로 | 설명 |
|---|---|
| `POST /api/record` | 측정값 저장. `status`는 `정상`/`경고`/`위험`만 허용 |
| `GET /api/results?limit=20` | 최근 측정값 (최대 500개) |
| `GET /api/stats?date=YYYY-MM-DD` | 그날 상태별 개수와 비율 |
| `POST /api/status` | 판별기가 지금 상태를 알림 `{"status": "경고"}` |
| `GET /api/status` | 지금 상태와 마지막 소식 후 지난 초 `{"status": "경고", "age": 1.2}` |
| `POST /api/sensor` | 센서값 저장 `{"timestamp": "...", "values": {"distance_cm": 42.5}}` |
| `GET /api/sensor?limit=20` | 최근 센서값 |

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
| 라즈베리파이에서 `No module named gpiozero` | `sudo apt install python3-gpiozero` |
| 라즈베리파이 카메라 모듈(리본 케이블)이 안 열림 | 최신 라즈베리파이 OS는 `cv2.VideoCapture`로 바로 안 열릴 수 있음. USB 웹캠을 쓰거나 `picamera2` 사용 |
| 사람이 있는데 `NO PERSON` / `MOVE BACK` | 양쪽 귀·입·양쪽 어깨가 모두 화면에 나오도록 의자를 뒤로 빼거나 카메라를 멀리 두기 |
| `config.json 형식 오류: N번째 줄` | 그 줄 근처의 쉼표·따옴표 확인 (한글 따옴표 “ ”, 끝에 남은 쉼표, `True` 대문자 등) |
| `가벼운 모델 다운로드 실패, 기본 모델로 실행` | 네트워크가 모델 다운로드를 막은 것. 자동으로 기본 모델로 실행되니 그대로 써도 됨 (라즈베리파이에서는 조금 느려질 수 있음) |
| 판정이 이상함 | `baseline.json`을 지우고 바른 자세로 기준값을 다시 측정 |

## DB 전달기 (forward.py, 선택)

서버의 `turtle_neck.db`에 쌓인 측정 결과를 **다른 서버로 옮겨 보내야 할 때** 사용합니다. 필요 없으면 실행하지 않아도 됩니다.

1. `forward.py` 위쪽의 `FORWARD_URL`을 받는 서버 주소로 바꿉니다. (예: `http://192.168.0.10:5050/api/record`)
2. `app.py`와 같은 폴더에서, 창을 하나 더 열어 실행합니다.
   ```bash
   python forward.py          # 계속 실행하면서 10초마다 새 데이터 전송
   python forward.py --once   # 지금까지 쌓인 것만 보내고 종료
   ```

이미 보낸 데이터는 다시 보내지 않습니다(어디까지 보냈는지 `forward_state.json`에 기록). 받는 서버가 꺼져 있으면 기다렸다가 켜지면 밀린 것부터 순서대로 보냅니다. 처음부터 다시 보내려면 `forward_state.json`을 삭제하세요. 받는 서버는 `app.py`의 `/api/record`와 같은 JSON 형식을 받아야 하며, 형식이 다르면 `forward.py`의 `make_payload()`만 고치면 됩니다.
