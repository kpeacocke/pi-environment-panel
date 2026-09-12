from __future__ import annotations

import json
import math
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import urllib.parse
import urllib.request
from pathlib import Path
from ..models import WeatherReading


WMO = {
    0: "CLEAR",
    1: "MOSTLY CLEAR",
    2: "PARTLY CLOUDY",
    3: "OVERCAST",
    45: "FOG",
    48: "RIME FOG",
    51: "LIGHT DRIZZLE",
    53: "DRIZZLE",
    55: "HEAVY DRIZZLE",
    56: "FREEZING DRIZZLE",
    57: "FREEZING DRIZZLE",
    61: "LIGHT RAIN",
    63: "RAIN",
    65: "HEAVY RAIN",
    66: "FREEZING RAIN",
    67: "FREEZING RAIN",
    71: "LIGHT SNOW",
    73: "SNOW",
    75: "HEAVY SNOW",
    77: "SNOW GRAINS",
    80: "RAIN SHOWERS",
    81: "RAIN SHOWERS",
    82: "HEAVY SHOWERS",
    85: "SNOW SHOWERS",
    86: "HEAVY SNOW SHOWERS",
    95: "THUNDERSTORM",
    96: "STORM / HAIL",
    99: "STORM / HAIL",
}


def _parse(data, stale=False):
    cur = data["current"]
    daily = data["daily"]
    hourly = data.get("hourly", {})
    rain_probs = hourly.get("precipitation_probability") or []
    return WeatherReading(
        ok=True,
        temperature_c=cur.get("temperature_2m"),
        humidity_pct=cur.get("relative_humidity_2m"),
        pressure_hpa=cur.get("pressure_msl"),
        wind_kmh=cur.get("wind_speed_10m"),
        condition=WMO.get(cur.get("weather_code"), f"WMO {cur.get('weather_code')}"),
        today_min_c=(daily.get("temperature_2m_min") or [None])[0],
        today_max_c=(daily.get("temperature_2m_max") or [None])[0],
        rain_probability_pct=max(rain_probs) if rain_probs else None,
        stale=stale,
    )


def collect(cfg, state_dir: str, gps=None) -> WeatherReading:
    if not cfg.enabled:
        return WeatherReading(error="disabled")

    latitude, longitude = cfg.latitude, cfg.longitude
    if cfg.location_source == "gps":
        if gps is None or not gps.ok:
            return WeatherReading(error=gps.error if gps else "GPS waiting for fix")
        latitude, longitude = gps.latitude, gps.longitude
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (latitude, longitude)) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return WeatherReading(error="Invalid weather coordinates")
    # Approximately 1 km cells: avoid refetching for GPS jitter, but invalidate
    # the cache when the deck moves, the local day changes or timezone changes.
    location_key = [round(latitude, 2), round(longitude, 2), cfg.timezone,
                    datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()]
    cache = None
    cache_path = Path(state_dir) / "weather.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
            if cache.get("_location") == location_key and 0 <= time.time() - cache["_fetched_at"] < cfg.cache_seconds:
                return _parse(cache["data"])
        except Exception:
            pass

    query = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": cfg.timezone,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "pressure_msl",
            "wind_speed_10m",
            "weather_code",
        ]),
        "daily": "temperature_2m_min,temperature_2m_max",
        "hourly": "precipitation_probability",
        "forecast_days": 1,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(query)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pi-environment-panel/0.1"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
        cache_path.write_text(json.dumps({"_fetched_at": time.time(), "_location": location_key, "data": data}))
        return _parse(data)
    except Exception as exc:
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text())
                if cache.get("_location") != location_key or not 0 <= time.time() - cache["_fetched_at"] <= cfg.max_stale_seconds:
                    raise ValueError("No recent weather cache for this location")
                result = _parse(cache["data"], stale=True)
                result.error = str(exc)
                return result
            except Exception:
                pass
        return WeatherReading(ok=False, error=str(exc))
