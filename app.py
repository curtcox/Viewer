import logging
import os
from os import getenv
from pathlib import Path
from typing import Any, Optional

# Optional logfire import - gracefully handle if not available
try:
    import logfire
    from logfire.exceptions import LogfireConfigError
    LOGFIRE_AVAILABLE = True
except ImportError:
    logfire = None  # type: ignore[assignment, misc]
    LogfireConfigError = Exception  # type: ignore[assignment, misc]
    LOGFIRE_AVAILABLE = False

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:  # type: ignore[no-redef]
        return False
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

import models  # noqa: F401  # pylint: disable=unused-import

from analytics import make_session_permanent, track_page_view
from authorization import authorize_request
from authorization_handler import create_authorization_error_response
from cid_directory_loader import load_cids_from_directory
from cid_presenter import (
    cid_full_url,
    cid_path,
    extract_cid_from_path,
    format_cid,
    format_cid_short,
    is_probable_cid_path,
    render_cid_link,
)
from database import db, init_db
from db_config import DatabaseConfig
from identity import ensure_default_resources
from link_presenter import (
    alias_full_url,
    alias_path,
    render_alias_link,
    render_server_link,
    render_url_link,
    server_full_url,
    server_path,
)
from response_formats import register_response_format_handlers
from routes import main_bp
from routes.core import internal_error, not_found_error

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def _setup_logfire_instrumentation(logger: logging.Logger) -> list[str]:
    """Set up Logfire instrumentation hooks.

    Returns:
        List of error messages for failed instrumentation steps.
    """
    if not LOGFIRE_AVAILABLE or logfire is None:
        return ["logfire module not available"]

    instrumentation_steps = (
        ("requests", logfire.instrument_requests),
        ("aiohttp", logfire.instrument_aiohttp_client),
        ("pydantic", logfire.instrument_pydantic),
    )

    instrumentation_errors: list[str] = []
    try:
        for name, instrument in instrumentation_steps:
            try:
                instrument()
            except Exception as exc:  # pragma: no cover - defensive guard  # pylint: disable=broad-exception-caught
                # Each instrumentation hook may import optional packages or
                # inspect environment state; we tolerate any failure here to
                # keep the application usable even when observability setup is
                # partially misconfigured.
                logger.warning(
                    "Logfire %s instrumentation failed: %s", name, exc
                )
                instrumentation_errors.append(f"{name} instrumentation failed: {exc}")
                break
    except Exception as exc:  # pragma: no cover - defensive guard  # pylint: disable=broad-exception-caught
        # Each instrumentation hook may import optional packages or
        # inspect environment state; we tolerate any failure here to
        # keep the application usable even when observability setup is
        # partially misconfigured.
        logger.warning(
            "Logfire instrumentation failed: %s", exc
        )
        instrumentation_errors.append(f"instrumentation failed: {exc}")

    return instrumentation_errors


def create_app(config_override: Optional[dict] = None) -> Flask:
    """Application factory for creating configured Flask instances."""
    logger = logging.getLogger(__name__)

    logfire_available = False
    logfire_reason: Optional[str] = None
    logfire_project_url: Optional[str] = None

    testing_env = getenv("TESTING", "").lower() in {"1", "true", "yes"}
    config_testing = bool(config_override and config_override.get("TESTING"))
    testing_mode = testing_env or config_testing

    send_to_logfire = getenv("LOGFIRE_SEND_TO_LOGFIRE")

    if send_to_logfire:
        if not LOGFIRE_AVAILABLE or logfire is None:
            logger.warning(
                "LOGFIRE_SEND_TO_LOGFIRE is set but logfire module is not available; "
                "install logfire package to enable observability"
            )
            logfire_reason = "logfire module not installed"
        else:
            if testing_mode:
                logger.debug(
                    "LOGFIRE_SEND_TO_LOGFIRE is set while TESTING is enabled; running Logfire setup"
                )

            logfire_token = getenv("LOGFIRE_TOKEN")

            if not logfire_token and not testing_mode:
                logger.warning(
                    "LOGFIRE_SEND_TO_LOGFIRE is set but LOGFIRE_TOKEN is missing; disabling Logfire"
                )
                logfire_reason = "LOGFIRE_TOKEN not set"
            else:
                if not logfire_token:
                    logger.debug(
                        "LOGFIRE_TOKEN is not set but TESTING is enabled; running Logfire setup anyway"
                    )
                logger.info("Logfire is enabled")

                try:
                    logfire.configure(
                        code_source=logfire.CodeSource(
                            repository='https://github.com/curtcox/Viewer',
                            revision=getenv("REVISION"),
                        )
                    )
                except LogfireConfigError as exc:
                    logfire_reason = str(exc)
                    logger.warning("Logfire configuration failed: %s", logfire_reason)
                except Exception as exc:  # pragma: no cover - defensive guard  # pylint: disable=broad-exception-caught
                    # Logfire loads optional integrations dynamically; keep a broad guard so
                    # unexpected configuration/import failures do not crash application
                    # startup in environments where those dependencies are absent.
                    logfire_reason = f"Unexpected Logfire error: {exc}"
                    logger.exception("Unexpected Logfire configuration failure")
                else:
                    instrumentation_errors = _setup_logfire_instrumentation(logger)

                    if instrumentation_errors:
                        logfire_available = False
                        logfire_reason = "; ".join(instrumentation_errors)
                    else:
                        logger.info("Logfire configured")
                        logfire_available = True
                        logfire_reason = None
                        logfire_project_url = getenv("LOGFIRE_PROJECT_URL")

    else:

        logger.warning("Logfire is not enabled, skipping logfire instrumentation")
        logfire_reason = "LOGFIRE_SEND_TO_LOGFIRE not set"

    flask_app = Flask(__name__)

    # Use DatabaseConfig for URI (respects memory mode and CLI flags)
    default_database_uri = DatabaseConfig.get_database_uri()

    engine_options: dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # sqlite:///:memory: requires a single shared connection; otherwise SQLAlchemy
    # may open multiple independent in-memory databases (one per connection),
    # causing tables created during app startup to be missing later.
    if default_database_uri.strip().lower() == "sqlite:///:memory:":
        from sqlalchemy.pool import StaticPool

        engine_options = {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }

    flask_app.config.update(
        SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=default_database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
    )

    flask_app.config.setdefault(
        "GITHUB_REPOSITORY_URL",
        os.environ.get("GITHUB_REPOSITORY_URL", "https://github.com/curtcox/Viewer"),
    )
    flask_app.config.setdefault("CID_DIRECTORY", str(Path(flask_app.root_path) / "cids"))
    
    # Set GIT_SHA from environment variable if provided (used in Vercel deployments)
    git_sha = os.environ.get("GIT_SHA")
    if git_sha:
        flask_app.config["GIT_SHA"] = git_sha

    cid_directory_overridden = bool(config_override and "CID_DIRECTORY" in config_override)
    load_cids_in_tests = bool(config_override and config_override.get("LOAD_CIDS_IN_TESTS"))

    if config_override:
        flask_app.config.update(config_override)

    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    flask_app.jinja_env.globals.update(
        alias_full_url=alias_full_url,
        alias_path=alias_path,
        cid_full_url=cid_full_url,
        cid_path=cid_path,
        extract_cid_from_path=extract_cid_from_path,
        format_cid=format_cid,
        format_cid_short=format_cid_short,
        is_probable_cid_path=is_probable_cid_path,
        render_cid_link=render_cid_link,
        render_alias_link=render_alias_link,
        render_server_link=render_server_link,
        render_url_link=render_url_link,
        server_full_url=server_full_url,
        server_path=server_path,
    )

    # Initialize database
    init_db(flask_app)

    # Register application components
    flask_app.before_request(make_session_permanent)

    # Check for CID loading errors before processing any requests
    @flask_app.before_request
    def check_cid_load_error():
        """Show 500 error page if CID directory is missing."""
        cid_error = flask_app.config.get("CID_LOAD_ERROR")
        if cid_error:
            # Create a RuntimeError with the stored message to trigger 500 handler
            error = RuntimeError(cid_error)
            return internal_error(error)

    # Add read-only mode check before authorization
    @flask_app.before_request
    def check_readonly_mode():
        """Block state-changing requests in read-only mode."""
        from readonly_middleware import is_state_changing_request
        from readonly_config import ReadOnlyConfig

        if ReadOnlyConfig.is_read_only_mode() and is_state_changing_request():
            from flask import abort
            abort(405, description="Operation not allowed in read-only mode")
        return None

    # Add authorization check for all requests
    @flask_app.before_request
    def check_authorization():
        """Check authorization for each request."""
        from flask import request as flask_request

        result = authorize_request(flask_request)
        if not result.allowed:
            return create_authorization_error_response(result)
        return None

    flask_app.after_request(track_page_view)

    flask_app.register_blueprint(main_bp)
    register_response_format_handlers(flask_app)

    @flask_app.context_processor
    def inject_template_helpers() -> dict[str, Any]:
        """Expose template management helpers to all templates."""
        from template_status import get_template_link_info, generate_template_status_label

        return {
            'get_template_link_info': get_template_link_info,
            'generate_template_status_label': generate_template_status_label,
        }

    # Force registration of custom error handlers even in debug mode
    # This ensures our enhanced error pages with source links always work
    flask_app.register_error_handler(500, internal_error)
    flask_app.register_error_handler(404, not_found_error)

    # Override Flask's debug mode error handling to use our custom handlers
    # This is necessary because Flask's debug mode bypasses custom error handlers
    def force_custom_error_handling() -> None:
        """Force Flask to use our custom error handlers even in debug mode."""
        def enhanced_handle_exception(e: Exception) -> Any:
            # Always use our custom error handlers, even in debug mode
            if hasattr(e, 'code') and e.code == 404:
                return not_found_error(e)
            return internal_error(e)

        # Only override in debug mode to preserve normal behavior in production
        if flask_app.debug:
            flask_app.handle_exception = enhanced_handle_exception

    force_custom_error_handling()

    skip_db_setup = bool(flask_app.config.get("SKIP_DB_SETUP"))

    with flask_app.app_context():
        if skip_db_setup:
            logging.info("Skipping database setup due to SKIP_DB_SETUP flag")
        else:
            try:
                db.create_all()
                logging.info("Database tables created")
            except Exception as e:
                # Database initialization failure is critical - log and re-raise
                logging.error("Failed to create database tables: %s", e, exc_info=True)
                raise

            if not testing_mode or cid_directory_overridden or load_cids_in_tests:
                # Try to load CIDs, but store error if it fails so we can show 500 page
                # On Vercel/serverless, allow missing CID directory (it may not be deployed)
                is_vercel = os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV")
                allow_missing_cids = is_vercel or flask_app.config.get("ALLOW_MISSING_CID_DIRECTORY", False)
                try:
                    load_cids_from_directory(flask_app, allow_missing=allow_missing_cids)
                    flask_app.config["CID_LOAD_ERROR"] = None
                except RuntimeError as e:
                    # Store the error so we can show it in a 500 error page
                    error_message = str(e)
                    logging.error("Failed to load CIDs from directory: %s", error_message)
                    flask_app.config["CID_LOAD_ERROR"] = error_message

            if not testing_mode:
                # Wrap ensure_default_resources in error handling to prevent initialization failures
                # This is especially important for serverless deployments where file access may be limited
                try:
                    ensure_default_resources()
                except Exception as e:
                    # Log but don't fail - default resources are nice-to-have, not critical
                    logging.warning("Failed to ensure default resources (non-fatal): %s", e, exc_info=True)

        # Set up observability status for template context
        logfire_enabled = logfire_available
        langsmith_enabled = bool(getenv("LANGSMITH_API_KEY"))

        flask_app.config["OBSERVABILITY_STATUS"] = {
            "logfire_available": logfire_enabled,
            "logfire_project_url": logfire_project_url if logfire_enabled else None,
            "logfire_reason": logfire_reason,
            "langsmith_available": langsmith_enabled,
            "langsmith_project_url": getenv("LANGSMITH_PROJECT_URL") if langsmith_enabled else None,
            "langsmith_reason": None if langsmith_enabled else "LANGSMITH_API_KEY not set",
        }

    return flask_app


# Maintain module-level application for backwards compatibility unless explicitly disabled
if getenv("VIEWER_SKIP_MODULE_APP", "").lower() not in {"1", "true", "yes"}:
    app = create_app()
else:  # pragma: no cover - used for CLI shortcuts that construct their own app instances
    app = None
