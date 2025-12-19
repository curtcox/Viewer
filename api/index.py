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


def _is_truthy_env(value: str | None) -> bool:
    return (value or "").strip().lower() in ("true", "1", "yes")


def _resolve_boot_cid(project_root: Path, read_only: bool) -> str | None:
    explicit_boot_cid = (os.environ.get("BOOT_CID") or "").strip()
    if explicit_boot_cid:
        return explicit_boot_cid

    if not read_only:
        return None

    boot_cid_file = project_root / "reference_templates" / "readonly.boot.cid"
    if not boot_cid_file.exists():
        return None

    return (boot_cid_file.read_text(encoding="utf-8") or "").strip() or None

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

    read_only_env = _is_truthy_env(os.environ.get("READ_ONLY"))
    testing_env = _is_truthy_env(os.environ.get("TESTING"))

    # Enable read-only mode if READ_ONLY environment variable is set
    if read_only_env:
        ReadOnlyConfig.set_read_only_mode(True)
        # Use in-memory database for read-only deployments
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)

    from app import create_app  # noqa: E402

    # Create Flask application instance with error handling
    # Note: RuntimeError from CID loading is handled inside create_app() and stored
    # in app config, so the app can still be created and show 500 error page
    try:
        logger.info("Initializing Flask application for Vercel...")
        logger.info("Environment: VERCEL=%s, VERCEL_ENV=%s, READ_ONLY=%s", 
                   os.environ.get("VERCEL"), os.environ.get("VERCEL_ENV"), 
                   os.environ.get("READ_ONLY"))

        config_override = None
        if testing_env:
            config_override = {
                "TESTING": True,
                "LOAD_CIDS_IN_TESTS": True,
            }

        app = create_app(config_override)

        boot_cid = _resolve_boot_cid(Path(parent_dir), read_only_env)
        if boot_cid:
            try:
                from boot_cid_importer import import_boot_cid  # noqa: E402

                with app.app_context():
                    success, error = import_boot_cid(app, boot_cid)

                if not success:
                    raise RuntimeError(error or "Boot CID import failed")

                app.config["BOOT_CID"] = boot_cid
                logger.info("Boot CID %s imported successfully", boot_cid)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                error_message = f"Boot CID import failed for {boot_cid}: {exc}"
                logger.exception(error_message)
                app.config["CID_LOAD_ERROR"] = error_message
        elif read_only_env:
            logger.warning("READ_ONLY is enabled but no boot CID was configured/found; skipping boot import")

        # Check if there was a CID loading error (app will still be created)
        cid_error = app.config.get("CID_LOAD_ERROR")
        if cid_error:
            logger.warning("CID loading failed, app will show 500 error page: %s", cid_error)
        else:
            logger.info("Flask application initialized successfully")
    except SystemExit as e:
        # SystemExit from legacy code should be caught and converted
        logger.error("SystemExit during app creation: %s", e)
        error_message = f"Application initialization failed: {e}"
        # Create a minimal error-handling app so Vercel has something to serve
        from flask import Flask
        error_app = Flask(__name__)
        @error_app.route('/', defaults={'path': ''})
        @error_app.route('/<path:path>')
        def error_handler(path):  # pylint: disable=unused-argument
            return error_message, 500
        app = error_app
    except Exception as e:
        # Log any other exceptions during app creation (these are fatal)
        logger.exception("Failed to create Flask application: %s", e)
        error_message = f"Application initialization failed: {e}"
        # Create a minimal error-handling app so Vercel has something to serve
        from flask import Flask
        error_app = Flask(__name__)
        @error_app.route('/', defaults={'path': ''})
        @error_app.route('/<path:path>')
        def error_handler(path):  # pylint: disable=unused-argument
            return error_message, 500
        app = error_app

except ImportError as e:
    # If imports fail, create a minimal error app so Vercel can serve error responses
    logger.exception("Failed to import required modules: %s", e)
    error_message = f"Failed to import required modules: {e}"
    from flask import Flask
    error_app = Flask(__name__)
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):  # pylint: disable=unused-argument
        return error_message, 500
    app = error_app
except Exception as e:
    # Catch-all for any other initialization errors
    logger.exception("Unexpected error during Vercel function initialization: %s", e)
    error_message = f"Unexpected initialization error: {e}"
    from flask import Flask
    error_app = Flask(__name__)
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):  # pylint: disable=unused-argument
        return error_message, 500
    app = error_app

# Ensure app is always defined (Vercel requires this at module level)
if app is None:
    from flask import Flask
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def fallback_handler(path):  # pylint: disable=unused-argument
        return "Application not initialized", 500
