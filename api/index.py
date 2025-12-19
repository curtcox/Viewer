"""
Vercel serverless function entry point.

This module provides the WSGI application interface required by Vercel's
Python runtime for deploying the Flask application.

Vercel's Python runtime requires a module-level variable named 'app' that
contains the WSGI application. This variable must be accessible at import time.
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

# Initialize app to None - will be set below, but must exist at module level
# Vercel requires 'app' to be defined at module level
app = None

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
    # in app config, so the app can still be created and show 500 error page
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
        # Create a minimal error-handling app so Vercel has something to serve
        from flask import Flask
        error_app = Flask(__name__)
        @error_app.route('/', defaults={'path': ''})
        @error_app.route('/<path:path>')
        def error_handler(path):  # pylint: disable=unused-argument
            return f"Application initialization failed: {e}", 500
        app = error_app
    except Exception as e:
        # Log any other exceptions during app creation (these are fatal)
        logger.exception("Failed to create Flask application: %s", e)
        # Create a minimal error-handling app so Vercel has something to serve
        from flask import Flask
        error_app = Flask(__name__)
        @error_app.route('/', defaults={'path': ''})
        @error_app.route('/<path:path>')
        def error_handler(path):  # pylint: disable=unused-argument
            return f"Application initialization failed: {e}", 500
        app = error_app

except ImportError as e:
    # If imports fail, create a minimal error app so Vercel can serve error responses
    logger.exception("Failed to import required modules: %s", e)
    from flask import Flask
    error_app = Flask(__name__)
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):  # pylint: disable=unused-argument
        return f"Failed to import required modules: {e}", 500
    app = error_app
except Exception as e:
    # Catch-all for any other initialization errors
    logger.exception("Unexpected error during Vercel function initialization: %s", e)
    from flask import Flask
    error_app = Flask(__name__)
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):  # pylint: disable=unused-argument
        return f"Unexpected initialization error: {e}", 500
    app = error_app

# Ensure app is always defined (Vercel requires this at module level)
if app is None:
    from flask import Flask
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def fallback_handler(path):  # pylint: disable=unused-argument
        return "Application not initialized", 500
