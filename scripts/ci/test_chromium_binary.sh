#!/bin/bash
set -e

echo "=== Running Chromium directly to capture crash output ==="
CHROMIUM_PATH=$(python3 -c "from pyppeteer.chromium_downloader import chromium_executable; print(chromium_executable())")

echo "Attempting to run: $CHROMIUM_PATH --version"
timeout 5s "$CHROMIUM_PATH" --version 2>&1 || echo "Exit code: $?"

echo ""
echo "=== Attempting to run Chromium with browser flags ==="
timeout 5s "$CHROMIUM_PATH" \
  --headless \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --dump-dom \
  data:text/html,test 2>&1 || echo "Exit code: $?"
