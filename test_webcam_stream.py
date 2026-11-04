import threading
import time
import types
import unittest
import tempfile
import urllib.request
import urllib.error
from unittest.mock import Mock, patch

import cv2
import numpy as np
from werkzeug.serving import make_server

import detect_video
from webcam_stream import Webcam, create_app


class StreamTests(unittest.TestCase):
    def test_missing_or_wrong_key_rejected(self):
        client = create_app(Webcam(cv2), 'test-key').test_client()
        self.assertEqual(client.get('/video_feed').status_code, 401)
        self.assertEqual(client.get('/video_feed?token=wrong').status_code, 401)
        self.assertEqual(client.get('/health').status_code, 401)

    def test_not_ready_returns_503(self):
        camera = Webcam(cv2)
        client = create_app(camera, 'test-key').test_client()
        self.assertEqual(client.get('/health?token=test-key').status_code, 503)
        self.assertEqual(client.get('/video_feed?token=test-key').status_code, 503)

    def test_multipart_format_and_shutdown(self):
        camera = Webcam(cv2)
        camera.publish(b'JPEG')
        frames = camera.frames()
        self.assertEqual(next(frames), b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: 4\r\n\r\nJPEG\r\n')
        self.assertEqual(create_app(camera, 'test-key').test_client().get('/health?token=test-key').status_code, 200)
        camera.stop()
        self.assertRaises(StopIteration, next, frames)

    def test_stale_frame_not_reported_ready(self):
        camera = Webcam(cv2)
        camera.publish(b'JPEG')
        camera.updated -= 6
        self.assertFalse(camera.ready())
        self.assertRaises(StopIteration, next, camera.frames())

    def test_invalid_url_rejected(self):
        with self.assertRaises(RuntimeError):
            detect_video.open_camera(cv2, stream_url='file:///tmp/video')

    def test_failed_network_frame_releases_capture(self):
        fake_cv = Mock()
        cap = fake_cv.VideoCapture.return_value
        cap.read.return_value = (False, None)
        with self.assertRaises(RuntimeError):
            detect_video.open_camera(fake_cv, stream_url='http://127.0.0.1:8080/video_feed?token=test-key')
        cap.release.assert_called_once()
        self.assertEqual(fake_cv.VideoCapture.call_args.args[1], fake_cv.CAP_FFMPEG)

    def test_sender_releases_on_disconnect(self):
        fake_cv = Mock()
        fake_cv.error = type('CVError', (Exception,), {})
        cap = fake_cv.VideoCapture.return_value
        camera = Webcam(fake_cv)
        def read():
            camera.stopped.set()
            return False, None
        cap.read.side_effect = read
        camera._capture()
        cap.release.assert_called_once()
        self.assertIsNone(camera.jpeg)

    def test_http_mjpeg_decoded_by_actual_opencv(self):
        camera = Webcam(cv2)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 1] = 180
        ok, encoded = cv2.imencode('.jpg', frame)
        self.assertTrue(ok)
        jpeg = encoded.tobytes()
        camera.publish(jpeg)
        server = make_server('127.0.0.1', 0, create_app(camera, 'test-key'), threaded=True)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        stop = threading.Event()
        def publish():
            while not stop.wait(0.02):
                camera.publish(jpeg)
        publisher = threading.Thread(target=publish, daemon=True)
        server_thread.start()
        publisher.start()
        cap = None
        try:
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/health?token=test-key', timeout=3).close()
            except urllib.error.URLError as exc:
                if isinstance(exc.reason, PermissionError):
                    self.skipTest('Environment blocks loopback network access')
                raise
            url = f'http://127.0.0.1:{server.server_port}/video_feed?token=test-key'
            cap, actual = detect_video.open_camera(cv2, stream_url=url)
            self.assertEqual(actual, url)
            ok, received = cap.read()
            self.assertTrue(ok)
            self.assertEqual(received.shape, (480, 640, 3))
            self.assertGreater(received[:, :, 1].mean(), 150)
        finally:
            if cap is not None:
                cap.release()
            stop.set()
            camera.stop()
            server.shutdown()
            server.server_close()
            server_thread.join(3)
            publisher.join(3)

    def test_flask_mjpeg_response_decodes_as_actual_video(self):
        camera = Webcam(cv2)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 1] = 180
        ok, jpeg = cv2.imencode('.jpg', frame)
        self.assertTrue(ok)
        camera.publish(jpeg.tobytes())
        response = create_app(camera, 'test-key').test_client().get('/video_feed?token=test-key', buffered=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn('multipart/x-mixed-replace', response.content_type)
        cap = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                from pathlib import Path
                path = Path(directory) / 'stream.mjpg'
                chunks = []
                stream = iter(response.response)
                for _ in range(20):
                    camera.publish(jpeg.tobytes())
                    chunks.append(next(stream))
                path.write_bytes(b''.join(chunks))
                cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
                try:
                    ok, actual = cap.read()
                    self.assertTrue(ok)
                    self.assertEqual(actual.shape, (480, 640, 3))
                    self.assertGreater(actual[:, :, 1].mean(), 150)
                finally:
                    cap.release()
        finally:
            response.close()
            camera.stop()


if __name__ == '__main__':
    unittest.main()
