"""Bounded SIM7600 GNSS queries on the modem UART, separate from e-paper."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
import time

from ..models import GPSReading


def _coordinate(value: str, hemisphere: str, latitude: bool) -> float:
    if hemisphere not in ("NS" if latitude else "EW"):
        raise ValueError("invalid hemisphere")
    if not re.fullmatch(r"\d{4}\.\d+" if latitude else r"\d{5}\.\d+", value):
        raise ValueError("invalid coordinate")
    number = float(value)
    degrees = int(number // 100)
    minutes = number - degrees * 100
    limit = 90 if latitude else 180
    if minutes >= 60 or degrees + minutes / 60 > limit:
        raise ValueError("coordinate out of range")
    result = degrees + minutes / 60
    return -result if hemisphere in "SW" else result


def parse_fix(response: str, max_age_seconds: float = 120, now=None) -> GPSReading:
    match = re.search(r"^\+CGPSINFO:\s*([^\r\n]*)", response, re.MULTILINE)
    if not match:
        return GPSReading(error="GPS response missing")
    fields = [x.strip() for x in match.group(1).split(",")]
    if len(fields) < 6 or not all(fields[:6]):
        return GPSReading(error="GPS waiting for fix")
    try:
        latitude = _coordinate(fields[0], fields[1], True)
        longitude = _coordinate(fields[2], fields[3], False)
        # SIM7600 reports ddmmyy and UTC hhmmss.sss.
        if not re.fullmatch(r"\d{6}(?:\.\d+)?", fields[5]):
            raise ValueError("invalid UTC time")
        stamp = datetime.strptime(fields[4] + fields[5][:6], "%d%m%y%H%M%S").replace(tzinfo=timezone.utc)
        now = now or datetime.now(timezone.utc)
        age = (now - stamp).total_seconds()
        if not math.isfinite(age) or age < -10 or age > max_age_seconds:
            return GPSReading(error="GPS fix is stale or clock is incorrect")
        return GPSReading(ok=True, latitude=latitude, longitude=longitude,
                          fix_time=stamp.isoformat(), age_seconds=max(0, age))
    except (ValueError, OverflowError):
        return GPSReading(error="GPS fix is malformed")


def command(port, text: str, timeout: float) -> str:
    port.reset_input_buffer()
    port.write((text + "\r").encode("ascii"))
    deadline = time.monotonic() + timeout
    received = bytearray()
    while time.monotonic() < deadline and len(received) < 16384:
        received.extend(port.read(min(port.in_waiting or 1, 1024)))
        if b"\r\nOK\r\n" in received or b"\r\nERROR\r\n" in received or b"+CME ERROR:" in received:
            break
    result = received.decode("ascii", errors="replace")
    if "OK" not in result.split():
        raise RuntimeError("Modem command failed or timed out: " + text)
    return result


def collect(cfg) -> GPSReading:
    if not cfg.enabled:
        return GPSReading(error="GPS disabled")
    try:
        import serial
        with serial.Serial(cfg.serial_device, cfg.baud, timeout=0.1,
                           write_timeout=cfg.timeout_seconds, exclusive=True) as port:
            status = command(port, "AT+CGPS?", cfg.timeout_seconds)
            if re.search(r"\+CGPS:\s*0(?:,|\s)", status):
                if not cfg.auto_enable:
                    return GPSReading(error="GPS engine is off")
                command(port, "AT+CGPS=1", cfg.timeout_seconds)
            return parse_fix(command(port, "AT+CGPSINFO", cfg.timeout_seconds), cfg.max_age_seconds)
    except (OSError, RuntimeError, ValueError) as exc:
        return GPSReading(error=str(exc))
