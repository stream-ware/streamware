#!/bin/bash
# =============================================================================
# Prepare all resources for offline USB
# Run this script while connected to internet to download everything needed
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Preparing Offline LLM Station"
echo "=========================================="

# Create cache directory
CACHE_DIR="$SCRIPT_DIR/cache"
mkdir -p "$CACHE_DIR/images" "$CACHE_DIR/models"

echo ""
echo "[1/5] Downloading Ollama models..."
cd "$ENV_DIR/ollama-webui"
./download-models.sh

echo ""
echo "[2/5] Downloading GGUF models for llama.cpp..."
cd "$ENV_DIR/llama-cpp-rocm"
./download-models.sh

echo ""
echo "[3/5] Pulling container images..."
echo "  → ollama/ollama:rocm"
podman pull ollama/ollama:rocm

echo "  → ghcr.io/open-webui/open-webui:main"
podman pull ghcr.io/open-webui/open-webui:main

echo ""
echo "[4/5] Saving container images for offline use..."
echo "  Saving ollama image..."
podman save ollama/ollama:rocm -o "$CACHE_DIR/images/ollama-rocm.tar"

echo "  Saving open-webui image..."
podman save ghcr.io/open-webui/open-webui:main -o "$CACHE_DIR/images/open-webui.tar"

echo ""
echo "[5/5] Building llama.cpp image..."
cd "$ENV_DIR/llama-cpp-rocm"
podman build -t llama-cpp-rocm .
podman save llama-cpp-rocm -o "$CACHE_DIR/images/llama-cpp-rocm.tar"

# Calculate total size
TOTAL_SIZE=$(du -sh "$CACHE_DIR" | cut -f1)
MODELS_SIZE=$(du -sh "$ENV_DIR"/*/models 2>/dev/null | awk '{sum+=$1} END {print sum}')

echo ""
echo "=========================================="
echo "Offline preparation complete!"
echo ""
echo "Cache location: $CACHE_DIR"
echo "Total cache size: $TOTAL_SIZE"
echo ""
echo "Contents:"
ls -lh "$CACHE_DIR/images/"
echo ""
echo "Models:"
du -sh "$ENV_DIR"/*/models 2>/dev/null
echo ""
echo "To create USB, run:"
echo "  sudo ./build-usb.sh /dev/sdX"
echo "=========================================="
