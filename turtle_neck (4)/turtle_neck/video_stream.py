"""Latest-frame-only MJPEG transport. This module never opens the camera."""
import logging
import threading
import time
import urllib.request
from urllib.parse import urlsplit


class FramePublisher:
    def __init__(self, cfg):
        port = urlsplit(cfg['server_url']).port or 5050
        self.url = f'http://127.0.0.1:{port}/api/video_frame'
        self.interval = 1 / max(1, min(30, float(cfg.get('video_fps', 10))))
        self.quality = max(30, min(95, int(cfg.get('video_jpeg_quality', 75))))
        self.condition = threading.Condition()
        self.frame = None
        self.closed = False
        self.next_frame = 0
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def submit(self, frame):
        now = time.monotonic()
        if now < self.next_frame:
            return
        self.next_frame = now + self.interval
        with self.condition:
            self.frame = frame.copy()
            self.condition.notify()

    def _run(self):
        import cv2
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        last_warning = -float('inf')
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.closed or self.frame is not None)
                if self.closed:
                    return
                frame, self.frame = self.frame, None
            try:
                ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                if not ok:
                    continue
                req = urllib.request.Request(self.url, data=jpeg.tobytes(),
                                             headers={'Content-Type': 'image/jpeg'}, method='POST')
                with opener.open(req, timeout=1) as response:
                    response.read()
            except Exception as exc:
                if time.monotonic() - last_warning > 10:
                    logging.getLogger(__name__).warning('Web video unavailable: %s', exc)
                    last_warning = time.monotonic()
                # No backlog: failed frames are discarded, measurements use their own DB queue.
                time.sleep(0.2)

    def close(self):
        with self.condition:
            self.closed = True
            self.frame = None
            self.condition.notify_all()
        self.thread.join(timeout=2)


class FrameStore:
    def __init__(self):
        self.condition = threading.Condition()
        self.frame = None
        self.sequence = 0
        self.updated = -float('inf')

    def publish(self, jpeg):
        with self.condition:
            self.frame = jpeg
            self.sequence += 1
            self.updated = time.monotonic()
            self.condition.notify_all()

    def online(self):
        with self.condition:
            return self.frame is not None and time.monotonic() - self.updated < 3

    def stream(self):
        sequence = -1
        while True:
            with self.condition:
                ready = self.condition.wait_for(
                    lambda: self.sequence != sequence and self.frame is not None
                    and time.monotonic() - self.updated < 3, timeout=1)
                if not ready:
                    continue
                sequence, jpeg = self.sequence, self.frame
            yield (b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '
                   + str(len(jpeg)).encode('ascii') + b'\r\n\r\n' + jpeg + b'\r\n')
