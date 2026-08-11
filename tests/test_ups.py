import unittest
from pi_environment_panel.collectors.ups import _u16, _s16


class Bus:
    def __init__(self, values):
        self.values = values

    def read_byte_data(self, address, reg):
        return self.values[reg]


class UPSTests(unittest.TestCase):
    def test_little_endian_u16(self):
        bus = Bus({0x20: 0x34, 0x21: 0x12})
        self.assertEqual(_u16(bus, 0x2D, 0x20), 0x1234)

    def test_signed_current(self):
        bus = Bus({0x22: 0x18, 0x23: 0xFC})  # -1000
        self.assertEqual(_s16(bus, 0x2D, 0x22), -1000)


if __name__ == "__main__":
    unittest.main()
