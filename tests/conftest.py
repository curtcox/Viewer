"""Root conftest for all tests - patches and global fixtures."""
from __future__ import annotations

import importlib.metadata


def patch_testmon_for_invalid_metadata():
    """
    Patch testmon to handle packages with invalid metadata.

    This fixes an issue where testmon crashes when encountering packages
    with None or invalid metadata (e.g., corrupted PyJWT installations).

    The testmon plugin tries to enumerate all installed packages to track
    dependencies, but doesn't handle the case where pkg.metadata is None.

    This patch wraps the get_system_packages_raw() function to skip
    packages with invalid metadata instead of crashing.
    """
    try:
        import testmon.common

        def patched_get_system_packages_raw():
            """Get system packages, skipping ones with invalid metadata."""
            for pkg in importlib.metadata.distributions():
                try:
                    # Check if metadata is None or inaccessible
                    if pkg.metadata is None:
                        continue

                    # Try to get name and version
                    name = pkg.metadata.get("Name")
                    version = pkg.version

                    if name and version:
                        yield (name, version)
                except (TypeError, KeyError, AttributeError):
                    # Skip packages with invalid or corrupted metadata
                    continue

        # Apply the patch
        testmon.common.get_system_packages_raw = patched_get_system_packages_raw

    except ImportError:
        # Testmon not installed, no need to patch
        pass


# Apply the patch when pytest starts
patch_testmon_for_invalid_metadata()
