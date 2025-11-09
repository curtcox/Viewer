#!/usr/bin/env python3
"""Test pyppeteer browser launch and screenshot capture for CI diagnostics."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


async def test_browser_launch(output_path: Path) -> bool:
    """
    Test launching Chromium and capturing a screenshot.

    Args:
        output_path: Path where the test screenshot should be saved

    Returns:
        True if successful, False otherwise
    """
    try:
        from pyppeteer import launch
    except ImportError as e:
        print(f"✗ Failed to import pyppeteer: {e}")
        return False

    browser = None
    try:
        print("Attempting to launch browser...")
        browser = await launch(
            headless=True,
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            dumpio=True,  # Enable dumping browser process stdout/stderr
        )
        print("✓ Browser launched successfully")

        page = await browser.newPage()
        await page.setContent("<html><body><h1>Test Screenshot</h1></body></html>")
        await page.screenshot(path=str(output_path))
        print("✓ Screenshot captured successfully")

        await browser.close()
        print("✓ Browser closed cleanly")
        return True

    except Exception as e:
        print(f"✗ Browser launch failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass


def main() -> int:
    """Run the browser launch test and validate the screenshot."""

    output_path = Path("/tmp/test-screenshot.png")

    try:
        success = asyncio.run(test_browser_launch(output_path))
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if not success:
        return 1

    # Verify the screenshot file was created
    if output_path.exists():
        file_size = output_path.stat().st_size
        print("\nScreenshot file created successfully")
        print(f"File size: {file_size} bytes")
        if file_size > 0:
            return 0
        print("✗ Screenshot file is empty")
        return 1
    print("\n✗ Screenshot file was not created")
    return 1


if __name__ == "__main__":
    sys.exit(main())
