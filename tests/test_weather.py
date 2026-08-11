import unittest
from pi_environment_panel.collectors.weather import WMO


class WeatherTests(unittest.TestCase):
    def test_wmo_mapping(self):
        self.assertEqual(WMO[0], "CLEAR")
        self.assertEqual(WMO[63], "RAIN")
        self.assertEqual(WMO[95], "THUNDERSTORM")


if __name__ == "__main__":
    unittest.main()
