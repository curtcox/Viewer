"""
Vercel serverless function entry point.

This module provides the WSGI application interface required by Vercel's
Python runtime for deploying the Flask application.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from the main app
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from readonly_config import ReadOnlyConfig  # noqa: E402
from db_config import DatabaseConfig, DatabaseMode  # noqa: E402

# Enable read-only mode if READ_ONLY environment variable is set
if os.environ.get("READ_ONLY", "").lower() in ("true", "1", "yes"):
    ReadOnlyConfig.set_read_only_mode(True)
    # Use in-memory database for read-only deployments
    DatabaseConfig.set_mode(DatabaseMode.MEMORY)

from app import create_app  # noqa: E402

# Create Flask application instance
app = create_app()
