from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import tomllib


DEFAULT_CONFIG = Path("/etc/pi-environment-panel/config.toml")


@dataclass
class PanelConfig:
    title: str = "KP PI"
    serial_device: str = "/dev/ttyAMA10"
    baud: int = 115200
    wake_gpio: int = 22
    reset_gpio: int = 17
    english_font_command: int = 0x1E
    sample_seconds: int = 60
    refresh_seconds: int = 300
    health_seconds: int = 600
    history_days: int = 90
    state_dir: str = "/var/lib/pi-environment-panel"
    nvme_path: str = "/mnt/nvme"


@dataclass
class SenseConfig:
    enabled: bool = True
    temperature_offset_c: float = 0.0
    pressure_retries: int = 6
    pressure_retry_seconds: float = 0.25


@dataclass
class UPSConfig:
    enabled: bool = True
    bus: int = 1
    address: int = 0x2D


@dataclass
class GPSConfig:
    enabled: bool = False
    serial_device: str = "/dev/ttyAMA0"
    baud: int = 115200
    auto_enable: bool = True
    timeout_seconds: float = 2.0
    max_age_seconds: float = 120.0


@dataclass
class WeatherConfig:
    enabled: bool = False
    location_source: str = "static"
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = "Australia/Sydney"
    cache_seconds: int = 900
    max_stale_seconds: int = 3600


@dataclass
class ThresholdConfig:
    room_cold_c: float = 18.0
    room_warm_c: float = 27.0
    humidity_dry_pct: float = 30.0
    humidity_humid_pct: float = 65.0
    pressure_trend_hpa_6h: float = 1.5
    cpu_hot_c: float = 75.0
    disk_low_free_pct: float = 10.0
    ups_low_pct: float = 20.0


@dataclass
class Config:
    panel: PanelConfig = field(default_factory=PanelConfig)
    sense: SenseConfig = field(default_factory=SenseConfig)
    ups: UPSConfig = field(default_factory=UPSConfig)
    gps: GPSConfig = field(default_factory=GPSConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)


def _merge(dc, values: dict):
    for key, value in values.items():
        if hasattr(dc, key):
            setattr(dc, key, value)


def load_config(path: str | Path | None = None) -> Config:
    cfg = Config()
    cfg_path = Path(path or os.environ.get("PI_PANEL_CONFIG", DEFAULT_CONFIG))
    if cfg_path.exists():
        data = tomllib.loads(cfg_path.read_text())
        _merge(cfg.panel, data.get("panel", {}))
        _merge(cfg.sense, data.get("sense", {}))
        _merge(cfg.ups, data.get("ups", {}))
        _merge(cfg.gps, data.get("gps", {}))
        _merge(cfg.weather, data.get("weather", {}))
        _merge(cfg.thresholds, data.get("thresholds", {}))

    # Environment overrides are useful for testing without mutating /etc.
    if os.getenv("PANEL_LATITUDE"):
        cfg.weather.latitude = float(os.environ["PANEL_LATITUDE"])
    if os.getenv("PANEL_LONGITUDE"):
        cfg.weather.longitude = float(os.environ["PANEL_LONGITUDE"])
    if os.getenv("PANEL_WEATHER_ENABLED"):
        cfg.weather.enabled = os.environ["PANEL_WEATHER_ENABLED"].lower() in {"1", "true", "yes", "on"}

    if cfg.weather.location_source not in {"static", "gps"}:
        raise ValueError("weather.location_source must be static or gps")
    if cfg.gps.enabled:
        if Path(cfg.gps.serial_device).resolve() == Path(cfg.panel.serial_device).resolve():
            raise ValueError("GPS and e-paper must use different UART devices")
        if cfg.gps.timeout_seconds <= 0 or cfg.gps.max_age_seconds <= 0 or cfg.gps.baud <= 0:
            raise ValueError("GPS timing and baud must be positive")
    return cfg
