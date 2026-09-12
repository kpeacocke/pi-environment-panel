import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from pi_environment_panel.collectors.gps import parse_fix, collect, command
from pi_environment_panel.config import GPSConfig, load_config
import tempfile
from pathlib import Path

NOW = datetime(2026, 9, 12, 12, 0, 1, tzinfo=timezone.utc)
FIX = '+CGPSINFO: 3351.0000,S,15112.0000,E,120926,120000.0,0,0,0\r\nOK\r\n'


class GPSTests(unittest.TestCase):
    def test_southern_eastern_degrees_minutes(self):
        result = parse_fix(FIX, now=NOW)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.latitude, -33.85)
        self.assertAlmostEqual(result.longitude, 151.2)
        self.assertEqual(result.age_seconds, 1)

    def test_north_west(self):
        result = parse_fix(FIX.replace(',S,', ',N,').replace(',E,', ',W,'), now=NOW)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.latitude, 33.85)
        self.assertAlmostEqual(result.longitude, -151.2)

    def test_rejects_empty_malformed_and_stale(self):
        for response in ('+CGPSINFO: ,,,,,,,,\r\nOK', 'OK',
                         FIX.replace('3351.0000', '3399.0000'),
                         FIX.replace('15112.0000', '18112.0000'),
                         FIX.replace('120926', '110926'),
                         FIX.replace('120926', '130926'),
                         FIX.replace(',S,', ',X,'),
                         FIX.replace('3351.0000', 'nan')):
            with self.subTest(response=response):
                self.assertFalse(parse_fix(response, now=NOW).ok)

    def test_auto_enables_only_when_off(self):
        for state, count in (('0,1', 3), ('1,1', 2)):
            responses = ['+CGPS: '+state+'\r\nOK']
            if state.startswith('0'): responses.append('OK')
            responses.append(FIX)
            with patch('serial.Serial'), patch('pi_environment_panel.collectors.gps.command', side_effect=responses) as cmd:
                collect(GPSConfig(enabled=True))
                self.assertEqual(cmd.call_count, count)
                self.assertEqual(cmd.call_args.args[1], 'AT+CGPSINFO')

    def test_command_error_does_not_become_fix(self):
        with patch('serial.Serial'), patch('pi_environment_panel.collectors.gps.command', side_effect=RuntimeError('timed out')):
            self.assertFalse(collect(GPSConfig(enabled=True)).ok)

    def test_disabled_never_opens_uart(self):
        with patch('serial.Serial') as port:
            self.assertFalse(collect(GPSConfig()).ok)
            port.assert_not_called()

    def test_rejects_shared_uart(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'config.toml'
            p.write_text('[gps]\nenabled=true\nserial_device="/dev/ttyAMA10"\n')
            with self.assertRaisesRegex(ValueError, 'different UART'):
                load_config(p)
