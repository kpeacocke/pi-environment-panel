import unittest
from pi_environment_panel.config import PanelConfig

class ConfigTests(unittest.TestCase):
    def test_default_uart_is_pi5_debug_uart(self):
        self.assertEqual(PanelConfig().serial_device, "/dev/ttyAMA10")

if __name__ == "__main__":
    unittest.main()
