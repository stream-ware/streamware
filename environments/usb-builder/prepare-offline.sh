#!/bin/bash
# =============================================================================
# Prepare all resources for offline USB/ISO
# Run this script while connected to internet to download everything needed
#
# CACHING: All downloads are cached - re-running skips existing files
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"
CACHE_DIR="${CACHE_DIR:-$SCRIPT_DIR/cache}"

source "$SCRIPT_DIR/config.sh" 2>/dev/null || true
ENABLE_OPENWEBUI="${ENABLE_OPENWEBUI:-true}"

echo "=========================================="
echo "Preparing Offline LLM Station"
echo "=========================================="
echo "Cache directory: $CACHE_DIR"

# Create cache directories
mkdir -p "$CACHE_DIR/images" "$CACHE_DIR/iso"

# Helper function for checking cached files
check_cached() {
    local file="$1"
    local desc="$2"
    if [ -f "$file" ]; then
        local size=$(du -h "$file" | cut -f1)
        echo "  ✓ Cached: $desc ($size)"
        return 0
    fi
    return 1
}

echo ""
echo "[1/6] Checking Ollama models..."
if [ -d "$ENV_DIR/ollama-webui/models" ] && [ "$(ls -A $ENV_DIR/ollama-webui/models 2>/dev/null)" ]; then
    MODELS_SIZE=$(du -sh "$ENV_DIR/ollama-webui/models" | cut -f1)
    echo "  ✓ Ollama models cached ($MODELS_SIZE)"
else
    echo "  Downloading Ollama models..."
    cd "$ENV_DIR/ollama-webui"
    ./download-models.sh || echo "  ⚠ Ollama model download skipped (run manually if needed)"
fi

echo ""
echo "[2/6] Checking GGUF models for llama.cpp..."
if [ -d "$ENV_DIR/llama-cpp-rocm/models" ] && [ "$(ls -A $ENV_DIR/llama-cpp-rocm/models/*.gguf 2>/dev/null)" ]; then
    MODELS_SIZE=$(du -sh "$ENV_DIR/llama-cpp-rocm/models" | cut -f1)
    echo "  ✓ GGUF models cached ($MODELS_SIZE)"
else
    echo "  Downloading GGUF models..."
    cd "$ENV_DIR/llama-cpp-rocm"
    ./download-models.sh || echo "  ⚠ GGUF model download skipped (run manually if needed)"
fi

echo ""
echo "[3/6] Checking container images..."

# Check if we have podman or docker
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
else
    echo "  ⚠ No container runtime found (podman/docker)"
    echo "    Skipping container image caching"
    CONTAINER_CMD=""
fi

if [ -n "$CONTAINER_CMD" ]; then
    # Ollama image
    if ! check_cached "$CACHE_DIR/images/ollama-rocm.tar" "ollama/ollama:rocm"; then
        echo "  Pulling ollama/ollama:rocm..."
        $CONTAINER_CMD pull ollama/ollama:rocm || $CONTAINER_CMD pull ollama/ollama:latest
        echo "  Saving to cache..."
        $CONTAINER_CMD save ollama/ollama:rocm -o "$CACHE_DIR/images/ollama-rocm.tar" 2>/dev/null || \
        $CONTAINER_CMD save ollama/ollama:latest -o "$CACHE_DIR/images/ollama-rocm.tar"
    fi
    
    # Open-WebUI image
    if [ "$ENABLE_OPENWEBUI" = "true" ]; then
        if ! check_cached "$CACHE_DIR/images/open-webui.tar" "open-webui"; then
            echo "  Pulling ghcr.io/open-webui/open-webui:main..."
            $CONTAINER_CMD pull ghcr.io/open-webui/open-webui:main
            echo "  Saving to cache..."
            $CONTAINER_CMD save ghcr.io/open-webui/open-webui:main -o "$CACHE_DIR/images/open-webui.tar"
        fi
    else
        echo "  Skipping Open-WebUI image cache (ENABLE_OPENWEBUI=$ENABLE_OPENWEBUI)"
    fi
fi

echo ""
echo "[4/6] Checking llama.cpp ROCm image..."
if [ -n "$CONTAINER_CMD" ]; then
    if ! check_cached "$CACHE_DIR/images/llama-cpp-rocm.tar" "llama-cpp-rocm"; then
        echo "  Building llama.cpp ROCm image (this may take 10-15 minutes)..."
        cd "$ENV_DIR/llama-cpp-rocm"
        if [ -f "Dockerfile" ]; then
            $CONTAINER_CMD build -t llama-cpp-rocm . && \
            $CONTAINER_CMD save llama-cpp-rocm -o "$CACHE_DIR/images/llama-cpp-rocm.tar"
        else
            echo "  ⚠ Dockerfile not found, skipping"
        fi
    fi
fi

echo ""
echo "[5/6] Checking base ISO cache..."
# Pre-download base ISO for faster ISO builds
BASE_ISO_URL="https://download.fedoraproject.org/pub/fedora/linux/releases/40/Spins/x86_64/iso/Fedora-LXQt-Live-x86_64-40-1.14.iso"
BASE_ISO_NAME="Fedora-LXQt-Live-x86_64-40-1.14.iso"
CACHED_ISO="$CACHE_DIR/iso/$BASE_ISO_NAME"

if ! check_cached "$CACHED_ISO" "Fedora LXQt ISO"; then
    echo "  Downloading base ISO (this may take a while)..."
    curl -L "$BASE_ISO_URL" -o "$CACHED_ISO" --progress-bar
fi

echo ""
echo "[6/6] Calculating cache sizes..."

# Calculate sizes
TOTAL_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1 || echo "0")
IMAGES_SIZE=$(du -sh "$CACHE_DIR/images" 2>/dev/null | cut -f1 || echo "0")
ISO_SIZE=$(du -sh "$CACHE_DIR/iso" 2>/dev/null | cut -f1 || echo "0")

echo ""
echo "=========================================="
echo "Offline preparation complete!"
echo "=========================================="
echo ""
echo "Cache location: $CACHE_DIR"
echo ""
echo "Cached items:"
echo "  Container images: $IMAGES_SIZE"
ls -1h "$CACHE_DIR/images/"*.tar 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo ""
echo "  Base ISO: $ISO_SIZE"
ls -1h "$CACHE_DIR/iso/"*.iso 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo ""
echo "  Ollama models:"
du -sh "$ENV_DIR/ollama-webui/models" 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo ""
echo "  GGUF models:"
du -sh "$ENV_DIR/llama-cpp-rocm/models" 2>/dev/null | sed 's/^/    /' || echo "    (none)"
echo ""
echo "Total cache size: $TOTAL_SIZE"
echo ""
echo "Next steps:"
echo "  Create USB:  sudo ./build-usb.sh /dev/sdX"
echo "  Create ISO:  sudo ./build-iso.sh"
echo "=========================================="
