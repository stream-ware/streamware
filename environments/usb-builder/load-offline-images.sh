#!/bin/bash
# =============================================================================
# Load pre-saved container images (run this on the USB-booted system)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_DIR="$SCRIPT_DIR/cache/images"

echo "=========================================="
echo "Loading offline container images"
echo "=========================================="

if [ ! -d "$CACHE_DIR" ]; then
    echo "Cache directory not found: $CACHE_DIR"
    echo "Run prepare-offline.sh first while connected to internet"
    exit 1
fi

echo ""
echo "[1/3] Loading Ollama image..."
if [ -f "$CACHE_DIR/ollama-rocm.tar" ]; then
    podman load -i "$CACHE_DIR/ollama-rocm.tar"
    echo "  ✓ Loaded"
else
    echo "  ⚠ Not found"
fi

echo ""
echo "[2/3] Loading Open-WebUI image..."
if [ -f "$CACHE_DIR/open-webui.tar" ]; then
    podman load -i "$CACHE_DIR/open-webui.tar"
    echo "  ✓ Loaded"
else
    echo "  ⚠ Not found"
fi

echo ""
echo "[3/3] Loading llama.cpp image..."
if [ -f "$CACHE_DIR/llama-cpp-rocm.tar" ]; then
    podman load -i "$CACHE_DIR/llama-cpp-rocm.tar"
    echo "  ✓ Loaded"
else
    echo "  ⚠ Not found"
fi

echo ""
echo "=========================================="
echo "Loaded images:"
podman images
echo "=========================================="
