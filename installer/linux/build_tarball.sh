#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/linux"
TARBALL="$ROOT_DIR/mandatemind-agent-linux-x64.tar.gz"

echo "[MandateMind] Building Linux tarball..."

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/mandatemind-agent"

cp -r "$ROOT_DIR/mm_agent" "$BUILD_DIR/mandatemind-agent/"
cp "$ROOT_DIR/config.example.yaml" "$BUILD_DIR/mandatemind-agent/config.example.yaml"
cp "$ROOT_DIR/installer/linux/install.sh" "$BUILD_DIR/mandatemind-agent/install.sh"
cp "$ROOT_DIR/installer/linux/uninstall.sh" "$BUILD_DIR/mandatemind-agent/uninstall.sh"
cp "$ROOT_DIR/installer/linux/mandatemind-agent.service" "$BUILD_DIR/mandatemind-agent/mandatemind-agent.service"
cp "$ROOT_DIR/README.md" "$BUILD_DIR/mandatemind-agent/README.md"

chmod +x "$BUILD_DIR/mandatemind-agent/install.sh" "$BUILD_DIR/mandatemind-agent/uninstall.sh"

tar -C "$BUILD_DIR" -czf "$TARBALL" mandatemind-agent

echo "[MandateMind] Tarball created at: $TARBALL"
