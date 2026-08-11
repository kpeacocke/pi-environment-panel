import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pi_environment_panel.collectors import ups


class FakeSMBus:
    last_instance = None

    def __init__(self, busno):
        self.busno = busno
        self.closed = False
        FakeSMBus.last_instance = self
        values = {
            0x10: 0x50, 0x11: 0x14,  # 5200 mV VBUS
            0x20: 0xA8, 0x21: 0x3F,  # 16296 mV battery
            0x22: 0xDC, 0x23: 0x00,  # +220 mA
            0x24: 87,   0x25: 0x00,  # 87 %
            0x28: 134,  0x29: 0x00,  # 134 min
        }
        self.values = values

    def read_byte_data(self, address, reg):
        self.assert_address = address
        return self.values[reg]

    def close(self):
        self.closed = True


class UPSCollectorTests(unittest.TestCase):
    def test_collect_without_context_manager_support(self):
        fake_mod = types.SimpleNamespace(SMBus=FakeSMBus)
        cfg = SimpleNamespace(enabled=True, bus=1, address=0x2D)

        with patch.dict(sys.modules, {"smbus": fake_mod}):
            result = ups.collect(cfg)

        self.assertTrue(result.ok, result.error)
        self.assertTrue(result.mains)
        self.assertAlmostEqual(result.vbus_voltage_v, 5.2, places=2)
        self.assertAlmostEqual(result.battery_voltage_v, 16.296, places=3)
        self.assertEqual(result.battery_current_ma, 220)
        self.assertEqual(result.battery_pct, 87.0)
        self.assertEqual(result.remaining_minutes, 134)
        self.assertTrue(FakeSMBus.last_instance.closed)


if __name__ == "__main__":
    unittest.main()
