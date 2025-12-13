#!/bin/bash
# =============================================================================
# Stop llama.cpp server
# =============================================================================

echo "Stopping llama-server..."
podman stop llama-server 2>/dev/null || true
podman rm llama-server 2>/dev/null || true

podman stop llama-webui 2>/dev/null || true
podman rm llama-webui 2>/dev/null || true

echo "Server stopped."
