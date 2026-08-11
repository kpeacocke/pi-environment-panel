import unittest
from unittest.mock import MagicMock, patch

from pi_environment_panel.epaper import WaveshareUART


class FakeSerial:
    def __init__(self, responses):
        self.responses = list(responses)
        self.current = b""
        self.writes = []

    def reset_input_buffer(self):
        self.current = b""

    def write(self, data):
        self.writes.append(bytes(data))
        self.current = self.responses.pop(0) if self.responses else b""
        return len(data)

    def flush(self):
        pass

    @property
    def in_waiting(self):
        return len(self.current)

    def read(self, n):
        data = self.current[:n]
        self.current = self.current[n:]
        return data


class HandshakeTests(unittest.TestCase):
    def test_already_awake_panel_does_not_touch_wake(self):
        panel = WaveshareUART()
        panel._serial = FakeSerial([b"OK"])
        panel.wake = MagicMock()

        self.assertTrue(panel.handshake())
        panel.wake.assert_not_called()
        self.assertEqual(len(panel._serial.writes), 1)

    def test_wake_is_only_fallback_after_failed_first_attempt(self):
        panel = WaveshareUART()
        panel._serial = FakeSerial([b"", b"OK"])
        panel.wake = MagicMock(return_value=(True, "GPIO4 low->high"))

        with patch("pi_environment_panel.epaper.time.sleep", return_value=None):
            self.assertTrue(panel.handshake())

        panel.wake.assert_called_once()
        self.assertEqual(len(panel._serial.writes), 2)


if __name__ == "__main__":
    unittest.main()
