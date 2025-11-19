"""Root conftest for all tests - patches and global fixtures."""
from __future__ import annotations

import importlib.metadata
import os
import tempfile
from pathlib import Path

import pytest

from app import create_app
from database import db
from db_config import DatabaseConfig, DatabaseMode


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "memory_db: mark test as using in-memory database")
    config.addinivalue_line(
        "markers", "db_equivalence: mark test as database equivalence test"
    )


@pytest.fixture()
def memory_db_app():
    """Flask app configured with in-memory database."""
    DatabaseConfig.set_mode(DatabaseMode.MEMORY)

    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    DatabaseConfig.reset()


@pytest.fixture()
def memory_client(memory_db_app):
    """Test client bound to memory database app."""
    return memory_db_app.test_client()


@pytest.fixture()
def disk_db_app(tmp_path):
    """Flask app configured with disk-based SQLite database."""
    db_path = tmp_path / "test.db"
    db_uri = f"sqlite:///{db_path}"

    DatabaseConfig.set_mode(DatabaseMode.DISK)
    os.environ["DATABASE_URL"] = db_uri

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": db_uri,
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    # Cleanup
    if db_path.exists():
        db_path.unlink()
    DatabaseConfig.reset()
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture()
def disk_client(disk_db_app):
    """Test client bound to disk database app."""
    return disk_db_app.test_client()


@pytest.fixture(params=["memory", "disk"])
def any_db_app(request, tmp_path):
    """Parameterized fixture that provides both memory and disk database apps."""
    if request.param == "memory":
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        db_uri = "sqlite:///:memory:"
    else:
        db_path = tmp_path / "test.db"
        db_uri = f"sqlite:///{db_path}"
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        os.environ["DATABASE_URL"] = db_uri

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": db_uri,
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app, request.param
        db.session.remove()
        db.drop_all()

    DatabaseConfig.reset()
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture()
def any_client(any_db_app):
    """Test client that works with any database type."""
    app, db_type = any_db_app
    return app.test_client(), db_type


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
