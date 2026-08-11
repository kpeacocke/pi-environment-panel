from __future__ import annotations

import subprocess
import time
from pathlib import Path
from ..models import HealthReading


def _run(cmd, timeout=8):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout + p.stderr)
    except Exception as exc:
        return False, str(exc)


def collect(sense_ok: bool, ups_ok: bool) -> HealthReading:
    hailo_ok = False
    hailo_out = ""
    for attempt in range(2):
        rc_ok, hailo_out = _run(
            ["/usr/bin/hailortcli", "fw-control", "identify"],
            timeout=10,
        )
        hailo_ok = rc_ok and "Device Architecture: HAILO10H" in hailo_out
        if hailo_ok:
            break
        if attempt == 0:
            time.sleep(0.5)

    camera_ok, camera_out = _run(["rpicam-hello", "--list-cameras"], timeout=10)
    camera_ok = camera_ok and "imx500" in camera_out.lower()

    cards = Path("/proc/asound/cards").read_text(errors="ignore") if Path("/proc/asound/cards").exists() else ""
    dac_ok = "RPi DAC Pro" in cards

    docker_ok, _ = _run(["systemctl", "is-active", "--quiet", "docker"], timeout=3)
    ollama_ok, _ = _run(["systemctl", "is-active", "--quiet", "ollama"], timeout=3)

    open_webui = None
    if docker_ok:
        ok, out = _run([
            "docker", "inspect", "-f", "{{.State.Running}}", "open-webui"
        ], timeout=4)
        open_webui = ok and out.strip().lower() == "true"

    return HealthReading(
        hailo=hailo_ok,
        camera=camera_ok,
        sense=sense_ok,
        ups=ups_ok,
        dac=dac_ok,
        docker=docker_ok,
        ollama=ollama_ok,
        open_webui=open_webui,
    )
