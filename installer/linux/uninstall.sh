#!/usr/bin/env bash
set -euo pipefail

AGENT_INSTALL_DIR="/opt/mandatemind-agent"
CONFIG_DIR="/etc/mandatemind"
DATA_DIR="/var/lib/mandatemind"
LOG_DIR="/var/log/mandatemind"
SYSTEMD_UNIT="/etc/systemd/system/mandatemind-agent.service"
AGENT_USER="mandatemind"

echo "[MandateMind] Linux uninstaller starting..."

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: run as root or with sudo."
  exit 1
fi

systemctl stop mandatemind-agent || true
systemctl disable mandatemind-agent || true

rm -f "$SYSTEMD_UNIT"
systemctl daemon-reload

rm -rf "$AGENT_INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

userdel "$AGENT_USER" 2>/dev/null || true

echo "[MandateMind] Uninstallation complete."
