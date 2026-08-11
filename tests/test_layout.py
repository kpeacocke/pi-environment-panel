import unittest
from types import SimpleNamespace
from datetime import datetime
from pi_environment_panel.layout import build_plan
from pi_environment_panel.models import (
    DashboardState, SenseReading, UPSReading, SystemReading,
    HealthReading, WeatherReading, Trends
)


class LayoutTests(unittest.TestCase):
    def test_all_ops_fit_panel(self):
        cfg = SimpleNamespace(
            panel=SimpleNamespace(title="KP PI"),
            thresholds=SimpleNamespace(pressure_trend_hpa_6h=1.5),
        )
        state = DashboardState(
            timestamp=datetime.now().astimezone().isoformat(),
            sense=SenseReading(True, 23.8, 41, 1016.1, 9.8),
            ups=UPSReading(True, True, 5.1, 16.3, 300, 87, 134),
            system=SystemReading(43, 8, 21, 58, 198, 370000, "192.168.1.29"),
            health=HealthReading(True, True, True, True, True, True, True, True),
            weather=WeatherReading(True, 19, 54, 1015, 12, "PARTLY CLOUDY", 13, 20, 20),
            trends=Trends(0.3, 2.4, 4.7, -0.4, 0.2),
            comfort="COMFORTABLE",
            overall="ALL SYSTEMS NOMINAL",
        )
        plan = build_plan(state, cfg)
        self.assertTrue(plan.operations)
        for op in plan.operations:
            self.assertGreaterEqual(op.x1, 0)
            self.assertGreaterEqual(op.y1, 0)
            self.assertLess(op.x1, 800)
            self.assertLess(op.y1, 600)
            if op.kind != "text":
                self.assertLess(op.x2, 800)
                self.assertLess(op.y2, 600)


if __name__ == "__main__":
    unittest.main()
