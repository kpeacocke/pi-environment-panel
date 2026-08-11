import unittest
from pi_environment_panel.epaper import frame


class FrameTests(unittest.TestCase):
    def test_vendor_clear_example(self):
        expected = bytes.fromhex("A5 00 09 2E CC 33 C3 3C 82")
        self.assertEqual(frame(0x2E), expected)

    def test_vendor_line_example(self):
        payload = bytes.fromhex("00 0A 00 0A 00 FF 00 FF")
        expected = bytes.fromhex(
            "A5 00 11 22 00 0A 00 0A 00 FF 00 FF CC 33 C3 3C 96"
        )
        self.assertEqual(frame(0x22, payload), expected)

    def test_vendor_handshake_example(self):
        expected = bytes.fromhex("A5 00 09 00 CC 33 C3 3C AC")
        self.assertEqual(frame(0x00), expected)


if __name__ == "__main__":
    unittest.main()
