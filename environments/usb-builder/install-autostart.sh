#!/bin/bash
# =============================================================================
# Install autostart for LLM Station on USB-booted system
# Run this ONCE after first boot from USB
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Installing LLM Station Autostart"
echo "=========================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Detect data directory
DATA_DIR=$(find /run/media -name "LLM_DATA" -type d 2>/dev/null | head -1)
if [ -z "$DATA_DIR" ]; then
    DATA_DIR="$SCRIPT_DIR/.."
fi

echo "Data directory: $DATA_DIR"

# Create symlink
echo "[1/4] Creating symlink..."
mkdir -p /opt
ln -sf "$DATA_DIR" /opt/llm-station

# Install systemd service
echo "[2/4] Installing systemd service..."
cp "$SCRIPT_DIR/systemd/llm-station.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable llm-station.service

# Create desktop shortcut
echo "[3/4] Creating desktop shortcuts..."
DESKTOP_DIR="/usr/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/llm-station.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LLM Station
Comment=Open LLM Chat Interface
Exec=xdg-open http://localhost:3000
Icon=applications-science
Terminal=false
Categories=Development;Science;
Keywords=AI;LLM;Chat;
EOF

cat > "$DESKTOP_DIR/llm-station-terminal.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LLM Station Terminal
Comment=Open LLM Station management terminal
Exec=gnome-terminal -- bash -c "cd /opt/llm-station && bash"
Icon=utilities-terminal
Terminal=false
Categories=Development;
EOF

# XDG autostart for GUI
echo "[4/4] Setting up XDG autostart..."
mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/llm-browser.desktop << EOF
[Desktop Entry]
Type=Application
Name=LLM Browser
Exec=sh -c "sleep 15 && xdg-open http://localhost:3000"
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

echo ""
echo "=========================================="
echo "Autostart installed!"
echo ""
echo "Services will start automatically on boot."
echo "Browser will open to http://localhost:3000"
echo ""
echo "Manual control:"
echo "  Start:  systemctl start llm-station"
echo "  Stop:   systemctl stop llm-station"
echo "  Status: systemctl status llm-station"
echo "=========================================="
