"""Camera-free checks; all measurement writes go to a temporary database."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from video_stream import FramePublisher, FrameStore


class VideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        original_connect = sqlite3.connect
        db = str(Path(cls.temp.name) / 'test.db')
        spec = importlib.util.spec_from_file_location('web_video_app', Path(__file__).with_name('app.py'))
        cls.module = importlib.util.module_from_spec(spec)
        with patch('sqlite3.connect', side_effect=lambda *a, **k: original_connect(db, **k)):
            spec.loader.exec_module(cls.module)
        cls.module.DB_FILE = db

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_upload_stream_and_measurement(self):
        import cv2
        import numpy as np
        client = self.module.app.test_client()
        done = threading.Event()

        class Reply:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b''

        class LocalServer:
            def open(self, req, timeout):
                response = client.post('/api/video_frame', data=req.data, content_type='image/jpeg')
                if response.status_code != 204:
                    raise RuntimeError(response.status)
                done.set()
                return Reply()

        with patch('urllib.request.build_opener', return_value=LocalServer()):
            publisher = FramePublisher({'server_url': 'http://127.0.0.1:5050/api/record'})
            try:
                publisher.submit(np.full((48, 64, 3), 128, dtype=np.uint8))
                self.assertTrue(done.wait(5))
            finally:
                publisher.close()
        self.assertTrue(client.get('/api/video_status').json['online'])
        response = client.get('/video_feed', buffered=False)
        packet = next(iter(response.response))
        self.assertIn(b'Content-Type: image/jpeg', packet)
        jpeg = packet.split(b'\r\n\r\n', 1)[1][:-2]
        self.assertEqual(cv2.imdecode(np.frombuffer(jpeg, np.uint8), 1).shape, (48, 64, 3))
        response.close()
        self.assertEqual(client.post('/api/record', json={'status': '����', 'worse_pct': 12}).status_code, 200)
        self.assertEqual(client.get('/api/results').json[0]['worse_pct'], 12)
        self.assertEqual(client.post('/api/status', json={'status': '����'}).status_code, 200)
        page = client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'camera-feed', page.data)
        self.module.video.updated = time.monotonic() - 4
        self.assertFalse(client.get('/api/video_status').json['online'])

    def test_reject_invalid_or_remote_frames(self):
        client = self.module.app.test_client()
        self.assertEqual(client.post('/api/video_frame', data=b'bad', content_type='image/jpeg').status_code, 400)
        self.assertEqual(client.post('/api/video_frame', data=b'bad', content_type='text/plain').status_code, 415)
        self.assertEqual(client.post('/api/video_frame', data=b'x'*2_000_001, content_type='image/jpeg').status_code, 413)
        self.assertEqual(client.post('/api/video_frame', data=b'bad', content_type='image/jpeg',
                                     environ_base={'REMOTE_ADDR': '192.168.1.8'}).status_code, 403)

    def test_store_discards_backlog(self):
        store = FrameStore()
        store.publish(b'old')
        store.publish(b'new')
        stream = store.stream()
        self.assertIn(b'new', next(stream))
        stream.close()


if __name__ == '__main__':
    unittest.main()
