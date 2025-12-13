#!/bin/bash
# =============================================================================
# Start Ollama + Open-WebUI environment
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Starting Ollama + Open-WebUI"
echo "=========================================="

# Check GPU availability
echo "[1/3] Checking GPU..."
if [ -e /dev/kfd ] && [ -e /dev/dri ]; then
    echo "  ✓ AMD GPU devices found"
else
    echo "  ⚠ Warning: GPU devices not found"
    echo "    /dev/kfd: $([ -e /dev/kfd ] && echo 'found' || echo 'missing')"
    echo "    /dev/dri: $([ -e /dev/dri ] && echo 'found' || echo 'missing')"
fi

# Check if models exist
echo "[2/3] Checking models..."
if [ -d "$SCRIPT_DIR/models" ] && [ "$(ls -A $SCRIPT_DIR/models 2>/dev/null)" ]; then
    echo "  ✓ Models directory found"
else
    echo "  ⚠ No models found. Run ./download-models.sh first"
fi

# Start containers
echo "[3/3] Starting containers..."
if command -v podman-compose &> /dev/null; then
    podman-compose up -d
elif command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    echo "Starting with podman directly..."
    
    # Create network
    podman network create ollama-net 2>/dev/null || true
    
    # Start Ollama
    podman run -d --name ollama \
        --network ollama-net \
        --group-add video \
        --device /dev/kfd \
        --device /dev/dri \
        -p 11434:11434 \
        -v "$SCRIPT_DIR/models:/root/.ollama" \
        -e OLLAMA_HOST=0.0.0.0 \
        -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
        --restart unless-stopped \
        ollama/ollama:rocm 2>/dev/null || \
    podman start ollama
    
    # Wait for Ollama
    sleep 3
    
    # Start Open-WebUI
    podman run -d --name open-webui \
        --network ollama-net \
        -p 3000:8080 \
        -v "$SCRIPT_DIR/webui-data:/app/backend/data" \
        -e OLLAMA_BASE_URL=http://ollama:11434 \
        -e WEBUI_AUTH=false \
        --restart unless-stopped \
        ghcr.io/open-webui/open-webui:main 2>/dev/null || \
    podman start open-webui
fi

echo ""
echo "=========================================="
echo "Services started!"
echo ""
echo "  Ollama API:   http://localhost:11434"
echo "  Open-WebUI:   http://localhost:3000"
echo ""
echo "Open your browser: http://localhost:3000"
echo "=========================================="
