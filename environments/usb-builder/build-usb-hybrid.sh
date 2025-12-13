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
        # Avoid division by zero
        if [ "$elapsed" -gt 0 ]; then
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

# Cache directory (must be set before config.sh uses it)
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"

# Distro selection (before loading config)
DISTRO="${DISTRO:-fedora}"

# Source config (loads BASE_ISO_* variables)
source "$SCRIPT_DIR/config.sh" 2>/dev/null || true

# Source ISO - use distro-specific or default
# Note: BASE_ISO_* variables are now loaded from config.sh
case "$DISTRO" in
    suse|opensuse)
        ISO_FILE="${ISO_FILE:-$CACHE_DIR/iso/${BASE_ISO_NAME_SUSE:-openSUSE-Tumbleweed-KDE-Live-x86_64-Current.iso}}"
        ISO_URL="${BASE_ISO_URL_SUSE:-https://download.opensuse.org/tumbleweed/iso/openSUSE-Tumbleweed-KDE-Live-x86_64-Current.iso}"
        ;;
    suse-leap)
        ISO_FILE="${ISO_FILE:-$CACHE_DIR/iso/${BASE_ISO_NAME_SUSE_LEAP:-openSUSE-Leap-15.5-KDE-Live-x86_64-Media.iso}}"
        ISO_URL="${BASE_ISO_URL_SUSE_LEAP:-https://download.opensuse.org/distribution/leap/15.5/live/openSUSE-Leap-15.5-KDE-Live-x86_64-Media.iso}"
        ;;
    ubuntu)
        ISO_FILE="${ISO_FILE:-$CACHE_DIR/iso/${BASE_ISO_NAME_UBUNTU:-ubuntu-24.04-desktop-amd64.iso}}"
        ISO_URL="${BASE_ISO_URL_UBUNTU:-https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso}"
        ;;
    fedora|*)
        ISO_FILE="${ISO_FILE:-$SCRIPT_DIR/output/llm-station-um790pro.iso}"
        ISO_URL="${BASE_ISO_URL_FEDORA:-https://download.fedoraproject.org/pub/fedora/linux/releases/40/Spins/x86_64/iso/Fedora-LXQt-Live-x86_64-40-1.14.iso}"
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
# Create autorun for desktop session (runs on first login)
# =============================================================================

log_info "Creating desktop autostart..."

# Create autostart directory for live user
mkdir -p "$MOUNT_LIVE/etc/skel/.config/autostart"

# Create desktop autostart entry
cat > "$MOUNT_LIVE/etc/skel/.config/autostart/llm-station-setup.desktop" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=LLM Station Setup
Comment=Automatically setup LLM Station on first boot
Exec=/usr/local/bin/llm-station-autorun.sh
Terminal=true
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
DESKTOP

# Create the autorun script on boot partition
mkdir -p "$MOUNT_LIVE/usr/local/bin"
cat > "$MOUNT_LIVE/usr/local/bin/llm-station-autorun.sh" << 'AUTORUN'
#!/bin/bash
# =============================================================================
# LLM Station Auto-Setup (runs on first login)
# =============================================================================

# Check if already installed
if [ -f /var/lib/llm-station-installed ]; then
    echo "LLM Station already installed."
    exit 0
fi

echo "=========================================="
echo "LLM Station First Boot Setup"
echo "=========================================="

# Find data partition
DATA_PART=""
for mount in /run/media/*/LLM-DATA /media/*/LLM-DATA; do
    if [ -d "$mount" ]; then
        DATA_PART="$mount"
        break
    fi
done

if [ -z "$DATA_PART" ]; then
    # Try to mount it
    DATA_DEV=$(lsblk -o NAME,LABEL -n | grep LLM-DATA | awk '{print $1}' | head -1)
    if [ -n "$DATA_DEV" ]; then
        mkdir -p /mnt/llm-data
        sudo mount "/dev/$DATA_DEV" /mnt/llm-data 2>/dev/null
        DATA_PART="/mnt/llm-data"
    fi
fi

if [ -z "$DATA_PART" ] || [ ! -d "$DATA_PART" ]; then
    echo "ERROR: Cannot find LLM-DATA partition"
    echo "Please mount it manually and run: $DATA_PART/install-service.sh"
    read -p "Press Enter to continue..."
    exit 1
fi

echo "Found data partition: $DATA_PART"

# Run install-service.sh
if [ -f "$DATA_PART/install-service.sh" ]; then
    echo "Installing LLM Station service..."
    sudo "$DATA_PART/install-service.sh"
    
    # Mark as installed
    sudo touch /var/lib/llm-station-installed
    
    echo ""
    echo "=========================================="
    echo "LLM Station installed successfully!"
    echo ""
    echo "Services:"
    echo "  Open-WebUI:  http://localhost:3000"
    echo "  Ollama API:  http://localhost:11434"
    echo "  Accounting:  http://localhost:8080"
    echo ""
    echo "Check status: sudo systemctl status llm-station"
    echo "=========================================="
else
    echo "ERROR: install-service.sh not found in $DATA_PART"
fi

read -p "Press Enter to close..."
AUTORUN

chmod +x "$MOUNT_LIVE/usr/local/bin/llm-station-autorun.sh"

# Also create rc.local fallback for non-desktop systems
cat > "$MOUNT_LIVE/etc/rc.local" << 'RCLOCAL'
#!/bin/bash
# LLM Station auto-setup on boot

# Skip if already installed
[ -f /var/lib/llm-station-installed ] && exit 0

# Find and mount data partition
DATA_DEV=$(lsblk -o NAME,LABEL -n | grep LLM-DATA | awk '{print $1}' | head -1)
if [ -n "$DATA_DEV" ]; then
    mkdir -p /opt/llm-data
    mount "/dev/$DATA_DEV" /opt/llm-data 2>/dev/null
    
    if [ -f /opt/llm-data/install-service.sh ]; then
        /opt/llm-data/install-service.sh
        touch /var/lib/llm-station-installed
    fi
fi

exit 0
RCLOCAL

chmod +x "$MOUNT_LIVE/etc/rc.local"

log_success "Desktop autostart created"

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

# =============================================================================
# Copy entire streamware project (development environment)
# =============================================================================

# Find project root (parent of environments/usb-builder)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -d "$PROJECT_ROOT/streamware" ] && [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    log_info "Copying streamware project (development mode)..."
    
    mkdir -p "$MOUNT_DATA/streamware"
    
    # Copy everything including .git (ignore .gitignore rules)
    # Use rsync with --no-exclude to copy all files
    rsync -a \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache/' \
        --exclude='*.egg-info/' \
        --exclude='dist/' \
        --exclude='build/' \
        --exclude='environments/usb-builder/cache/' \
        --exclude='environments/usb-builder/output/' \
        --exclude='*.iso' \
        "$PROJECT_ROOT/" "$MOUNT_DATA/streamware/" 2>/dev/null &
    
    RSYNC_PID=$!
    PROJECT_SIZE=$(du -sb "$PROJECT_ROOT" 2>/dev/null | cut -f1)
    START_TIME=$(date +%s)
    
    while kill -0 $RSYNC_PID 2>/dev/null; do
        CURRENT=$(du -sb "$MOUNT_DATA/streamware" 2>/dev/null | cut -f1)
        [ -z "$CURRENT" ] && CURRENT=0
        show_progress "Copying streamware" "$CURRENT" "$PROJECT_SIZE" "$START_TIME"
        sleep 1
    done
    wait $RSYNC_PID
    echo ""
    
    log_success "Streamware project copied (development mode)"
    
    # Create activation script
    cat > "$MOUNT_DATA/streamware/activate-dev.sh" << 'DEVSCRIPT'
#!/bin/bash
# Activate streamware development environment

cd "$(dirname "$0")"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate
source venv/bin/activate

# Install in development mode
pip install -e . 2>/dev/null

echo ""
echo "Streamware development environment activated!"
echo "Run: sq --help"
DEVSCRIPT
    chmod +x "$MOUNT_DATA/streamware/activate-dev.sh"
else
    log_warn "Streamware project root not found at $PROJECT_ROOT"
fi

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

log_info "Creating setup scripts (4 files)..."
printf "  [1/4] setup.sh..."

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

# Install streamware if not present
if ! command -v sq &> /dev/null; then
    echo "Installing streamware..."
    pip install streamware 2>/dev/null || pip3 install streamware 2>/dev/null || {
        echo "⚠ Could not install streamware. Install manually: pip install streamware"
    }
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "To start services manually:"
echo "  cd /opt/llm-station/ollama-webui && ./start.sh"
echo "  sq accounting web --project faktury --source camera"
echo ""
echo "Open: http://localhost:3000"
echo "=========================================="
SETUP

chmod +x "$MOUNT_DATA/setup.sh"
echo " done"
printf "  [2/4] README.md..."

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
# Create autostart service (systemd)
# =============================================================================

log_info "Creating autostart service..."

# Create systemd service file
cat > "$MOUNT_DATA/llm-station.service" << 'SERVICE'
[Unit]
Description=LLM Station Autostart
After=network.target graphical.target
Wants=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/llm-data/autostart.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Create autostart script
cat > "$MOUNT_DATA/autostart.sh" << 'AUTOSTART'
#!/bin/bash
# =============================================================================
# LLM Station Autostart Script
# This runs automatically on boot via systemd
# =============================================================================

LOG="/var/log/llm-station.log"
exec > >(tee -a "$LOG") 2>&1

echo "=========================================="
echo "LLM Station Autostart - $(date)"
echo "=========================================="

# Find and mount data partition
DATA_PART=""
for mount in /run/media/*/LLM-DATA /media/*/LLM-DATA /mnt/LLM-DATA /opt/llm-data; do
    if [ -d "$mount" ]; then
        DATA_PART="$mount"
        break
    fi
done

if [ -z "$DATA_PART" ]; then
    echo "Mounting data partition..."
    DATA_DEV=$(lsblk -o NAME,LABEL -n | grep LLM-DATA | awk '{print "/dev/"$1}')
    if [ -n "$DATA_DEV" ]; then
        mkdir -p /opt/llm-data
        mount "$DATA_DEV" /opt/llm-data
        DATA_PART="/opt/llm-data"
    else
        echo "ERROR: Cannot find LLM-DATA partition"
        exit 1
    fi
fi

echo "Data partition: $DATA_PART"

# Create symlinks
mkdir -p /opt
ln -sf "$DATA_PART/environments" /opt/llm-station 2>/dev/null || true

# Link Ollama models for all users
for home in /home/*; do
    if [ -d "$home" ]; then
        user=$(basename "$home")
        mkdir -p "$home/.ollama"
        ln -sf "$DATA_PART/models/ollama" "$home/.ollama/models" 2>/dev/null || true
        chown -R "$user:$user" "$home/.ollama" 2>/dev/null || true
    fi
done

# Load container images (if not already loaded)
if [ -d "$DATA_PART/images" ]; then
    for img in "$DATA_PART/images"/*.tar; do
        if [ -f "$img" ]; then
            imgname=$(basename "$img" .tar)
            if ! podman images | grep -q "$imgname" 2>/dev/null; then
                echo "Loading container: $imgname"
                podman load -i "$img" 2>/dev/null || docker load -i "$img" 2>/dev/null || true
            fi
        fi
    done
fi

# =============================================================================
# Install Python dependencies
# =============================================================================

echo "Setting up Python environment..."

# Install pip if missing
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    python3 -m ensurepip --upgrade 2>/dev/null || true
fi

# Install streamware from local project if available
if [ -d "$DATA_PART/streamware" ] && [ -f "$DATA_PART/streamware/pyproject.toml" ]; then
    echo "Installing streamware from local project..."
    cd "$DATA_PART/streamware"
    pip3 install -e . 2>/dev/null || pip3 install . 2>/dev/null || true
    cd -
elif ! command -v sq &> /dev/null; then
    echo "Installing streamware from PyPI..."
    pip3 install streamware 2>/dev/null || true
fi

# Install additional dependencies for accounting
pip3 install flask opencv-python pillow 2>/dev/null || true

# =============================================================================
# Install and start Ollama
# =============================================================================

echo "Setting up Ollama..."

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || {
        # Fallback: try snap or flatpak
        snap install ollama 2>/dev/null || flatpak install -y flathub com.ollama.Ollama 2>/dev/null || true
    }
fi

# Start Ollama service
if command -v ollama &> /dev/null; then
    echo "Starting Ollama..."
    # Kill existing if running
    pkill -f "ollama serve" 2>/dev/null || true
    sleep 1
    ollama serve &
    OLLAMA_PID=$!
    sleep 5
    
    # Pull default model if not present
    if ! ollama list 2>/dev/null | grep -q "llava"; then
        echo "Pulling llava model (this may take a while)..."
        ollama pull llava:7b &
    fi
fi

# =============================================================================
# Start Open-WebUI container
# =============================================================================

echo "Setting up Open-WebUI..."

# Check if podman or docker available
CONTAINER_CMD=""
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
fi

if [ -n "$CONTAINER_CMD" ]; then
    # Stop existing container
    $CONTAINER_CMD stop open-webui 2>/dev/null || true
    $CONTAINER_CMD rm open-webui 2>/dev/null || true
    
    # Start Open-WebUI
    echo "Starting Open-WebUI container..."
    $CONTAINER_CMD run -d --name open-webui \
        -p 3000:8080 \
        -e OLLAMA_BASE_URL=http://host.containers.internal:11434 \
        --add-host=host.containers.internal:host-gateway \
        ghcr.io/open-webui/open-webui:latest 2>/dev/null || {
            # Try with localhost if host.containers.internal fails
            $CONTAINER_CMD run -d --name open-webui \
                -p 3000:8080 \
                --network=host \
                -e OLLAMA_BASE_URL=http://localhost:11434 \
                ghcr.io/open-webui/open-webui:latest 2>/dev/null || true
        }
fi

# =============================================================================
# Start streamware accounting
# =============================================================================

echo "Starting streamware services..."

# Load configuration
if [ -f "$DATA_PART/config/accounting.conf" ]; then
    source "$DATA_PART/config/accounting.conf"
fi

PROJECT="${PROJECT:-faktury}"
SOURCE="${SOURCE:-camera}"
PORT="${PORT:-8080}"

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready!"
        break
    fi
    sleep 2
done

# Start streamware accounting web interface
if command -v sq &> /dev/null; then
    echo "Starting: sq accounting web --project $PROJECT --source $SOURCE --port $PORT"
    sq accounting web --project "$PROJECT" --source "$SOURCE" --port "$PORT" &
    SQ_PID=$!
    echo "Streamware accounting started (PID: $SQ_PID)"
else
    echo "WARNING: sq command not found. Install with: pip install streamware"
fi

echo ""
echo "=========================================="
echo "LLM Station started!"
echo "Open: http://localhost:3000"
echo "=========================================="
AUTOSTART

chmod +x "$MOUNT_DATA/autostart.sh"

# Create install-service script
cat > "$MOUNT_DATA/install-service.sh" << 'INSTALL'
#!/bin/bash
# Install LLM Station as systemd service for auto-start on boot

set -e

DATA_PART="$(cd "$(dirname "$0")" && pwd)"

echo "Installing LLM Station autostart service..."

# Copy service file
sudo cp "$DATA_PART/llm-station.service" /etc/systemd/system/

# Create symlink to data partition
sudo mkdir -p /opt/llm-data
sudo mount --bind "$DATA_PART" /opt/llm-data 2>/dev/null || true

# Add to fstab for persistent mount
PART_UUID=$(blkid -o value -s UUID "$(df "$DATA_PART" | tail -1 | awk '{print $1}')")
if ! grep -q "llm-data" /etc/fstab; then
    echo "UUID=$PART_UUID /opt/llm-data auto defaults,nofail 0 0" | sudo tee -a /etc/fstab
fi

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable llm-station.service
sudo systemctl start llm-station.service

echo ""
echo "✓ Service installed and started!"
echo "  Status: sudo systemctl status llm-station"
echo "  Logs:   sudo journalctl -u llm-station"
echo ""
echo "The service will start automatically on next boot."
INSTALL

chmod +x "$MOUNT_DATA/install-service.sh"

# Create accounting config
mkdir -p "$MOUNT_DATA/config"
cat > "$MOUNT_DATA/config/accounting.conf" << 'CONFIG'
# LLM Station Accounting Configuration
# Edit this file to customize autostart behavior

# Project name for accounting
PROJECT="faktury"

# Video source (camera, screen, or RTSP URL)
SOURCE="camera"

# Web interface port
PORT="8080"

# Enable TTS announcements
TTS_ENABLED="false"

# Ollama model for analysis
MODEL="llava:7b"
CONFIG

log_success "Autostart service created"

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
