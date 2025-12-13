#!/bin/bash
# =============================================================================
# Setup script for UM790 Pro host system with ROCm for Radeon 780M
# Run this ONCE on the host system before using containers
# =============================================================================

set -e

echo "=========================================="
echo "UM790 Pro ROCm Setup for Radeon 780M"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Detect distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "Cannot detect distribution"
    exit 1
fi

echo "[1/5] Adding user to video group..."
usermod -aG video $SUDO_USER 2>/dev/null || true
usermod -aG render $SUDO_USER 2>/dev/null || true

echo "[2/5] Installing ROCm dependencies..."
case $DISTRO in
    ubuntu|debian)
        apt-get update
        apt-get install -y \
            rocm-hip-runtime \
            rocm-libs \
            rocm-dev \
            rocm-smi-lib \
            amdgpu-dkms
        ;;
    fedora)
        dnf install -y \
            rocm-hip-runtime \
            rocm-libs \
            rocm-smi
        ;;
    arch|endeavouros|manjaro)
        pacman -S --noconfirm \
            rocm-hip-runtime \
            rocm-opencl-runtime \
            rocm-smi-lib
        ;;
    *)
        echo "Unsupported distribution: $DISTRO"
        echo "Please install ROCm manually"
        ;;
esac

echo "[3/5] Setting up AMD GPU environment..."
cat > /etc/profile.d/rocm.sh << 'EOF'
export ROCM_PATH=/opt/rocm
export PATH=$PATH:$ROCM_PATH/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ROCM_PATH/lib
export HSA_OVERRIDE_GFX_VERSION=11.0.0
EOF

echo "[4/5] Installing Podman..."
case $DISTRO in
    ubuntu|debian)
        apt-get install -y podman podman-compose
        ;;
    fedora)
        dnf install -y podman podman-compose
        ;;
    arch|endeavouros|manjaro)
        pacman -S --noconfirm podman podman-compose
        ;;
esac

echo "[5/5] Verifying GPU detection..."
if command -v rocm-smi &> /dev/null; then
    rocm-smi --showproductname || echo "GPU not yet detected (reboot may be required)"
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo "Please REBOOT your system before running containers."
echo "After reboot, run: ./start.sh"
echo "=========================================="
