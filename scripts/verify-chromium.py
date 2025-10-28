#!/usr/bin/env python3
"""Verify pyppeteer and Chromium installation for CI diagnostics."""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Check pyppeteer installation and Chromium binary availability."""

    print("=== Checking pyppeteer installation ===")
    try:
        import pyppeteer
        print(f"pyppeteer version: {pyppeteer.__version__}")
    except ImportError as e:
        print(f"✗ Failed to import pyppeteer: {e}")
        return 1

    print("\n=== Checking Chromium browser path ===")
    try:
        from pyppeteer.chromium_downloader import current_platform, chromium_executable

        platform = current_platform()
        chromium_path = chromium_executable()

        print(f"Platform: {platform}")
        print(f"Expected Chromium path: {chromium_path}")

        if os.path.exists(chromium_path):
            print("✓ Chromium binary exists")
            stat_info = os.stat(chromium_path)
            print(f"Permissions: {oct(stat_info.st_mode)[-3:]}")
            print(f"Size: {stat_info.st_size} bytes")
        else:
            print("✗ Chromium binary NOT FOUND")
            return 1

    except Exception as e:
        print(f"✗ Error checking Chromium: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
