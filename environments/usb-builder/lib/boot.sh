#!/bin/bash
# =============================================================================
# Boot Configuration Library
# Source this file: source "$(dirname "$0")/lib/boot.sh"
# =============================================================================

# Requires common.sh to be sourced first
[ -z "$RED" ] && source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# =============================================================================
# First Boot Script Generation
# =============================================================================

# Generate first-boot.sh script
generate_first_boot_script() {
    local output_file="$1"
    
    cat > "$output_file" << 'FIRSTBOOT'
#!/bin/bash
# =============================================================================
# LLM Station First Boot Setup
# Run this after booting from the ISO/USB
# =============================================================================

set -e

echo "=========================================="
echo "LLM Station First Boot Setup"
echo "=========================================="

# Find LLM data directory
LLM_DATA=""
for search_path in /run/media /media /cdrom; do
    found=$(find "$search_path" -name "llm-data" -type d 2>/dev/null | head -1)
    if [ -n "$found" ]; then
        LLM_DATA="$found"
        break
    fi
done

if [ -z "$LLM_DATA" ]; then
    echo "Error: Could not find llm-data directory"
    echo "Make sure you booted from the LLM Station ISO/USB"
    exit 1
fi

echo "LLM Data: $LLM_DATA"

# Detect distro
if [ -f /etc/fedora-release ]; then
    PKG_MGR="dnf"
elif [ -f /etc/debian_version ]; then
    PKG_MGR="apt"
else
    PKG_MGR="unknown"
fi

echo ""
echo "[1/5] Installing dependencies..."
case $PKG_MGR in
    dnf)
        dnf install -y podman podman-compose firefox || true
        # ROCm (if AMD GPU)
        if lspci | grep -qi "AMD.*VGA\|AMD.*Display"; then
            dnf install -y rocm-hip-runtime 2>/dev/null || true
        fi
        ;;
    apt)
        apt-get update
        apt-get install -y podman podman-compose firefox || true
        ;;
    *)
        echo "Unknown package manager, skipping dependency installation"
        ;;
esac

echo ""
echo "[2/5] Configuring user..."
# Add user to video group for GPU access
usermod -aG video $(logname 2>/dev/null || echo $SUDO_USER) 2>/dev/null || true

echo ""
echo "[3/5] Loading container images..."
if [ -d "$LLM_DATA/images" ]; then
    for img in "$LLM_DATA/images"/*.tar; do
        if [ -f "$img" ]; then
            echo "  Loading: $(basename $img)"
            podman load -i "$img" 2>/dev/null || docker load -i "$img" 2>/dev/null || true
        fi
    done
else
    echo "  No cached images found"
fi

echo ""
echo "[4/5] Setting up environment..."
mkdir -p /opt
ln -sf "$LLM_DATA/environments" /opt/llm-station 2>/dev/null || true

echo ""
echo "[5/5] Creating desktop shortcuts..."
mkdir -p /usr/share/applications

# LLM Station launcher
cat > /usr/share/applications/llm-station.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LLM Station
Comment=Start LLM Chat Interface
Exec=sh -c "cd /opt/llm-station/ollama-webui && ./start.sh && sleep 5 && xdg-open http://localhost:3000"
Icon=applications-science
Terminal=false
Categories=Development;
EOF

# llama.cpp launcher
cat > /usr/share/applications/llama-cpp.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=llama.cpp Server
Comment=Start llama.cpp with ROCm
Exec=sh -c "cd /opt/llm-station/llama-cpp-rocm && ./start.sh"
Icon=utilities-terminal
Terminal=true
Categories=Development;
EOF

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "To start LLM Station:"
echo "  cd /opt/llm-station/ollama-webui && ./start.sh"
echo ""
echo "Then open: http://localhost:3000"
echo "=========================================="
FIRSTBOOT

    chmod +x "$output_file"
}

# =============================================================================
# Autostart Configuration
# =============================================================================

# Generate autostart desktop file
generate_autostart_desktop() {
    local output_file="$1"
    local script_path="${2:-/cdrom/llm-data/autorun.sh}"
    
    cat > "$output_file" << EOF
[Desktop Entry]
Type=Application
Name=LLM Station Autostart
Exec=sh -c "sleep 10 && $script_path"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
}

# Generate autorun script
generate_autorun_script() {
    local output_file="$1"
    
    cat > "$output_file" << 'AUTORUN'
#!/bin/bash
# LLM Station Autorun Script

# Check if first-boot was run
if [ ! -d /opt/llm-station ]; then
    # Show notification
    notify-send "LLM Station" "First boot setup required. Run: sudo /cdrom/llm-data/first-boot.sh" 2>/dev/null || true
    exit 0
fi

# Start Ollama + WebUI
cd /opt/llm-station/ollama-webui
./start.sh &

# Wait for services
sleep 10

# Open browser
xdg-open http://localhost:3000 2>/dev/null || firefox http://localhost:3000 &
AUTORUN

    chmod +x "$output_file"
}

# =============================================================================
# GRUB Configuration
# =============================================================================

# Generate custom GRUB config additions
generate_grub_config() {
    local output_file="$1"
    
    cat > "$output_file" << 'GRUB'
# LLM Station GRUB additions

# Set default timeout
set timeout=10

# Custom menu entry for LLM Station
menuentry "LLM Station (AMD GPU)" {
    set gfxpayload=keep
    linux /vmlinuz root=live:CDLABEL=LLM_STATION rd.live.image quiet rhgb
    initrd /initrd.img
}
GRUB
}

# =============================================================================
# Systemd Services
# =============================================================================

# Generate systemd service for LLM Station
generate_systemd_service() {
    local output_file="$1"
    local service_name="${2:-llm-station}"
    
    cat > "$output_file" << EOF
[Unit]
Description=LLM Station Service
After=network.target

[Service]
Type=simple
User=root
Environment=HSA_OVERRIDE_GFX_VERSION=11.0.0
ExecStart=/opt/llm-station/ollama-webui/start.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
}
