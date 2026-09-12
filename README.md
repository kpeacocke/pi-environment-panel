# Pi Environment Panel

A single-page 800×600 e-paper instrument panel for this Raspberry Pi 5.

It deliberately does **not** contain calendar, email, tasks or generic productivity data. It answers two questions:

1. What is happening in the physical area around the Pi?
2. Is the Pi and its attached hardware healthy?

## Inputs

- Raspberry Pi Sense HAT V2
  - temperature
  - humidity
  - atmospheric pressure
  - pressure/temperature trends
  - derived dew point and comfort state
- Waveshare UPS HAT (E), I²C address `0x2d`
  - external VBUS voltage / mains state
  - battery voltage
  - battery current
  - battery percentage
  - remaining discharge time
- Raspberry Pi
  - CPU temperature/utilisation
  - RAM utilisation
  - NVMe free space
  - uptime
  - network address
- Hardware health
  - Hailo-10H
  - IMX500 camera
  - Sense HAT
  - UPS
  - Raspberry Pi DAC Pro
  - Docker
  - Ollama
  - Open WebUI
- Outside weather
  - Open-Meteo forecast API
  - current temperature/humidity/pressure/wind/condition
  - today's minimum/maximum temperature
  - maximum precipitation probability

## Output

- One fixed dashboard page
- Preview as an 800×600 PNG
- Native Waveshare UART drawing commands on the Raspberry Pi 5 dedicated UART/debug connector (`/dev/ttyAMA10`)
- SQLite history on NVMe when available
- systemd daemon for continuous updates

The display driver uses the module's native drawing commands rather than uploading a bitmap. This keeps the serial protocol small and avoids a second image-transfer/storage workflow.

## Hardware assumptions

Current known wiring:

| Function | Pi |
|---|---|
| Panel VCC (red) | 3.3V pin 17 |
| Panel GND | GND |
| Panel serial | Raspberry Pi 5 dedicated UART/debug connector |
| UART device | `/dev/ttyAMA10`, 115200 baud |
| WAKE_UP (yellow) | GPIO22, pin 15 |
| RESET (blue) | GPIO17, pin 11 |
| UPS HAT (E) | I²C bus 1, address `0x2d` |

## Install

Copy this project to the Pi, then:

```bash
cd pi-environment-panel
sudo ./scripts/install.sh
```

The installer:

- installs only missing APT dependencies
- creates `/opt/pi-environment-panel/.venv` with system site packages
- installs this project into the venv
- creates `/etc/pi-environment-panel/config.toml` if it does not exist
- creates `/var/lib/pi-environment-panel`
- installs `pi-environment-panel.service`

It does **not** overwrite an existing config.

## GPS and local weather

The deck has a SIMCOM SIM7600NA-H modem on **`/dev/ttyAMA0`**, using
GPIO14/15 (header pins 8/10). E-paper uses **`/dev/ttyAMA10`** on the dedicated
3-pin connector. Do not use `/dev/serial0` for the modem: after reboot it was
observed pointing at `ttyAMA10`. GPS and e-paper must never share a port.

The example configuration enables GPS-based weather:

```toml
[gps]
enabled = true
serial_device = "/dev/ttyAMA0"
baud = 115200
auto_enable = true
timeout_seconds = 2.0
max_age_seconds = 120.0

[weather]
enabled = true
location_source = "gps"
timezone = "Australia/Sydney"
cache_seconds = 900
max_stale_seconds = 3600
```

`pi-panel gps` reports fix status and coordinates (exit 2 without a usable fix).
The collector checks `AT+CGPS?`, enables the GNSS engine with `AT+CGPS=1` if off,
and reads `AT+CGPSINFO`. Queries are bounded and use exclusive serial access;
don't run another modem/AT client concurrently. No SIM or cellular data connection
is needed for standalone GNSS; weather uses the Pi's existing internet connection.
Connect the GNSS antenna and provide a clear sky view for a fix.

Coordinates are converted from degrees/minutes, with southern and western signs,
and checked against UTC fix time. Missing, malformed or stale fixes result in
unavailable weather, never an implicit 0,0 request or a previous location's forecast.
The Pi clock must be correct. No last-location fallback is used. Once a fix arrives,
the next sampling cycle supplies coordinates to Open-Meteo automatically.

The weather cache is keyed by approximately 1 km coordinate cells, local date and
timezone. Fresh data is cached for 15 minutes; during an API failure, matching data
may be shown as STALE for at most one hour. Movement or a missing GPS fix prevents
reuse of another location's weather. GPS coordinates are sent to Open-Meteo to
retrieve the forecast and saved in local runtime state; do not commit runtime files.
For a fixed installation, `location_source = "static"` uses explicitly configured
`latitude` and `longitude` instead.

References: [SIMCom GNSS application note](https://files.waveshare.com/upload/e/e1/SIM7500_SIM7600_Series_GNSS_Application_Note_V2.00.pdf),
[Open-Meteo API](https://open-meteo.com/en/docs).

## First run

Before touching the e-paper:

```bash
sudo -u kpeacocke /opt/pi-environment-panel/.venv/bin/pi-panel snapshot
sudo -u kpeacocke /opt/pi-environment-panel/.venv/bin/pi-panel preview --output /tmp/pi-panel.png
```

Then run the transport diagnostic:

```bash
sudo -u kpeacocke /opt/pi-environment-panel/.venv/bin/pi-panel diagnose-epaper
```

This prints the resolved UART device, permissions/groups, the exact transmitted
Waveshare handshake frame, raw received bytes, whether the WAKE GPIO pulse
actually succeeded, and a non-destructive baud scan. It does not change the
panel's configured baud rate.

Once diagnostics pass, the shorter probe is:

```bash
sudo -u kpeacocke /opt/pi-environment-panel/.venv/bin/pi-panel probe-epaper
```

Then display the page:

```bash
sudo -u kpeacocke /opt/pi-environment-panel/.venv/bin/pi-panel display
```

If all of that works:

```bash
sudo systemctl enable --now pi-environment-panel
```

## Useful commands

```bash
pi-panel snapshot
pi-panel preview --output dashboard.png
pi-panel probe-epaper
pi-panel display
pi-panel daemon
```

## Refresh behaviour

Default daemon behaviour:

- sample Sense HAT, UPS and Pi every 60 seconds
- weather cached for 15 minutes
- Hailo/camera/service health cached for 10 minutes
- e-paper normal refresh every 5 minutes
- e-paper refresh immediately when the overall status changes
- SQLite history retained for 90 days

The dashboard is intentionally slow-moving. E-paper should show meaningful state, not imitate an LCD.

## Temperature calibration

A Sense HAT mounted close to the Pi can read warmer than the surrounding air. Use:

```toml
[sense]
temperature_offset_c = 0.0
```

to apply a calibration offset after comparing with a trusted room thermometer.

## Waveshare protocol references

The UART driver follows the Waveshare 4.3-inch e-Paper UART Module command format:

- frame header `0xA5`
- two-byte frame length
- command byte
- command payload
- fixed trailer `CC 33 C3 3C`
- XOR parity byte
- handshake `0x00`
- refresh `0x0A`
- English font size `0x1E` (configurable for module variants)
- line `0x22`
- filled rectangle `0x24`
- clear `0x2E`
- character string `0x30`

Official documentation:
- https://www.waveshare.com/wiki/4.3inch_e-Paper_UART_Module
- https://www.waveshare.com/wiki/UPS_HAT_%28E%29
- https://www.waveshare.com/wiki/UPS_HAT_%28E%29_Register
- https://www.raspberrypi.com/documentation/accessories/sense-hat.html
- https://open-meteo.com/en/docs

## Design

The renderer creates a device-independent display plan containing text, lines and rectangles.

That same plan can be:

- drawn to a PNG with Pillow for development, or
- translated into native e-paper UART commands.

This means layout work can be done without repeatedly refreshing the physical display.

## v0.1.1

- Added `diagnose-epaper` transport diagnostics.
- WAKE GPIO errors are no longer silently hidden in diagnostic mode.
- Added raw RX byte reporting and non-destructive host-side baud scan.

## v0.1.2

- Fixed `diagnose-epaper` crashing before UART access because `frame` was not imported into the CLI module.
- Added a regression test that executes the diagnostic path and verifies the exact documented handshake frame.

## v0.1.3

- Corrected the physical UART target for this Pi 5 build to `/dev/ttyAMA10`.
- The panel's serial TX/RX are on the Pi 5 dedicated UART/debug connector; the 40-pin header is used for auxiliary GPIO such as WAKE and RESET.
- `/dev/serial0` is no longer used as the default because this machine currently maps it to `/dev/ttyAMA0` on GPIO14/15, which is not where this panel is physically connected.
- Verified on the target Pi: the Waveshare handshake on `/dev/ttyAMA10` returned ASCII `OK` (`4F 4B`).

## v0.1.4

- Fixed `probe-epaper` / normal display handshake sequencing.
- The driver now tries the already-awake `/dev/ttyAMA10` panel first and only pulses the configured WAKE GPIO if the first handshake fails.
- This matches the target hardware observation: a direct handshake on `/dev/ttyAMA10` returned `OK` while the module state LED was already on.

## v0.1.5

- Fixed UPS collection to use explicit `SMBus.close()` instead of requiring context-manager support.
- Kept the Waveshare register mapping at VBUS `0x10/11`, battery voltage `0x20/21`,
  signed current `0x22/23`, percentage `0x24/25`, and remaining minutes `0x28/29`.
- Hailo health now retries one transient failed `fw-control identify` before marking the accelerator failed.
- A repeated Hailo failure remains a real dashboard fault rather than being hidden.

## September 2026 deployment findings

User-confirmed auxiliary wiring: red → 3.3V/header pin 17; yellow WAKE →
GPIO22/header pin 15; blue RESET → GPIO17/header pin 11. Cable colours at the
Pi UART adapter must be mapped by connector signals, not assumed to match the
display harness. Pi UART pin 1 RX ← display DOUT; pin 2 GND ↔ display GND;
pin 3 TX → display DIN.

The systemd working directory must be writable by the service user because lgpio
creates notification FIFOs there. Both installer and unit now set
`WorkingDirectory=/var/lib/pi-environment-panel`. Earlier source edits were not
necessarily installed: after changes, rebuild/install into the service venv.

A restart was reported to restore the visible dashboard, but a subsequent live
inspection again found repeated failed handshakes and zero UART10 RX bytes since
boot. That does not establish a root cause or prove continuous refresh. The daemon
now logs successful command sends and writes `display-status.json` separately from
sensor `latest.json`. Handshake failure remains a failure; it is not hidden by
bypassing the handshake. `commands_sent_at` is not a visual acknowledgement from
the screen. The serial cable, electrical continuity and power stability remain
possible causes until a current successful exchange is observed.

See [the live hardware diagnosis](docs/hardware-diagnostics.md) for the raw GNSS
no-fix reports, cold-start test and unsuccessful display recovery after a controlled
reboot. These distinguish verified settings from unresolved electrical causes.
