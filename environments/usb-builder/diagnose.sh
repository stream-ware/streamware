#!/bin/bash
# =============================================================================
# LLM Station Environment Diagnostics
# Usage: ./diagnose.sh [--full]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"
CACHE_DIR="$SCRIPT_DIR/cache"

FULL_CHECK=false
[ "$1" = "--full" ] && FULL_CHECK=true

echo "=========================================="
echo "LLM Station Diagnostics"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }

# System info
echo "## System Information"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || uname -s)"
echo "Kernel: $(uname -r)"
echo "Arch: $(uname -m)"
echo ""

# Hardware
echo "## Hardware"
if [ -f /proc/cpuinfo ]; then
    CPU=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
    echo "CPU: $CPU"
fi

# GPU detection
echo ""
echo "## GPU Detection"
if command -v lspci &> /dev/null; then
    AMD_GPU=$(lspci | grep -i "VGA.*AMD\|Display.*AMD" | head -1)
    if [ -n "$AMD_GPU" ]; then
        pass "AMD GPU: $AMD_GPU"
    else
        warn "No AMD GPU detected"
    fi
fi

# ROCm
if [ -d /opt/rocm ]; then
    ROCM_VER=$(cat /opt/rocm/.info/version 2>/dev/null || echo "unknown")
    pass "ROCm installed: $ROCM_VER"
else
    warn "ROCm not installed"
fi

# KFD device
if [ -e /dev/kfd ]; then
    pass "/dev/kfd available (GPU compute)"
else
    warn "/dev/kfd not available"
fi

# DRI devices
DRI_COUNT=$(ls /dev/dri/render* 2>/dev/null | wc -l)
if [ "$DRI_COUNT" -gt 0 ]; then
    pass "DRI render nodes: $DRI_COUNT"
else
    warn "No DRI render nodes"
fi

echo ""
echo "## Container Runtime"
if command -v podman &> /dev/null; then
    PODMAN_VER=$(podman --version | cut -d' ' -f3)
    pass "Podman: $PODMAN_VER"
elif command -v docker &> /dev/null; then
    DOCKER_VER=$(docker --version | cut -d' ' -f3 | tr -d ',')
    pass "Docker: $DOCKER_VER"
else
    fail "No container runtime (podman/docker)"
fi

echo ""
echo "## LLM Environments"

# Ollama-WebUI
if [ -d "$ENV_DIR/ollama-webui" ]; then
    pass "ollama-webui environment exists"
    if [ -f "$ENV_DIR/ollama-webui/start.sh" ]; then
        pass "  start.sh present"
    else
        warn "  start.sh missing"
    fi
else
    warn "ollama-webui environment not found"
fi

# llama.cpp ROCm
if [ -d "$ENV_DIR/llama-cpp-rocm" ]; then
    pass "llama-cpp-rocm environment exists"
    if [ -f "$ENV_DIR/llama-cpp-rocm/Dockerfile" ]; then
        pass "  Dockerfile present"
    else
        warn "  Dockerfile missing"
    fi
else
    warn "llama-cpp-rocm environment not found"
fi

echo ""
echo "## Cache Status"

# ISO cache
if [ -d "$CACHE_DIR/iso" ]; then
    ISO_COUNT=$(ls "$CACHE_DIR/iso/"*.iso 2>/dev/null | wc -l)
    if [ "$ISO_COUNT" -gt 0 ]; then
        ISO_SIZE=$(du -sh "$CACHE_DIR/iso" | cut -f1)
        pass "ISO cache: $ISO_COUNT file(s), $ISO_SIZE"
    else
        warn "ISO cache: empty"
    fi
else
    warn "ISO cache directory not found"
fi

# Images cache
if [ -d "$CACHE_DIR/images" ]; then
    IMG_COUNT=$(ls "$CACHE_DIR/images/"*.tar 2>/dev/null | wc -l)
    if [ "$IMG_COUNT" -gt 0 ]; then
        IMG_SIZE=$(du -sh "$CACHE_DIR/images" | cut -f1)
        pass "Container images cache: $IMG_COUNT file(s), $IMG_SIZE"
    else
        warn "Container images cache: empty (run prepare-offline.sh)"
    fi
else
    warn "Container images cache not found"
fi

echo ""
echo "## Output"
if [ -d "$SCRIPT_DIR/output" ]; then
    ISO_OUTPUT=$(ls "$SCRIPT_DIR/output/"*.iso 2>/dev/null | head -1)
    if [ -n "$ISO_OUTPUT" ]; then
        ISO_SIZE=$(du -h "$ISO_OUTPUT" | cut -f1)
        pass "Built ISO: $(basename $ISO_OUTPUT) ($ISO_SIZE)"
    else
        warn "No ISO built yet (run: make iso-build)"
    fi
else
    warn "Output directory not found"
fi

if $FULL_CHECK; then
    echo ""
    echo "## Full Diagnostics"
    
    # Check container images
    echo ""
    echo "### Container Images"
    if command -v podman &> /dev/null; then
        echo "Podman images:"
        podman images --format "  {{.Repository}}:{{.Tag}} ({{.Size}})" 2>/dev/null | head -10
    fi
    
    # Check running containers
    echo ""
    echo "### Running Containers"
    if command -v podman &> /dev/null; then
        RUNNING=$(podman ps --format "{{.Names}}" 2>/dev/null | wc -l)
        if [ "$RUNNING" -gt 0 ]; then
            podman ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null
        else
            echo "  No containers running"
        fi
    fi
    
    # Check ports
    echo ""
    echo "### Port Usage"
    for port in 11434 3000 8080; do
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            echo "  Port $port: IN USE"
        else
            echo "  Port $port: available"
        fi
    done
    
    # Disk space
    echo ""
    echo "### Disk Space"
    df -h "$SCRIPT_DIR" | tail -1 | awk '{print "  Available: " $4 " of " $2}'
    
    # Memory
    echo ""
    echo "### Memory"
    free -h | grep Mem | awk '{print "  Total: " $2 ", Available: " $7}'
fi

echo ""
echo "=========================================="
echo "Diagnostics complete"
echo "=========================================="
