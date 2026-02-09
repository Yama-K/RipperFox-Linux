#!/usr/bin/env bash
set -euo pipefail

# Run the launcher (tray icon + backend). Prefer .venv/python if present.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv"
if [ -x "$VENV/bin/python" ]; then
    PY="$VENV/bin/python"
else
    PY="$(command -v python3 || command -v python || true)"
    if [ -z "$PY" ]; then
        echo "python3 is required but not found. Install Python 3 or run './python_install.sh' to create a virtualenv." >&2
        exit 1
    fi
fi

echo "Using Python: $PY"
echo "Running RipperFox launcher (PyQt5 version)..."
"$PY" ripperfox_launcher.py || {
    rc=$?
    echo "Launcher exited with code $rc." >&2
    exit $rc
}
