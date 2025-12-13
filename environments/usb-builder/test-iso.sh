#!/bin/bash
# =============================================================================
# Test ISO in QEMU/KVM Virtual Machine
# Usage: ./test-iso.sh [--gui]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_FILE="${ISO_FILE:-$SCRIPT_DIR/output/llm-station-um790pro.iso}"
RAM="${RAM:-8G}"
CPUS="${CPUS:-4}"
# Find available port starting from 8080
find_free_port() {
    local port=${1:-8080}
    while ss -tuln 2>/dev/null | grep -q ":$port "; do
        port=$((port + 1))
        [ $port -gt 9000 ] && return 1
    done
    echo $port
}

HOST_PORT=$(find_free_port 8080)
PORT_FORWARD="${PORT_FORWARD:-$HOST_PORT:3000}"

# Parse arguments
USE_GUI=false
for arg in "$@"; do
    case $arg in
        --gui)
            USE_GUI=true
            ;;
        --iso=*)
            ISO_FILE="${arg#*=}"
            ;;
        --ram=*)
            RAM="${arg#*=}"
            ;;
        --cpus=*)
            CPUS="${arg#*=}"
            ;;
    esac
done

echo "=========================================="
echo "LLM Station ISO Tester"
echo "=========================================="
echo "ISO: $ISO_FILE"
echo "RAM: $RAM"
echo "CPUs: $CPUS"
echo "Port forward: localhost:${PORT_FORWARD%:*} → VM:${PORT_FORWARD#*:}"
echo ""

# Check ISO exists
if [ ! -f "$ISO_FILE" ]; then
    echo "Error: ISO file not found: $ISO_FILE"
    echo ""
    echo "Build it first with:"
    echo "  make iso-build"
    exit 1
fi

# Check for virtualization support
if [ ! -e /dev/kvm ]; then
    echo "Warning: KVM not available, using software emulation (slower)"
    KVM_FLAG=""
else
    KVM_FLAG="-enable-kvm"
fi

if $USE_GUI; then
    # Use virt-manager
    if ! command -v virt-manager &> /dev/null; then
        echo "Installing virt-manager..."
        if [ -f /etc/fedora-release ]; then
            sudo dnf install -y virt-manager
        elif [ -f /etc/debian_version ]; then
            sudo apt-get install -y virt-manager
        else
            echo "Please install virt-manager manually"
            exit 1
        fi
    fi
    
    echo "Opening virt-manager..."
    echo ""
    echo "To create a new VM:"
    echo "  1. File → New Virtual Machine"
    echo "  2. Select 'Local install media (ISO image)'"
    echo "  3. Browse to: $ISO_FILE"
    echo "  4. Set RAM to 8192 MB, CPUs to 4+"
    echo "  5. Enable 'Customize before install'"
    echo "  6. In Overview, set Firmware to 'UEFI x86_64'"
    echo "  7. Begin installation"
    echo ""
    virt-manager &
else
    # Use QEMU directly
    if ! command -v qemu-system-x86_64 &> /dev/null; then
        echo "Installing QEMU..."
        if [ -f /etc/fedora-release ]; then
            sudo dnf install -y qemu-kvm qemu-system-x86
        elif [ -f /etc/debian_version ]; then
            sudo apt-get install -y qemu-kvm qemu-system-x86
        else
            echo "Please install qemu-kvm manually"
            exit 1
        fi
    fi
    
    echo "Starting QEMU..."
    echo ""
    echo "Controls:"
    echo "  Ctrl+Alt+G    - Release mouse grab"
    echo "  Ctrl+Alt+F    - Toggle fullscreen"
    echo "  Ctrl+Alt+Q    - Quit"
    echo ""
    echo "After boot, run:"
    echo "  sudo /cdrom/llm-data/first-boot.sh"
    echo ""
    echo "Access Open-WebUI at: http://localhost:${PORT_FORWARD%:*}"
    echo ""
    
    # Create UEFI firmware path
    OVMF_CODE=""
    for path in \
        "/usr/share/OVMF/OVMF_CODE.fd" \
        "/usr/share/OVMF/OVMF_CODE_4M.fd" \
        "/usr/share/edk2/ovmf/OVMF_CODE.fd" \
        "/usr/share/qemu/OVMF_CODE.fd" \
        "/usr/share/edk2-ovmf/x64/OVMF_CODE.fd" \
        "/usr/share/ovmf/OVMF.fd"; do
        if [ -f "$path" ]; then
            OVMF_CODE="$path"
            break
        fi
    done
    
    if [ -z "$OVMF_CODE" ]; then
        echo ""
        echo -e "${YELLOW}Warning: UEFI firmware not found${NC}"
        echo "The ISO requires UEFI boot. Install OVMF:"
        echo "  Ubuntu/Debian: sudo apt install ovmf"
        echo "  Fedora: sudo dnf install edk2-ovmf"
        echo ""
        echo "Attempting BIOS mode (may not boot)..."
        UEFI_FLAGS=""
    else
        echo "Using UEFI firmware: $OVMF_CODE"
        # Use -drive with pflash for proper UEFI boot
        UEFI_FLAGS="-drive if=pflash,format=raw,readonly=on,file=$OVMF_CODE"
    fi
    
    qemu-system-x86_64 \
        $KVM_FLAG \
        -m "$RAM" \
        -smp "$CPUS" \
        -cpu host \
        $UEFI_FLAGS \
        -cdrom "$ISO_FILE" \
        -boot d \
        -display gtk \
        -device virtio-net,netdev=n0 \
        -netdev user,id=n0,hostfwd=tcp::${PORT_FORWARD%:*}-:${PORT_FORWARD#*:} \
        -usb \
        -device usb-tablet
fi
