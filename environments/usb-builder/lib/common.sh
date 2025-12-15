#!/bin/bash
# =============================================================================
# Common Functions Library
# Source this file in other scripts: source "$(dirname "$0")/lib/common.sh"
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

log_step() {
    local step="$1"
    local total="$2"
    local msg="$3"
    echo ""
    echo -e "${BLUE}[$step/$total]${NC} $msg"
}

# =============================================================================
# Error Handling
# =============================================================================

# Global variables for cleanup
_CLEANUP_DIRS=()
_CLEANUP_MOUNTS=()

# Register directory for cleanup
register_cleanup_dir() {
    _CLEANUP_DIRS+=("$1")
}

# Register mount point for cleanup
register_cleanup_mount() {
    _CLEANUP_MOUNTS+=("$1")
}

# Cleanup function - call on exit
cleanup() {
    local exit_code=$?
    
    # Unmount any registered mount points
    for mount in "${_CLEANUP_MOUNTS[@]}"; do
        if mountpoint -q "$mount" 2>/dev/null; then
            umount "$mount" 2>/dev/null || true
        fi
    done
    
    # Remove registered temp directories
    for dir in "${_CLEANUP_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            rm -rf "$dir" 2>/dev/null || true
        fi
    done
    
    return $exit_code
}

# Setup trap for cleanup
setup_cleanup_trap() {
    trap cleanup EXIT INT TERM
}

# =============================================================================
# Validation Functions
# =============================================================================

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root"
        echo "Usage: sudo $0"
        exit 1
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check required commands
check_commands() {
    local missing=()
    for cmd in "$@"; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing commands: ${missing[*]}"
        return 1
    fi
    return 0
}

# =============================================================================
# Dependency Installation
# =============================================================================

# Detect package manager
detect_package_manager() {
    if [ -f /etc/fedora-release ]; then
        echo "dnf"
    elif [ -f /etc/debian_version ]; then
        echo "apt"
    elif [ -f /etc/arch-release ]; then
        echo "pacman"
    else
        echo "unknown"
    fi
}

# Install packages based on distro
install_packages() {
    local pm=$(detect_package_manager)
    
    case $pm in
        dnf)
            dnf install -y "$@"
            ;;
        apt)
            apt-get update
            apt-get install -y "$@"
            ;;
        pacman)
            pacman -S --noconfirm "$@"
            ;;
        *)
            log_error "Unknown package manager. Please install manually: $*"
            return 1
            ;;
    esac
}

# Check and install build dependencies
check_build_deps() {
    local missing=()
    
    # ISO creation tool
    if ! command_exists xorriso && ! command_exists genisoimage && ! command_exists mkisofs; then
        missing+=("xorriso")
    fi
    
    # Extraction tool
    if ! command_exists 7z && ! command_exists bsdtar; then
        missing+=("p7zip")
    fi
    
    # Other tools
    command_exists file || missing+=("file")
    command_exists isohybrid || missing+=("syslinux")
    command_exists curl || missing+=("curl")
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_warn "Missing dependencies: ${missing[*]}"
        log_info "Installing..."
        
        local pm=$(detect_package_manager)
        case $pm in
            dnf)
                install_packages xorriso squashfs-tools p7zip p7zip-plugins file syslinux curl
                ;;
            apt)
                install_packages xorriso squashfs-tools p7zip-full file syslinux-utils curl
                ;;
            pacman)
                install_packages xorriso squashfs-tools p7zip file syslinux curl
                ;;
            *)
                log_error "Please install: xorriso squashfs-tools p7zip file syslinux curl"
                return 1
                ;;
        esac
    fi
    
    return 0
}

# =============================================================================
# File Operations
# =============================================================================

# Create directory if not exists
ensure_dir() {
    [ -d "$1" ] || mkdir -p "$1"
}

# Get file size in bytes
file_size() {
    stat -c%s "$1" 2>/dev/null || echo 0
}

# Get file size human readable
file_size_human() {
    du -h "$1" 2>/dev/null | cut -f1
}

# Check if file is valid ISO
is_valid_iso() {
    local iso="$1"
    local min_size="${2:-500000000}"  # 500MB default
    
    [ -f "$iso" ] || return 1
    
    local size=$(file_size "$iso")
    [ "$size" -ge "$min_size" ] || return 1
    
    file "$iso" 2>/dev/null | grep -q "ISO 9660" || return 1
    
    return 0
}

# =============================================================================
# ISO Operations
# =============================================================================

# Extract ISO using best available tool
extract_iso() {
    local iso="$1"
    local dest="$2"
    
    ensure_dir "$dest"
    
    if command_exists 7z; then
        log_info "Extracting with 7z..."
        7z x -o"$dest" "$iso" -y > /dev/null
    elif command_exists bsdtar; then
        log_info "Extracting with bsdtar..."
        bsdtar -xf "$iso" -C "$dest"
    else
        log_info "Extracting with mount..."
        local mnt=""
        if [ -n "${CACHE_DIR:-}" ]; then
            ensure_dir "$CACHE_DIR/tmp"
            mnt=$(mktemp -d -p "$CACHE_DIR/tmp")
        else
            mnt=$(mktemp -d)
        fi
        register_cleanup_dir "$mnt"
        register_cleanup_mount "$mnt"
        mount -o loop,ro "$iso" "$mnt"
        cp -a "$mnt/." "$dest/"
        umount "$mnt"
    fi
}

# Make ISO hybrid (bootable from USB)
make_iso_hybrid() {
    local iso="$1"
    
    if command_exists isohybrid; then
        log_info "Applying isohybrid MBR..."
        isohybrid --uefi "$iso" 2>/dev/null || isohybrid "$iso" 2>/dev/null || true
        log_success "ISO is now USB-bootable"
    else
        log_warn "isohybrid not found - ISO may not boot from USB"
    fi
}

# Detect boot type from ISO contents
detect_boot_type() {
    local iso_root="$1"
    local boot_type="unknown"
    
    [ -d "$iso_root/EFI" ] && boot_type="efi"
    [ -d "$iso_root/isolinux" ] && boot_type="bios"
    [ -d "$iso_root/EFI" ] && [ -d "$iso_root/isolinux" ] && boot_type="hybrid"
    
    echo "$boot_type"
}

# Find EFI boot image
find_efi_image() {
    local iso_root="$1"
    
    for path in "images/efiboot.img" "boot/grub/efi.img" "EFI/BOOT/efiboot.img"; do
        if [ -f "$iso_root/$path" ]; then
            echo "$path"
            return 0
        fi
    done
    
    return 1
}

# Find squashfs image
find_squashfs() {
    local iso_root="$1"
    
    for pattern in "LiveOS/squashfs.img" "casper/filesystem.squashfs" "live/filesystem.squashfs"; do
        local found=$(find "$iso_root" -path "*$pattern" 2>/dev/null | head -1)
        if [ -n "$found" ]; then
            echo "$found"
            return 0
        fi
    done
    
    return 1
}

# =============================================================================
# Utility Functions
# =============================================================================

# Find free port starting from given port
find_free_port() {
    local port="${1:-8080}"
    local max="${2:-9000}"
    
    while ss -tuln 2>/dev/null | grep -q ":$port "; do
        port=$((port + 1))
        [ $port -gt $max ] && return 1
    done
    
    echo $port
}

# Generate checksums for file
generate_checksums() {
    local file="$1"
    local dir=$(dirname "$file")
    local name=$(basename "$file")
    
    cd "$dir"
    sha256sum "$name" > "${name}.sha256"
    md5sum "$name" > "${name}.md5"
    cd - > /dev/null
}

# Verify checksum
verify_checksum() {
    local file="$1"
    local checksum_file="${file}.sha256"
    
    if [ -f "$checksum_file" ]; then
        cd "$(dirname "$file")"
        sha256sum -c "$(basename "$checksum_file")" 2>/dev/null
        local result=$?
        cd - > /dev/null
        return $result
    fi
    
    return 1
}
