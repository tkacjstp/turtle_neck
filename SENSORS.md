# RGB LED·부저 직결

기준: feature/p 커밋 b699ad280614a65fb623a08033b1b52d0252c120.
최신 저장소 최상위 app.py·posture.py와 함께 사용합니다.
이 폴더에는 최신 웹 시작·종료 기능을 유지한 실행 파일이 들어 있습니다.

## 동작

| 자세 | LED | 부저 |
| --- | --- | --- |
| 정상 | 파랑 | 꺼짐 |
| 연결 대기 | 꺼짐 | 꺼짐 |
| 경고 | 빨강 점멸 | 꺼짐 |
| 위험 | 노랑 | 위험 상태가 유지되는 동안 계속 울림 |

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
| 빨강 R | GPIO10 | 19번 |
| 초록 G | GPIO9 | 21번 |
| 파랑 B | GPIO11 | 23번 |
| 부저 신호 | GPIO2 | 3번 |
| 공통 GND | GND | 예: 6번 |

`rgb_pins`는 R, G, B 순서로 `[10, 9, 11]`을 지정합니다. `buzzer_pin`은 `2`입니다.
물리 2번은 5V 전원입니다. 부저 신호선은 물리 3번(GPIO2)에 연결합니다.
GPIO2는 I²C SDA와 겹칩니다. 같은 핀에 I²C 장치를 연결하지 마세요.
일반 RGB LED에는 채널마다 직렬 저항을 사용합니다. 공통 캐소드면 `rgb_active_high: true`, 공통 애노드면 `false`입니다.
부저 모듈은 인쇄된 S/+/− 표시로 신호·전원·GND를 구분하세요.
모듈의 왼쪽부터 순서를 추측해서 연결하지 마세요.
GPIO는 3.3V 신호입니다. 부저의 전원 전압·구동 전류는 모듈 사양을 확인해야 하며,
2핀 부저를 GPIO에서 직접 구동할 수 있다고 가정하지 마세요. 필요하면 트랜지스터 구동 회로를 사용합니다.

- 능동 부저: buzzer_type을 active로 설정합니다(기본).
- 수동 부저: buzzer_type을 passive로 설정하고 tone_hz로 음높이를 지정합니다.
- LOW 신호에 켜지는 능동 모듈: buzzer_active_high를 false로 설정합니다.
- RGB나 부저를 비활성화하려면 해당 `rgb_pins` 또는 `buzzer_pin`을 `null`로 설정할 수 있습니다.

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
