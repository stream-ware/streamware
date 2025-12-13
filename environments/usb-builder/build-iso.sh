#!/bin/bash
# =============================================================================
# Build bootable ISO for LLM Station (UM790 Pro)
# Compatible with Balena Etcher, Rufus, dd
#
# Creates a custom ISO with:
# - Fedora/Ubuntu base system
# - Pre-installed ROCm drivers
# - Podman with pre-loaded container images
# - Pre-downloaded LLM models
# - Auto-start configuration
#
# CACHING: Downloads are cached in cache/ directory for reuse
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"
ISO_NAME="${ISO_NAME:-llm-station-um790pro.iso}"
DISTRO="${DISTRO:-fedora}"

echo "=========================================="
echo "LLM Station ISO Builder"
echo "=========================================="
echo "Cache directory: $CACHE_DIR"
echo "Output directory: $OUTPUT_DIR"

# Create cache and output directories
mkdir -p "$CACHE_DIR/iso" "$CACHE_DIR/images" "$OUTPUT_DIR"

# Check dependencies
check_deps() {
    local missing=()
    
    # Check for ISO creation tool
    local has_iso_tool=0
    for cmd in xorriso genisoimage mkisofs; do
        if command -v $cmd &> /dev/null; then
            has_iso_tool=1
            break
        fi
    done
    [ $has_iso_tool -eq 0 ] && missing+=("xorriso")
    
    # Check for extraction tool (prefer 7z)
    if ! command -v 7z &> /dev/null && ! command -v bsdtar &> /dev/null; then
        missing+=("p7zip-full")
    fi
    
    # Check for file command
    command -v file &> /dev/null || missing+=("file")
    
    if [ ${#missing[@]} -gt 0 ]; then
        echo "Installing missing tools: ${missing[*]}..."
        if [ -f /etc/fedora-release ]; then
            dnf install -y xorriso squashfs-tools p7zip p7zip-plugins file
        elif [ -f /etc/debian_version ]; then
            apt-get update
            apt-get install -y xorriso squashfs-tools p7zip-full file
        elif [ -f /etc/arch-release ]; then
            pacman -S --noconfirm xorriso squashfs-tools p7zip file
        else
            echo "Please install: xorriso squashfs-tools p7zip file"
            exit 1
        fi
    fi
}

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root"
    echo "Usage: sudo $0"
    exit 1
fi

check_deps

# Create working directories
WORK_DIR="/tmp/iso-builder-$$"
ISO_ROOT="$WORK_DIR/iso"
SQUASH_ROOT="$WORK_DIR/squashfs"

mkdir -p "$WORK_DIR" "$ISO_ROOT" "$SQUASH_ROOT"
trap "rm -rf $WORK_DIR" EXIT

echo ""
echo "[1/7] Checking base ISO cache..."

case $DISTRO in
    fedora)
        BASE_ISO_URL="https://download.fedoraproject.org/pub/fedora/linux/releases/40/Spins/x86_64/iso/Fedora-LXQt-Live-x86_64-40-1.14.iso"
        BASE_ISO_NAME="Fedora-LXQt-Live-x86_64-40-1.14.iso"
        ;;
    ubuntu)
        BASE_ISO_URL="https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso"
        BASE_ISO_NAME="ubuntu-24.04-desktop-amd64.iso"
        ;;
esac

# Use cached ISO if exists and is valid
CACHED_ISO="$CACHE_DIR/iso/$BASE_ISO_NAME"

verify_iso() {
    local iso="$1"
    # Check file exists and has reasonable size (> 500MB for live ISO)
    if [ ! -f "$iso" ]; then
        return 1
    fi
    local size=$(stat -c%s "$iso" 2>/dev/null || echo 0)
    if [ "$size" -lt 500000000 ]; then
        echo "  ⚠ ISO file too small (corrupted download?)"
        return 1
    fi
    # Quick check if ISO is readable
    if ! file "$iso" | grep -q "ISO 9660"; then
        echo "  ⚠ ISO file appears corrupted"
        return 1
    fi
    return 0
}

if [ -f "$CACHED_ISO" ] && verify_iso "$CACHED_ISO"; then
    ISO_SIZE=$(du -h "$CACHED_ISO" | cut -f1)
    echo "  ✓ Using cached ISO: $CACHED_ISO ($ISO_SIZE)"
    BASE_ISO="$CACHED_ISO"
else
    if [ -f "$CACHED_ISO" ]; then
        echo "  Removing corrupted cached ISO..."
        rm -f "$CACHED_ISO"
    fi
    echo "  Downloading base ISO (will be cached for future use)..."
    curl -L "$BASE_ISO_URL" -o "$CACHED_ISO" --progress-bar -C -
    BASE_ISO="$CACHED_ISO"
fi

echo ""
echo "[2/7] Extracting base ISO..."

# Use 7z or bsdtar if available (more reliable than mount)
if command -v 7z &> /dev/null; then
    echo "  Using 7z for extraction..."
    7z x -o"$ISO_ROOT" "$BASE_ISO" -y > /dev/null
elif command -v bsdtar &> /dev/null; then
    echo "  Using bsdtar for extraction..."
    bsdtar -xf "$BASE_ISO" -C "$ISO_ROOT"
else
    echo "  Using mount for extraction..."
    mkdir -p "$WORK_DIR/mnt"
    mount -o loop,ro "$BASE_ISO" "$WORK_DIR/mnt"
    cp -a "$WORK_DIR/mnt/." "$ISO_ROOT/"
    umount "$WORK_DIR/mnt"
fi

echo ""
echo "[3/7] Analyzing ISO structure..."

# Detect boot type (EFI vs BIOS)
BOOT_TYPE="unknown"
if [ -d "$ISO_ROOT/EFI" ]; then
    BOOT_TYPE="efi"
    echo "  Detected: EFI boot (GRUB)"
fi
if [ -d "$ISO_ROOT/isolinux" ]; then
    BOOT_TYPE="bios"
    echo "  Detected: BIOS boot (ISOLINUX)"
fi
if [ -d "$ISO_ROOT/EFI" ] && [ -d "$ISO_ROOT/isolinux" ]; then
    BOOT_TYPE="hybrid"
    echo "  Detected: Hybrid boot (EFI + BIOS)"
fi

# Find squashfs (Fedora uses LiveOS/squashfs.img)
SQUASH_FILE=""
for pattern in "LiveOS/squashfs.img" "casper/filesystem.squashfs" "live/filesystem.squashfs" "*.squashfs"; do
    found=$(find "$ISO_ROOT" -path "*$pattern" 2>/dev/null | head -1)
    if [ -n "$found" ]; then
        SQUASH_FILE="$found"
        break
    fi
done

if [ -n "$SQUASH_FILE" ]; then
    echo "  Squashfs: $SQUASH_FILE"
else
    echo "  No squashfs found - will add data as overlay"
fi

echo ""
echo "[4/7] Adding LLM Station files..."

# Create LLM data directory on ISO
LLM_DATA="$ISO_ROOT/llm-data"
mkdir -p "$LLM_DATA/environments"

# Copy environment configurations
cp -r "$ENV_DIR/ollama-webui" "$LLM_DATA/environments/"
cp -r "$ENV_DIR/llama-cpp-rocm" "$LLM_DATA/environments/"
cp -r "$SCRIPT_DIR" "$LLM_DATA/environments/usb-builder"

# Copy pre-downloaded models if they exist
if [ -d "$ENV_DIR/ollama-webui/models" ]; then
    echo "  Adding Ollama models..."
    cp -r "$ENV_DIR/ollama-webui/models" "$LLM_DATA/environments/ollama-webui/"
fi

if [ -d "$ENV_DIR/llama-cpp-rocm/models" ]; then
    echo "  Adding llama.cpp models..."
    cp -r "$ENV_DIR/llama-cpp-rocm/models" "$LLM_DATA/environments/llama-cpp-rocm/"
fi

# Copy pre-saved container images if they exist
if [ -d "$SCRIPT_DIR/cache/images" ]; then
    echo "  Adding container images..."
    mkdir -p "$LLM_DATA/images"
    cp -r "$SCRIPT_DIR/cache/images/"* "$LLM_DATA/images/"
fi

echo ""
echo "[5/7] Creating autostart configuration..."

# Create first-boot script
cat > "$LLM_DATA/first-boot.sh" << 'FIRSTBOOT'
#!/bin/bash
# LLM Station First Boot Setup

set -e

echo "=========================================="
echo "LLM Station First Boot Setup"
echo "=========================================="

# Find LLM data directory
LLM_DATA=$(find /run/media -name "llm-data" -type d 2>/dev/null | head -1)
if [ -z "$LLM_DATA" ]; then
    LLM_DATA=$(find /media -name "llm-data" -type d 2>/dev/null | head -1)
fi
if [ -z "$LLM_DATA" ]; then
    LLM_DATA="/cdrom/llm-data"
fi

echo "LLM Data: $LLM_DATA"

# Install dependencies
echo "[1/4] Installing dependencies..."
if [ -f /etc/fedora-release ]; then
    dnf install -y rocm-hip-runtime podman podman-compose firefox
elif [ -f /etc/debian_version ]; then
    apt-get update
    apt-get install -y rocm-hip-runtime podman podman-compose firefox
fi

# Add user to video group
echo "[2/4] Configuring user..."
usermod -aG video $(logname) 2>/dev/null || true

# Load container images
echo "[3/4] Loading container images..."
if [ -d "$LLM_DATA/images" ]; then
    for img in "$LLM_DATA/images"/*.tar; do
        [ -f "$img" ] && podman load -i "$img"
    done
fi

# Create symlink
echo "[4/4] Setting up environment..."
mkdir -p /opt
ln -sf "$LLM_DATA/environments" /opt/llm-station

# Create desktop shortcut
mkdir -p /usr/share/applications
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

echo ""
echo "=========================================="
echo "Setup complete! Reboot or run:"
echo "  cd /opt/llm-station/ollama-webui && ./start.sh"
echo "=========================================="
FIRSTBOOT
chmod +x "$LLM_DATA/first-boot.sh"

# Create autostart desktop file
cat > "$LLM_DATA/llm-autostart.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=LLM Station Autostart
Exec=sh -c "sleep 10 && /cdrom/llm-data/autorun.sh"
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
DESKTOP

# Create autorun script
cat > "$LLM_DATA/autorun.sh" << 'AUTORUN'
#!/bin/bash
# Auto-run on boot

LLM_DATA=$(dirname "$(readlink -f "$0")")

# Check if first boot setup was done
if [ ! -f /opt/llm-station ]; then
    # Show notification
    notify-send "LLM Station" "Run first-boot setup: sudo $LLM_DATA/first-boot.sh" 2>/dev/null || true
    exit 0
fi

# Start services
cd /opt/llm-station/ollama-webui
./start.sh &

# Wait and open browser
sleep 15
xdg-open http://localhost:3000 2>/dev/null || firefox http://localhost:3000 &
AUTORUN
chmod +x "$LLM_DATA/autorun.sh"

echo ""
echo "[6/7] Rebuilding ISO..."

# Calculate sizes
LLM_SIZE=$(du -sh "$LLM_DATA" | cut -f1)
echo "  LLM Data size: $LLM_SIZE"

# Create new ISO
ISO_OUTPUT="$OUTPUT_DIR/$ISO_NAME"

# Find EFI boot image (for Fedora/modern distros)
EFI_IMG=""
for efi_path in "images/efiboot.img" "boot/grub/efi.img" "EFI/BOOT/efiboot.img"; do
    if [ -f "$ISO_ROOT/$efi_path" ]; then
        EFI_IMG="$efi_path"
        break
    fi
done

echo "  Boot type: $BOOT_TYPE"
[ -n "$EFI_IMG" ] && echo "  EFI image: $EFI_IMG"

if command -v xorriso &> /dev/null; then
    echo "  Using xorriso..."
    
    if [ "$BOOT_TYPE" = "efi" ] || [ "$BOOT_TYPE" = "hybrid" ]; then
        # EFI boot (Fedora-style)
        if [ -n "$EFI_IMG" ]; then
            xorriso -as mkisofs \
                -o "$ISO_OUTPUT" \
                -R -J -joliet-long \
                -V "LLM_STATION" \
                -eltorito-alt-boot \
                -e "$EFI_IMG" \
                -no-emul-boot \
                -isohybrid-gpt-basdat \
                "$ISO_ROOT"
        else
            # Simple EFI without eltorito
            xorriso -as mkisofs \
                -o "$ISO_OUTPUT" \
                -R -J -joliet-long \
                -V "LLM_STATION" \
                "$ISO_ROOT"
        fi
    elif [ "$BOOT_TYPE" = "bios" ]; then
        # BIOS boot (isolinux)
        xorriso -as mkisofs \
            -o "$ISO_OUTPUT" \
            -R -J -joliet-long \
            -V "LLM_STATION" \
            -b isolinux/isolinux.bin \
            -c isolinux/boot.cat \
            -no-emul-boot \
            -boot-load-size 4 \
            -boot-info-table \
            "$ISO_ROOT"
    else
        # Unknown - create simple data ISO
        xorriso -as mkisofs \
            -o "$ISO_OUTPUT" \
            -R -J -joliet-long \
            -V "LLM_STATION" \
            "$ISO_ROOT"
    fi
elif command -v genisoimage &> /dev/null; then
    echo "  Using genisoimage..."
    genisoimage \
        -o "$ISO_OUTPUT" \
        -R -J -joliet-long \
        -V "LLM_STATION" \
        "$ISO_ROOT"
else
    echo "Error: No ISO creation tool found"
    exit 1
fi

# Make hybrid ISO (bootable on USB via dd)
if command -v isohybrid &> /dev/null; then
    echo "  Making ISO hybrid (USB bootable)..."
    isohybrid --uefi "$ISO_OUTPUT" 2>/dev/null || isohybrid "$ISO_OUTPUT" 2>/dev/null || true
fi

echo ""
echo "[7/7] Generating checksums..."
cd "$OUTPUT_DIR"
sha256sum "$ISO_NAME" > "${ISO_NAME}.sha256"
md5sum "$ISO_NAME" > "${ISO_NAME}.md5"

# Final size
ISO_SIZE=$(du -h "$ISO_OUTPUT" | cut -f1)

echo ""
echo "=========================================="
echo "ISO creation complete!"
echo ""
echo "Output: $ISO_OUTPUT"
echo "Size: $ISO_SIZE"
echo ""
echo "Checksums:"
cat "${ISO_NAME}.sha256"
echo ""
echo "To flash with Balena Etcher:"
echo "  1. Open Balena Etcher"
echo "  2. Select: $ISO_OUTPUT"
echo "  3. Select target USB drive"
echo "  4. Flash!"
echo ""
echo "After booting:"
echo "  sudo /cdrom/llm-data/first-boot.sh"
echo "=========================================="
