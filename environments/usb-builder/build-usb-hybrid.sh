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

if [ -z "${BASH_VERSION:-}" ]; then
    exec /bin/bash "$0" "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# =============================================================================
# Cleanup and signal handling
# =============================================================================

CLEANUP_PIDS=()
MOUNT_LIVE=""
MOUNT_DATA=""

cleanup() {
    local exit_code=$?
    echo ""
    log_warn "Cleaning up..."
    
    # Kill any background processes we started
    for pid in "${CLEANUP_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    
    # Unmount if mounted
    if [ -n "$MOUNT_LIVE" ] && mountpoint -q "$MOUNT_LIVE" 2>/dev/null; then
        umount "$MOUNT_LIVE" 2>/dev/null || true
    fi
    if [ -n "$MOUNT_DATA" ] && mountpoint -q "$MOUNT_DATA" 2>/dev/null; then
        umount "$MOUNT_DATA" 2>/dev/null || true
    fi
    
    # Remove temp directories
    [ -n "$MOUNT_LIVE" ] && [ -d "$MOUNT_LIVE" ] && rmdir "$MOUNT_LIVE" 2>/dev/null || true
    [ -n "$MOUNT_DATA" ] && [ -d "$MOUNT_DATA" ] && rmdir "$MOUNT_DATA" 2>/dev/null || true
    
    if [ $exit_code -ne 0 ]; then
        log_error "Script interrupted or failed (exit code: $exit_code)"
    fi
    exit $exit_code
}

trap cleanup EXIT INT TERM

# Run command with spinner (for commands without progress info)
# Usage: run_with_spinner "description" command [args...]
run_with_spinner() {
    local desc="$1"
    shift
    local spin='|/-\\'
    local i=0
    local start_time=$(date +%s)
    
    # Run command in background
    "$@" &
    local pid=$!
    CLEANUP_PIDS+=("$pid")
    
    # Show spinner while running
    while kill -0 "$pid" 2>/dev/null; do
        local elapsed=$(($(date +%s) - start_time))
        i=$(((i + 1) % 4))
        printf "\r${BLUE}[INFO]${NC} %s %s (%ds)" "$desc" "${spin:$i:1}" "$elapsed"
        sleep 0.2
    done
    
    # Get exit status
    wait "$pid"
    local status=$?
    
    # Remove from cleanup list
    CLEANUP_PIDS=("${CLEANUP_PIDS[@]/$pid}")
    
    local elapsed=$(($(date +%s) - start_time))
    if [ $status -eq 0 ]; then
        printf "\r${GREEN}✓${NC} %s (completed in %ds)%s\n" "$desc" "$elapsed" "          "
    else
        printf "\r${RED}✗${NC} %s (failed after %ds)%s\n" "$desc" "$elapsed" "          "
        return $status
    fi
}

# Run command with timeout and spinner
# Usage: run_with_timeout timeout_sec "description" command [args...]
run_with_timeout() {
    local timeout="$1"
    local desc="$2"
    shift 2
    local spin='|/-\\'
    local i=0
    local start_time=$(date +%s)
    
    # Run command in background
    "$@" &
    local pid=$!
    CLEANUP_PIDS+=("$pid")
    
    # Show spinner while running, check timeout
    while kill -0 "$pid" 2>/dev/null; do
        local elapsed=$(($(date +%s) - start_time))
        if [ "$elapsed" -ge "$timeout" ]; then
            kill "$pid" 2>/dev/null || true
            printf "\r${RED}✗${NC} %s (TIMEOUT after %ds)%s\n" "$desc" "$elapsed" "          "
            CLEANUP_PIDS=("${CLEANUP_PIDS[@]/$pid}")
            return 124
        fi
        i=$(((i + 1) % 4))
        printf "\r${BLUE}[INFO]${NC} %s %s (%ds/%ds)" "$desc" "${spin:$i:1}" "$elapsed" "$timeout"
        sleep 0.2
    done
    
    wait "$pid"
    local status=$?
    CLEANUP_PIDS=("${CLEANUP_PIDS[@]/$pid}")
    
    local elapsed=$(($(date +%s) - start_time))
    if [ $status -eq 0 ]; then
        printf "\r${GREEN}✓${NC} %s (completed in %ds)%s\n" "$desc" "$elapsed" "          "
    else
        printf "\r${RED}✗${NC} %s (failed after %ds)%s\n" "$desc" "$elapsed" "          "
        return $status
    fi
}
ENV_DIR="$(dirname "$SCRIPT_DIR")"
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"

# Colors (define early for cleanup function)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }

mkdir -p "$CACHE_DIR/tmp"
export TMPDIR="$CACHE_DIR/tmp"

# Timing helper - returns elapsed time in human readable format
format_duration() {
    local seconds=$1
    if [ "$seconds" -ge 60 ]; then
        printf "%dm %ds" $((seconds / 60)) $((seconds % 60))
    else
        printf "%ds" "$seconds"
    fi
}

# Log with timing
log_timed() {
    local start=$1
    local msg=$2
    local elapsed=$(($(date +%s) - start))
    echo -e "${GREEN}✓${NC} $msg ($(format_duration $elapsed))"
}

# Global script start time
SCRIPT_START_TIME=$(date +%s)

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
    local i=0
    while [ "$i" -lt "$filled" ]; do
        bar="${bar}█"
        i=$((i + 1))
    done
    i=0
    while [ "$i" -lt "$empty" ]; do
        bar="${bar}░"
        i=$((i + 1))
    done
    
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
        mkdir -p "$CACHE_DIR/tmp"
        local mnt=$(mktemp -d -p "$CACHE_DIR/tmp")
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

STEP_START=$(date +%s)
log_info "Unmounting existing partitions..."
for part in ${USB_DEVICE}*; do
    umount "$part" >/dev/null 2>&1 || true
    umount -l "$part" >/dev/null 2>&1 || true
done

# Kill any processes using the device (suppress output)
fuser -k "${USB_DEVICE}" >/dev/null 2>&1 || true
fuser -k "${USB_DEVICE}1" >/dev/null 2>&1 || true
fuser -k "${USB_DEVICE}2" >/dev/null 2>&1 || true
sleep 2

# Check if device is still busy
if lsof "${USB_DEVICE}" >/dev/null 2>&1; then
    log_error "Device $USB_DEVICE is still in use!"
    log_error "Processes using device:"
    lsof "${USB_DEVICE}"* 2>/dev/null | head -5
    log_error ""
    log_error "Please unplug and replug the USB drive, then try again."
    exit 1
fi

log_timed $STEP_START "Partitions unmounted"

# =============================================================================
# Create partition table
# =============================================================================

STEP_START=$(date +%s)
log_info "Creating GPT partition table..."

# Wipe existing partition table
log_info "  Wiping existing partition table..."
if ! wipefs -af "$USB_DEVICE" 2>&1; then
    log_warn "wipefs failed, trying dd..."
    dd if=/dev/zero of="$USB_DEVICE" bs=1M count=10 status=none 2>/dev/null || true
fi
sync
sleep 1

# Create GPT partition table with two partitions
log_info "  Creating GPT label..."

# Use timeout to prevent hanging
if ! timeout 30 parted -s "$USB_DEVICE" mklabel gpt 2>&1; then
    log_error "Failed to create GPT partition table (timeout or error)"
    log_error ""
    log_error "The device may be stuck. Try:"
    log_error "  1. Unplug and replug the USB drive"
    log_error "  2. Run: sudo kill -9 \$(pgrep -f 'parted.*$USB_DEVICE')"
    log_error "  3. Try again: make usb-hybrid"
    exit 1
fi

log_info "  Creating partition 1 (Live system, ${LIVE_PARTITION_SIZE})..."
parted -s "$USB_DEVICE" mkpart primary fat32 1MiB "$LIVE_PARTITION_SIZE" >/dev/null 2>&1
parted -s "$USB_DEVICE" set 1 boot on >/dev/null 2>&1
parted -s "$USB_DEVICE" set 1 esp on >/dev/null 2>&1

log_info "  Creating partition 2 (Data, remaining space)..."
parted -s "$USB_DEVICE" mkpart primary ext4 "$LIVE_PARTITION_SIZE" 100% >/dev/null 2>&1

# Wait for kernel to recognize partitions
log_info "  Syncing and waiting for kernel..."
sync
partprobe "$USB_DEVICE" >/dev/null 2>&1 || true
sleep 3

# Determine partition names (handles both /dev/sdX1 and /dev/nvme0n1p1 styles)
if [[ "$USB_DEVICE" == *"nvme"* ]] || [[ "$USB_DEVICE" == *"mmcblk"* ]]; then
    PART1="${USB_DEVICE}p1"
    PART2="${USB_DEVICE}p2"
else
    PART1="${USB_DEVICE}1"
    PART2="${USB_DEVICE}2"
fi

log_timed $STEP_START "Partitions created: $PART1, $PART2"

# =============================================================================
# Format partitions
# =============================================================================

STEP_START=$(date +%s)
log_info "Waiting for kernel to recognize partitions..."
partprobe "$USB_DEVICE" >/dev/null 2>&1 || true
udevadm settle 2>/dev/null || true

for i in {1..20}; do
    if [ -b "$PART1" ] && [ -b "$PART2" ]; then
        break
    fi
    sleep 0.5
done

if [ ! -b "$PART1" ] || [ ! -b "$PART2" ]; then
    log_error "Partitions not ready: $PART1 or $PART2 not found"
    lsblk "$USB_DEVICE" 2>/dev/null || true
    exit 1
fi

umount "$PART1" 2>/dev/null || true
umount "$PART2" 2>/dev/null || true

MKFS_VFAT="mkfs.vfat"
if ! command -v mkfs.vfat &> /dev/null; then
    if command -v mkfs.fat &> /dev/null; then
        MKFS_VFAT="mkfs.fat"
    else
        log_error "mkfs.vfat not found (dosfstools). Please install dosfstools and re-run."
        if command -v dnf &> /dev/null; then
            log_error "  sudo dnf install -y dosfstools"
        elif command -v apt-get &> /dev/null; then
            log_error "  sudo apt-get install -y dosfstools"
        else
            log_error "  Install dosfstools using your distro's package manager"
        fi
        exit 1
    fi
fi

log_info "Formatting partition 1 (FAT32 for EFI)..."
if ! MKFS_OUT=$($MKFS_VFAT -F 32 -n "$LIVE_LABEL" "$PART1" 2>&1); then
    log_error "Failed to format $PART1 as FAT32"
    echo "$MKFS_OUT"
    exit 1
fi

log_info "Formatting partition 2 (ext4 for data)..."
if ! MKFS_OUT=$(mkfs.ext4 -L "$DATA_LABEL" -F "$PART2" 2>&1); then
    log_error "Failed to format $PART2 as ext4"
    echo "$MKFS_OUT"
    exit 1
fi

log_timed $STEP_START "Partitions formatted"

# =============================================================================
# Mount partitions
# =============================================================================

mkdir -p "$CACHE_DIR/tmp"
MOUNT_LIVE=$(mktemp -d -p "$CACHE_DIR/tmp")
MOUNT_DATA=$(mktemp -d -p "$CACHE_DIR/tmp")

mount "$PART1" "$MOUNT_LIVE"
mount "$PART2" "$MOUNT_DATA"

log_success "Partitions mounted"

# Diagnostic: Show partition sizes
log_info "Partition sizes:"
log_info "  Live partition ($PART1): $(df -h "$MOUNT_LIVE" | tail -1 | awk '{print $2 " total, " $4 " available"}')"
log_info "  Data partition ($PART2): $(df -h "$MOUNT_DATA" | tail -1 | awk '{print $2 " total, " $4 " available"}')"

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
        LIVE_OVERLAY_ARGS="rd.live.overlay=LABEL=$DATA_LABEL:/LiveOS/overlay rd.live.overlay.overlayfs=1 rd.live.overlay.nouserconfirmprompt"
        # Replace old label with new label in GRUB config
        sed -i "s/CDLABEL=$ORIG_ISO_LABEL/CDLABEL=$LIVE_LABEL/g" "$grub_cfg"
        sed -i "s/LABEL=$ORIG_ISO_LABEL/LABEL=$LIVE_LABEL/g" "$grub_cfg"
        # Also handle URL-encoded versions (spaces as %20, etc)
        ORIG_ENCODED=$(echo "$ORIG_ISO_LABEL" | sed 's/ /%20/g; s/-/\\x2d/g')
        sed -i "s/$ORIG_ENCODED/$LIVE_LABEL/g" "$grub_cfg" 2>/dev/null || true
        sed -i -E "/^[[:space:]]*(linux|linuxefi)[[:space:]]/ { /rd\\.live\\.image/ { /rd\\.live\\.overlay=/! s|$| $LIVE_OVERLAY_ARGS| } }" "$grub_cfg" 2>/dev/null || true
        sed -i 's/^set default="1"/set default="0"/' "$grub_cfg" 2>/dev/null || true
    fi
done

# Also update isolinux config if present
for syslinux_cfg in "$MOUNT_LIVE/isolinux/isolinux.cfg" "$MOUNT_LIVE/syslinux/syslinux.cfg"; do
    if [ -f "$syslinux_cfg" ]; then
        log_info "  Updating: $syslinux_cfg"
        sed -i "s/CDLABEL=$ORIG_ISO_LABEL/CDLABEL=$LIVE_LABEL/g" "$syslinux_cfg"
        sed -i "s/LABEL=$ORIG_ISO_LABEL/LABEL=$LIVE_LABEL/g" "$syslinux_cfg"
        LIVE_OVERLAY_ARGS="rd.live.overlay=LABEL=$DATA_LABEL:/LiveOS/overlay rd.live.overlay.overlayfs=1 rd.live.overlay.nouserconfirmprompt"
        sed -i -E "/^[[:space:]]*[Aa][Pp][Pp][Ee][Nn][Dd][[:space:]]/ { /rd\\.live\\.image/ { /rd\\.live\\.overlay=/! s|$| $LIVE_OVERLAY_ARGS| } }" "$syslinux_cfg" 2>/dev/null || true
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
    if [ "${ENABLE_OPENWEBUI:-true}" = "true" ]; then
        echo "  Open-WebUI:  http://localhost:3000"
    fi
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

STEP_START=$(date +%s)
log_info "Copying project data to partition 2..."

# Diagnostic: Show available space before copying
DATA_AVAIL_BEFORE=$(df -B1 --output=avail "$MOUNT_DATA" 2>/dev/null | tail -1)
log_info "Available space on data partition: $(numfmt --to=iec-i --suffix=B $DATA_AVAIL_BEFORE 2>/dev/null || echo "${DATA_AVAIL_BEFORE} bytes")"

# Create directory structure
mkdir -p "$MOUNT_DATA/environments"
mkdir -p "$MOUNT_DATA/models/ollama"
mkdir -p "$MOUNT_DATA/models/gguf"
mkdir -p "$MOUNT_DATA/images"
mkdir -p "$MOUNT_DATA/LiveOS/overlay"
mkdir -p "$MOUNT_DATA/LiveOS/ovlwork"

# Copy environments with progress
if [ -d "$ENV_DIR/ollama-webui" ]; then
    DIR_SIZE=$(du -sb "$ENV_DIR/ollama-webui" 2>/dev/null | cut -f1)
    log_info "  → ollama-webui: $(numfmt --to=iec-i --suffix=B $DIR_SIZE 2>/dev/null || echo "${DIR_SIZE} bytes")"
    copy_with_progress "$ENV_DIR/ollama-webui/" "$MOUNT_DATA/environments/ollama-webui/" "ollama-webui"
fi

if [ -d "$ENV_DIR/llama-cpp-rocm" ]; then
    DIR_SIZE=$(du -sb "$ENV_DIR/llama-cpp-rocm" 2>/dev/null | cut -f1)
    log_info "  → llama-cpp-rocm: $(numfmt --to=iec-i --suffix=B $DIR_SIZE 2>/dev/null || echo "${DIR_SIZE} bytes")"
    copy_with_progress "$ENV_DIR/llama-cpp-rocm/" "$MOUNT_DATA/environments/llama-cpp-rocm/" "llama-cpp-rocm"
fi

# Copy usb-builder (small, no progress needed)
DIR_SIZE=$(du -sb "$SCRIPT_DIR" --exclude='cache' --exclude='output' 2>/dev/null | cut -f1 || echo "0")
log_info "  → usb-builder: $(numfmt --to=iec-i --suffix=B $DIR_SIZE 2>/dev/null || echo "small")"
rsync -a --exclude='cache/' --exclude='output/' --exclude='*.iso' \
    "$SCRIPT_DIR/" "$MOUNT_DATA/environments/usb-builder/" 2>/dev/null || true
log_success "usb-builder copied"

# =============================================================================
# Copy entire streamware project (development environment)
# =============================================================================

# Find project root (parent of environments/usb-builder)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -d "$PROJECT_ROOT/streamware" ] && [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    PROJECT_SIZE=$(du -sb "$PROJECT_ROOT" \
        --exclude='__pycache__' \
        --exclude='.pytest_cache' \
        --exclude='environments/usb-builder/cache' \
        --exclude='environments/usb-builder/output' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='video' \
        --exclude='*.mp4' \
        --exclude='*.mkv' \
        --exclude='*.avi' \
        --exclude='*.mov' \
        --exclude='*.webm' \
        --exclude='dist' \
        --exclude='build' \
        2>/dev/null | cut -f1)
    log_info "  → streamware project: $(numfmt --to=iec-i --suffix=B $PROJECT_SIZE 2>/dev/null || echo "${PROJECT_SIZE} bytes")"
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
        --exclude='venv/' \
        --exclude='.venv/' \
        --exclude='video/' \
        --exclude='*.mp4' \
        --exclude='*.mkv' \
        --exclude='*.avi' \
        --exclude='*.mov' \
        --exclude='*.webm' \
        --exclude='environments/usb-builder/cache/' \
        --exclude='environments/usb-builder/output/' \
        --exclude='*.iso' \
        "$PROJECT_ROOT/" "$MOUNT_DATA/streamware/" 2>/dev/null &
    
    RSYNC_PID=$!
    PROJECT_SIZE=$(du -sb "$PROJECT_ROOT" \
        --exclude='__pycache__' \
        --exclude='.pytest_cache' \
        --exclude='environments/usb-builder/cache' \
        --exclude='environments/usb-builder/output' \
        --exclude='venv' \
        --exclude='.venv' \
        --exclude='video' \
        --exclude='*.mp4' \
        --exclude='*.mkv' \
        --exclude='*.avi' \
        --exclude='*.mov' \
        --exclude='*.webm' \
        --exclude='dist' \
        --exclude='build' \
        2>/dev/null | cut -f1)
    START_TIME=$(date +%s)
    
    while kill -0 $RSYNC_PID 2>/dev/null; do
        CURRENT=$(du -sb "$MOUNT_DATA/streamware" 2>/dev/null | cut -f1)
        [ -z "$CURRENT" ] && CURRENT=0
        show_progress "Copying streamware" "$CURRENT" "$PROJECT_SIZE" "$START_TIME"
        sleep 1
    done
    wait $RSYNC_PID
    echo ""
    
    log_timed $STEP_START "Streamware project copied (development mode)"
    
    # Copy .env file if exists (contains camera and scanner configuration)
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_info "Copying .env configuration..."
        mkdir -p "$MOUNT_DATA/config"
        cp "$PROJECT_ROOT/.env" "$MOUNT_DATA/config/.env"
        # Also copy to streamware directory for development mode
        cp "$PROJECT_ROOT/.env" "$MOUNT_DATA/streamware/.env"
        log_success ".env configuration copied"
    fi
    
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
python -m pip install -e . 2>/dev/null

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
    IMAGES_SIZE=$(du -sb "$CACHE_DIR/images" 2>/dev/null | cut -f1)
    log_info "  → container images: $(numfmt --to=iec-i --suffix=B $IMAGES_SIZE 2>/dev/null || echo "${IMAGES_SIZE} bytes")"

    for image_tar in "$CACHE_DIR/images/"*.tar; do
        [ -f "$image_tar" ] || continue
        tar_base=$(basename "$image_tar")

        if [ "$tar_base" = "open-webui.tar" ]; then
            continue
        fi

        IMAGE_SIZE_BYTES=$(stat -c%s "$image_tar" 2>/dev/null || echo 0)
        DATA_AVAIL_NOW=$(df -B1 --output=avail "$MOUNT_DATA" 2>/dev/null | tail -1 | tr -d ' ')
        [ -z "$DATA_AVAIL_NOW" ] && DATA_AVAIL_NOW=0

        IMAGE_REQUIRED_BYTES=$((IMAGE_SIZE_BYTES + 104857600))
        if [ "$DATA_AVAIL_NOW" -lt "$IMAGE_REQUIRED_BYTES" ]; then
            IMAGE_REQUIRED_HUMAN=$(numfmt --to=iec-i --suffix=B "$IMAGE_REQUIRED_BYTES" 2>/dev/null || echo "${IMAGE_REQUIRED_BYTES} bytes")
            DATA_AVAIL_HUMAN=$(numfmt --to=iec-i --suffix=B "$DATA_AVAIL_NOW" 2>/dev/null || echo "${DATA_AVAIL_NOW} bytes")
            log_warn "Skipping container image $tar_base (need $IMAGE_REQUIRED_HUMAN, have $DATA_AVAIL_HUMAN)"
            continue
        fi

        copy_with_progress "$image_tar" "$MOUNT_DATA/images/" "Container image: $tar_base"
    done
fi

if [ "${ENABLE_OPENWEBUI:-true}" != "true" ]; then
    rm -f "$MOUNT_DATA/images/open-webui.tar" 2>/dev/null || true
    log_info "  (Open-WebUI disabled - removed open-webui.tar)"
fi

# Copy Ollama models if exist
OLLAMA_HOME="${OLLAMA_HOME:-$HOME/.ollama}"
if [ -d "$OLLAMA_HOME/models" ] && [ "$(ls -A $OLLAMA_HOME/models 2>/dev/null)" ]; then
    MODELS_SIZE=$(du -sb "$OLLAMA_HOME/models" 2>/dev/null | cut -f1)
    log_info "  → Ollama models: $(numfmt --to=iec-i --suffix=B $MODELS_SIZE 2>/dev/null || echo "${MODELS_SIZE} bytes")"
    copy_with_progress "$OLLAMA_HOME/models/" "$MOUNT_DATA/models/ollama/" "Ollama models"
fi

# Copy GGUF models if exist
if [ -d "$ENV_DIR/llama-cpp-rocm/models" ] && [ "$(ls -A $ENV_DIR/llama-cpp-rocm/models/*.gguf 2>/dev/null)" ]; then
    GGUF_SIZE=$(du -sb "$ENV_DIR/llama-cpp-rocm/models" 2>/dev/null | cut -f1)
    log_info "  → GGUF models: $(numfmt --to=iec-i --suffix=B $GGUF_SIZE 2>/dev/null || echo "${GGUF_SIZE} bytes")"
    copy_with_progress "$ENV_DIR/llama-cpp-rocm/models/" "$MOUNT_DATA/models/gguf/" "GGUF models"
fi

# Copy cached models
if [ -d "$CACHE_DIR/models" ] && [ "$(ls -A $CACHE_DIR/models/*.gguf 2>/dev/null)" ]; then
    CACHED_SIZE=$(du -sb "$CACHE_DIR/models" 2>/dev/null | cut -f1)
    log_info "  → cached models: $(numfmt --to=iec-i --suffix=B $CACHED_SIZE 2>/dev/null || echo "${CACHED_SIZE} bytes")"
    copy_with_progress "$CACHE_DIR/models/" "$MOUNT_DATA/models/gguf/" "Cached models"
fi

# Diagnostic: Show available space after copying data
DATA_AVAIL_AFTER=$(df -B1 --output=avail "$MOUNT_DATA" 2>/dev/null | tail -1)
DATA_USED=$((DATA_AVAIL_BEFORE - DATA_AVAIL_AFTER))
log_info "Space used for project data: $(numfmt --to=iec-i --suffix=B $DATA_USED 2>/dev/null || echo "${DATA_USED} bytes")"
log_info "Remaining space on data partition: $(numfmt --to=iec-i --suffix=B $DATA_AVAIL_AFTER 2>/dev/null || echo "${DATA_AVAIL_AFTER} bytes")"

# =============================================================================
# Download and copy Chromium AppImage for kiosk mode
# =============================================================================

CHROMIUM_APPIMAGE="$CACHE_DIR/chromium.AppImage"
CHROMIUM_URL="https://github.com/nicotine-plus/nicotine-plus/releases/download/3.3.0/nicotine-plus.AppImage"
# Use ungoogled-chromium AppImage
CHROMIUM_URL="https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/nicotine-plus.AppImage"

# Better: use a simple browser or just rely on Firefox which is in Fedora
log_info "Setting up browser for kiosk mode..."
mkdir -p "$MOUNT_DATA/bin"

# Create a wrapper script that finds and uses available browser
cat > "$MOUNT_DATA/bin/kiosk-browser.sh" << 'BROWSER_SCRIPT'
#!/bin/bash
# Kiosk browser wrapper - finds and launches available browser in fullscreen

URL="${1:-http://localhost:8080}"

# Find available browser (prefer Chromium/Chrome for better kiosk support)
if command -v chromium-browser &> /dev/null; then
    exec chromium-browser --start-fullscreen --disable-infobars --noerrdialogs \
        --disable-session-crashed-bubble --disable-restore-session-state "$URL"
elif command -v chromium &> /dev/null; then
    exec chromium --start-fullscreen --disable-infobars --noerrdialogs \
        --disable-session-crashed-bubble --disable-restore-session-state "$URL"
elif command -v google-chrome &> /dev/null; then
    exec google-chrome --start-fullscreen --disable-infobars --noerrdialogs \
        --disable-session-crashed-bubble --disable-restore-session-state "$URL"
elif command -v firefox &> /dev/null; then
    # Firefox kiosk mode (F11 to exit fullscreen)
    exec firefox --kiosk "$URL"
else
    echo "ERROR: No browser found!"
    echo "Install firefox or chromium:"
    echo "  sudo dnf install firefox    # Fedora"
    echo "  sudo apt install firefox    # Ubuntu/Debian"
    exit 1
fi
BROWSER_SCRIPT
chmod +x "$MOUNT_DATA/bin/kiosk-browser.sh"
log_success "Kiosk browser wrapper created"
# Pre-download Python dependencies for offline installation
# =============================================================================

log_info "Preparing Python dependencies for offline mode..."
mkdir -p "$MOUNT_DATA/pip-cache"

# Download wheel files for streamware and dependencies
if command -v pip3 &> /dev/null; then
    PIP_CACHE_PACKAGES=(
        pip
        streamware
        requests aiohttp pydantic rich PyYAML click jinja2 jsonpath-ng
        flask opencv-python-headless pillow numpy av
        setuptools wheel
    )

    run_with_timeout 300 "Downloading pip packages (host Python)" \
        pip3 download -d "$MOUNT_DATA/pip-cache" "${PIP_CACHE_PACKAGES[@]}" \
        || log_warn "Some packages may not have been downloaded"

    run_with_timeout 600 "Downloading pip packages (Fedora Live Python 3.12)" \
        pip3 download -d "$MOUNT_DATA/pip-cache" \
            --only-binary=:all: \
            --platform manylinux_2_28_x86_64 \
            --platform manylinux2014_x86_64 \
            --platform linux_x86_64 \
            --platform any \
            --implementation cp \
            --python-version 3.12 \
            --abi cp312 \
            --abi abi3 \
            --abi none \
            "${PIP_CACHE_PACKAGES[@]}" \
        || log_warn "Some Fedora Live (cp312) wheels may not have been downloaded"

    log_success "Pip packages cached for offline installation"
else
    log_warn "pip3 not available - skipping package cache"
fi

# =============================================================================
# Pre-download Ollama binary for offline installation
# =============================================================================

OLLAMA_ARCHIVE="$CACHE_DIR/ollama-linux-amd64.tgz"
if [ ! -f "$OLLAMA_ARCHIVE" ]; then
    mkdir -p "$CACHE_DIR"
    run_with_timeout 600 "Downloading Ollama archive (~150MB)" \
        curl -fsSL -o "$OLLAMA_ARCHIVE" \
            "https://ollama.com/download/ollama-linux-amd64.tgz" \
        || log_warn "Failed to download Ollama archive"
fi

if [ -f "$OLLAMA_ARCHIVE" ]; then
    log_info "Copying Ollama archive..."
    cp "$OLLAMA_ARCHIVE" "$MOUNT_DATA/bin/ollama-linux-amd64.tgz"
    log_success "Ollama archive copied"
fi

# =============================================================================
# Save Open-WebUI container image for offline use
# =============================================================================

if [ "${ENABLE_OPENWEBUI:-true}" = "true" ]; then
    OPENWEBUI_IMAGE="$CACHE_DIR/images/open-webui.tar"
    mkdir -p "$CACHE_DIR/images"

    if [ ! -f "$OPENWEBUI_IMAGE" ]; then
        if command -v podman &> /dev/null; then
            run_with_timeout 600 "Pulling Open-WebUI image (~1.5GB)" \
                podman pull ghcr.io/open-webui/open-webui:main && \
            run_with_spinner "Saving Open-WebUI image" \
                podman save -o "$OPENWEBUI_IMAGE" ghcr.io/open-webui/open-webui:main || \
            log_warn "Failed to save Open-WebUI image"
        elif command -v docker &> /dev/null; then
            run_with_timeout 600 "Pulling Open-WebUI image (~1.5GB)" \
                docker pull ghcr.io/open-webui/open-webui:main && \
            run_with_spinner "Saving Open-WebUI image" \
                docker save -o "$OPENWEBUI_IMAGE" ghcr.io/open-webui/open-webui:main || \
            log_warn "Failed to save Open-WebUI image"
        fi
    fi

    if [ -f "$OPENWEBUI_IMAGE" ]; then
        log_info "Copying Open-WebUI container image..."
        OPENWEBUI_SIZE_BYTES=$(stat -c%s "$OPENWEBUI_IMAGE" 2>/dev/null || echo 0)
        DATA_AVAIL_NOW=$(df -B1 --output=avail "$MOUNT_DATA" 2>/dev/null | tail -1 | tr -d ' ')
        [ -z "$DATA_AVAIL_NOW" ] && DATA_AVAIL_NOW=0
        OPENWEBUI_REQUIRED_BYTES=$((OPENWEBUI_SIZE_BYTES + 104857600))

        if [ "$DATA_AVAIL_NOW" -lt "$OPENWEBUI_REQUIRED_BYTES" ]; then
            OPENWEBUI_REQUIRED_HUMAN=$(numfmt --to=iec-i --suffix=B "$OPENWEBUI_REQUIRED_BYTES" 2>/dev/null || echo "${OPENWEBUI_REQUIRED_BYTES} bytes")
            DATA_AVAIL_HUMAN=$(numfmt --to=iec-i --suffix=B "$DATA_AVAIL_NOW" 2>/dev/null || echo "${DATA_AVAIL_NOW} bytes")
            log_warn "Not enough space for Open-WebUI image (need $OPENWEBUI_REQUIRED_HUMAN, have $DATA_AVAIL_HUMAN) - skipping"
        else
            if cp "$OPENWEBUI_IMAGE" "$MOUNT_DATA/images/open-webui.tar" 2>/dev/null; then
                log_success "Open-WebUI image copied"
            else
                log_warn "Failed to copy Open-WebUI image - continuing without it"
                rm -f "$MOUNT_DATA/images/open-webui.tar" 2>/dev/null || true
            fi
        fi
    fi
else
    log_info "Open-WebUI disabled (ENABLE_OPENWEBUI=false) - skipping image cache"
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

if [ "$EUID" -ne 0 ]; then
    if command -v sudo &> /dev/null; then
        exec sudo -E bash "$0" "$@"
    else
        echo "Error: This script must be run as root (sudo not found)"
        exit 1
    fi
fi

echo "=========================================="
echo "LLM Station Setup"
echo "=========================================="

# Find data partition
DATA_PART=""
for mount in /run/media/*/LLM-DATA /media/*/LLM-DATA /mnt/LLM-DATA /opt/llm-data; do
    if [ -d "$mount" ]; then
        DATA_PART="$mount"
        break
    fi
done

if [ -z "$DATA_PART" ]; then
    echo "Data partition not found. Mounting..."
    DATA_DEV=$(lsblk -o NAME,LABEL -n | grep LLM-DATA | awk '{print $1}' | head -n1)
    if [ -n "$DATA_DEV" ]; then
        mkdir -p /opt/llm-data
        mount "/dev/$DATA_DEV" /opt/llm-data
        DATA_PART="/opt/llm-data"
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

RUN_USER="${SUDO_USER:-$USER}"
RUN_HOME="$HOME"
if [ -n "$SUDO_USER" ] && [ -d "/home/$SUDO_USER" ]; then
    RUN_HOME="/home/$SUDO_USER"
fi

# Set up Ollama models
if [ -d "$DATA_PART/models/ollama" ]; then
    mkdir -p "$RUN_HOME/.ollama"
    ln -sf "$DATA_PART/models/ollama" "$RUN_HOME/.ollama/models"
    chown -R "$RUN_USER:$RUN_USER" "$RUN_HOME/.ollama" 2>/dev/null || true
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
    echo "Installing streamware (offline)..."
    PIP_CMD=""
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    elif python3 -m pip --version &> /dev/null; then
        PIP_CMD="python3 -m pip"
    else
        python3 -m ensurepip --upgrade 2>/dev/null || true
        if command -v pip3 &> /dev/null; then
            PIP_CMD="pip3"
        elif command -v pip &> /dev/null; then
            PIP_CMD="pip"
        elif python3 -m pip --version &> /dev/null; then
            PIP_CMD="python3 -m pip"
        fi
    fi

    PIP_WHL=""
    if [ -d "$DATA_PART/pip-cache" ]; then
        PIP_WHL=$(ls "$DATA_PART/pip-cache"/pip-*.whl 2>/dev/null | head -n1)
    fi

    run_pip_from_whl() {
        local whl="$1"
        shift
        python3 - "$whl" "$@" << 'PY'
import runpy, sys
whl = sys.argv[1]
sys.path.insert(0, whl)
sys.argv = ['pip'] + sys.argv[2:]
runpy.run_module('pip', run_name='__main__')
PY
    }

    pip_install() {
        if [ -n "$PIP_CMD" ]; then
            $PIP_CMD "$@"
        elif [ -n "$PIP_WHL" ]; then
            run_pip_from_whl "$PIP_WHL" "$@"
        else
            return 127
        fi
    }

    if [ -z "$PIP_CMD" ] && [ -z "$PIP_WHL" ]; then
        echo "⚠ Could not find pip. Install manually: sudo dnf install -y python3-pip"
    elif [ -d "$DATA_PART/pip-cache" ]; then
        pip_install install --break-system-packages --no-index --find-links="$DATA_PART/pip-cache" streamware 2>/dev/null || \
        pip_install install --break-system-packages --no-index --find-links="$DATA_PART/pip-cache" "$DATA_PART/streamware" 2>/dev/null || \
        pip_install install --no-index --find-links="$DATA_PART/pip-cache" streamware 2>/dev/null || \
        pip_install install --no-index --find-links="$DATA_PART/pip-cache" "$DATA_PART/streamware" 2>/dev/null || {
            echo "⚠ Could not install streamware from offline cache"
        }
    else
        echo "⚠ Offline pip-cache not found at: $DATA_PART/pip-cache"
    fi
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
echo " done"

log_success "Setup scripts created"

# =============================================================================
# Create autostart service (systemd)
# =============================================================================

log_info "Creating autostart service (4 files)..."
printf "  [1/4] llm-station.service..."

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
echo " done"
printf "  [2/4] autostart.sh..."

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
# Install Python dependencies (OFFLINE from cached packages)
# =============================================================================

echo "Setting up Python environment (offline mode)..."

PIP_CMD=""
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
elif python3 -m pip --version &> /dev/null; then
    PIP_CMD="python3 -m pip"
else
    echo "Installing pip..."
    python3 -m ensurepip --upgrade 2>/dev/null || true
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    elif python3 -m pip --version &> /dev/null; then
        PIP_CMD="python3 -m pip"
    fi
fi

PIP_WHL=""
if [ -d "$DATA_PART/pip-cache" ]; then
    PIP_WHL=$(ls "$DATA_PART/pip-cache"/pip-*.whl 2>/dev/null | head -n1)
fi

run_pip_from_whl() {
    local whl="$1"
    shift
    python3 - "$whl" "$@" << 'PY'
import runpy, sys
whl = sys.argv[1]
sys.path.insert(0, whl)
sys.argv = ['pip'] + sys.argv[2:]
runpy.run_module('pip', run_name='__main__')
PY
}

pip_install() {
    if [ -n "$PIP_CMD" ]; then
        $PIP_CMD "$@"
    elif [ -n "$PIP_WHL" ]; then
        run_pip_from_whl "$PIP_WHL" "$@"
    else
        return 127
    fi
}

# Install from offline cache first
if [ -d "$DATA_PART/pip-cache" ] && [ "$(ls -A $DATA_PART/pip-cache/*.whl 2>/dev/null)" ] && { [ -n "$PIP_CMD" ] || [ -n "$PIP_WHL" ]; }; then
    echo "Installing packages from offline cache..."
    pip_install install --break-system-packages --no-index --find-links="$DATA_PART/pip-cache" \
        requests aiohttp pydantic rich PyYAML click jinja2 jsonpath-ng \
        flask pillow numpy 2>/dev/null || \
    pip_install install --no-index --find-links="$DATA_PART/pip-cache" \
        requests aiohttp pydantic rich PyYAML click jinja2 jsonpath-ng \
        flask pillow numpy 2>/dev/null || true

    # Try opencv-python-headless from cache
    pip_install install --break-system-packages --no-index --find-links="$DATA_PART/pip-cache" \
        opencv-python-headless 2>/dev/null || \
    pip_install install --no-index --find-links="$DATA_PART/pip-cache" \
        opencv-python-headless 2>/dev/null || true
fi

# Install streamware from local project
if [ -d "$DATA_PART/streamware" ] && [ -f "$DATA_PART/streamware/pyproject.toml" ] && { [ -n "$PIP_CMD" ] || [ -n "$PIP_WHL" ]; }; then
    echo "Installing streamware from local project..."
    cd "$DATA_PART/streamware"
    pip_install install --break-system-packages --no-index --find-links="$DATA_PART/pip-cache" -e . 2>/dev/null || \
    pip_install install --break-system-packages -e . 2>/dev/null || \
    pip_install install --break-system-packages . 2>/dev/null || \
    pip_install install --no-index --find-links="$DATA_PART/pip-cache" -e . 2>/dev/null || \
    pip_install install -e . 2>/dev/null || \
    pip_install install . 2>/dev/null || true
    cd -
fi

echo "Python environment ready"

# Load .env configuration (contains all settings including camera URL)
if [ -f "$DATA_PART/config/.env" ]; then
    echo "Loading configuration from .env..."
    set -a  # Export all variables
    source "$DATA_PART/config/.env"
    set +a
fi

ENABLE_OPENWEBUI="${ENABLE_OPENWEBUI:-true}"

# =============================================================================
# Install and start Ollama (OFFLINE from pre-downloaded binary)
# =============================================================================

echo "Setting up Ollama (offline mode)..."

# Install Ollama from offline binary if not present
if ! command -v ollama &> /dev/null; then
    if [ -f "$DATA_PART/bin/ollama-linux-amd64.tgz" ]; then
        echo "Installing Ollama from offline archive..."
        sudo tar -C /usr -xzf "$DATA_PART/bin/ollama-linux-amd64.tgz"
        echo "Ollama installed from USB"
    else
        echo "WARNING: Ollama archive not found in offline cache"
        echo "Trying online installation..."
        curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || true
    fi
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
    
    # Models should already be linked from USB - check if available
    if ollama list 2>/dev/null | grep -q "llava"; then
        echo "Model llava already available"
    else
        echo "NOTE: Model llava not found. Models should be pre-copied to USB."
        echo "If online, run: ollama pull llava:7b"
    fi
fi

# =============================================================================
# Start Open-WebUI container
# =============================================================================

if [ "$ENABLE_OPENWEBUI" = "true" ]; then
    echo "Setting up Open-WebUI (offline mode)..."

    # Check if podman or docker available
    CONTAINER_CMD=""
    if command -v podman &> /dev/null; then
        CONTAINER_CMD="podman"
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD="docker"
    fi

    if [ -n "$CONTAINER_CMD" ]; then
        # Load image from offline cache if not already loaded
        if ! $CONTAINER_CMD images | grep -q "open-webui"; then
            if [ -f "$DATA_PART/images/open-webui.tar" ]; then
                echo "Loading Open-WebUI from offline cache..."
                $CONTAINER_CMD load -i "$DATA_PART/images/open-webui.tar" 2>/dev/null || true
            fi
        fi
        
        # Stop existing container
        $CONTAINER_CMD stop open-webui 2>/dev/null || true
        $CONTAINER_CMD rm open-webui 2>/dev/null || true
        
        # Start Open-WebUI (from local image)
        echo "Starting Open-WebUI container..."
        $CONTAINER_CMD run -d --name open-webui \
            -p 3000:8080 \
            -e OLLAMA_BASE_URL=http://host.containers.internal:11434 \
            --add-host=host.containers.internal:host-gateway \
            ghcr.io/open-webui/open-webui:main 2>/dev/null || {
                # Try with localhost if host.containers.internal fails
                $CONTAINER_CMD run -d --name open-webui \
                    -p 3000:8080 \
                    --network=host \
                    -e OLLAMA_BASE_URL=http://localhost:11434 \
                    ghcr.io/open-webui/open-webui:main 2>/dev/null || \
                echo "WARNING: Open-WebUI container not available"
            }
    else
        echo "NOTE: No container runtime (podman/docker) - skipping Open-WebUI"
    fi
else
    echo "Open-WebUI disabled (ENABLE_OPENWEBUI=$ENABLE_OPENWEBUI) - skipping"
fi

# =============================================================================
# Start streamware accounting
# =============================================================================

echo "Starting streamware services..."

# Set defaults for kiosk mode
PROJECT="${PROJECT:-faktury_2024}"
PORT="${SQ_WEB_PORT:-8080}"
KIOSK_ENABLED="${KIOSK_ENABLED:-true}"
KIOSK_URL="${KIOSK_URL:-http://localhost:$PORT}"

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
    echo "Starting: sq accounting web --project $PROJECT --port $PORT"
    sq accounting web --project "$PROJECT" --port "$PORT" &
    SQ_PID=$!
    echo "Streamware accounting started (PID: $SQ_PID)"
    
    # Wait for web interface to be ready
    echo "Waiting for accounting web interface..."
    for i in {1..20}; do
        if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
            echo "Accounting web ready!"
            break
        fi
        sleep 1
    done
else
    echo "WARNING: sq command not found. Install with: pip install streamware"
fi

# Start kiosk browser if enabled
if [ "$KIOSK_ENABLED" = "true" ]; then
    echo "Starting kiosk browser at $KIOSK_URL ..."
    
    # Set display for GUI
    export DISPLAY=${DISPLAY:-:0}
    
    # Use kiosk browser wrapper from data partition
    if [ -x "$DATA_PART/bin/kiosk-browser.sh" ]; then
        "$DATA_PART/bin/kiosk-browser.sh" "$KIOSK_URL" &
        echo "Kiosk browser started (via wrapper)"
    else
        # Fallback: try Firefox directly (included in Fedora LXQt)
        if command -v firefox &> /dev/null; then
            firefox --kiosk "$KIOSK_URL" &
            echo "Kiosk browser started (Firefox)"
        else
            echo "WARNING: No browser found. Install firefox:"
            echo "  sudo dnf install firefox"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "LLM Station started!"
echo "  Accounting: http://localhost:$PORT"
if [ "$ENABLE_OPENWEBUI" = "true" ]; then
    echo "  Open-WebUI: http://localhost:3000"
fi
echo "=========================================="
AUTOSTART

chmod +x "$MOUNT_DATA/autostart.sh"
echo " done"
printf "  [3/4] install-service.sh..."

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
echo " done"
printf "  [4/4] config/accounting.conf..."

# Create accounting config
mkdir -p "$MOUNT_DATA/config"
cat > "$MOUNT_DATA/config/accounting.conf" << 'CONFIG'
# LLM Station Accounting Configuration
# Edit this file to customize autostart behavior

# Project name for accounting
PROJECT="faktury_2024"

# Web interface port
PORT="8080"

# RTSP camera URL (leave empty for local USB camera /dev/video0)
# Example: rtsp://admin:password@192.168.1.100:554/h264Preview_01_main
RTSP_URL=""

# Scanner settings
SCANNER_FPS="2"
MIN_CONFIDENCE="0.25"
CONFIRM_THRESHOLD="0.60"
AUTO_SAVE_THRESHOLD="0.85"

# Enable kiosk mode (auto-open browser)
KIOSK_ENABLED="true"
KIOSK_URL="http://localhost:8080"

# Ollama model for analysis
MODEL="llava:7b"
CONFIG
echo " done"

log_success "Autostart service created"

# =============================================================================
# Calculate sizes and finalize
# =============================================================================

LIVE_SIZE=$(du -sh "$MOUNT_LIVE" | cut -f1)
DATA_SIZE=$(du -sh "$MOUNT_DATA" | cut -f1)

# Sync and unmount
STEP_START=$(date +%s)
log_info "Syncing data to USB..."
sync &
SYNC_PID=$!
SPIN='|/-\'
i=0
while kill -0 "$SYNC_PID" 2>/dev/null; do
    elapsed=$(($(date +%s) - STEP_START))
    i=$(((i + 1) % 4))
    printf "\r${BLUE}[INFO]${NC} Syncing data... %s (%ds)" "${SPIN:$i:1}" "$elapsed"
    sleep 0.2
done
wait "$SYNC_PID"
echo ""
log_timed $STEP_START "Data synced to USB"

log_info "Unmounting USB partitions..."
if [ -n "$MOUNT_LIVE" ] && mountpoint -q "$MOUNT_LIVE" 2>/dev/null; then
    umount "$MOUNT_LIVE" 2>/dev/null || true
fi
if [ -n "$MOUNT_DATA" ] && mountpoint -q "$MOUNT_DATA" 2>/dev/null; then
    umount "$MOUNT_DATA" 2>/dev/null || true
fi

# Calculate total time
TOTAL_TIME=$(($(date +%s) - SCRIPT_START_TIME))
TOTAL_MINS=$((TOTAL_TIME / 60))
TOTAL_SECS=$((TOTAL_TIME % 60))

echo ""
echo "=========================================="
echo "Hybrid USB creation complete!"
echo "Total time: ${TOTAL_MINS}m ${TOTAL_SECS}s"
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
