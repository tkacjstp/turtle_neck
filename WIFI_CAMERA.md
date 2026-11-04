# 노트북 웹캠 → Wi-Fi → 라즈베리 파이

두 기기에 feature/p 코드를 받고, 서로 접속 가능한 네트워크에 연결합니다.
USB 케이블은 필요하지 않습니다. 학교 Wi-Fi가 기기 간 접속을 차단한다면
허용된 개인 공유기나 핫스팟 등 서로 접속 가능한 네트워크를 사용하세요.

## 1. 노트북에서 웹캠 송출

```powershell
python -m pip install flask opencv-python
python webcam_stream.py --host 노트북의Wi-FiIPv4
```

실행 창에 출력된 키 포함 영상 주소를 노트북 브라우저에서 열어 영상을 확인합니다.
기본값은 로컬 접속만 허용하므로, 파이와 공유할 때는 위처럼 Wi-Fi IPv4를 지정하세요.
카메라가 안 나오면 다른 카메라 앱을 닫고 Windows 카메라 접근 권한을 확인하세요.
다른 카메라를 쓰려면 실행 명령에 `--camera 1`을 추가합니다.
종료는 Ctrl+C입니다. 실행 중인 창은 계속 열어 두세요.

`ipconfig`의 Wi-Fi IPv4를 확인합니다. 예를 들어 `192.168.0.10`이라면
영상 주소는 `http://192.168.0.10:8080/video_feed?token=출력된키`입니다.
Windows 방화벽에서 사용하는 네트워크에 대해 Python의 TCP 8080 수신을 허용해야 합니다.
이 스트림은 실행할 때마다 생성되는 무작위 키로 인증합니다. 주소에 키가 있으므로 공유하지 마세요.
HTTP 영상은 암호화되지 않으므로 신뢰하는 네트워크에서만 실행하고
외부 인터넷으로 포트를 공개하지 마세요.

## 2. 파이에서 영상 수신 확인

파이 브라우저에서 노트북이 출력한 키 포함 영상 주소가 열리는지 확인합니다.
OpenCV(FFmpeg 백엔드 포함)가 설치된 Python 환경에서 실행하세요.

```bash
python3 detect_video.py --url "http://노트북IP:8080/video_feed?token=출력된키"
```

`[연결 성공] 노트북 네트워크 카메라`가 나오면 실제 영상 수신까지 확인된 것입니다.
이 명령은 확인 후 종료합니다. `/health?token=출력된키` 주소는 카메라가 준비되면 200,
준비되지 않았으면 503을 반환합니다.

## 3. 자세 분석 시작

파이의 config.json에서 다음 값을 설정합니다. IP는 실제 노트북 주소로 바꾸세요.

```json
"camera_url": "http://192.168.0.10:8080/video_feed?token=출력된키",
"camera_device": null
```

```bash
python3 posture.py
```

camera_url이 있으면 해당 영상이 우선입니다. 수신이 끊어지면 같은 주소로 재연결합니다.
USB 카메라로 돌아가려면 camera_url을 null로 바꾸고 posture.py를 재시작하세요.
노트북 IP가 바뀌면 camera_url도 수정해야 합니다.
송출 프로그램을 다시 시작하면 키가 바뀌므로 camera_url을 다시 복사하고 posture.py를 재시작하세요.
키가 없거나 잘못되면 401 응답입니다. 키 포함 설정 파일을 GitHub에 올리지 마세요.

측정 결과를 받는 app.py는 별도로 실행합니다. 노트북에서 받는다면
`server_url`은 `http://노트북IP:5050/api/record`로 설정합니다.
영상 포트 8080과 측정 결과 포트 5050은 서로 다른 역할입니다.
웹캠 송출만 하는 노트북에는 MediaPipe가 필요하지 않습니다.

## 검증

`python -m unittest test_detect_video test_webcam_stream -v`

테스트에는 Flask 스트리밍 응답과 실제 OpenCV JPEG 영상 디코딩 확인이 포함됩니다.
로컬 HTTP 송수신 테스트도 포함되지만, 실행 환경에서 로컬 접속을 차단하면 건너뜁니다.
실제 노트북 카메라, 라즈베리 파이 및 학교 Wi-Fi에서의 확인은 별도로 필요합니다.

OpenCV 네트워크 열기·읽기 제한 시간은 FFmpeg 백엔드에 설정하며 각 5초입니다.
드라이버·백엔드 구현에 따라 응답 시간이 달라질 수 있습니다.
문서: https://docs.opencv.org/4.10.0/d4/d15/group__videoio__flags__base.html
