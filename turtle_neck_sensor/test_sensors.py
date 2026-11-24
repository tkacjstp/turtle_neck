import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from sensor_state import SensorState
from rpi_device import Outputs, output_pattern, StatusPoller


class SensorTests(unittest.TestCase):
    def test_timeout_and_reset(self):
        now = [10]
        state = SensorState(clock=lambda: now[0])
        self.assertFalse(state.snapshot()['online'])
        state.publish('위험')
        self.assertEqual(state.snapshot()['status'], '위험')
        now[0] += 8
        self.assertIsNone(state.snapshot()['status'])
        state.publish('경고')
        state.clear()
        self.assertFalse(state.snapshot()['online'])

    def test_patterns_and_network_loss(self):
        self.assertEqual(output_pattern('정상', 0), ((0, 0, 1), False))
        self.assertEqual(output_pattern('경고', .1), ((1, 0, 0), False))
        self.assertEqual(output_pattern('경고', .6), ((0, 0, 0), False))
        self.assertEqual(output_pattern('위험', .1), ((1, 1, 0), True))
        self.assertEqual(output_pattern('위험', 5.7), ((1, 1, 0), True))
        self.assertEqual(output_pattern(None, 0), ((0, 0, 0), False))
        poller = StatusPoller({}, MagicMock())
        poller.status, poller.received = '위험', 10
        with patch('rpi_device.time.monotonic', return_value=13):
            self.assertIsNone(poller.current())

    def test_active_and_passive_outputs(self):
        import types
        fake = types.SimpleNamespace(RGBLED=MagicMock(), Buzzer=MagicMock(), PWMOutputDevice=MagicMock())
        for kind in ('active', 'passive'):
            with patch.dict('sys.modules', {'gpiozero': fake}):
                out = Outputs(dict(rgb_pins=[10, 9, 11], buzzer_pin=18, buzzer_type=kind))
                out.set((1, 0, 0), True)
                self.assertEqual(fake.RGBLED.call_args.args, (10, 9, 11))
                self.assertEqual(fake.RGBLED.return_value.value, (1, 0, 0))
                if kind == 'passive':
                    fake.PWMOutputDevice.assert_called_once_with(
                        18, active_high=True, initial_value=0, frequency=880)
                    buzzer = fake.PWMOutputDevice.return_value
                    self.assertEqual(buzzer.value, 0.5)
                else:
                    buzzer = fake.Buzzer.return_value
                    buzzer.on.assert_called_once()
                out.set((0, 0, 0), False)
                if kind == 'passive':
                    self.assertEqual(buzzer.value, 0)
                else:
                    buzzer.off.assert_called_once()
                out.close()
                buzzer.close.assert_called()

    def test_live_api_ignores_record_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            connect = sqlite3.connect
            db = str(Path(directory) / 'test.db')
            spec = importlib.util.spec_from_file_location('sensor_test_app', Path(__file__).with_name('app.py'))
            module = importlib.util.module_from_spec(spec)
            with patch('sqlite3.connect', side_effect=lambda *a, **k: connect(db, **k)):
                spec.loader.exec_module(module)
            module.DB_FILE = db
            client = module.app.test_client()
            self.assertFalse(client.get('/api/sensor_status').json['online'])
            self.assertEqual(client.post('/api/record', json={'status': '위험'}).status_code, 200)
            self.assertFalse(client.get('/api/sensor_status').json['online'])
            self.assertEqual(client.post('/api/status', json={'status': '경고'}).status_code, 200)
            self.assertEqual(client.get('/api/sensor_status').json['status'], '경고')
            self.assertEqual(client.post('/api/status', json={'status': 'bad'}).status_code, 400)
            self.assertEqual(client.get('/api/sensor_status').json['status'], '경고')


if __name__ == '__main__':
    unittest.main()
