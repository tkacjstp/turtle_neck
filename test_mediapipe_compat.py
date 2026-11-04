import types
import unittest
from unittest.mock import patch

from mediapipe_compat import load_mediapipe


class CompatibilityTests(unittest.TestCase):
    def test_legacy_api_supported(self):
        legacy = types.SimpleNamespace(__version__="0.10.18", solutions=types.SimpleNamespace(
            pose=types.SimpleNamespace(Pose=lambda: None),
            face_mesh=types.SimpleNamespace(FaceMesh=lambda: None)))
        with patch("mediapipe_compat.importlib.import_module", return_value=legacy):
            self.assertIs(load_mediapipe(), legacy)

    def test_new_api_gives_install_instructions(self):
        with patch("mediapipe_compat.importlib.import_module", return_value=types.SimpleNamespace(__version__="0.10.31")):
            with self.assertRaisesRegex(RuntimeError, "0.10.18"):
                load_mediapipe()

    def test_missing_package(self):
        with patch("mediapipe_compat.importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaisesRegex(RuntimeError, "requirements-pi.txt"):
                load_mediapipe()

    def test_shadowing_module(self):
        with patch("mediapipe_compat.importlib.import_module", return_value=types.SimpleNamespace(__file__="/home/pi/mediapipe.py")):
            with self.assertRaisesRegex(RuntimeError, "이름 충돌"):
                load_mediapipe()


if __name__ == "__main__":
    unittest.main()
