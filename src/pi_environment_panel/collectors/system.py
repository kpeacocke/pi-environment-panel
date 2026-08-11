from __future__ import annotations

import os
import shutil
import socket
import time
from pathlib import Path
from ..models import SystemReading


def _cpu_times():
    fields = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
    nums = [int(x) for x in fields]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    return sum(nums), idle


def _cpu_percent(interval=0.15):
    total1, idle1 = _cpu_times()
    time.sleep(interval)
    total2, idle2 = _cpu_times()
    dt = total2 - total1
    di = idle2 - idle1
    return 0.0 if dt <= 0 else max(0.0, min(100.0, (dt - di) * 100.0 / dt))


def _ram_percent():
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            values[k] = int(v.strip().split()[0])
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    return 0.0 if total == 0 else (total - available) * 100.0 / total


def _cpu_temp():
    for path in [
        Path("/sys/class/thermal/thermal_zone0/temp"),
        Path("/sys/devices/virtual/thermal/thermal_zone0/temp"),
    ]:
        if path.exists():
            return float(path.read_text().strip()) / 1000.0
    return None


def _ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        value = sock.getsockname()[0]
        sock.close()
        return value
    except OSError:
        return None


def collect(nvme_path: str) -> SystemReading:
    path = nvme_path if Path(nvme_path).is_mount() else "/"
    usage = shutil.disk_usage(path)
    free_pct = usage.free * 100.0 / usage.total
    uptime = int(float(Path("/proc/uptime").read_text().split()[0]))

    return SystemReading(
        cpu_temp_c=_cpu_temp(),
        cpu_pct=_cpu_percent(),
        ram_pct=_ram_percent(),
        disk_free_pct=free_pct,
        disk_free_gb=usage.free / (1024 ** 3),
        uptime_seconds=uptime,
        ip_address=_ip(),
    )
