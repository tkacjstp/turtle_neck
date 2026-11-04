"""Run on the laptop: python webcam_stream.py (port 8080).

Shares the laptop camera as MJPEG on the local network. Stop with Ctrl+C.
Dependencies: pip install flask opencv-python
"""

import argparse
import logging
import hmac
import secrets
import threading
import time

from flask import Flask, Response, jsonify, request


class Webcam:
    def __init__(self, cv2, device=0, fps=15):
        self.cv2 = cv2
        self.device = device
        self.fps = fps
        self.condition = threading.Condition()
        self.stopped = threading.Event()
        self.jpeg = None
        self.updated = 0.0
        self.sequence = 0
        self.thread = None

    def publish(self, jpeg):
        with self.condition:
            self.jpeg = jpeg
            self.updated = time.monotonic()
            self.sequence += 1
            self.condition.notify_all()

    def ready(self):
        with self.condition:
            return self.jpeg is not None and time.monotonic() - self.updated < 5

    def frames(self):
        sequence = -1
        while not self.stopped.is_set():
            with self.condition:
                self.condition.wait_for(
                    lambda: self.stopped.is_set() or self.sequence != sequence, timeout=5)
                if self.stopped.is_set():
                    return
                if self.sequence == sequence or self.jpeg is None:
                    return  # Close stale connections so receivers can reconnect.
                if time.monotonic() - self.updated >= 5:
                    return
                jpeg, sequence = self.jpeg, self.sequence
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpeg)).encode("ascii") + b"\r\n\r\n" + jpeg + b"\r\n")

    def start(self):
        self.thread = threading.Thread(target=self._capture, daemon=True)
        self.thread.start()

    def stop(self):
        self.stopped.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread:
            self.thread.join(timeout=6)

    def _capture(self):
        cv2 = self.cv2
        while not self.stopped.is_set():
            cap = None
            try:
                cap = cv2.VideoCapture(self.device)
                if not cap.isOpened():
                    raise RuntimeError("노트북 카메라를 열지 못했습니다. 카메라 권한과 다른 앱의 사용 여부를 확인하세요.")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                while not self.stopped.is_set():
                    ok, frame = cap.read()
                    if not ok or frame is None or not frame.size:
                        raise RuntimeError("노트북 카메라 영상 수신 실패")
                    ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if not ok:
                        raise RuntimeError("JPEG 변환 실패")
                    self.publish(jpeg.tobytes())
                    self.stopped.wait(1 / self.fps)
            except (RuntimeError, cv2.error) as exc:
                logging.warning("%s; 2초 후 재시도", exc)
            finally:
                if cap is not None:
                    cap.release()
                with self.condition:
                    self.jpeg = None
            self.stopped.wait(2)


def create_app(camera, token):
    if not token:
        raise ValueError("접속 키가 필요합니다.")
    app = Flask(__name__)

    @app.before_request
    def authenticate():
        supplied = request.args.get("token", "")
        if not hmac.compare_digest(supplied.encode(), token.encode()):
            return jsonify(error="접속 키가 없거나 올바르지 않습니다."), 401

    @app.get("/health")
    def health():
        ready = camera.ready()
        return jsonify(camera_ready=ready), 200 if ready else 503

    @app.get("/")
    def index():
        from urllib.parse import urlencode
        return '<h1>Laptop Webcam</h1><img src="/video_feed?' + urlencode({"token": token}) + '" alt="Camera stream">'

    @app.get("/video_feed")
    def video_feed():
        if not camera.ready():
            return jsonify(error="카메라 준비 중입니다. 잠시 후 다시 접속하세요."), 503
        return Response(camera.frames(), content_type="multipart/x-mixed-replace; boundary=frame",
                        headers={"Cache-Control": "no-store"})

    return app


def main():
    parser = argparse.ArgumentParser(description="노트북 웹캠을 라즈베리 파이에 전송")
    parser.add_argument("--host", default="127.0.0.1", help="파이에서 접속하려면 노트북 Wi-Fi IPv4 지정")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--fps", type=int, default=15)
    args = parser.parse_args()
    if not 1 <= args.fps <= 60 or not 1 <= args.port <= 65535:
        parser.error("fps는 1~60, port는 1~65535로 지정하세요.")
    import cv2
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)  # Do not log URL keys.
    token = secrets.token_urlsafe(24)
    camera = Webcam(cv2, args.camera, args.fps)
    camera.start()
    print(f"접속 키: {token}", flush=True)
    print(f"영상 주소: http://{args.host}:{args.port}/video_feed?token={token}", flush=True)
    print("이 주소를 파이의 camera_url에 넣으세요. 종료 후 재시작하면 키가 바뀝니다.", flush=True)
    try:
        create_app(camera, token).run(host=args.host, port=args.port, threaded=True, debug=False, use_reloader=False)
    finally:
        camera.stop()


if __name__ == "__main__":
    main()
