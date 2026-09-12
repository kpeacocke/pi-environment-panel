#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="/opt/pi-environment-panel"
CFG_DIR="/etc/pi-environment-panel"
STATE_DIR="/var/lib/pi-environment-panel"
SERVICE_USER="${SUDO_USER:-kpeacocke}"

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo ./scripts/install.sh" >&2
  exit 1
fi

apt-get update
apt-get install -y --no-upgrade \
  python3-venv python3-pip python3-pil \
  python3-serial python3-gpiozero python3-smbus \
  sense-hat i2c-tools fonts-dejavu-core

mkdir -p "$APP_DIR" "$CFG_DIR" "$STATE_DIR"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  "$PROJECT_DIR/" "$APP_DIR/"

python3 -m venv --system-site-packages "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --disable-pip-version-check "$APP_DIR"

if [[ ! -f "$CFG_DIR/config.toml" ]]; then
  install -m 0644 "$APP_DIR/config.example.toml" "$CFG_DIR/config.toml"
  echo "Created $CFG_DIR/config.toml"
else
  echo "Keeping existing $CFG_DIR/config.toml"
fi

chown -R "$SERVICE_USER":"$SERVICE_USER" "$STATE_DIR"

cat > /etc/systemd/system/pi-environment-panel.service <<EOF
[Unit]
Description=Pi Environment Panel
After=multi-user.target network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
SupplementaryGroups=dialout gpio i2c
WorkingDirectory=/var/lib/pi-environment-panel
Environment=PYTHONUNBUFFERED=1
ExecStart=$APP_DIR/.venv/bin/pi-panel daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo
echo "Installed."
echo "1. Edit $CFG_DIR/config.toml (especially weather coordinates)."
echo "2. Test: sudo -u $SERVICE_USER $APP_DIR/.venv/bin/pi-panel preview --output /tmp/pi-panel.png"
echo "3. Probe: sudo -u $SERVICE_USER $APP_DIR/.venv/bin/pi-panel probe-epaper"
echo "4. Enable: systemctl enable --now pi-environment-panel"
