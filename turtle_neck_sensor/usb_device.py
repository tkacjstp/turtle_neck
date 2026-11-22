"""Forward live posture status to an Arduino over USB serial."""
import argparse
import logging
import signal
import threading
from pathlib import Path

from rpi_device import StatusPoller, read_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--config', default=str(Path(__file__).with_name('sensor_config.json')))
    args = parser.parse_args()
    import serial

    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    poller = StatusPoller(read_config(args.config), stop)
    commands = {'정상': b'N', '경고': b'W', '위험': b'D'}
    poller.thread.start()
    try:
        while not stop.is_set():
            try:
                with serial.Serial(args.port, 9600, write_timeout=.5) as board:
                    # Opening the Uno serial port may restart its sketch.
                    stop.wait(2)
                    try:
                        while not stop.is_set():
                            board.write(commands.get(poller.current(), b'O'))
                            stop.wait(.25)
                    finally:
                        board.write(b'O')
            except serial.SerialException as exc:
                logging.warning('USB serial: %s', exc)
                stop.wait(2)
    finally:
        stop.set()
        poller.thread.join(timeout=2)


if __name__ == '__main__':
    main()
