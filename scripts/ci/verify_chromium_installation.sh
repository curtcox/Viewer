#!/bin/bash
set -e

python3 scripts/verify-chromium.py

echo ""
echo "=== Listing pyppeteer directory ==="
ls -la ~/.local/share/pyppeteer/ || echo "pyppeteer directory not found"
ls -la ~/.local/share/pyppeteer/local-chromium/ || echo "chromium directory not found"

echo ""
echo "=== Environment info ==="
echo "HOME: $HOME"
echo "USER: $USER"
echo "PWD: $PWD"
