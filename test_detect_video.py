import ast
import errno
import logging
import struct
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import detect_video as camera


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.cv = Mock()
        self.cv.error = type("CVError", (Exception,), {})
        self.frame = types.SimpleNamespace(size=100, shape=(480, 640, 3))
        self.linux = patch.object(camera.sys, "platform", "linux")
        self.linux.start()
        self.addCleanup(self.linux.stop)
        for target, kwargs in [("device_name", {"return_value": "USB Camera"}),
                               ("capture_device", {"return_value": True})]:
            p = patch.object(camera, target, **kwargs)
            setattr(self, target, p.start())
            self.addCleanup(p.stop)
        p = patch.object(camera.time, "sleep")
        p.start()
        self.addCleanup(p.stop)

    def cap(self, frames=None, opened=True):
        cap = Mock()
        cap.isOpened.return_value = opened
        cap.read.side_effect = frames or [(True, self.frame)]
        return cap

    def test_skips_metadata_and_tries_later_camera(self):
        self.capture_device.side_effect = [False, True, True]
        bad, good = self.cap(opened=False), self.cap()
        self.cv.VideoCapture.side_effect = [bad, good]
        with patch.object(camera.glob, "glob", return_value=["/dev/video10", "/dev/video2", "/dev/video0"]):
            cap, path = camera.open_camera(self.cv)
        self.assertEqual(path, "/dev/video10")
        self.assertIs(cap, good)
        bad.release.assert_called_once()
        good.release.assert_not_called()

    def test_rejects_open_camera_without_frames(self):
        cap = self.cap([(False, None)] * 10)
        self.cv.VideoCapture.return_value = cap
        with self.assertRaises(RuntimeError):
            camera.open_camera(self.cv, "/dev/video2")
        cap.release.assert_called_once()

    def test_empty_frame_then_warmup_success(self):
        cap = self.cap([(True, types.SimpleNamespace(size=0)), (True, self.frame)])
        self.cv.VideoCapture.return_value = cap
        self.assertIs(camera.open_camera(self.cv, 2)[0], cap)
        self.cv.VideoCapture.assert_called_once_with("/dev/video2", self.cv.CAP_V4L2)

    def test_opencv_error_releases_and_continues(self):
        bad, good = self.cap([self.cv.error("busy")]), self.cap()
        self.cv.VideoCapture.side_effect = [bad, good]
        with patch.object(camera.glob, "glob", return_value=["/dev/video0", "/dev/video1"]):
            self.assertIs(camera.open_camera(self.cv)[0], good)
        bad.release.assert_called_once()

    def test_missing_devices(self):
        with patch.object(camera.glob, "glob", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "/dev/video"):
                camera.open_camera(self.cv)

    def test_stop_releases_camera_during_probe(self):
        cap = self.cap()
        self.cv.VideoCapture.return_value = cap
        with self.assertRaises(RuntimeError):
            camera.open_camera(self.cv, "/dev/video0", should_run=Mock(side_effect=[True, False]))
        cap.release.assert_called_once()

    def test_windows_keeps_default_camera(self):
        self.cv.VideoCapture.return_value = self.cap()
        with patch.object(camera.sys, "platform", "win32"):
            camera.open_camera(self.cv)
        self.cv.VideoCapture.assert_called_once_with(0)
        self.capture_device.assert_not_called()


class CapabilityTests(unittest.TestCase):
    def query(self, caps, device_caps=0, error=None):
        def ioctl(fd, command, buffer, mutate):
            self.assertEqual(command, 0x80685600)
            self.assertEqual(len(buffer), 104)
            if error:
                raise error
            struct.pack_into("=II", buffer, 84, caps, device_caps)
        fake = types.SimpleNamespace(ioctl=ioctl)
        with patch.dict(sys.modules, {"fcntl": fake}), \
                patch.object(camera.os, "O_NONBLOCK", 2048, create=True), \
                patch.object(camera.os, "open", return_value=7), \
                patch.object(camera.os, "close") as close:
            result = camera.capture_device("/dev/video0")
            close.assert_called_once_with(7)
            return result

    def test_capture_and_multiplanar(self):
        self.assertTrue(self.query(1))
        self.assertTrue(self.query(0x1000))

    def test_device_caps_overrides_global_caps(self):
        self.assertFalse(self.query(0x80000001, 0x00800000))
        self.assertTrue(self.query(0x80000000, 1))

    def test_codec_and_metadata_excluded(self):
        self.assertFalse(self.query(1 | 0x8000))
        self.assertFalse(self.query(0x00800000))

    def test_permission_error_is_recoverable(self):
        self.assertFalse(self.query(1, error=PermissionError(errno.EACCES, "denied")))


class IntegrationTests(unittest.TestCase):
    def test_posture_retries_and_passes_device_configuration(self):
        # Load only the camera wrapper, avoiding posture logging/ML side effects.
        source = Path(__file__).with_name("posture.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "open_camera")
        namespace = {"running": True, "log": logging.getLogger("test"), "time": Mock()}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "posture.py", "exec"), namespace)
        cv = types.SimpleNamespace(error=type("CVError", (Exception,), {}))
        cap = Mock()
        with patch.object(camera, "open_camera", side_effect=[RuntimeError("unplugged"), (cap, "/dev/video2")]) as find:
            self.assertIs(namespace["open_camera"](cv, {"camera_device": "/dev/video2"}), cap)
        self.assertEqual(find.call_count, 2)
        self.assertEqual(find.call_args.kwargs["device"], "/dev/video2")
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        calls = [n for n in ast.walk(run) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == "open_camera"]
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(len(n.args) == 2 and n.args[1].id == "cfg" for n in calls))


if __name__ == "__main__":
    unittest.main()
