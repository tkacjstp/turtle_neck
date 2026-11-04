"""Raspberry Pi USB diagnostics. Run: python3 check_usb.py [--watch]

Read-only; uses only Python's standard library. Does not configure USB gadget
mode or prove that an enumerated device/host is a particular computer.
"""

import argparse
import json
import sys
import time
from pathlib import Path


def read(path, default="확인 불가"):
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return default


def children(path):
    try:
        return sorted(path.iterdir())
    except OSError:
        return []


def inspect_usb(root=Path("/sys")):
    devices = []
    for node in children(root / "bus/usb/devices"):
        # Skip root hubs and interface entries: show enumerated devices only.
        if node.name.startswith("usb") or ":" in node.name:
            continue
        vendor, product = read(node / "idVendor", ""), read(node / "idProduct", "")
        if vendor and product:
            devices.append({"port": node.name, "id": f"{vendor}:{product}",
                            "manufacturer": read(node / "manufacturer"),
                            "product": read(node / "product")})
    controllers = [{"name": node.name, "state": read(node / "state")}
                   for node in children(root / "class/udc")]
    networks = []
    for node in children(root / "class/net"):
        try:
            device = (node / "device").resolve()
            usb_device = any((parent / "idVendor").exists()
                             for parent in [device, *device.parents])
        except OSError:
            usb_device = False
        # Gadget network interfaces can be virtual and have no USB ancestor.
        if usb_device or node.name.startswith("usb"):
            networks.append({"name": node.name, "state": read(node / "operstate"),
                             "carrier": read(node / "carrier")})
    return {"usb_devices": devices, "gadget_controllers": controllers,
            "usb_networks": networks}


def display(report):
    print("\n=== 라즈베리 파이 USB 연결 확인 ===", flush=True)
    print("[USB 호스트에서 인식한 장치]")
    for device in report["usb_devices"]:
        print(f"  {device['port']}  {device['id']}  {device['manufacturer']} / {device['product']}")
    if not report["usb_devices"]:
        print("  인식된 외부 장치 없음 (또는 목록 접근 불가)")
    print("[PC가 라즈베리 파이를 USB 장치로 인식하는 gadget 상태]")
    for controller in report["gadget_controllers"]:
        state = controller["state"]
        meaning = {"configured": "호스트가 USB 구성을 완료함",
                   "not attached": "호스트 연결 없음",
                   "not-attached": "호스트 연결 없음",
                   "suspended": "USB 일시 정지 상태; 현재 통신 여부는 확인 필요"}.get(
                       state, "USB 구성 완료 여부를 확인할 수 없음")
        print(f"  {controller['name']}: {state} — {meaning}")
    if not report["gadget_controllers"]:
        print("  USB 장치 컨트롤러 없음 (또는 접근 불가). 이 방식으로 PC 연결을 확인할 수 없습니다.")
    print("[USB 관련 네트워크 인터페이스]")
    for network in report["usb_networks"]:
        print(f"  {network['name']}: state={network['state']}, carrier={network['carrier']}")
    if not report["usb_networks"]:
        print("  없음 (또는 접근 불가)")
    print("※ USB 장치나 링크 인식만으로 상대가 특정 PC인지, IP 통신이 되는지 확정하지 않습니다.")
    print("※ 케이블 연결만으로 USB 데이터 연결이 성립하지는 않습니다. 포트·케이블·gadget 설정을 확인하세요.", flush=True)


def main():
    parser = argparse.ArgumentParser(description="USB 장치 및 USB gadget 연결 상태 확인")
    parser.add_argument("--watch", action="store_true", help="2초 간격으로 확인하고 변경 시 출력")
    args = parser.parse_args()
    if not sys.platform.startswith("linux"):
        print("이 코드는 라즈베리 파이의 Linux에서 실행하세요.", file=sys.stderr)
        return 1
    previous = None
    try:
        while True:
            report = inspect_usb()
            current = json.dumps(report, sort_keys=True)
            if current != previous:
                display(report)
                previous = current
            if not args.watch:
                return 0
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n확인 종료")
        return 0


if __name__ == "__main__":
    sys.exit(main())
