from __future__ import annotations

import math
import time
from ..models import SenseReading
from ..derive import dew_point_c


def _movement_g(accel: dict[str, float]) -> float:
    magnitude = math.sqrt(
        float(accel.get("x", 0.0)) ** 2
        + float(accel.get("y", 0.0)) ** 2
        + float(accel.get("z", 0.0)) ** 2
    )
    return abs(magnitude - 1.0)


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

        orientation = s.get_orientation_degrees()
        acceleration = s.get_accelerometer_raw()
        gyro = s.get_gyroscope_raw()
        movement = _movement_g(acceleration)

        return SenseReading(
            ok=True,
            temperature_c=temperature,
            humidity_pct=humidity,
            pressure_hpa=pressure,
            dew_point_c=dew_point_c(temperature, humidity),
            heading_deg=float(s.get_compass()),
            pitch_deg=float(orientation.get("pitch", 0.0)),
            roll_deg=float(orientation.get("roll", 0.0)),
            yaw_deg=float(orientation.get("yaw", 0.0)),
            accel_x_g=float(acceleration.get("x", 0.0)),
            accel_y_g=float(acceleration.get("y", 0.0)),
            accel_z_g=float(acceleration.get("z", 0.0)),
            gyro_x_rads=float(gyro.get("x", 0.0)),
            gyro_y_rads=float(gyro.get("y", 0.0)),
            gyro_z_rads=float(gyro.get("z", 0.0)),
            movement_g=movement,
            motion="MOVING" if movement >= cfg.motion_threshold_g else "STATIONARY",
        )
    except Exception as exc:
        return SenseReading(ok=False, error=str(exc))
