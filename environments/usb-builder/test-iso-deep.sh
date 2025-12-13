#!/bin/bash
# =============================================================================
# Deep ISO Testing Script
# Validates ISO structure, boot configuration, and content before deployment
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_FILE="${1:-$SCRIPT_DIR/output/llm-station-um790pro.iso}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

pass() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; WARNINGS=$((WARNINGS+1)); }
fail() { echo -e "${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
info() { echo -e "${BLUE}ℹ${NC} $1"; }

echo "=========================================="
echo "Deep ISO Validation"
echo "=========================================="
echo "ISO: $ISO_FILE"
echo ""

# =============================================================================
# Phase 1: File Validation
# =============================================================================
echo "## Phase 1: File Validation"

if [ ! -f "$ISO_FILE" ]; then
    fail "ISO file not found"
    exit 1
fi
pass "ISO file exists"

# Size check
SIZE=$(stat -c%s "$ISO_FILE")
SIZE_MB=$((SIZE / 1024 / 1024))
if [ "$SIZE_MB" -lt 500 ]; then
    fail "ISO too small: ${SIZE_MB}MB (expected >500MB)"
elif [ "$SIZE_MB" -lt 1500 ]; then
    warn "ISO smaller than typical Live ISO: ${SIZE_MB}MB"
else
    pass "ISO size: ${SIZE_MB}MB"
fi

# File type
FILE_TYPE=$(file "$ISO_FILE")
if echo "$FILE_TYPE" | grep -q "ISO 9660"; then
    pass "Valid ISO 9660 format"
else
    fail "Not a valid ISO 9660 image"
fi

if echo "$FILE_TYPE" | grep -q "bootable"; then
    pass "ISO marked as bootable"
else
    warn "ISO not marked as bootable in file header"
fi

echo ""

# =============================================================================
# Phase 2: ISO Structure
# =============================================================================
echo "## Phase 2: ISO Structure"

# Extract to temp for inspection
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

info "Extracting ISO for inspection..."
if command -v 7z &> /dev/null; then
    7z x -o"$TEMP_DIR" "$ISO_FILE" -y > /dev/null 2>&1
elif command -v bsdtar &> /dev/null; then
    bsdtar -xf "$ISO_FILE" -C "$TEMP_DIR" 2>/dev/null
else
    # Use isoinfo
    if command -v isoinfo &> /dev/null; then
        info "Using isoinfo (limited extraction)"
    else
        warn "No extraction tool available (install p7zip or bsdtar)"
    fi
fi

# Check key directories
for dir in "EFI" "EFI/BOOT" "LiveOS" "boot" "images"; do
    if [ -d "$TEMP_DIR/$dir" ]; then
        pass "Directory exists: $dir"
    else
        if [ "$dir" = "LiveOS" ]; then
            fail "Missing critical directory: $dir"
        else
            warn "Missing directory: $dir"
        fi
    fi
done

echo ""

# =============================================================================
# Phase 3: Boot Configuration
# =============================================================================
echo "## Phase 3: Boot Configuration"

# EFI bootloader
if [ -f "$TEMP_DIR/EFI/BOOT/BOOTX64.EFI" ]; then
    pass "EFI bootloader: BOOTX64.EFI"
elif [ -f "$TEMP_DIR/EFI/BOOT/grubx64.efi" ]; then
    pass "EFI bootloader: grubx64.efi"
else
    fail "No EFI bootloader found"
fi

# GRUB config
GRUB_CFG=""
for cfg in "EFI/BOOT/grub.cfg" "boot/grub2/grub.cfg" "boot/grub/grub.cfg"; do
    if [ -f "$TEMP_DIR/$cfg" ]; then
        GRUB_CFG="$TEMP_DIR/$cfg"
        pass "GRUB config: $cfg"
        break
    fi
done

if [ -z "$GRUB_CFG" ]; then
    fail "No GRUB configuration found"
else
    # Check GRUB config for volume label
    if command -v isoinfo &> /dev/null; then
        VOLUME_LABEL=$(isoinfo -d -i "$ISO_FILE" 2>/dev/null | grep "Volume id:" | cut -d':' -f2 | xargs)
        info "ISO Volume Label: $VOLUME_LABEL"
        
        if grep -q "$VOLUME_LABEL" "$GRUB_CFG" 2>/dev/null; then
            pass "GRUB config references correct volume label"
        else
            GRUB_LABEL=$(grep -oP 'CDLABEL=\K[^ ]+' "$GRUB_CFG" 2>/dev/null | head -1 || echo "unknown")
            if [ "$GRUB_LABEL" != "$VOLUME_LABEL" ] && [ -n "$GRUB_LABEL" ]; then
                fail "Volume label mismatch: ISO='$VOLUME_LABEL' GRUB='$GRUB_LABEL'"
                info "This will cause dracut to fail finding root filesystem!"
            fi
        fi
    fi
fi

# Eltorito (BIOS boot)
if [ -f "$TEMP_DIR/images/eltorito.img" ]; then
    pass "BIOS boot image: images/eltorito.img"
elif [ -f "$TEMP_DIR/isolinux/isolinux.bin" ]; then
    pass "BIOS boot image: isolinux/isolinux.bin"
else
    warn "No BIOS boot image found (EFI-only)"
fi

# EFI boot image
if [ -f "$TEMP_DIR/images/efiboot.img" ]; then
    pass "EFI boot image: images/efiboot.img"
else
    warn "No efiboot.img (may affect some UEFI systems)"
fi

echo ""

# =============================================================================
# Phase 4: Live System
# =============================================================================
echo "## Phase 4: Live System"

# Squashfs
SQUASH=""
for sq in "LiveOS/squashfs.img" "casper/filesystem.squashfs" "live/filesystem.squashfs"; do
    if [ -f "$TEMP_DIR/$sq" ]; then
        SQUASH="$TEMP_DIR/$sq"
        SQUASH_SIZE=$(du -h "$SQUASH" | cut -f1)
        pass "Squashfs: $sq ($SQUASH_SIZE)"
        break
    fi
done

if [ -z "$SQUASH" ]; then
    fail "No squashfs filesystem found - Live system won't boot!"
fi

# Kernel and initrd
if [ -f "$TEMP_DIR/images/pxeboot/vmlinuz" ]; then
    pass "Kernel: images/pxeboot/vmlinuz"
elif [ -f "$TEMP_DIR/boot/vmlinuz" ]; then
    pass "Kernel: boot/vmlinuz"
else
    warn "Kernel not found in expected location"
fi

if [ -f "$TEMP_DIR/images/pxeboot/initrd.img" ]; then
    pass "Initrd: images/pxeboot/initrd.img"
elif [ -f "$TEMP_DIR/boot/initrd.img" ]; then
    pass "Initrd: boot/initrd.img"
else
    warn "Initrd not found in expected location"
fi

echo ""

# =============================================================================
# Phase 5: LLM Station Content
# =============================================================================
echo "## Phase 5: LLM Station Content"

if [ -d "$TEMP_DIR/llm-data" ]; then
    pass "LLM data directory exists"
    
    # Check subdirectories
    [ -d "$TEMP_DIR/llm-data/environments" ] && pass "  environments/" || warn "  environments/ missing"
    [ -f "$TEMP_DIR/llm-data/first-boot.sh" ] && pass "  first-boot.sh" || warn "  first-boot.sh missing"
    [ -f "$TEMP_DIR/llm-data/autorun.sh" ] && pass "  autorun.sh" || warn "  autorun.sh missing"
    
    # Check for models
    if [ -d "$TEMP_DIR/llm-data/environments/ollama-webui/models" ]; then
        MODEL_SIZE=$(du -sh "$TEMP_DIR/llm-data/environments/ollama-webui/models" 2>/dev/null | cut -f1)
        pass "  Ollama models: $MODEL_SIZE"
    else
        warn "  No Ollama models (will need internet)"
    fi
    
    # Check for container images
    if [ -d "$TEMP_DIR/llm-data/images" ] && [ "$(ls -A $TEMP_DIR/llm-data/images/*.tar 2>/dev/null)" ]; then
        IMG_COUNT=$(ls "$TEMP_DIR/llm-data/images/"*.tar 2>/dev/null | wc -l)
        IMG_SIZE=$(du -sh "$TEMP_DIR/llm-data/images" 2>/dev/null | cut -f1)
        pass "  Container images: $IMG_COUNT files, $IMG_SIZE"
    else
        warn "  No container images (will need internet)"
    fi
else
    warn "LLM data directory not found"
fi

echo ""

# =============================================================================
# Phase 6: Checksums
# =============================================================================
echo "## Phase 6: Checksums"

SHA256_FILE="${ISO_FILE}.sha256"
if [ -f "$SHA256_FILE" ]; then
    cd "$(dirname "$ISO_FILE")"
    if sha256sum -c "$(basename "$SHA256_FILE")" 2>/dev/null; then
        pass "SHA256 checksum valid"
    else
        fail "SHA256 checksum mismatch - ISO may be corrupted!"
    fi
    cd - > /dev/null
else
    warn "No SHA256 checksum file"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}ISO is fully validated and ready for deployment!${NC}"
    else
        echo -e "${YELLOW}ISO has warnings but should be bootable.${NC}"
    fi
    echo ""
    echo "Next steps:"
    echo "  Test in VM:     make iso-test"
    echo "  Flash to USB:   Use Balena Etcher"
    exit 0
else
    echo -e "${RED}ISO has critical errors and may not boot!${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Volume label mismatch: Keep original Fedora label"
    echo "  - Missing squashfs: Check base ISO extraction"
    echo "  - No bootloader: Verify EFI/BOOT directory"
    exit 1
fi
