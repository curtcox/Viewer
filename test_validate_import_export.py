#!/usr/bin/env python3
"""Tests for validate_import_export.py."""

import tempfile
from pathlib import Path

from validate_import_export import (
    ValidationReporter,
    validate_circular_imports,
    analyze_imports,
)


def test_validate_circular_imports_with_windows_paths():
    """Test that circular import detection works with Windows-style path separators.

    This test would have caught the bug where Path.as_posix() was not used,
    causing circular imports to be silently missed on Windows.
    """
    # Simulate Windows-style paths (backslashes) as returned by discover_modules()
    # on Windows. On Linux, Path().relative_to() returns forward slashes,
    # but on Windows it returns backslashes.
    windows_style_paths = [
        r"routes\import_export\module_a.py",
        r"routes\import_export\module_b.py",
    ]

    # Mock analyze_imports to return the imports we defined above
    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        # Normalize the path for comparison
        normalized = Path(file_path).as_posix()
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        elif "module_b" in normalized:
            return [('from', 'routes.import_export.module_a', 'func_a')]
        return []

    # Temporarily replace analyze_imports
    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(windows_style_paths, reporter)

        # Should detect the circular import even with Windows paths
        assert not result.passed, "Should detect circular import with Windows-style paths"
        assert "Circular imports detected" in result.message
        assert any("circular" in detail.lower() for detail in result.details)

    finally:
        # Restore original function
        validate_import_export.analyze_imports = original_analyze


def test_validate_circular_imports_with_posix_paths():
    """Test that circular import detection works with POSIX-style path separators."""
    # POSIX-style paths (forward slashes)
    posix_style_paths = [
        "routes/import_export/module_a.py",
        "routes/import_export/module_b.py",
    ]

    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        normalized = Path(file_path).as_posix()
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        elif "module_b" in normalized:
            return [('from', 'routes.import_export.module_a', 'func_a')]
        return []

    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(posix_style_paths, reporter)

        # Should detect the circular import with POSIX paths too
        assert not result.passed, "Should detect circular import with POSIX-style paths"
        assert "Circular imports detected" in result.message

    finally:
        validate_import_export.analyze_imports = original_analyze


def test_validate_circular_imports_no_cycles():
    """Test that non-circular imports pass validation."""
    # Non-circular module paths
    paths = [
        "routes/import_export/module_a.py",
        "routes/import_export/module_b.py",
    ]

    original_analyze = analyze_imports

    def mock_analyze_imports(file_path):
        # A imports B, but B doesn't import A (no cycle)
        normalized = Path(file_path).as_posix()
        if "module_a" in normalized:
            return [('from', 'routes.import_export.module_b', 'something')]
        elif "module_b" in normalized:
            return []  # No imports from A
        return []

    import validate_import_export
    validate_import_export.analyze_imports = mock_analyze_imports

    try:
        reporter = ValidationReporter()
        result = validate_circular_imports(paths, reporter)

        # Should pass when there's no circular import
        assert result.passed, "Should pass when there are no circular imports"
        assert "No circular imports" in result.message

    finally:
        validate_import_export.analyze_imports = original_analyze


if __name__ == '__main__':
    # Run tests manually
    print("Running tests...")

    try:
        print("\n1. Testing circular import detection with Windows paths...")
        test_validate_circular_imports_with_windows_paths()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")

    try:
        print("\n2. Testing circular import detection with POSIX paths...")
        test_validate_circular_imports_with_posix_paths()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")

    try:
        print("\n3. Testing non-circular imports...")
        test_validate_circular_imports_no_cycles()
        print("   ✓ PASSED")
    except AssertionError as e:
        print(f"   ✗ FAILED: {e}")

    print("\n✅ All tests completed!")
