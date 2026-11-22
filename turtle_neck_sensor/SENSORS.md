# Arduino USB RGB·부저 연동

Sensor Shield 5.0을 꽂은 Arduino를 USB로 연결하는 구성입니다.
배선 번호는 `posture_rgb/posture_rgb.ino`의 상수에서 관리합니다.

| 출력 | Sensor Shield 신호 핀 |
| --- | --- |
| 파랑 B | D11의 S |
| 초록 G | D10의 S |
| 빨강 R | D9의 S |
| 부저 | D3의 S |

Arduino IDE에서 `posture_rgb/posture_rgb.ino`를 업로드하세요.
Windows에서는 `python -m pip install pyserial`로 시리얼 패키지를 설치하고,
`python usb_device.py --port COM3`을 실행합니다. COM3은 실제 포트로 바꾸세요.
별도 터미널에서 `python app.py`를 실행한 뒤 웹에서 측정을 시작합니다.
기본 동작은 정상 초록, 경고 노랑 점멸, 위험 빨강과 부저입니다.
스케치는 공통 GND RGB와 HIGH에서 켜지는 능동 부저를 기본으로 설정합니다.

## 라즈베리파이 GPIO 직접 연결용 설정

아래 내용은 USB Arduino 없이 Raspberry Pi GPIO에 직접 연결할 때의 설정입니다.
`sensor_config.json`의 BCM 17·18은 이 방식에서만 출력 핀으로 쓰입니다.

기준: feature/p 커밋 b699ad280614a65fb623a08033b1b52d0252c120.
최신 저장소 최상위 app.py·posture.py와 함께 사용합니다.
이 폴더에는 최신 웹 시작·종료 기능을 유지한 실행 파일이 들어 있습니다.

## 동작

| 자세 | LED | 부저 |
| --- | --- | --- |
| 정상 / 연결 대기 | 꺼짐 | 꺼짐 |
| 경고 | 0.5초 간격 점멸 | 꺼짐 |
| 위험 | 켜짐 | 1초마다 0.2초 울림 |

posture.py → POST /api/status → app.py → GET /api/sensor_status → rpi_device.py → GPIO.
밀린 DB 기록은 센서 알림으로 재생하지 않습니다. 새 상태가 8초 동안 없으면 꺼집니다.
서버 연결 실패 시 꺼지고, 통신 스레드가 멈추어도 마지막 수신으로부터 2초 후 꺼집니다.
GPIO 제어와 통신을 분리해 HTTP 대기 중에도 부저 펄스가 길어지지 않게 합니다.
Ctrl+C/SIGTERM 종료 시 출력을 끄고 GPIO를 해제합니다.

## 배선 설정

아래는 기본 예시이며 실제 연결을 확인한 핀 번호가 아닙니다.
sensor_config.json을 실제 배선에 맞게 수정하세요. 핀 번호는 BCM입니다.

| 출력 | 설정 | 물리 핀 |
| --- | --- | --- |
| LED 신호 | led_pin: 17 | 11번 |
| 부저 신호 | buzzer_pin: 18 | 12번 |
| 공통 GND | GND | 예: 6번 |

LED가 일반 소자라면 GPIO와 LED 사이에 전류 제한 저항을 넣습니다.
부저 모듈은 인쇄된 S/+/− 표시로 신호·전원·GND를 구분하세요.
모듈의 왼쪽부터 순서를 추측해서 연결하지 마세요.
GPIO는 3.3V 신호입니다. 부저의 전원 전압·구동 전류는 모듈 사양을 확인해야 하며,
2핀 부저를 GPIO에서 직접 구동할 수 있다고 가정하지 마세요. 필요하면 트랜지스터 구동 회로를 사용합니다.

- 능동 부저: buzzer_type을 active로 설정합니다(기본).
- 수동 부저: buzzer_type을 passive로 설정하고 tone_hz로 음높이를 지정합니다.
- LOW 신호에 켜지는 능동 모듈: buzzer_active_high를 false로 설정합니다.
- 사용하지 않는 출력의 pin은 null로 설정할 수 있습니다.

## 실행

라즈베리파이에서 GPIO 라이브러리를 설치합니다.

```bash
sudo apt install python3-gpiozero python3-lgpio
```

app.py·posture.py는 기존 MediaPipe 가상환경에서 실행합니다.

```bash
python app.py
```

브라우저 http://127.0.0.1:5050 의 시작 버튼으로 측정을 시작합니다.
별도 터미널에서 OS Python으로 센서 제어를 실행합니다(apt로 설치한 GPIO 패키지를 사용).

```bash
/usr/bin/python3 rpi_device.py
```

윈도우 또는 GPIO 없이 상태 전달을 확인하려면:

```bash
python rpi_device.py --dry-run
```

GPIO 번호와 부저 종류를 바꾼 뒤에는 rpi_device.py를 재실행하세요.
app.py는 단일 프로세스로 실행합니다. 최신 상태는 메모리에 보관합니다.

## 검사

```bash
python -m unittest test_sensors test_web_video -v
```

자동 검사는 상태 만료, 통신 지연 시 출력 차단, 능동·수동 부저 호출,
DB 재전송과 실시간 알림 분리, 기존 영상 전송을 확인합니다.
실제 라즈베리파이 GPIO·배선·부저 소리는 대상 기기에서 확인해야 합니다.

GPIO Zero API: https://gpiozero.readthedocs.io/en/stable/api_output.html
