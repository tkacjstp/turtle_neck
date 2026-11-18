"""Live notifications only; never replay historical measurement records."""
import threading
import time


class SensorState:
    def __init__(self, timeout=8, clock=time.monotonic):
        self.timeout, self.clock = timeout, clock
        self.lock = threading.Lock()
        self.status, self.updated = None, None

    def publish(self, status):
        with self.lock:
            self.status, self.updated = status, self.clock()

    def clear(self):
        with self.lock:
            self.status, self.updated = None, None

    def snapshot(self):
        with self.lock:
            age = None if self.updated is None else max(0, self.clock() - self.updated)
            online = age is not None and age < self.timeout
            return dict(online=online, status=self.status if online else None,
                        age_seconds=age, timeout_seconds=self.timeout)
