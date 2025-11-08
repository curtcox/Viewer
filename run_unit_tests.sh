#!/bin/bash
# Simple script to run unit tests after a clean checkout
# This script installs dependencies and runs the test suite

set -e  # Exit on error

# Get the script's directory (repository root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages --ignore-installed blinker 2>&1 | grep -E "(Installing|Requirement already|Successfully|ERROR)" || true

echo "==> Running unit tests..."
python3 -m pytest tests/ -m "not integration" -v "$@"
