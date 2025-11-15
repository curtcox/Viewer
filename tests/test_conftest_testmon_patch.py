"""Unit tests for the testmon conftest patch."""
from __future__ import annotations

import importlib.metadata
from typing import Any
from unittest.mock import MagicMock, patch


def test_patched_get_system_packages_raw_handles_none_metadata():
    """Test that the patched function handles packages with None metadata.

    This test ensures that when a package has None metadata (like a
    corrupted PyJWT installation), the patched get_system_packages_raw()
    function skips it instead of crashing with a TypeError.
    """
    # Import the conftest to apply the patch
    import tests.conftest  # noqa: F401

    try:
        import testmon.common

        # Get the patched function
        patched_fn = testmon.common.get_system_packages_raw

        # Create mock distributions - some valid, some with None metadata
        mock_distributions = []

        # Valid package
        valid_pkg = MagicMock()
        valid_pkg.metadata = {"Name": "test-package"}
        valid_pkg.version = "1.0.0"
        mock_distributions.append(valid_pkg)

        # Package with None metadata (like corrupted PyJWT)
        invalid_pkg = MagicMock()
        invalid_pkg.metadata = None
        invalid_pkg.version = "2.0.0"
        mock_distributions.append(invalid_pkg)

        # Another valid package
        valid_pkg2 = MagicMock()
        valid_pkg2.metadata = {"Name": "another-package"}
        valid_pkg2.version = "3.0.0"
        mock_distributions.append(valid_pkg2)

        # Patch importlib.metadata.distributions to return our mocks
        with patch.object(
            importlib.metadata, 'distributions', return_value=iter(mock_distributions)
        ):
            # Call the patched function
            result = list(patched_fn())

            # Should return only the valid packages
            assert len(result) == 2
            assert ("test-package", "1.0.0") in result
            assert ("another-package", "3.0.0") in result

            # Should NOT include the package with None metadata
            # (would have caused TypeError before the patch)

    except ImportError:
        # Testmon not installed, skip test
        pass


def test_patched_get_system_packages_raw_handles_missing_name():
    """Test that the patched function handles packages with missing Name field.

    Some packages may have metadata but be missing the Name field.
    The patch should handle this gracefully.
    """
    # Import the conftest to apply the patch
    import tests.conftest  # noqa: F401

    try:
        import testmon.common

        patched_fn = testmon.common.get_system_packages_raw

        mock_distributions = []

        # Package with metadata but no Name field
        pkg_no_name = MagicMock()
        pkg_no_name.metadata = {"Description": "Some package"}  # No Name field
        pkg_no_name.version = "1.0.0"
        mock_distributions.append(pkg_no_name)

        # Valid package
        valid_pkg = MagicMock()
        valid_pkg.metadata = {"Name": "good-package"}
        valid_pkg.version = "2.0.0"
        mock_distributions.append(valid_pkg)

        with patch.object(
            importlib.metadata, 'distributions', return_value=iter(mock_distributions)
        ):
            result = list(patched_fn())

            # Should only return the valid package
            assert len(result) == 1
            assert result[0] == ("good-package", "2.0.0")

    except ImportError:
        pass


def test_patched_get_system_packages_raw_handles_attribute_error():
    """Test that the patched function handles AttributeError when accessing metadata.

    Some packages may raise AttributeError when accessing metadata fields.
    The patch should catch these and skip the package.
    """
    # Import the conftest to apply the patch
    import tests.conftest  # noqa: F401

    try:
        import testmon.common

        patched_fn = testmon.common.get_system_packages_raw

        mock_distributions = []

        # Package that raises AttributeError on metadata.get()
        error_pkg = MagicMock()
        error_metadata = MagicMock()

        def raise_attribute_error(*args: Any, **kwargs: Any) -> None:
            raise AttributeError("Cannot access metadata field")

        error_metadata.get = MagicMock(side_effect=raise_attribute_error)
        error_pkg.metadata = error_metadata
        error_pkg.version = "1.0.0"
        mock_distributions.append(error_pkg)

        # Valid package
        valid_pkg = MagicMock()
        valid_pkg.metadata = {"Name": "good-package"}
        valid_pkg.version = "2.0.0"
        mock_distributions.append(valid_pkg)

        with patch.object(
            importlib.metadata, 'distributions', return_value=iter(mock_distributions)
        ):
            result = list(patched_fn())

            # Should only return the valid package
            assert len(result) == 1
            assert result[0] == ("good-package", "2.0.0")

    except ImportError:
        pass
