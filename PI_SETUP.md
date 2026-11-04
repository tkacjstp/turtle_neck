# 파이의 낮은 버전 MediaPipe 환경

posture.py는 최신 Tasks API가 아닌 기존 mp.solutions API를 사용합니다.
MediaPipe 0.10.18로 설치 버전을 고정합니다. 낮은 버전의 Pose·FaceMesh 방식과
노트북 Wi-Fi 영상 수신은 함께 사용할 수 있습니다.

Python 3.9~3.12 및 64비트 ARM Linux 환경을 사용하세요.

```bash
cd /home/pi/turtle_neck
python3 --version
uname -m
python3 -m venv .venv-pi
source .venv-pi/bin/activate
python -m pip install -r requirements-pi.txt
python -c "import mediapipe as mp; print(mp.__version__, mp.__file__); print(hasattr(mp, 'solutions'))"
python posture.py
```

매번 실행 전 `source .venv-pi/bin/activate`로 같은 환경을 활성화하세요.
기존에 쓰던 가상 환경이 있다면 그 환경을 활성화한 후 requirements-pi.txt로 설치해도 됩니다.
설정 파일과 보정값은 이 설치 명령으로 변경하지 않습니다.

Python 3.13 이상 또는 32비트 환경이라서 설치 가능한 배포본이 없다는 오류가 나오면
설치된 Python 버전과 uname -m 결과부터 확인하세요. 이 환경에서는 0.10.18 설치를
강제로 진행하지 말고 지원하는 Python/OS 환경을 준비해야 합니다.

시작 시 호환 API를 확인하고, 맞지 않으면 카메라를 열기 전에 설치 안내와
실제로 불러온 모듈 위치를 표시하고 종료합니다. 설치만 바꾸려면 코드 전체를
덮어쓸 필요가 없습니다. 최신 버전의 posture.py를 받을 때는 mediapipe_compat.py도 함께 받으세요.

MediaPipe 0.10.18 배포 정보: https://pypi.org/project/mediapipe/0.10.18/
