#!/bin/bash
# =============================================================================
# Stop Ollama + Open-WebUI environment
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping containers..."

if command -v podman-compose &> /dev/null; then
    podman-compose down
elif command -v docker-compose &> /dev/null; then
    docker-compose down
else
    podman stop open-webui ollama 2>/dev/null || true
    podman rm open-webui ollama 2>/dev/null || true
fi

echo "Containers stopped."
