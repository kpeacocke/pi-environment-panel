import unittest
from unittest.mock import patch
from pathlib import Path

from pi_environment_panel.collectors import health


class HealthTests(unittest.TestCase):
    @patch("pi_environment_panel.collectors.health.time.sleep", return_value=None)
    @patch("pi_environment_panel.collectors.health.Path")
    @patch("pi_environment_panel.collectors.health._run")
    def test_hailo_retries_once(self, run, path_cls, _sleep):
        # Hailo fail, Hailo pass, camera pass, docker, ollama, webui.
        run.side_effect = [
            (False, "temporary fail"),
            (True, "Device Architecture: HAILO10H"),
            (True, "imx500"),
            (True, ""),
            (True, ""),
            (True, "true"),
        ]

        fake_cards = unittest.mock.MagicMock()
        fake_cards.exists.return_value = True
        fake_cards.read_text.return_value = "RPi DAC Pro"
        path_cls.return_value = fake_cards

        result = health.collect(True, True)
        self.assertTrue(result.hailo)
        self.assertTrue(result.camera)
        self.assertTrue(result.sense)
        self.assertTrue(result.ups)


if __name__ == "__main__":
    unittest.main()
