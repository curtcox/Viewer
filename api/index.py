"""
Vercel serverless function entry point.

This module provides the WSGI application interface required by Vercel's
Python runtime for deploying the Flask application.
"""
import logging
import os
import sys
from pathlib import Path

# Configure logging early for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import from the main app
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from readonly_config import ReadOnlyConfig  # noqa: E402
    from db_config import DatabaseConfig, DatabaseMode  # noqa: E402

    # Enable read-only mode if READ_ONLY environment variable is set
    if os.environ.get("READ_ONLY", "").lower() in ("true", "1", "yes"):
        ReadOnlyConfig.set_read_only_mode(True)
        # Use in-memory database for read-only deployments
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)

    from app import create_app  # noqa: E402

    # Create Flask application instance with error handling
    # Note: RuntimeError from CID loading is handled inside create_app() and stored
    # in app config, so the app can still be created and show a 500 error page
    try:
        logger.info("Initializing Flask application for Vercel...")
        app = create_app()
        # Check if there was a CID loading error (app will still be created)
        cid_error = app.config.get("CID_LOAD_ERROR")
        if cid_error:
            logger.warning("CID loading failed, app will show 500 error page: %s", cid_error)
        else:
            logger.info("Flask application initialized successfully")
    except SystemExit as e:
        # SystemExit from legacy code should be caught and converted
        logger.error("SystemExit during app creation: %s", e)
        # Re-raise as a regular exception so Vercel can handle it
        raise RuntimeError(f"Application initialization failed: {e}") from e
    except Exception as e:
        # Log any other exceptions during app creation (these are fatal)
        logger.exception("Failed to create Flask application: %s", e)
        # Re-raise so Vercel can report the error
        raise

except ImportError as e:
    # If imports fail, log and re-raise with context
    logger.exception("Failed to import required modules: %s", e)
    raise
except Exception as e:
    # Catch-all for any other initialization errors
    logger.exception("Unexpected error during Vercel function initialization: %s", e)
    raise
