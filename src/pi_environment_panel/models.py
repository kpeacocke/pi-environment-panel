from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional, Any


@dataclass
class SenseReading:
    ok: bool = False
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    dew_point_c: Optional[float] = None
    heading_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    roll_deg: Optional[float] = None
    yaw_deg: Optional[float] = None
    accel_x_g: Optional[float] = None
    accel_y_g: Optional[float] = None
    accel_z_g: Optional[float] = None
    gyro_x_rads: Optional[float] = None
    gyro_y_rads: Optional[float] = None
    gyro_z_rads: Optional[float] = None
    movement_g: Optional[float] = None
    motion: str = "UNKNOWN"
    error: Optional[str] = None


@dataclass
class UPSReading:
    ok: bool = False
    mains: Optional[bool] = None
    vbus_voltage_v: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    battery_current_ma: Optional[int] = None
    battery_pct: Optional[float] = None
    remaining_minutes: Optional[int] = None
    error: Optional[str] = None


@dataclass
class SystemReading:
    cpu_temp_c: Optional[float] = None
    cpu_pct: Optional[float] = None
    ram_pct: Optional[float] = None
    disk_free_pct: Optional[float] = None
    disk_free_gb: Optional[float] = None
    uptime_seconds: Optional[int] = None
    ip_address: Optional[str] = None


@dataclass
class HealthReading:
    hailo: Optional[bool] = None
    camera: Optional[bool] = None
    sense: Optional[bool] = None
    ups: Optional[bool] = None
    dac: Optional[bool] = None
    docker: Optional[bool] = None
    ollama: Optional[bool] = None
    open_webui: Optional[bool] = None


@dataclass
class GPSReading:
    ok: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    fix_time: Optional[str] = None
    age_seconds: Optional[float] = None
    error: Optional[str] = None


@dataclass
class WeatherReading:
    ok: bool = False
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_kmh: Optional[float] = None
    condition: Optional[str] = None
    today_min_c: Optional[float] = None
    today_max_c: Optional[float] = None
    rain_probability_pct: Optional[float] = None
    stale: bool = False
    error: Optional[str] = None


@dataclass
class Trends:
    pressure_1h: Optional[float] = None
    pressure_6h: Optional[float] = None
    pressure_24h: Optional[float] = None
    temperature_6h: Optional[float] = None
    temperature_24h: Optional[float] = None


@dataclass
class DashboardState:
    timestamp: str
    sense: SenseReading
    ups: UPSReading
    system: SystemReading
    health: HealthReading
    weather: WeatherReading
    trends: Trends
    comfort: str = "UNKNOWN"
    overall: str = "UNKNOWN"
    gps: GPSReading = field(default_factory=GPSReading)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
