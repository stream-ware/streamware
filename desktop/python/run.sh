#!/bin/bash
# Run Voice Shell Desktop without Conda library conflicts

# Remove conda paths from LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -v conda | grep -v miniconda | tr '\n' ':' | sed 's/:$//')

# Ensure system libraries are first
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/lib:$LD_LIBRARY_PATH"

# Change to script directory
cd "$(dirname "$0")"

# Use the venv but with fixed library path
VENV_PYTHON="/home/tom/github/stream-ware/streamware/venv/bin/python3"

if [ -f "$VENV_PYTHON" ]; then
    echo "🚀 Starting Voice Shell Desktop (venv + system libs)..."
    exec "$VENV_PYTHON" app.py "$@"
else
    echo "❌ venv not found at $VENV_PYTHON"
    echo "   Run: python3 -m venv /home/tom/github/stream-ware/streamware/venv"
    exit 1
fi
