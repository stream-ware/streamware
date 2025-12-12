#!/bin/bash
# Deactivate conda to avoid library conflicts
unset CONDA_PREFIX
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

cd "$(dirname "$0")"
/usr/bin/python3 app.py "$@"

