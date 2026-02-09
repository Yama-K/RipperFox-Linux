#!/usr/bin/env bash
set -euo pipefail

# Install Python dependencies for RipperFox (Linux/macOS)
VENV='.venv'

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $(pwd)"
echo "Script directory: $SCRIPT_DIR"

# Ensure python3 is available
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found. Install Python 3 first." >&2
  exit 1
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
  echo "ERROR: requirements.txt not found in $(pwd)" >&2
  echo "Looking for requirements.txt..." >&2
  find . -name "requirements.txt" -type f 2>/dev/null || true
  exit 1
fi

echo "Found requirements.txt at: $(pwd)/requirements.txt"

# Check if PyQt5 system packages are available
echo "Checking for system dependencies..."
if command -v apt-get >/dev/null 2>&1; then
  echo "Detected Debian/Ubuntu system"
  echo "Note: PyQt5 is often better installed via system package manager"
  echo "You can run: sudo apt-get install python3-pyqt5 python3-pyqt5.qtwebengine"
elif command -v pacman >/dev/null 2>&1; then
  echo "Detected Arch Linux system"
  echo "Consider running: sudo pacman -S python-pyqt5"
elif command -v dnf >/dev/null 2>&1; then
  echo "Detected Fedora system"
  echo "Consider running: sudo dnf install python3-qt5"
fi

# Ask user if they want to install system PyQt5
read -p "Do you want to install PyQt5 system package now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-pyqt5 python3-pyqt5.qtwebengine
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm python-pyqt5
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3-qt5
  fi
fi

# Create virtualenv
echo "Creating virtualenv at ${VENV}..."
python3 -m venv "${VENV}"

# Upgrade pip in venv and install requirements
echo "Installing dependencies into ${VENV}..."
"${VENV}/bin/python" -m pip install --upgrade pip
echo "Installing packages from requirements.txt..."
"${VENV}/bin/pip" install -r requirements.txt

echo ""
echo "=" * 50
echo "Dependencies installed into ${VENV}."
echo ""
echo "To activate the virtual environment:"
echo "  source ${VENV}/bin/activate"
echo ""
echo "To run RipperFox:"
echo "  python3 ripperfox_launcher.py"
echo ""
echo "To run in background (detached):"
echo "  python3 ripperfox_launcher.py --detach"
echo "=" * 50