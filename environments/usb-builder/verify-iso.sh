#!/bin/bash
# =============================================================================
# Verify ISO Image Integrity and Bootability
# Usage: ./verify-iso.sh [path/to/iso]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_FILE="${1:-$SCRIPT_DIR/output/llm-station-um790pro.iso}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }

ERRORS=0

echo "=========================================="
echo "ISO Verification"
echo "=========================================="
echo "File: $ISO_FILE"
echo ""

# Check file exists
if [ ! -f "$ISO_FILE" ]; then
    fail "ISO file not found"
    exit 1
fi

# File size
SIZE=$(stat -c%s "$ISO_FILE")
SIZE_MB=$((SIZE / 1024 / 1024))
echo "Size: ${SIZE_MB} MB"

if [ "$SIZE_MB" -lt 500 ]; then
    fail "ISO too small (< 500 MB) - likely corrupted"
elif [ "$SIZE_MB" -lt 1500 ]; then
    warn "ISO smaller than expected (< 1.5 GB)"
else
    pass "Size looks reasonable"
fi

echo ""
echo "## File Type"
FILE_TYPE=$(file "$ISO_FILE")
if echo "$FILE_TYPE" | grep -q "ISO 9660"; then
    pass "Valid ISO 9660 format"
else
    fail "Not a valid ISO 9660 image"
fi

if echo "$FILE_TYPE" | grep -q "bootable"; then
    pass "ISO is bootable"
else
    warn "ISO may not be bootable"
fi

echo ""
echo "## ISO Contents"

# Check with isoinfo if available
if command -v isoinfo &> /dev/null; then
    VOLUME_ID=$(isoinfo -d -i "$ISO_FILE" 2>/dev/null | grep "Volume id:" | cut -d':' -f2 | xargs)
    echo "Volume ID: $VOLUME_ID"
    
    # Check for key files
    echo ""
    echo "Checking required files..."
    
    # Extract file list
    FILE_LIST=$(isoinfo -f -i "$ISO_FILE" 2>/dev/null)
    
    # Check EFI boot
    if echo "$FILE_LIST" | grep -qi "EFI"; then
        pass "EFI boot directory present"
    else
        warn "No EFI boot directory"
    fi
    
    # Check for squashfs
    if echo "$FILE_LIST" | grep -qi "squashfs"; then
        pass "Squashfs filesystem present"
    else
        warn "No squashfs found"
    fi
    
    # Check for LLM data
    if echo "$FILE_LIST" | grep -qi "llm-data"; then
        pass "LLM data directory present"
    else
        warn "No llm-data directory"
    fi
    
    # Check for first-boot script
    if echo "$FILE_LIST" | grep -qi "first-boot"; then
        pass "First-boot script present"
    else
        warn "No first-boot script"
    fi
    
elif command -v 7z &> /dev/null; then
    echo "Using 7z to inspect..."
    
    # List contents
    CONTENTS=$(7z l "$ISO_FILE" 2>/dev/null)
    
    if echo "$CONTENTS" | grep -qi "EFI"; then
        pass "EFI boot directory present"
    else
        warn "No EFI boot directory"
    fi
    
    if echo "$CONTENTS" | grep -qi "llm-data"; then
        pass "LLM data directory present"
    else
        warn "No llm-data directory"
    fi
else
    warn "Install isoinfo or 7z for detailed inspection"
fi

echo ""
echo "## Checksums"

# Check if checksum files exist
SHA256_FILE="${ISO_FILE}.sha256"
MD5_FILE="${ISO_FILE}.md5"

if [ -f "$SHA256_FILE" ]; then
    echo "Verifying SHA256..."
    cd "$(dirname "$ISO_FILE")"
    if sha256sum -c "$(basename "$SHA256_FILE")" 2>/dev/null; then
        pass "SHA256 checksum valid"
    else
        fail "SHA256 checksum mismatch"
    fi
else
    warn "No SHA256 checksum file"
fi

if [ -f "$MD5_FILE" ]; then
    echo "Verifying MD5..."
    cd "$(dirname "$ISO_FILE")"
    if md5sum -c "$(basename "$MD5_FILE")" 2>/dev/null; then
        pass "MD5 checksum valid"
    else
        fail "MD5 checksum mismatch"
    fi
else
    warn "No MD5 checksum file"
fi

echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}Verification passed${NC}"
    echo ""
    echo "Next steps:"
    echo "  Test in VM:    make iso-test"
    echo "  Flash to USB:  Use Balena Etcher"
else
    echo -e "${RED}Verification failed with $ERRORS error(s)${NC}"
    echo ""
    echo "Try rebuilding:"
    echo "  make iso-cache-clean"
    echo "  make iso-build"
fi
echo "=========================================="

exit $ERRORS
