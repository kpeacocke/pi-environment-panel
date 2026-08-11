from __future__ import annotations

import time
from ..models import SenseReading
from ..derive import dew_point_c


def collect(cfg) -> SenseReading:
    if not cfg.enabled:
        return SenseReading(error="disabled")

    try:
        from sense_hat import SenseHat
        s = SenseHat()
        temperature = float(s.get_temperature()) + cfg.temperature_offset_c
        humidity = float(s.get_humidity())

        pressure = 0.0
        for _ in range(max(1, cfg.pressure_retries)):
            pressure = float(s.get_pressure())
            if 300.0 <= pressure <= 1200.0:
                break
            time.sleep(cfg.pressure_retry_seconds)

        if not 300.0 <= pressure <= 1200.0:
            raise RuntimeError(f"invalid pressure after retries: {pressure}")

        return SenseReading(
            ok=True,
            temperature_c=temperature,
            humidity_pct=humidity,
            pressure_hpa=pressure,
            dew_point_c=dew_point_c(temperature, humidity),
        )
    except Exception as exc:
        return SenseReading(ok=False, error=str(exc))
