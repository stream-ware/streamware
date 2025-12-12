#!/bin/bash
# Run Voice Shell Desktop - use env -i for clean environment

cd "$(dirname "$0")"

echo "🚀 Starting Voice Shell Desktop (clean environment)..."

# Run with completely clean environment, only essential vars
exec env -i \
    HOME="$HOME" \
    PATH="/usr/bin:/bin" \
    DISPLAY="$DISPLAY" \
    WAYLAND_DISPLAY="$WAYLAND_DISPLAY" \
    XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
    DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" \
    PYTHONPATH="/home/tom/github/stream-ware/streamware" \
    /usr/bin/python3 -c "
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
sys.path.insert(0, '/home/tom/github/stream-ware/streamware/venv/lib/python3.13/site-packages')
sys.path.insert(0, '/home/tom/github/stream-ware/streamware')
sys.path.insert(0, '.')
exec(open('app.py').read())
"
