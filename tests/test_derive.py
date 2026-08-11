import unittest
from types import SimpleNamespace
from pi_environment_panel.derive import dew_point_c, comfort_label, pressure_label


class DeriveTests(unittest.TestCase):
    def setUp(self):
        self.t = SimpleNamespace(
            room_cold_c=18.0,
            room_warm_c=27.0,
            humidity_dry_pct=30.0,
            humidity_humid_pct=65.0,
        )

    def test_dew_point(self):
        self.assertAlmostEqual(dew_point_c(23.8, 41.0), 9.8, delta=0.5)

    def test_comfort(self):
        self.assertEqual(comfort_label(23.8, 41.0, self.t), "COMFORTABLE")

    def test_pressure(self):
        self.assertEqual(pressure_label(2.2, 1.5), "PRESSURE RISING")
        self.assertEqual(pressure_label(-2.2, 1.5), "PRESSURE FALLING")
        self.assertEqual(pressure_label(0.2, 1.5), "PRESSURE STEADY")


if __name__ == "__main__":
    unittest.main()
