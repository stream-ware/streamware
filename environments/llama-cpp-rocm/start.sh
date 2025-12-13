#!/bin/bash
# =============================================================================
# Start llama.cpp server with ROCm GPU support
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default model
MODEL="${1:-model.gguf}"
MODEL_PATH="$SCRIPT_DIR/models/$MODEL"

echo "=========================================="
echo "Starting llama.cpp with ROCm"
echo "=========================================="

# Check GPU
echo "[1/4] Checking GPU..."
if [ -e /dev/kfd ] && [ -e /dev/dri ]; then
    echo "  ✓ AMD GPU devices found"
else
    echo "  ⚠ Warning: GPU devices not found, will use CPU"
fi

# Check model
echo "[2/4] Checking model..."
if [ -f "$MODEL_PATH" ]; then
    echo "  ✓ Model found: $MODEL"
    MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
    echo "    Size: $MODEL_SIZE"
else
    echo "  ✗ Model not found: $MODEL_PATH"
    echo "    Run ./download-models.sh first"
    echo ""
    echo "Available models:"
    ls -1 "$SCRIPT_DIR/models/"*.gguf 2>/dev/null || echo "  (none)"
    exit 1
fi

# Check if image is built
echo "[3/4] Checking container image..."
if ! podman image exists llama-cpp-rocm 2>/dev/null; then
    echo "  Building image (this may take 10-15 minutes)..."
    podman build -t llama-cpp-rocm .
else
    echo "  ✓ Image exists"
fi

# Start server
echo "[4/4] Starting server..."

# Stop existing container
podman stop llama-server 2>/dev/null || true
podman rm llama-server 2>/dev/null || true

podman run -d --name llama-server \
    --group-add video \
    --device /dev/kfd \
    --device /dev/dri \
    -p 8080:8080 \
    -v "$SCRIPT_DIR/models:/models:ro" \
    -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
    -e HIP_VISIBLE_DEVICES=0 \
    llama-cpp-rocm \
    ./build/bin/llama-server \
    --host 0.0.0.0 \
    --port 8080 \
    -m "/models/$MODEL" \
    -ngl 99 \
    --ctx-size 4096 \
    --parallel 2

# Wait and check
sleep 3

if podman ps | grep -q llama-server; then
    echo ""
    echo "=========================================="
    echo "Server started!"
    echo ""
    echo "  API endpoint:  http://localhost:8080"
    echo "  OpenAI compat: http://localhost:8080/v1"
    echo "  Health check:  http://localhost:8080/health"
    echo ""
    echo "Test with:"
    echo "  curl http://localhost:8080/v1/models"
    echo ""
    echo "Chat example:"
    echo '  curl http://localhost:8080/v1/chat/completions \'
    echo '    -H "Content-Type: application/json" \'
    echo '    -d '\''{"messages":[{"role":"user","content":"Hello!"}]}'\'''
    echo "=========================================="
else
    echo "⚠ Server failed to start. Check logs:"
    echo "  podman logs llama-server"
fi
