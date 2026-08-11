#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo." >&2
  exit 1
fi

systemctl disable --now pi-environment-panel.service 2>/dev/null || true
rm -f /etc/systemd/system/pi-environment-panel.service
systemctl daemon-reload

echo "Service removed."
echo "Configuration and history were deliberately retained:"
echo "  /etc/pi-environment-panel"
echo "  /var/lib/pi-environment-panel"
echo "Application files remain at /opt/pi-environment-panel unless you remove them."
