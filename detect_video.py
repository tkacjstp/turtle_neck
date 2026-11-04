"""Find a working V4L2 camera on Raspberry Pi (USB/V4L2 devices).

Run: python3 detect_video.py
Select explicitly: python3 detect_video.py --device /dev/video2
Dependency: sudo apt install python3-opencv
CSI cameras requiring Picamera2/libcamera are outside this script's scope.
"""

import argparse
import errno
import glob
import os
import struct
import sys
import time
from pathlib import Path


def capture_device(path):
    """Ignore codec/output/metadata-only nodes using VIDIOC_QUERYCAP."""
    import fcntl
    buffer = bytearray(104)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            fcntl.ioctl(fd, 0x80685600, buffer, True)
        finally:
            os.close(fd)
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM):
            print(f"[권한 없음] {path}: video 그룹 권한을 확인하세요.")
        else:
            print(f"[확인 실패] {path}: {exc}")
        return False

    capabilities, device_caps = struct.unpack_from("=II", buffer, 84)
    if capabilities & 0x80000000:  # V4L2_CAP_DEVICE_CAPS
        capabilities = device_caps
    capture = capabilities & (0x00000001 | 0x00001000)
    memory_to_memory = capabilities & (0x00004000 | 0x00008000)
    return bool(capture and not memory_to_memory)


def device_name(path):
    try:
        return (Path("/sys/class/video4linux") / Path(path).name / "name").read_text().strip()
    except OSError:
        return "이름 확인 불가"


def open_camera(cv2, device=None, width=640, height=480, should_run=lambda: True,
                stream_url=None):
    """Return (opened_capture, device_path); caller must release the capture.

    Each candidate must supply a nonempty frame. A driver can block in read();
    the attempt count below is not a hard timeout for a stalled driver.
    """
    if stream_url:
        from urllib.parse import urlsplit
        parsed = urlsplit(stream_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise RuntimeError("camera_url은 http://노트북IP:8080/video_feed 형식이어야 합니다.")
        cap = None
        keep = False
        try:
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG, [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000,
            ])
            if not cap.isOpened():
                raise RuntimeError("노트북 영상 연결 실패: 송출 프로그램·주소·방화벽·네트워크를 확인하세요. FFmpeg 지원 OpenCV가 필요합니다.")
            for _ in range(10):
                if not should_run():
                    raise RuntimeError("카메라 검색 종료")
                ok, frame = cap.read()
                if ok and frame is not None and frame.size:
                    keep = True
                    print("[연결 성공] 노트북 네트워크 카메라")
                    return cap, stream_url
            raise RuntimeError("노트북에서 영상 프레임을 받지 못했습니다.")
        finally:
            if cap is not None and not keep:
                cap.release()

    linux = sys.platform.startswith("linux")
    if device is not None:
        devices = [device]
    elif linux:
        devices = sorted(
            (path for path in glob.glob("/dev/video[0-9]*")
             if Path(path).name[5:].isdigit()),
            key=lambda path: int(Path(path).name[5:]),
        )
    else:
        devices = [0]
    if not devices:
        raise RuntimeError("/dev/video* 장치가 없습니다. 카메라 연결을 확인하세요.")

    for path in devices:
        if not should_run():
            raise RuntimeError("카메라 검색 종료")
        if linux and isinstance(path, int):
            path = f"/dev/video{path}"
        name = device_name(path) if linux else f"Camera {path}"
        print(f"[장치 확인] {path}: {name}")
        if linux and not capture_device(path):
            continue
        cap = None
        keep = False
        try:
            cap = cv2.VideoCapture(path, cv2.CAP_V4L2) if linux else cv2.VideoCapture(path)
            if not cap.isOpened():
                print(f"[열기 실패] {path}")
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            for _ in range(10):
                if not should_run():
                    raise RuntimeError("카메라 검색 종료")
                ok, frame = cap.read()
                if ok and frame is not None and frame.size:
                    actual_height, actual_width = frame.shape[:2]
                    print(f"[연결 성공] {path}: {name} ({actual_width}x{actual_height})")
                    keep = True
                    return cap, path
                time.sleep(0.1)
            print(f"[영상 수신 실패] {path}")
        except cv2.error as exc:
            print(f"[카메라 오류] {path}: {exc}")
        finally:
            if cap is not None and not keep:
                cap.release()

    raise RuntimeError("영상을 읽을 수 있는 장치가 없습니다. 권한·연결·다른 앱의 카메라 사용 여부를 확인하세요.")


def main():
    parser = argparse.ArgumentParser(description="라즈베리 파이 V4L2 카메라 검색 및 영상 수신 확인")
    parser.add_argument("--device", help="장치를 직접 지정 (예: /dev/video2)")
    parser.add_argument("--url", help="노트북 영상 주소 (예: http://192.168.0.10:8080/video_feed)")
    args = parser.parse_args()
    try:
        import cv2
    except ImportError:
        print("OpenCV가 필요합니다: sudo apt install python3-opencv", file=sys.stderr)
        return 1
    try:
        cap, _ = open_camera(cv2, device=args.device, stream_url=args.url)
        cap.release()
        return 0
    except (OSError, RuntimeError, cv2.error) as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
