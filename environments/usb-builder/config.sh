#!/bin/bash
# =============================================================================
# LLM Station USB/ISO Builder Configuration
# =============================================================================
#
# This file contains all configurable values for the build scripts.
# Override any value by setting environment variables before running scripts.
#
# Example:
#   DISTRO=ubuntu ISO_NAME=my-custom.iso ./build-iso.sh
#
# Or create a .env file in this directory with your overrides.
#
# =============================================================================

# Load .env file if exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# =============================================================================
# Output Configuration
# =============================================================================

# ISO filename
ISO_NAME="${ISO_NAME:-llm-station-um790pro.iso}"

# Output directory
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR/output}"

# Cache directory
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"

# =============================================================================
# Base Distribution
# =============================================================================

# Base distro: fedora or ubuntu
DISTRO="${DISTRO:-fedora}"

# Fedora ISO URL and name
BASE_ISO_URL_FEDORA="https://download.fedoraproject.org/pub/fedora/linux/releases/40/Spins/x86_64/iso/Fedora-LXQt-Live-x86_64-40-1.14.iso"
BASE_ISO_NAME_FEDORA="Fedora-LXQt-Live-x86_64-40-1.14.iso"

# Ubuntu ISO URL and name
BASE_ISO_URL_UBUNTU="https://releases.ubuntu.com/24.04/ubuntu-24.04-desktop-amd64.iso"
BASE_ISO_NAME_UBUNTU="ubuntu-24.04-desktop-amd64.iso"

# openSUSE Tumbleweed KDE Live ISO
BASE_ISO_URL_SUSE="https://download.opensuse.org/tumbleweed/iso/openSUSE-Tumbleweed-KDE-Live-x86_64-Current.iso"
BASE_ISO_NAME_SUSE="openSUSE-Tumbleweed-KDE-Live-x86_64-Current.iso"

# openSUSE Leap (stable) - alternative
BASE_ISO_URL_SUSE_LEAP="https://download.opensuse.org/distribution/leap/15.5/live/openSUSE-Leap-15.5-KDE-Live-x86_64-Media.iso"
BASE_ISO_NAME_SUSE_LEAP="openSUSE-Leap-15.5-KDE-Live-x86_64-Media.iso"

# Get URL and name based on selected distro
get_base_iso_url() {
    case "${DISTRO}" in
        fedora) echo "$BASE_ISO_URL_FEDORA" ;;
        ubuntu) echo "$BASE_ISO_URL_UBUNTU" ;;
        suse|opensuse) echo "$BASE_ISO_URL_SUSE" ;;
        suse-leap) echo "$BASE_ISO_URL_SUSE_LEAP" ;;
        *) echo "$BASE_ISO_URL_FEDORA" ;;
    esac
}

get_base_iso_name() {
    case "${DISTRO}" in
        fedora) echo "$BASE_ISO_NAME_FEDORA" ;;
        ubuntu) echo "$BASE_ISO_NAME_UBUNTU" ;;
        suse|opensuse) echo "$BASE_ISO_NAME_SUSE" ;;
        suse-leap) echo "$BASE_ISO_NAME_SUSE_LEAP" ;;
        *) echo "$BASE_ISO_NAME_FEDORA" ;;
    esac
}

# =============================================================================
# Container Images
# =============================================================================

# Container images to include
CONTAINER_IMAGES=(
    "ollama/ollama:rocm"
    "ghcr.io/open-webui/open-webui:main"
)

# Fallback images (if ROCm not available)
CONTAINER_IMAGES_FALLBACK=(
    "ollama/ollama:latest"
    "ghcr.io/open-webui/open-webui:main"
)

# =============================================================================
# Hardware Configuration
# =============================================================================

# Target hardware
TARGET_HARDWARE="${TARGET_HARDWARE:-um790pro}"

# GPU configuration for ROCm
HSA_OVERRIDE_GFX_VERSION="${HSA_OVERRIDE_GFX_VERSION:-11.0.0}"

# GPU devices for container passthrough
GPU_DEVICES=(
    "/dev/kfd"
    "/dev/dri"
)

# =============================================================================
# QEMU/VM Testing
# =============================================================================

# Default RAM for VM testing
RAM_DEFAULT="${RAM_DEFAULT:-8G}"

# Default CPUs for VM testing
CPUS_DEFAULT="${CPUS_DEFAULT:-4}"

# Port forwarding (host:guest)
PORT_FORWARD_DEFAULT="${PORT_FORWARD_DEFAULT:-8080:3000}"

# =============================================================================
# LLM Models
# =============================================================================

# Ollama models to pre-download
OLLAMA_MODELS=(
    "llama3.2:3b"
    "llava:7b"
)

# GGUF models for llama.cpp
GGUF_MODELS=(
    "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
)

# =============================================================================
# Paths
# =============================================================================

# Environment directory (parent of usb-builder)
ENV_DIR="${ENV_DIR:-$(dirname "$SCRIPT_DIR")}"

# Ollama-WebUI environment
OLLAMA_WEBUI_DIR="$ENV_DIR/ollama-webui"

# llama.cpp ROCm environment
LLAMA_CPP_DIR="$ENV_DIR/llama-cpp-rocm"

# =============================================================================
# Build Options
# =============================================================================

# Minimum ISO size to consider valid (bytes)
MIN_ISO_SIZE="${MIN_ISO_SIZE:-500000000}"

# Enable verbose output
VERBOSE="${VERBOSE:-false}"

# Dry run mode (don't actually build)
DRY_RUN="${DRY_RUN:-false}"

# =============================================================================
# Helper Functions
# =============================================================================

# Print configuration
print_config() {
    echo "=== LLM Station Configuration ==="
    echo ""
    echo "Output:"
    echo "  ISO_NAME=$ISO_NAME"
    echo "  OUTPUT_DIR=$OUTPUT_DIR"
    echo "  CACHE_DIR=$CACHE_DIR"
    echo ""
    echo "Distribution:"
    echo "  DISTRO=$DISTRO"
    echo "  BASE_ISO=$(get_base_iso_name)"
    echo ""
    echo "Hardware:"
    echo "  TARGET_HARDWARE=$TARGET_HARDWARE"
    echo "  HSA_OVERRIDE_GFX_VERSION=$HSA_OVERRIDE_GFX_VERSION"
    echo ""
    echo "VM Testing:"
    echo "  RAM_DEFAULT=$RAM_DEFAULT"
    echo "  CPUS_DEFAULT=$CPUS_DEFAULT"
    echo ""
    echo "Container Images:"
    for img in "${CONTAINER_IMAGES[@]}"; do
        echo "  - $img"
    done
    echo ""
}

# Validate configuration
validate_config() {
    local errors=0
    
    # Check distro
    case "$DISTRO" in
        fedora|ubuntu) ;;
        *)
            echo "Error: Invalid DISTRO=$DISTRO (use fedora or ubuntu)"
            errors=$((errors + 1))
            ;;
    esac
    
    # Check paths
    if [ ! -d "$ENV_DIR" ]; then
        echo "Warning: ENV_DIR=$ENV_DIR does not exist"
    fi
    
    return $errors
}
