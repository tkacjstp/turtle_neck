# 라즈베리 파이 비디오 장치 인식

USB 웹캠이나 USB 비디오 캡처 장치처럼 V4L2로 영상을 제공하는 장치용입니다.
CSI 카메라의 Picamera2/libcamera 연결은 별도로 구현해야 합니다.

## 연결 확인

```bash
sudo apt install python3-opencv
python3 detect_video.py
python3 detect_video.py --device /dev/video2
```

이 명령은 장치를 열어 실제 프레임을 확인하고 장치 경로·이름·해상도를 출력한 뒤 종료합니다.
설치는 실행에 사용하는 Python 환경에 맞게 진행하세요.

## 자세 판별 프로그램

기존 의존성이 설치된 환경에서 `python3 posture.py`를 실행합니다.
`config.json`의 `"camera_device": null`은 자동 검색입니다.
고정하려면 `"camera_device": "/dev/video2"`로 설정합니다.
숫자 `2`도 Linux에서 `/dev/video2`로 처리됩니다.
재연결할 때도 이 설정을 사용합니다.

자동 검색은 `/dev/video*`를 번호순으로 확인하고 V4L2 기능을 조회합니다.
메타데이터 전용 장치와 메모리 간 영상 처리 장치를 제외하고,
실제 프레임을 읽을 수 있는 첫 장치를 선택합니다.
카메라가 여러 개라면 장치를 직접 지정하세요.
연결 실패 시 5초 후 장치 목록을 다시 검색합니다.
Windows에서는 기존처럼 기본 카메라 0번을 사용합니다.

권한 오류가 나오면 `ls -l /dev/video*`와 `groups`로 접근 권한을 확인하세요.
영상 수신이 실패하면 케이블, 입력 신호, 다른 프로그램의 장치 사용 여부를 확인하세요.
프레임 확인은 최대 10회 시도하지만 드라이버의 `read()`가 멈추는 경우를 위한
강제 시간 제한은 없습니다.

## 검증

```bash
python3 -m unittest test_detect_video -v
```

이 테스트는 장치 기능 조회, 프레임 수신, 실패, 종료, 재검색을 모의 검증합니다.
실제 라즈베리 파이의 드라이버·권한·영상 입력 검증은 위 연결 확인 명령으로 수행하세요.

V4L2 장치 기능 확인 기준:
https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/vidioc-querycap.html
