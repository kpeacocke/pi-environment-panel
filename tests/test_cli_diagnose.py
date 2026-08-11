import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import pi_environment_panel.__main__ as cli


class DiagnoseCLIRegressionTests(unittest.TestCase):
    def test_diagnostic_constructs_documented_handshake_before_uart(self):
        cfg = SimpleNamespace(
            panel=SimpleNamespace(
                serial_device="/dev/null",
                baud=115200,
                wake_gpio=4,
                reset_gpio=17,
                english_font_command=0x1E,
            )
        )

        class StopHerePanel:
            def __init__(self, **kwargs):
                raise RuntimeError("reached UART setup")

        args = SimpleNamespace(config=None)
        output = io.StringIO()

        with patch.object(cli, "load_config", return_value=cfg), \
             patch.object(cli, "WaveshareUART", StopHerePanel), \
             redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, "reached UART setup"):
                cli.cmd_diagnose_epaper(args)

        self.assertIn(
            "TX expected: A5 00 09 00 CC 33 C3 3C AC",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
