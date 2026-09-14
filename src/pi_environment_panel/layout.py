from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from .derive import pressure_label


WIDTH = 800
HEIGHT = 600


@dataclass
class Op:
    kind: str
    x1: int
    y1: int
    x2: int = 0
    y2: int = 0
    text: str = ""
    size: int = 32


@dataclass
class DisplayPlan:
    operations: list[Op] = field(default_factory=list)

    def text(self, x, y, text, size=32):
        self.operations.append(Op("text", x, y, text=str(text), size=size))

    def line(self, x1, y1, x2, y2):
        self.operations.append(Op("line", x1, y1, x2, y2))

    def fill_rect(self, x1, y1, x2, y2):
        self.operations.append(Op("fill_rect", x1, y1, x2, y2))


def _f(value, fmt, fallback="--"):
    if value is None:
        return fallback
    return format(value, fmt)


def _uptime(seconds):
    if seconds is None:
        return "--"
    days, rem = divmod(seconds, 86400)
    hours = rem // 3600
    return f"{days}d {hours}h" if days else f"{hours}h"


def _health(value):
    return "OK" if value is True else ("FAIL" if value is False else "--")


def build_plan(state, cfg) -> DisplayPlan:
    p = DisplayPlan()
    ts = datetime.fromisoformat(state.timestamp).astimezone()
    pressure_state = pressure_label(
        state.trends.pressure_6h,
        cfg.thresholds.pressure_trend_hpa_6h,
    )

    # Header.
    p.text(18, 8, cfg.panel.title[:18], 32)
    p.text(500, 8, ts.strftime("%a %d %H:%M").upper(), 32)
    p.line(15, 46, 785, 46)

    # Room / environment.
    room_temp = f"{_f(state.sense.temperature_c, '.1f')} C"
    p.text(20, 58, room_temp, 64)
    p.text(300, 66, f"RH {_f(state.sense.humidity_pct, '.0f')}%", 48)
    p.text(520, 66, f"{_f(state.sense.pressure_hpa, '.0f')} hPa", 48)

    trend = state.trends.pressure_6h
    trend_text = ""
    if trend is not None:
        trend_text = f" {trend:+.1f}/6h"
    p.text(20, 132, f"{state.comfort} - {pressure_state}{trend_text}"[:48], 32)

    p.line(15, 174, 785, 174)

    # Outside weather.
    if state.weather.ok:
        stale = " STALE" if state.weather.stale else ""
        p.text(20, 188, "OUTSIDE", 32)
        p.text(170, 188, f"{_f(state.weather.temperature_c, '.0f')} C {state.weather.condition}{stale}"[:35], 32)
        p.text(
            20, 228,
            f"TODAY {_f(state.weather.today_min_c, '.0f')}-{_f(state.weather.today_max_c, '.0f')} C"
            f"  RH {_f(state.weather.humidity_pct, '.0f')}%"
            f"  RAIN {_f(state.weather.rain_probability_pct, '.0f')}%",
            32,
        )
        p.text(
            20, 264,
            f"WIND {_f(state.weather.wind_kmh, '.0f')} km/h"
            f"  PRESS {_f(state.weather.pressure_hpa, '.0f')} hPa",
            32,
        )
    else:
        label = "OUTSIDE WEATHER DISABLED / UNAVAILABLE"
        if state.weather.error and state.weather.error.startswith("GPS"):
            label = "OUTSIDE: WAITING FOR GPS FIX"
        p.text(20, 202, label, 32)

    p.line(15, 306, 785, 306)

    # Power left.
    p.text(20, 320, "POWER", 32)
    mains = "ON" if state.ups.mains is True else ("OFF" if state.ups.mains is False else "--")
    p.text(20, 358, f"MAINS {mains}", 32)
    p.text(20, 394, f"UPS {_f(state.ups.battery_pct, '.0f')}%  {_f(state.ups.battery_voltage_v, '.2f')}V", 32)
    if state.ups.remaining_minutes is not None and state.ups.remaining_minutes < 65000:
        hours, mins = divmod(state.ups.remaining_minutes, 60)
        runtime = f"{hours}h{mins:02d}"
    else:
        runtime = "--"
    current = "--" if state.ups.battery_current_ma is None else f"{state.ups.battery_current_ma:+d}mA"
    p.text(20, 430, f"RUNTIME {runtime}  {current}", 32)

    # Pi right.
    p.line(398, 315, 398, 465)
    p.text(420, 320, "PI", 32)
    p.text(420, 358, f"CPU {_f(state.system.cpu_temp_c, '.0f')}C  LOAD {_f(state.system.cpu_pct, '.0f')}%", 32)
    p.text(420, 394, f"RAM {_f(state.system.ram_pct, '.0f')}%  NVME {_f(state.system.disk_free_pct, '.0f')}% FREE", 32)
    p.text(420, 430, f"UP {_uptime(state.system.uptime_seconds)}  {state.system.ip_address or '--'}"[:26], 32)

    p.line(15, 474, 785, 474)

    # Hardware.
    h = state.health
    p.text(
        20, 488,
        f"HAILO {_health(h.hailo)}  CAM {_health(h.camera)}  SENSE {_health(h.sense)}  UPS {_health(h.ups)}"[:48],
        32,
    )
    p.text(
        20, 524,
        f"DAC {_health(h.dac)}  DOCKER {_health(h.docker)}  OLLAMA {_health(h.ollama)}  WEBUI {_health(h.open_webui)}"[:48],
        32,
    )

    p.line(15, 562, 785, 562)
    gps = "GPS FIX" if state.gps.ok else "GPS --"
    field = (
        f"HDG {_f(state.sense.heading_deg, '.0f')}  "
        f"{state.sense.motion}  {gps}  {state.overall}"
    )
    p.text(20, 568, field[:48], 32)

    return p
