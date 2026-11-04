"""Validate the legacy MediaPipe API before opening the camera."""

import importlib


def load_mediapipe():
    try:
        mp = importlib.import_module("mediapipe")
    except ImportError as exc:
        raise RuntimeError(
            "MediaPipe 로드 실패. 현재 Python 환경에서 "
            "python3 -m pip install -r requirements-pi.txt 를 실행하세요. "
            f"원인: {exc}"
        ) from exc
    solutions = getattr(mp, "solutions", None)
    if not (callable(getattr(getattr(solutions, "pose", None), "Pose", None))
            and callable(getattr(getattr(solutions, "face_mesh", None), "FaceMesh", None))):
        raise RuntimeError(
            f"현재 MediaPipe {getattr(mp, '__version__', '버전 확인 불가')}에는 "
            "이 코드에 필요한 mp.solutions.pose / face_mesh가 없습니다. "
            "이 프로젝트는 낮은 버전 MediaPipe 0.10.18 기준입니다. "
            "같은 Python 환경에서 python3 -m pip install -r requirements-pi.txt 를 실행하세요. "
            f"불러온 모듈 위치: {getattr(mp, '__file__', '확인 불가')}. "
            "프로젝트에 mediapipe.py 또는 mediapipe 폴더가 있다면 이름 충돌도 확인하세요."
        )
    return mp
