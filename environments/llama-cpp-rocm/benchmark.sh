#!/bin/bash
# =============================================================================
# Benchmark llama.cpp performance on UM790 Pro
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${1:-model.gguf}"
MODEL_PATH="$SCRIPT_DIR/models/$MODEL"

echo "=========================================="
echo "Benchmarking llama.cpp on UM790 Pro"
echo "Model: $MODEL"
echo "=========================================="

if [ ! -f "$MODEL_PATH" ]; then
    echo "Model not found: $MODEL_PATH"
    exit 1
fi

# Build benchmark if needed
if ! podman image exists llama-cpp-rocm 2>/dev/null; then
    echo "Building image first..."
    podman build -t llama-cpp-rocm .
fi

echo ""
echo "Running benchmark..."
echo ""

podman run --rm \
    --group-add video \
    --device /dev/kfd \
    --device /dev/dri \
    -v "$SCRIPT_DIR/models:/models:ro" \
    -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
    llama-cpp-rocm \
    ./build/bin/llama-bench \
    -m "/models/$MODEL" \
    -ngl 99 \
    -p 512 \
    -n 128

echo ""
echo "=========================================="
echo "Expected performance on 780M (RDNA3):"
echo "  Q4_K_M 7B: ~8-12 tokens/sec"
echo "  Q4_K_M 3B: ~15-25 tokens/sec"
echo "=========================================="
