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
- Native Waveshare UART drawing commands on `/dev/serial0`
- SQLite history on NVMe when available
- systemd daemon for continuous updates

The display driver uses the module's native drawing commands rather than uploading a bitmap. This keeps the serial protocol small and avoids a second image-transfer/storage workflow.

## Hardware assumptions

Current known wiring:

| Function | Pi |
|---|---|
| Panel VCC | 5V pin 4 |
| Panel GND | GND |
| Panel RX/DIN | GPIO14/TX, pin 8 |
| Panel TX/DOUT | GPIO15/RX, pin 10 |
| WAKE_UP | GPIO4, pin 7 |
| RESET | GPIO17, pin 11 |
| UART | `/dev/serial0`, 115200 baud |
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

## Configure weather

Edit:

```bash
sudo nano /etc/pi-environment-panel/config.toml
```

Set your desired weather coordinate and enable weather:

```toml
[weather]
enabled = true
latitude = -33.0000
longitude = 151.0000
timezone = "Australia/Sydney"
```

The project deliberately does not guess the Pi's location.

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
