#!/usr/bin/env bash
# Simple install script that always works from current directory

# Get absolute path to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing RipperFox dependencies in: $SCRIPT_DIR"

# Check for Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check for venv module
if ! python3 -c "import venv" 2>/dev/null; then
    echo "ERROR: Python venv module not found."
    echo "On Ubuntu/Debian, install it with: sudo apt-get install python3-venv"
    echo "On Arch: sudo pacman -S python-venv"
    exit 1
fi

# Remove old venv if exists
if [ -d ".venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf .venv
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate and install dependencies
echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "To run RipperFox:"
echo "  source .venv/bin/activate"
echo "  python3 ripperfox_launcher.py"
echo ""
echo "Or run directly:"
echo "  .venv/bin/python ripperfox_launcher.py"