#!/bin/bash
# =============================================================================
# Download models for offline use
# Run this script BEFORE creating the USB to pre-download all models
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"

echo "=========================================="
echo "Downloading models for offline use"
echo "Target: $MODELS_DIR"
echo "=========================================="

mkdir -p "$MODELS_DIR"

# Start Ollama temporarily to download models
echo "[1/4] Starting temporary Ollama container..."
podman run -d --name ollama-download \
    -v "$MODELS_DIR:/root/.ollama" \
    ollama/ollama:rocm

# Wait for Ollama to start
sleep 5

echo "[2/4] Downloading recommended models for 16GB RAM..."

# Small models (< 4GB) - fast inference
SMALL_MODELS=(
    "llama3.2:3b"
    "phi3:mini"
    "gemma2:2b"
    "qwen2.5:3b"
)

# Medium models (4-8GB) - balanced
MEDIUM_MODELS=(
    "llama3.2:latest"
    "mistral:7b"
    "codellama:7b"
    "deepseek-coder:6.7b"
)

# Large models (8-12GB) - high quality (optional)
LARGE_MODELS=(
    "llama3.1:8b"
    "qwen2.5:7b"
)

echo ""
echo "Downloading small models (recommended)..."
for model in "${SMALL_MODELS[@]}"; do
    echo "  → $model"
    podman exec ollama-download ollama pull "$model" || echo "  ⚠ Failed: $model"
done

echo ""
echo "Downloading medium models..."
for model in "${MEDIUM_MODELS[@]}"; do
    echo "  → $model"
    podman exec ollama-download ollama pull "$model" || echo "  ⚠ Failed: $model"
done

echo ""
read -p "Download large models (requires more USB space)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    for model in "${LARGE_MODELS[@]}"; do
        echo "  → $model"
        podman exec ollama-download ollama pull "$model" || echo "  ⚠ Failed: $model"
    done
fi

echo ""
echo "[3/4] Listing downloaded models..."
podman exec ollama-download ollama list

echo ""
echo "[4/4] Cleaning up..."
podman stop ollama-download
podman rm ollama-download

# Calculate size
TOTAL_SIZE=$(du -sh "$MODELS_DIR" | cut -f1)

echo ""
echo "=========================================="
echo "Download complete!"
echo "Models location: $MODELS_DIR"
echo "Total size: $TOTAL_SIZE"
echo "=========================================="
