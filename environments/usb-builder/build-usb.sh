#!/bin/bash
# =============================================================================
# Build bootable USB with Linux + Podman + LLM environments
# For UM790 Pro with Radeon 780M (RDNA3)
#
# This script creates a 64GB USB with:
# - Fedora/Ubuntu minimal system (boots to RAM)
# - ROCm drivers for AMD GPU
# - Podman with pre-pulled container images
# - Pre-downloaded LLM models
# - Auto-start graphical interface
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "USB Builder for UM790 Pro LLM Station"
echo "=========================================="

# Configuration
USB_SIZE_GB=64
DISTRO="${DISTRO:-fedora}"  # fedora or ubuntu

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root"
    echo "Usage: sudo $0 /dev/sdX"
    exit 1
fi

# Check USB device argument
if [ -z "$1" ]; then
    echo ""
    echo "Usage: sudo $0 /dev/sdX"
    echo ""
    echo "Available devices:"
    lsblk -d -o NAME,SIZE,MODEL | grep -v loop
    echo ""
    echo "⚠ WARNING: This will ERASE all data on the selected device!"
    exit 1
fi

USB_DEVICE="$1"

# Safety check
if [[ "$USB_DEVICE" == *"sda"* ]] || [[ "$USB_DEVICE" == *"nvme0n1"* ]]; then
    echo "⚠ ERROR: Refusing to write to what appears to be a system drive"
    exit 1
fi

# Confirm
echo ""
echo "Target device: $USB_DEVICE"
echo "Distribution: $DISTRO"
echo ""
lsblk "$USB_DEVICE"
echo ""
read -p "This will ERASE ALL DATA on $USB_DEVICE. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Create working directory
WORK_DIR="/tmp/usb-builder-$$"
mkdir -p "$WORK_DIR"
trap "rm -rf $WORK_DIR" EXIT

echo ""
echo "[1/8] Downloading base system..."

case $DISTRO in
    fedora)
        # Download Fedora IoT (optimized for edge devices)
        ISO_URL="https://download.fedoraproject.org/pub/fedora/linux/releases/40/Spins/x86_64/iso/Fedora-LXQt-Live-x86_64-40-1.14.iso"
        ISO_FILE="$WORK_DIR/fedora.iso"
        ;;
    ubuntu)
        # Download Ubuntu minimal
        ISO_URL="https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso"
        ISO_FILE="$WORK_DIR/ubuntu.iso"
        ;;
esac

if [ ! -f "$ISO_FILE" ]; then
    echo "Downloading ISO..."
    curl -L "$ISO_URL" -o "$ISO_FILE" --progress-bar
fi

echo ""
echo "[2/8] Writing base system to USB..."
dd if="$ISO_FILE" of="$USB_DEVICE" bs=4M status=progress conv=fsync

echo ""
echo "[3/8] Creating data partition..."
# Create additional partition for models/containers
parted "$USB_DEVICE" --script mkpart primary ext4 10GB 100%
DATA_PART="${USB_DEVICE}2"
[ -b "${USB_DEVICE}p2" ] && DATA_PART="${USB_DEVICE}p2"

mkfs.ext4 -L "LLM_DATA" "$DATA_PART"

echo ""
echo "[4/8] Mounting data partition..."
DATA_MOUNT="$WORK_DIR/data"
mkdir -p "$DATA_MOUNT"
mount "$DATA_PART" "$DATA_MOUNT"

echo ""
echo "[5/8] Copying environment files..."
mkdir -p "$DATA_MOUNT/environments"
cp -r "$ENV_DIR/ollama-webui" "$DATA_MOUNT/environments/"
cp -r "$ENV_DIR/llama-cpp-rocm" "$DATA_MOUNT/environments/"

echo ""
echo "[6/8] Creating autostart scripts..."

# Create setup script that runs on first boot
cat > "$DATA_MOUNT/setup-first-boot.sh" << 'FIRSTBOOT'
#!/bin/bash
# First boot setup script

# Install ROCm
if [ -f /etc/fedora-release ]; then
    dnf install -y rocm-hip-runtime podman podman-compose
elif [ -f /etc/lsb-release ]; then
    apt-get update
    apt-get install -y rocm-hip-runtime podman podman-compose
fi

# Add user to video group
usermod -aG video $(logname)

# Enable autostart
mkdir -p /etc/xdg/autostart
cp /run/media/$(logname)/LLM_DATA/llm-station.desktop /etc/xdg/autostart/
FIRSTBOOT
chmod +x "$DATA_MOUNT/setup-first-boot.sh"

# Create desktop autostart file
cat > "$DATA_MOUNT/llm-station.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=LLM Station
Comment=Start LLM services
Exec=/run/media/*/LLM_DATA/autostart.sh
Terminal=false
Categories=Development;
StartupNotify=false
DESKTOP

# Create autostart script
cat > "$DATA_MOUNT/autostart.sh" << 'AUTOSTART'
#!/bin/bash
# Auto-start LLM services

DATA_DIR=$(dirname "$(readlink -f "$0")")

# Wait for system to settle
sleep 5

# Check which environment to start
if [ -f "$DATA_DIR/.use-llama-cpp" ]; then
    cd "$DATA_DIR/environments/llama-cpp-rocm"
    ./start.sh &
else
    cd "$DATA_DIR/environments/ollama-webui"
    ./start.sh &
fi

# Wait for services
sleep 10

# Open browser
if command -v firefox &> /dev/null; then
    firefox http://localhost:3000 &
elif command -v chromium &> /dev/null; then
    chromium http://localhost:3000 &
fi
AUTOSTART
chmod +x "$DATA_MOUNT/autostart.sh"

echo ""
echo "[7/8] Checking for pre-downloaded models..."

# Copy models if they exist
if [ -d "$ENV_DIR/ollama-webui/models" ]; then
    echo "Copying Ollama models..."
    cp -r "$ENV_DIR/ollama-webui/models" "$DATA_MOUNT/environments/ollama-webui/"
fi

if [ -d "$ENV_DIR/llama-cpp-rocm/models" ]; then
    echo "Copying llama.cpp models..."
    cp -r "$ENV_DIR/llama-cpp-rocm/models" "$DATA_MOUNT/environments/llama-cpp-rocm/"
fi

echo ""
echo "[8/8] Finalizing..."
sync
umount "$DATA_MOUNT"

TOTAL_SIZE=$(lsblk -b -o SIZE "$USB_DEVICE" | tail -1)
TOTAL_GB=$((TOTAL_SIZE / 1024 / 1024 / 1024))

echo ""
echo "=========================================="
echo "USB creation complete!"
echo ""
echo "Device: $USB_DEVICE"
echo "Size: ${TOTAL_GB}GB"
echo ""
echo "Next steps:"
echo "1. Download models before use:"
echo "   cd environments/ollama-webui && ./download-models.sh"
echo "   cd environments/llama-cpp-rocm && ./download-models.sh"
echo ""
echo "2. Pull container images (while online):"
echo "   podman pull ollama/ollama:rocm"
echo "   podman pull ghcr.io/open-webui/open-webui:main"
echo ""
echo "3. Boot UM790 Pro from USB"
echo "4. Run first-boot setup: sudo /run/media/*/LLM_DATA/setup-first-boot.sh"
echo "=========================================="
