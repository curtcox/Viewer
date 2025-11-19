#!/bin/bash
set -e

echo "=== Finding Chromium binary ==="
CHROMIUM_PATH=$(python3 -c "from pyppeteer.chromium_downloader import chromium_executable; print(chromium_executable())")
echo "Chromium path: $CHROMIUM_PATH"

if [ -f "$CHROMIUM_PATH" ]; then
    echo ""
    echo "=== Checking for missing shared libraries ==="
    LDD_OUTPUT=$(mktemp)
    if ! ldd "$CHROMIUM_PATH" >"$LDD_OUTPUT"; then
        echo "✗ Failed to inspect shared library dependencies"
        cat "$LDD_OUTPUT"
        exit 1
    fi

    if grep -q "not found" "$LDD_OUTPUT"; then
        echo "✗ Missing shared libraries detected"
        grep "not found" "$LDD_OUTPUT"
    else
        echo "✓ All shared libraries found"
    fi

    echo ""
    echo "=== Listing all shared library dependencies (first 30 lines) ==="
    head -30 "$LDD_OUTPUT"
else
    echo "✗ Chromium binary not found at expected path"
    exit 1
fi
