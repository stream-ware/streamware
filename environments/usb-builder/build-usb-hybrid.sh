#!/bin/bash
# =============================================================================
# Hybrid USB Builder - Two Partitions
# 
# Creates a USB drive with:
#   Partition 1: Bootable Linux Live system (~8GB)
#   Partition 2: Project data - models, configs, container images (rest of disk)
#
# Usage: sudo ./build-usb-hybrid.sh /dev/sdX
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }

# Progress bar function
# Usage: show_progress "message" current total [start_time]
show_progress() {
    local msg="$1"
    local current="$2"
    local total="$3"
    local start_time="${4:-}"
    
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))
    
    # Build progress bar
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    
    # Calculate ETA if start_time provided
    local eta=""
    if [ -n "$start_time" ] && [ "$current" -gt 0 ]; then
        local elapsed=$(($(date +%s) - start_time))
        local rate=$((current * 1000 / elapsed))  # bytes per second * 1000
        if [ "$rate" -gt 0 ]; then
            local remaining=$(((total - current) * 1000 / rate))
            if [ "$remaining" -gt 60 ]; then
                eta=" ETA: $((remaining / 60))m $((remaining % 60))s"
            else
                eta=" ETA: ${remaining}s"
            fi
        fi
    fi
    
    # Print progress
    printf "\r${BLUE}[INFO]${NC} %-30s [%s] %3d%%%s" "$msg" "$bar" "$percent" "$eta"
}

# Copy with progress
# Usage: copy_with_progress source dest description
copy_with_progress() {
    local src="$1"
    local dst="$2"
    local desc="$3"
    
    if [ ! -e "$src" ]; then
        log_warn "$desc: source not found"
        return 1
    fi
    
    # Get total size
    local total_size=$(du -sb "$src" 2>/dev/null | cut -f1)
    [ -z "$total_size" ] || [ "$total_size" -eq 0 ] && total_size=1
    
    local total_mb=$((total_size / 1024 / 1024))
    local start_time=$(date +%s)
    
    log_info "$desc (${total_mb}MB)..."
    
    # Use rsync with progress if available
    if command -v rsync &> /dev/null; then
        rsync -a --info=progress2 --no-inc-recursive \
            --exclude='*.iso' --exclude='cache/' --exclude='output/' \
            "$src" "$dst" 2>/dev/null | while read -r line; do
            # Parse rsync progress output
            if [[ "$line" =~ ([0-9]+)% ]]; then
                local pct="${BASH_REMATCH[1]}"
                local current=$((total_size * pct / 100))
                show_progress "$desc" "$current" "$total_size" "$start_time"
            fi
        done
        echo ""  # New line after progress
    else
        # Fallback to cp with periodic progress updates
        cp -r "$src" "$dst" &
        local pid=$!
        
        while kill -0 $pid 2>/dev/null; do
            local current_size=$(du -sb "$dst" 2>/dev/null | cut -f1)
            [ -z "$current_size" ] && current_size=0
            show_progress "$desc" "$current_size" "$total_size" "$start_time"
            sleep 1
        done
        
        wait $pid
        echo ""  # New line after progress
    fi
    
    local elapsed=$(($(date +%s) - start_time))
    local speed=$((total_size / 1024 / 1024 / (elapsed + 1)))
    log_success "$desc completed (${speed}MB/s)"
}

# Extract ISO with progress
extract_iso_with_progress() {
    local iso="$1"
    local dest="$2"
    
    local iso_size=$(stat -c%s "$iso" 2>/dev/null)
    local iso_mb=$((iso_size / 1024 / 1024))
    local start_time=$(date +%s)
    
    log_info "Extracting ISO (${iso_mb}MB)..."
    
    # Use 7z directly (most reliable)
    if command -v 7z &> /dev/null; then
        # Run 7z in background and monitor progress
        7z x -o"$dest" "$iso" -y > /dev/null 2>&1 &
        local pid=$!
        
        while kill -0 $pid 2>/dev/null; do
            local current=$(du -sb "$dest" 2>/dev/null | cut -f1)
            [ -z "$current" ] && current=0
            show_progress "Extracting" "$current" "$iso_size" "$start_time"
            sleep 1
        done
        wait $pid
        local exit_code=$?
        echo ""
        
        if [ $exit_code -ne 0 ]; then
            log_error "7z extraction failed with code $exit_code"
            return 1
        fi
    elif command -v bsdtar &> /dev/null; then
        bsdtar -xf "$iso" -C "$dest" 2>&1 &
        local pid=$!
        
        while kill -0 $pid 2>/dev/null; do
            local current=$(du -sb "$dest" 2>/dev/null | cut -f1)
            [ -z "$current" ] && current=0
            show_progress "Extracting" "$current" "$iso_size" "$start_time"
            sleep 1
        done
        wait $pid
        echo ""
    else
        # Mount and copy with progress
        local mnt=$(mktemp -d)
        mount -o loop,ro "$iso" "$mnt"
        
        local total=$(du -sb "$mnt" 2>/dev/null | cut -f1)
        cp -a "$mnt"/* "$dest/" &
        local pid=$!
        
        while kill -0 $pid 2>/dev/null; do
            local current=$(du -sb "$dest" 2>/dev/null | cut -f1)
            [ -z "$current" ] && current=0
            show_progress "Copying" "$current" "$total" "$start_time"
            sleep 1
        done
        wait $pid
        echo ""
        
        umount "$mnt"
        rmdir "$mnt"
    fi
    
    local elapsed=$(($(date +%s) - start_time))
    local speed=$((iso_size / 1024 / 1024 / (elapsed + 1)))
    log_success "ISO extracted (${elapsed}s, ${speed}MB/s)"
}

# =============================================================================
# Configuration
# =============================================================================

# Partition sizes
LIVE_PARTITION_SIZE="${LIVE_PARTITION_SIZE:-8G}"  # Linux Live system
# DATA partition uses remaining space

# Labels - IMPORTANT: LIVE_LABEL must match what GRUB expects!
# Fedora Live ISO expects the original volume label for dracut to find root
DATA_LABEL="LLM-DATA"

# Source config
source "$SCRIPT_DIR/config.sh" 2>/dev/null || true

# Distro selection
DISTRO="${DISTRO:-fedora}"

# Source ISO - use distro-specific or default
case "$DISTRO" in
    suse|opensuse)
        ISO_FILE="${ISO_FILE:-$CACHE_DIR/iso/$BASE_ISO_NAME_SUSE}"
        ISO_URL="$BASE_ISO_URL_SUSE"
        ;;
    suse-leap)
        ISO_FILE="${ISO_FILE:-$CACHE_DIR/iso/$BASE_ISO_NAME_SUSE_LEAP}"
        ISO_URL="$BASE_ISO_URL_SUSE_LEAP"
        ;;
    ubuntu)
        ISO_FILE="${ISO_FILE:-$CACHE_DIR/iso/$BASE_ISO_NAME_UBUNTU}"
        ISO_URL="$BASE_ISO_URL_UBUNTU"
        ;;
    fedora|*)
        ISO_FILE="${ISO_FILE:-$SCRIPT_DIR/output/llm-station-um790pro.iso}"
        ISO_URL="$BASE_ISO_URL_FEDORA"
        ;;
esac

log_info "Distro: $DISTRO"

# Get original volume label from ISO (required for boot)
get_iso_label() {
    local iso="$1"
    if command -v isoinfo &> /dev/null; then
        isoinfo -d -i "$iso" 2>/dev/null | grep "Volume id:" | cut -d':' -f2 | xargs
    else
        # Fallback - try to extract from ISO
        echo "Fedora-LXQt-Live-40-1-14"
    fi
}

# Will be set after ISO validation
LIVE_LABEL=""

# =============================================================================
# Validation
# =============================================================================

if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
    echo "Usage: sudo $0 /dev/sdX"
    exit 1
fi

USB_DEVICE="$1"

# Interactive device selection
select_usb_device() {
    echo ""
    echo "Available USB devices:"
    echo "─────────────────────────────────────────────────────────────────"
    printf "%-4s %-10s %-8s %-20s %-10s %s\n" "#" "DEVICE" "SIZE" "MODEL" "TRANSPORT" "MOUNTED"
    echo "─────────────────────────────────────────────────────────────────"
    
    # Build device list
    local devices=()
    local i=1
    
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        
        dev=$(echo "$line" | awk '{print $1}')
        size=$(echo "$line" | awk '{print $2}')
        model=$(echo "$line" | awk '{print $3}')
        tran=$(echo "$line" | awk '{print $4}')
        
        # Skip devices with 0 size
        [ "$size" = "0B" ] && continue
        
        # Check if any partition is mounted
        mounted=""
        if mount | grep -q "/dev/${dev}"; then
            mounted="YES ⚠"
        fi
        
        printf "%-4s %-10s %-8s %-20s %-10s %s\n" "[$i]" "/dev/$dev" "$size" "${model:0:18}" "$tran" "$mounted"
        
        devices[$i]="/dev/$dev"
        i=$((i + 1))
    done < <(lsblk -d -n -o NAME,SIZE,MODEL,TRAN 2>/dev/null | grep -v "loop\|sr0\|nvme\|sda" | head -10)
    
    echo "─────────────────────────────────────────────────────────────────"
    echo ""
    
    local count=$((i - 1))
    
    if [ $count -eq 0 ]; then
        log_error "No USB devices found!"
        echo ""
        echo "Make sure your USB drive is connected and try again."
        echo "If using a USB hub, try connecting directly to the computer."
        exit 1
    fi
    
    echo "Enter device number [1-$count] or 'q' to quit:"
    read -p "> " selection
    
    if [ "$selection" = "q" ] || [ "$selection" = "Q" ]; then
        echo "Aborted."
        exit 0
    fi
    
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt $count ]; then
        log_error "Invalid selection: $selection"
        exit 1
    fi
    
    USB_DEVICE="${devices[$selection]}"
    
    if [ -z "$USB_DEVICE" ]; then
        log_error "Failed to get device for selection $selection"
        exit 1
    fi
    
    echo ""
    log_info "Selected: $USB_DEVICE"
}

if [ -z "$USB_DEVICE" ]; then
    echo "=========================================="
    echo "Hybrid USB Builder"
    echo "=========================================="
    echo ""
    echo "This will create a dual-partition USB drive:"
    echo "  Partition 1: Bootable Linux Live ($LIVE_PARTITION_SIZE)"
    echo "  Partition 2: Project data, models (remaining space)"
    echo ""
    
    select_usb_device
fi

# Validate device
if [ ! -b "$USB_DEVICE" ]; then
    log_error "Device not found: $USB_DEVICE"
    exit 1
fi

# Safety check - don't format system drives
if echo "$USB_DEVICE" | grep -qE "^/dev/(sda|nvme0n1|vda)$"; then
    log_error "Refusing to format what looks like a system drive: $USB_DEVICE"
    log_error "If this is really a USB drive, specify the full path like /dev/sdb"
    exit 1
fi

# Check ISO exists, download if needed
if [ ! -f "$ISO_FILE" ]; then
    log_warn "ISO file not found: $ISO_FILE"
    
    if [ -n "$ISO_URL" ]; then
        log_info "Downloading $DISTRO ISO..."
        mkdir -p "$(dirname "$ISO_FILE")"
        
        if command -v curl &> /dev/null; then
            curl -L "$ISO_URL" -o "$ISO_FILE" --progress-bar
        elif command -v wget &> /dev/null; then
            wget "$ISO_URL" -O "$ISO_FILE" --show-progress
        else
            log_error "No download tool available (install curl or wget)"
            exit 1
        fi
        
        if [ ! -f "$ISO_FILE" ]; then
            log_error "Download failed"
            exit 1
        fi
        log_success "ISO downloaded: $ISO_FILE"
    else
        log_error "No ISO URL configured for distro: $DISTRO"
        echo "Build Fedora ISO first with: make iso-build"
        exit 1
    fi
fi

# Get volume label from ISO - needed to update GRUB config
ORIG_ISO_LABEL=$(get_iso_label "$ISO_FILE")
if [ -z "$ORIG_ISO_LABEL" ]; then
    ORIG_ISO_LABEL="Fedora-LXQt-Live-40-1-14"
fi

# FAT32 has 11 character limit for labels
# Use short label for partition, but we'll update GRUB config to match
LIVE_LABEL="INTELI-LIVE"
log_info "Original ISO label: $ORIG_ISO_LABEL"
log_info "Using FAT32 label: $LIVE_LABEL (will update GRUB config)"

# Get detailed device info
DEVICE_SIZE=$(lsblk -b -d -o SIZE "$USB_DEVICE" | tail -1)
DEVICE_SIZE_GB=$((DEVICE_SIZE / 1024 / 1024 / 1024))
DEVICE_SIZE_HUMAN=$(lsblk -d -o SIZE "$USB_DEVICE" | tail -1 | xargs)
DEVICE_MODEL=$(lsblk -d -o MODEL "$USB_DEVICE" | tail -1 | xargs)
DEVICE_VENDOR=$(lsblk -d -o VENDOR "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)
DEVICE_SERIAL=$(lsblk -d -o SERIAL "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)
DEVICE_TRAN=$(lsblk -d -o TRAN "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)

# Calculate partition sizes
LIVE_SIZE_NUM=$(echo "$LIVE_PARTITION_SIZE" | sed 's/G//')
DATA_SIZE_GB=$((DEVICE_SIZE_GB - LIVE_SIZE_NUM - 1))

# Get current partition info
echo ""
echo "=========================================="
echo "Hybrid USB Builder"
echo "=========================================="
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ DEVICE INFORMATION                                         │"
echo "├─────────────────────────────────────────────────────────────┤"
printf "│ %-15s %-43s │\n" "Device:" "$USB_DEVICE"
printf "│ %-15s %-43s │\n" "Size:" "$DEVICE_SIZE_HUMAN ($DEVICE_SIZE_GB GB)"
printf "│ %-15s %-43s │\n" "Vendor:" "${DEVICE_VENDOR:-Unknown}"
printf "│ %-15s %-43s │\n" "Model:" "${DEVICE_MODEL:-Unknown}"
printf "│ %-15s %-43s │\n" "Serial:" "${DEVICE_SERIAL:0:30}"
printf "│ %-15s %-43s │\n" "Transport:" "${DEVICE_TRAN:-Unknown}"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

# Show current partitions
echo "Current partitions on $USB_DEVICE:"
echo "─────────────────────────────────────────────────────────────────"
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT "$USB_DEVICE" 2>/dev/null || echo "  (no partitions)"
echo "─────────────────────────────────────────────────────────────────"
echo ""

echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ NEW PARTITION LAYOUT                                       │"
echo "├─────────────────────────────────────────────────────────────┤"
printf "│ %-3s %-12s %-10s %-30s │\n" "#" "LABEL" "SIZE" "CONTENTS"
echo "├─────────────────────────────────────────────────────────────┤"
printf "│ %-3s %-12s %-10s %-30s │\n" "1" "$LIVE_LABEL" "${LIVE_PARTITION_SIZE}" "Bootable Fedora Live (EFI)"
printf "│ %-3s %-12s %-10s %-30s │\n" "2" "$DATA_LABEL" "~${DATA_SIZE_GB}G" "Project data, models, images"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

echo -e "${RED}╔═════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  ⚠  WARNING: ALL DATA ON $USB_DEVICE WILL BE DESTROYED!        ║${NC}"
echo -e "${RED}╚═════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "To proceed, type the device name (e.g., 'sdc') to confirm:"
read -p "> " confirm

# Validate confirmation matches device
DEVICE_SHORT=$(basename "$USB_DEVICE")

if [ "$confirm" != "$DEVICE_SHORT" ]; then
    log_error "Confirmation does not match device name '$DEVICE_SHORT'"
    echo "Aborted."
    exit 1
fi

log_success "Confirmed: $USB_DEVICE"

echo ""

# =============================================================================
# Unmount existing partitions
# =============================================================================

log_info "Unmounting existing partitions..."
for part in ${USB_DEVICE}*; do
    umount "$part" 2>/dev/null || true
done

# =============================================================================
# Create partition table
# =============================================================================

log_info "Creating GPT partition table..."

# Wipe existing partition table
wipefs -a "$USB_DEVICE" >/dev/null 2>&1 || true

# Create GPT partition table with two partitions
parted -s "$USB_DEVICE" mklabel gpt

# Partition 1: EFI + Live system (8GB)
parted -s "$USB_DEVICE" mkpart primary fat32 1MiB "$LIVE_PARTITION_SIZE"
parted -s "$USB_DEVICE" set 1 boot on
parted -s "$USB_DEVICE" set 1 esp on

# Partition 2: Data (rest of disk)
parted -s "$USB_DEVICE" mkpart primary ext4 "$LIVE_PARTITION_SIZE" 100%

# Wait for kernel to recognize partitions
sleep 2
partprobe "$USB_DEVICE"
sleep 2

# Determine partition names (handles both /dev/sdX1 and /dev/nvme0n1p1 styles)
if [[ "$USB_DEVICE" == *"nvme"* ]] || [[ "$USB_DEVICE" == *"mmcblk"* ]]; then
    PART1="${USB_DEVICE}p1"
    PART2="${USB_DEVICE}p2"
else
    PART1="${USB_DEVICE}1"
    PART2="${USB_DEVICE}2"
fi

log_success "Partitions created: $PART1, $PART2"

# =============================================================================
# Format partitions
# =============================================================================

log_info "Formatting partition 1 (FAT32 for EFI)..."
mkfs.vfat -F 32 -n "$LIVE_LABEL" "$PART1"

log_info "Formatting partition 2 (ext4 for data)..."
mkfs.ext4 -L "$DATA_LABEL" -F "$PART2"

log_success "Partitions formatted"

# =============================================================================
# Mount partitions
# =============================================================================

MOUNT_LIVE=$(mktemp -d)
MOUNT_DATA=$(mktemp -d)

cleanup() {
    umount "$MOUNT_LIVE" 2>/dev/null || true
    umount "$MOUNT_DATA" 2>/dev/null || true
    rmdir "$MOUNT_LIVE" 2>/dev/null || true
    rmdir "$MOUNT_DATA" 2>/dev/null || true
}
trap cleanup EXIT

mount "$PART1" "$MOUNT_LIVE"
mount "$PART2" "$MOUNT_DATA"

log_success "Partitions mounted"

# =============================================================================
# Copy Live system
# =============================================================================

# Extract ISO with progress
extract_iso_with_progress "$ISO_FILE" "$MOUNT_LIVE"

# =============================================================================
# Update GRUB config to use new volume label
# =============================================================================

log_info "Updating GRUB configuration for new volume label..."

# Find and update GRUB config files
for grub_cfg in "$MOUNT_LIVE/EFI/BOOT/grub.cfg" "$MOUNT_LIVE/boot/grub2/grub.cfg" "$MOUNT_LIVE/boot/grub/grub.cfg"; do
    if [ -f "$grub_cfg" ]; then
        log_info "  Updating: $grub_cfg"
        # Replace old label with new label in GRUB config
        sed -i "s/CDLABEL=$ORIG_ISO_LABEL/CDLABEL=$LIVE_LABEL/g" "$grub_cfg"
        sed -i "s/LABEL=$ORIG_ISO_LABEL/LABEL=$LIVE_LABEL/g" "$grub_cfg"
        # Also handle URL-encoded versions (spaces as %20, etc)
        ORIG_ENCODED=$(echo "$ORIG_ISO_LABEL" | sed 's/ /%20/g; s/-/\\x2d/g')
        sed -i "s/$ORIG_ENCODED/$LIVE_LABEL/g" "$grub_cfg" 2>/dev/null || true
    fi
done

# Also update isolinux config if present
for syslinux_cfg in "$MOUNT_LIVE/isolinux/isolinux.cfg" "$MOUNT_LIVE/syslinux/syslinux.cfg"; do
    if [ -f "$syslinux_cfg" ]; then
        log_info "  Updating: $syslinux_cfg"
        sed -i "s/CDLABEL=$ORIG_ISO_LABEL/CDLABEL=$LIVE_LABEL/g" "$syslinux_cfg"
        sed -i "s/LABEL=$ORIG_ISO_LABEL/LABEL=$LIVE_LABEL/g" "$syslinux_cfg"
    fi
done

log_success "GRUB configuration updated"

# =============================================================================
# Copy project data
# =============================================================================

log_info "Copying project data to partition 2..."

# Create directory structure
mkdir -p "$MOUNT_DATA/environments"
mkdir -p "$MOUNT_DATA/models/ollama"
mkdir -p "$MOUNT_DATA/models/gguf"
mkdir -p "$MOUNT_DATA/images"

# Copy environments with progress
if [ -d "$ENV_DIR/ollama-webui" ]; then
    copy_with_progress "$ENV_DIR/ollama-webui/" "$MOUNT_DATA/environments/ollama-webui/" "ollama-webui"
fi

if [ -d "$ENV_DIR/llama-cpp-rocm" ]; then
    copy_with_progress "$ENV_DIR/llama-cpp-rocm/" "$MOUNT_DATA/environments/llama-cpp-rocm/" "llama-cpp-rocm"
fi

# Copy usb-builder (small, no progress needed)
log_info "Copying usb-builder..."
rsync -a --exclude='cache/' --exclude='output/' --exclude='*.iso' \
    "$SCRIPT_DIR/" "$MOUNT_DATA/environments/usb-builder/" 2>/dev/null || true
log_success "usb-builder copied"

# Copy container images if cached
if [ -d "$CACHE_DIR/images" ] && [ "$(ls -A $CACHE_DIR/images/*.tar 2>/dev/null)" ]; then
    copy_with_progress "$CACHE_DIR/images/" "$MOUNT_DATA/images/" "Container images"
fi

# Copy Ollama models if exist
OLLAMA_HOME="${OLLAMA_HOME:-$HOME/.ollama}"
if [ -d "$OLLAMA_HOME/models" ] && [ "$(ls -A $OLLAMA_HOME/models 2>/dev/null)" ]; then
    copy_with_progress "$OLLAMA_HOME/models/" "$MOUNT_DATA/models/ollama/" "Ollama models"
fi

# Copy GGUF models if exist
if [ -d "$ENV_DIR/llama-cpp-rocm/models" ] && [ "$(ls -A $ENV_DIR/llama-cpp-rocm/models/*.gguf 2>/dev/null)" ]; then
    copy_with_progress "$ENV_DIR/llama-cpp-rocm/models/" "$MOUNT_DATA/models/gguf/" "GGUF models"
fi

# Copy cached models
if [ -d "$CACHE_DIR/models" ] && [ "$(ls -A $CACHE_DIR/models/*.gguf 2>/dev/null)" ]; then
    copy_with_progress "$CACHE_DIR/models/" "$MOUNT_DATA/models/gguf/" "Cached models"
fi

# =============================================================================
# Create setup scripts on data partition
# =============================================================================

log_info "Creating setup scripts..."

cat > "$MOUNT_DATA/setup.sh" << 'SETUP'
#!/bin/bash
# =============================================================================
# LLM Station Setup Script
# Run this after booting from the USB
# =============================================================================

set -e

echo "=========================================="
echo "LLM Station Setup"
echo "=========================================="

# Find data partition
DATA_PART=""
for mount in /run/media/*/LLM-DATA /media/*/LLM-DATA /mnt/LLM-DATA; do
    if [ -d "$mount" ]; then
        DATA_PART="$mount"
        break
    fi
done

if [ -z "$DATA_PART" ]; then
    echo "Data partition not found. Mounting..."
    DATA_DEV=$(lsblk -o NAME,LABEL | grep LLM-DATA | awk '{print $1}')
    if [ -n "$DATA_DEV" ]; then
        mkdir -p /mnt/llm-data
        mount "/dev/$DATA_DEV" /mnt/llm-data
        DATA_PART="/mnt/llm-data"
    else
        echo "Error: Cannot find LLM-DATA partition"
        exit 1
    fi
fi

echo "Data partition: $DATA_PART"

# Create symlinks
echo "Creating symlinks..."
mkdir -p /opt
ln -sf "$DATA_PART/environments" /opt/llm-station

# Set up Ollama models
if [ -d "$DATA_PART/models/ollama" ]; then
    mkdir -p ~/.ollama
    ln -sf "$DATA_PART/models/ollama" ~/.ollama/models
    echo "✓ Ollama models linked"
fi

# Load container images
if [ -d "$DATA_PART/images" ]; then
    echo "Loading container images..."
    for img in "$DATA_PART/images"/*.tar; do
        [ -f "$img" ] && podman load -i "$img" 2>/dev/null || docker load -i "$img" 2>/dev/null || true
    done
    echo "✓ Container images loaded"
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "To start LLM Station:"
echo "  cd /opt/llm-station/ollama-webui && ./start.sh"
echo ""
echo "Open: http://localhost:3000"
echo "=========================================="
SETUP

chmod +x "$MOUNT_DATA/setup.sh"

# Create README
cat > "$MOUNT_DATA/README.md" << 'README'
# LLM Station Data Partition

This partition contains:
- `environments/` - LLM environment configurations
- `models/ollama/` - Ollama model files
- `models/gguf/` - GGUF models for llama.cpp
- `images/` - Container images (.tar)

## Quick Start

After booting from this USB:

```bash
# Run setup script
/run/media/$USER/LLM-DATA/setup.sh

# Start LLM Station
cd /opt/llm-station/ollama-webui
./start.sh
```

## Manual Setup

```bash
# Mount data partition (if not auto-mounted)
sudo mount /dev/sdX2 /mnt/llm-data

# Create symlink
sudo ln -s /mnt/llm-data/environments /opt/llm-station

# Link Ollama models
ln -s /mnt/llm-data/models/ollama ~/.ollama/models
```
README

log_success "Setup scripts created"

# =============================================================================
# Calculate sizes
# =============================================================================

LIVE_SIZE=$(du -sh "$MOUNT_LIVE" | cut -f1)
DATA_SIZE=$(du -sh "$MOUNT_DATA" | cut -f1)

# Sync and unmount
log_info "Syncing data..."
sync

echo ""
echo "=========================================="
echo "Hybrid USB creation complete!"
echo "=========================================="

# Ask to verify
echo ""
read -p "Run verification now? [Y/n]: " verify_now
if [ "$verify_now" != "n" ] && [ "$verify_now" != "N" ]; then
    echo ""
    "$SCRIPT_DIR/verify-usb.sh" "$USB_DEVICE"
fi

# Ask to test boot in QEMU
echo ""
read -p "Test boot in QEMU virtual machine? [y/N]: " test_boot
if [ "$test_boot" = "y" ] || [ "$test_boot" = "Y" ]; then
    echo ""
    log_info "Starting QEMU boot test..."
    echo "Controls: Ctrl+Alt+G (release mouse), Ctrl+Alt+Q (quit)"
    echo ""
    
    # Find OVMF
    OVMF=""
    for path in "/usr/share/OVMF/OVMF_CODE_4M.fd" "/usr/share/OVMF/OVMF_CODE.fd" "/usr/share/edk2/ovmf/OVMF_CODE.fd"; do
        [ -f "$path" ] && OVMF="$path" && break
    done
    
    if [ -n "$OVMF" ]; then
        qemu-system-x86_64 \
            -enable-kvm \
            -m 4G \
            -smp 2 \
            -drive file="$USB_DEVICE",format=raw,if=virtio \
            -drive if=pflash,format=raw,readonly=on,file="$OVMF" \
            -display gtk \
            -usb \
            -device usb-tablet
    else
        log_warn "OVMF not found, using BIOS mode..."
        qemu-system-x86_64 \
            -enable-kvm \
            -m 4G \
            -smp 2 \
            -drive file="$USB_DEVICE",format=raw,if=virtio \
            -display gtk
    fi
fi
echo ""
echo "Device: $USB_DEVICE"
echo ""
echo "Partition 1 ($LIVE_LABEL): $LIVE_SIZE"
echo "  - Bootable Fedora Live system"
echo "  - EFI boot enabled"
echo ""
echo "Partition 2 ($DATA_LABEL): $DATA_SIZE"
echo "  - Project environments"
echo "  - LLM models"
echo "  - Container images"
echo ""
echo "To use:"
echo "  1. Boot from USB (select UEFI boot)"
echo "  2. Run: /run/media/\$USER/LLM-DATA/setup.sh"
echo "  3. Start: cd /opt/llm-station/ollama-webui && ./start.sh"
echo "=========================================="
