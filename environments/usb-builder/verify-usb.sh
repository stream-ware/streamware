#!/bin/bash
# =============================================================================
# USB Drive Verification Script
# Validates a freshly created USB drive for bootability and content integrity
#
# Usage: sudo ./verify-usb.sh /dev/sdX
#        sudo ./verify-usb.sh  (interactive selection)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
ERRORS=0
WARNINGS=0
CHECKS=0

pass() { 
    echo -e "${GREEN}✓${NC} $1"
    CHECKS=$((CHECKS + 1))
}

warn() { 
    echo -e "${YELLOW}⚠${NC} $1"
    WARNINGS=$((WARNINGS + 1))
    CHECKS=$((CHECKS + 1))
}

fail() { 
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
    CHECKS=$((CHECKS + 1))
}

info() { 
    echo -e "${BLUE}ℹ${NC} $1"
}

section() {
    echo ""
    echo -e "${CYAN}## $1${NC}"
    echo "─────────────────────────────────────────────────────────────────"
}

# =============================================================================
# Root check
# =============================================================================

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script must be run as root${NC}"
    echo "Usage: sudo $0 /dev/sdX"
    exit 1
fi

# =============================================================================
# Device selection
# =============================================================================

USB_DEVICE="$1"

if [ -z "$USB_DEVICE" ]; then
    echo "=========================================="
    echo "USB Drive Verification"
    echo "=========================================="
    echo ""
    echo "Available USB devices:"
    echo "─────────────────────────────────────────────────────────────────"
    
    i=1
    declare -a devices
    
    # List all block devices except system ones
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        dev=$(echo "$line" | awk '{print $1}')
        size=$(echo "$line" | awk '{print $2}')
        model=$(echo "$line" | awk '{$1=$2=""; print $0}' | xargs)
        
        # Skip empty size or loop devices
        [ "$size" = "0B" ] && continue
        [ -z "$size" ] && continue
        
        printf "[%d] /dev/%-6s %8s  %s\n" "$i" "$dev" "$size" "$model"
        devices[$i]="/dev/$dev"
        i=$((i + 1))
    done < <(lsblk -d -n -o NAME,SIZE,MODEL 2>/dev/null | grep -vE "^loop|^sr|^nvme0n1$|^sda$|^vda$")
    
    echo "─────────────────────────────────────────────────────────────────"
    echo ""
    
    if [ $((i - 1)) -eq 0 ]; then
        echo -e "${RED}No USB devices found${NC}"
        exit 1
    fi
    
    read -p "Select device [1-$((i-1))]: " sel
    USB_DEVICE="${devices[$sel]}"
    
    if [ -z "$USB_DEVICE" ]; then
        echo "Invalid selection"
        exit 1
    fi
fi

if [ ! -b "$USB_DEVICE" ]; then
    echo -e "${RED}Device not found: $USB_DEVICE${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo "USB Drive Verification"
echo "=========================================="
echo "Device: $USB_DEVICE"
echo "Time: $(date)"
echo ""

# =============================================================================
# Phase 1: Device Information
# =============================================================================

section "Phase 1: Device Information"

# Get device info
DEVICE_SIZE=$(lsblk -b -d -o SIZE "$USB_DEVICE" 2>/dev/null | tail -1)
DEVICE_SIZE_GB=$((DEVICE_SIZE / 1024 / 1024 / 1024))
DEVICE_MODEL=$(lsblk -d -o MODEL "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)
DEVICE_VENDOR=$(lsblk -d -o VENDOR "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)
DEVICE_SERIAL=$(lsblk -d -o SERIAL "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)
DEVICE_TRAN=$(lsblk -d -o TRAN "$USB_DEVICE" 2>/dev/null | tail -1 | xargs)

echo "Size:      ${DEVICE_SIZE_GB}GB"
echo "Vendor:    ${DEVICE_VENDOR:-Unknown}"
echo "Model:     ${DEVICE_MODEL:-Unknown}"
echo "Serial:    ${DEVICE_SERIAL:-Unknown}"
echo "Transport: ${DEVICE_TRAN:-Unknown}"

if [ "$DEVICE_TRAN" = "usb" ]; then
    pass "Device is USB connected"
else
    warn "Device transport is '$DEVICE_TRAN' (expected 'usb')"
fi

if [ "$DEVICE_SIZE_GB" -ge 16 ]; then
    pass "Device size adequate (${DEVICE_SIZE_GB}GB >= 16GB)"
elif [ "$DEVICE_SIZE_GB" -ge 8 ]; then
    warn "Device size marginal (${DEVICE_SIZE_GB}GB, recommended 16GB+)"
else
    fail "Device too small (${DEVICE_SIZE_GB}GB, minimum 8GB)"
fi

# =============================================================================
# Phase 2: Partition Table
# =============================================================================

section "Phase 2: Partition Table"

# Check partition table type
PTTYPE=$(blkid -o value -s PTTYPE "$USB_DEVICE" 2>/dev/null)
echo "Partition table: ${PTTYPE:-Unknown}"

if [ "$PTTYPE" = "gpt" ]; then
    pass "GPT partition table (UEFI compatible)"
elif [ "$PTTYPE" = "dos" ]; then
    warn "MBR partition table (legacy BIOS only)"
else
    fail "Unknown or missing partition table"
fi

# List partitions
echo ""
echo "Partitions:"
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT "$USB_DEVICE" 2>/dev/null

# Determine partition naming
if [[ "$USB_DEVICE" == *"nvme"* ]] || [[ "$USB_DEVICE" == *"mmcblk"* ]]; then
    PART1="${USB_DEVICE}p1"
    PART2="${USB_DEVICE}p2"
else
    PART1="${USB_DEVICE}1"
    PART2="${USB_DEVICE}2"
fi

# Check partitions exist
if [ -b "$PART1" ]; then
    pass "Partition 1 exists: $PART1"
else
    fail "Partition 1 not found: $PART1"
fi

if [ -b "$PART2" ]; then
    pass "Partition 2 exists: $PART2"
else
    warn "Partition 2 not found (single partition layout?)"
fi

# =============================================================================
# Phase 3: Filesystem Check
# =============================================================================

section "Phase 3: Filesystem Check"

# Check partition 1 filesystem
FSTYPE1=$(blkid -o value -s TYPE "$PART1" 2>/dev/null)
LABEL1=$(blkid -o value -s LABEL "$PART1" 2>/dev/null)

echo "Partition 1: $FSTYPE1 (Label: ${LABEL1:-none})"

if [ "$FSTYPE1" = "vfat" ]; then
    pass "Partition 1 is FAT32 (EFI compatible)"
else
    fail "Partition 1 is $FSTYPE1 (expected vfat for EFI)"
fi

# Check partition 2 if exists
if [ -b "$PART2" ]; then
    FSTYPE2=$(blkid -o value -s TYPE "$PART2" 2>/dev/null)
    LABEL2=$(blkid -o value -s LABEL "$PART2" 2>/dev/null)
    
    echo "Partition 2: $FSTYPE2 (Label: ${LABEL2:-none})"
    
    if [ "$FSTYPE2" = "ext4" ]; then
        pass "Partition 2 is ext4"
    elif [ -n "$FSTYPE2" ]; then
        warn "Partition 2 is $FSTYPE2 (expected ext4)"
    fi
fi

# =============================================================================
# Phase 4: Boot Configuration
# =============================================================================

section "Phase 4: Boot Configuration"

# Mount partition 1 temporarily
MOUNT1=$(mktemp -d)
mount -o ro "$PART1" "$MOUNT1" 2>/dev/null || {
    fail "Cannot mount partition 1"
    rmdir "$MOUNT1"
    MOUNT1=""
}

if [ -n "$MOUNT1" ]; then
    # Check EFI bootloader
    if [ -f "$MOUNT1/EFI/BOOT/BOOTX64.EFI" ]; then
        pass "EFI bootloader: BOOTX64.EFI"
    elif [ -f "$MOUNT1/EFI/BOOT/grubx64.efi" ]; then
        pass "EFI bootloader: grubx64.efi"
    else
        fail "No EFI bootloader found in EFI/BOOT/"
    fi
    
    # Check GRUB config
    GRUB_CFG=""
    for cfg in "EFI/BOOT/grub.cfg" "boot/grub2/grub.cfg" "boot/grub/grub.cfg"; do
        if [ -f "$MOUNT1/$cfg" ]; then
            GRUB_CFG="$MOUNT1/$cfg"
            pass "GRUB config: $cfg"
            break
        fi
    done
    
    if [ -z "$GRUB_CFG" ]; then
        fail "No GRUB configuration found"
    else
        # Check for common boot issues
        if grep -q "root=live" "$GRUB_CFG" 2>/dev/null; then
            pass "Live boot configuration present"
        fi
        
        # Check volume label matches
        GRUB_LABEL=$(grep -oP 'CDLABEL=\K[^ "]+' "$GRUB_CFG" 2>/dev/null | head -1)
        if [ -n "$GRUB_LABEL" ]; then
            info "GRUB expects volume label: $GRUB_LABEL"
        fi
    fi
    
    # Check for kernel and initrd
    if [ -f "$MOUNT1/images/pxeboot/vmlinuz" ]; then
        KERNEL_SIZE=$(stat -c%s "$MOUNT1/images/pxeboot/vmlinuz")
        pass "Kernel: images/pxeboot/vmlinuz ($((KERNEL_SIZE/1024/1024))MB)"
    elif [ -f "$MOUNT1/boot/vmlinuz" ]; then
        pass "Kernel: boot/vmlinuz"
    else
        fail "Kernel not found"
    fi
    
    if [ -f "$MOUNT1/images/pxeboot/initrd.img" ]; then
        INITRD_SIZE=$(stat -c%s "$MOUNT1/images/pxeboot/initrd.img")
        pass "Initrd: images/pxeboot/initrd.img ($((INITRD_SIZE/1024/1024))MB)"
    elif [ -f "$MOUNT1/boot/initrd.img" ]; then
        pass "Initrd: boot/initrd.img"
    else
        fail "Initrd not found"
    fi
    
    # Check squashfs
    if [ -f "$MOUNT1/LiveOS/squashfs.img" ]; then
        SQUASH_SIZE=$(stat -c%s "$MOUNT1/LiveOS/squashfs.img")
        pass "Squashfs: LiveOS/squashfs.img ($((SQUASH_SIZE/1024/1024))MB)"
    elif [ -f "$MOUNT1/casper/filesystem.squashfs" ]; then
        pass "Squashfs: casper/filesystem.squashfs"
    else
        fail "Squashfs filesystem not found"
    fi
    
    # Check LLM data on partition 1
    if [ -d "$MOUNT1/llm-data" ]; then
        pass "LLM data directory on boot partition"
        [ -f "$MOUNT1/llm-data/first-boot.sh" ] && pass "  first-boot.sh present"
        [ -f "$MOUNT1/llm-data/autorun.sh" ] && pass "  autorun.sh present"
    fi
    
    umount "$MOUNT1"
    rmdir "$MOUNT1"
fi

# =============================================================================
# Phase 5: Data Partition (if exists)
# =============================================================================

if [ -b "$PART2" ]; then
    section "Phase 5: Data Partition Content"
    
    MOUNT2=$(mktemp -d)
    mount -o ro "$PART2" "$MOUNT2" 2>/dev/null || {
        fail "Cannot mount partition 2"
        rmdir "$MOUNT2"
        MOUNT2=""
    }
    
    if [ -n "$MOUNT2" ]; then
        # Check directory structure
        [ -d "$MOUNT2/environments" ] && pass "environments/ directory" || warn "environments/ missing"
        [ -d "$MOUNT2/models" ] && pass "models/ directory" || warn "models/ missing"
        [ -d "$MOUNT2/images" ] && pass "images/ directory" || info "images/ not present"
        
        # Check environments
        if [ -d "$MOUNT2/environments" ]; then
            echo ""
            echo "Environments:"
            for env in "$MOUNT2/environments"/*; do
                if [ -d "$env" ]; then
                    env_name=$(basename "$env")
                    env_size=$(du -sh "$env" 2>/dev/null | cut -f1)
                    echo "  - $env_name ($env_size)"
                fi
            done
        fi
        
        # Check models
        if [ -d "$MOUNT2/models" ]; then
            echo ""
            echo "Models:"
            
            ollama_count=$(find "$MOUNT2/models/ollama" -type f 2>/dev/null | wc -l)
            if [ "$ollama_count" -gt 0 ]; then
                ollama_size=$(du -sh "$MOUNT2/models/ollama" 2>/dev/null | cut -f1)
                pass "Ollama models: $ollama_count files ($ollama_size)"
            else
                warn "No Ollama models found"
            fi
            
            gguf_count=$(find "$MOUNT2/models/gguf" -name "*.gguf" 2>/dev/null | wc -l)
            if [ "$gguf_count" -gt 0 ]; then
                gguf_size=$(du -sh "$MOUNT2/models/gguf" 2>/dev/null | cut -f1)
                pass "GGUF models: $gguf_count files ($gguf_size)"
            else
                warn "No GGUF models found"
            fi
        fi
        
        # Check container images
        if [ -d "$MOUNT2/images" ]; then
            img_count=$(find "$MOUNT2/images" -name "*.tar" 2>/dev/null | wc -l)
            if [ "$img_count" -gt 0 ]; then
                img_size=$(du -sh "$MOUNT2/images" 2>/dev/null | cut -f1)
                pass "Container images: $img_count files ($img_size)"
            else
                warn "No container images cached"
            fi
        fi
        
        # Check setup script
        if [ -f "$MOUNT2/setup.sh" ]; then
            pass "setup.sh present"
            if [ -x "$MOUNT2/setup.sh" ]; then
                pass "setup.sh is executable"
            else
                warn "setup.sh is not executable"
            fi
        else
            warn "setup.sh not found"
        fi
        
        # Check README
        [ -f "$MOUNT2/README.md" ] && pass "README.md present" || info "README.md not present"
        
        # Calculate total data size
        DATA_SIZE=$(du -sh "$MOUNT2" 2>/dev/null | cut -f1)
        info "Total data partition size: $DATA_SIZE"
        
        umount "$MOUNT2"
        rmdir "$MOUNT2"
    fi
fi

# =============================================================================
# Phase 6: Boot Test Preparation
# =============================================================================

section "Phase 6: Boot Test"

echo "To test boot in QEMU, run:"
echo ""
echo "  sudo qemu-system-x86_64 \\"
echo "    -enable-kvm \\"
echo "    -m 4G \\"
echo "    -drive file=$USB_DEVICE,format=raw,if=virtio \\"
echo "    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \\"
echo "    -display gtk"
echo ""

# Check if QEMU is available
if command -v qemu-system-x86_64 &> /dev/null; then
    pass "QEMU available for boot testing"
    
    read -p "Run QEMU boot test now? [y/N]: " run_test
    if [ "$run_test" = "y" ] || [ "$run_test" = "Y" ]; then
        echo ""
        info "Unmounting USB partitions..."
        for part in ${USB_DEVICE}*; do
            umount "$part" 2>/dev/null || true
        done
        sleep 1
        
        info "Starting QEMU boot test..."
        info "Press Ctrl+Alt+G to release mouse, Ctrl+Alt+Q to quit"
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
            warn "OVMF not found, trying BIOS mode..."
            qemu-system-x86_64 \
                -enable-kvm \
                -m 4G \
                -smp 2 \
                -drive file="$USB_DEVICE",format=raw,if=virtio \
                -display gtk
        fi
    fi
else
    warn "QEMU not installed (install with: sudo apt install qemu-system-x86)"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo ""
echo "Device:   $USB_DEVICE"
echo "Checks:   $CHECKS"
echo -e "Passed:   ${GREEN}$((CHECKS - ERRORS - WARNINGS))${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  USB drive is fully validated and ready for deployment!       ${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    else
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}  USB drive has warnings but should be bootable.               ${NC}"
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
    fi
    echo ""
    echo "Next steps:"
    echo "  1. Safely eject: sudo eject $USB_DEVICE"
    echo "  2. Insert into target machine"
    echo "  3. Boot from USB (select UEFI boot in BIOS)"
    echo "  4. Run: /run/media/\$USER/LLM-DATA/setup.sh"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  USB drive has errors and may not boot correctly!             ${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Recommended actions:"
    echo "  1. Rebuild USB: make usb-hybrid USB=$USB_DEVICE"
    echo "  2. Check ISO: make test-deep"
    echo "  3. Verify base ISO integrity"
    exit 1
fi
