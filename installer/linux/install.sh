#!/usr/bin/env bash
set -euo pipefail

AGENT_SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_INSTALL_DIR="/opt/mandatemind-agent"
CONFIG_DIR="/etc/mandatemind"
DATA_DIR="/var/lib/mandatemind"
LOG_DIR="/var/log/mandatemind"
SYSTEMD_UNIT="/etc/systemd/system/mandatemind-agent.service"
AGENT_USER="mandatemind"

SITE_ID="${SITE_ID:-}"
API_TOKEN="${API_TOKEN:-}"

echo "[MandateMind] Linux installer starting..."

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: run as root or with sudo."
  exit 1
fi

id "$AGENT_USER" &>/dev/null || useradd \
  --system --no-create-home --shell /usr/sbin/nologin "$AGENT_USER"

mkdir -p "$AGENT_INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
chown -R root:root "$AGENT_INSTALL_DIR"
chown -R "$AGENT_USER":"$AGENT_USER" "$DATA_DIR" "$LOG_DIR"

cp -r "$AGENT_SRC_DIR/mm_agent" "$AGENT_INSTALL_DIR/"
cp "$AGENT_SRC_DIR/config.example.yaml" "$CONFIG_DIR/agent.conf"

if [[ -n "$SITE_ID" && -n "$API_TOKEN" ]]; then
  sed -i "s/YOUR_TENANT_ID/$SITE_ID/" "$CONFIG_DIR/agent.conf"
  sed -i "s/YOUR_AGENT_API_TOKEN/$API_TOKEN/" "$CONFIG_DIR/agent.conf"
fi

cp "$AGENT_SRC_DIR/installer/linux/mandatemind-agent.service" "$SYSTEMD_UNIT"

systemctl daemon-reload
systemctl enable mandatemind-agent
systemctl start mandatemind-agent

echo "[MandateMind] Installation complete."
systemctl status mandatemind-agent --no-pager || true
