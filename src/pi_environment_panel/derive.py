from __future__ import annotations

import math
from .models import DashboardState


def dew_point_c(temp_c: float, humidity_pct: float) -> float:
    """Magnus approximation for typical indoor conditions."""
    rh = max(0.1, min(100.0, humidity_pct))
    a, b = 17.62, 243.12
    gamma = math.log(rh / 100.0) + (a * temp_c) / (b + temp_c)
    return (b * gamma) / (a - gamma)


def comfort_label(temp_c: float | None, humidity_pct: float | None, thresholds) -> str:
    if temp_c is None or humidity_pct is None:
        return "UNKNOWN"
    if temp_c < thresholds.room_cold_c:
        return "COOL"
    if temp_c > thresholds.room_warm_c:
        return "WARM"
    if humidity_pct < thresholds.humidity_dry_pct:
        return "DRY"
    if humidity_pct > thresholds.humidity_humid_pct:
        return "HUMID"
    return "COMFORTABLE"


def pressure_label(delta_6h: float | None, threshold: float) -> str:
    if delta_6h is None:
        return "TREND LEARNING"
    if delta_6h >= threshold:
        return "PRESSURE RISING"
    if delta_6h <= -threshold:
        return "PRESSURE FALLING"
    return "PRESSURE STEADY"


def overall_status(state: DashboardState, thresholds) -> str:
    u = state.ups
    h = state.health
    s = state.sense
    sys = state.system

    if u.ok and u.mains is False:
        if u.battery_pct is not None and u.battery_pct <= thresholds.ups_low_pct:
            return f"BATTERY LOW - {u.battery_pct:.0f}%"
        if u.battery_pct is not None:
            return f"ON UPS - {u.battery_pct:.0f}%"
        return "RUNNING ON UPS"

    failures = []
    for name, value in [
        ("HAILO", h.hailo),
        ("CAMERA", h.camera),
        ("SENSE", h.sense),
        ("UPS", h.ups),
        ("DAC", h.dac),
        ("DOCKER", h.docker),
    ]:
        if value is False:
            failures.append(name)
    if failures:
        return "FAULT - " + ", ".join(failures[:3])

    if sys.cpu_temp_c is not None and sys.cpu_temp_c >= thresholds.cpu_hot_c:
        return f"CPU HOT - {sys.cpu_temp_c:.0f} C"

    if sys.disk_free_pct is not None and sys.disk_free_pct <= thresholds.disk_low_free_pct:
        return f"NVME LOW - {sys.disk_free_pct:.0f}% FREE"

    if state.comfort in {"WARM", "COOL", "HUMID", "DRY"}:
        return f"ROOM {state.comfort}"

    return "ALL SYSTEMS NOMINAL"
