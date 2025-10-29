import logging
import os
from os import getenv
from typing import Any, Optional

import logfire
from dotenv import load_dotenv
from flask import Flask
from logfire.exceptions import LogfireConfigError
from werkzeug.middleware.proxy_fix import ProxyFix

from ai_defaults import ensure_ai_stub_for_all_users
from css_defaults import ensure_css_alias_for_all_users
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
from identity import current_user, ensure_default_user
from link_presenter import (
    alias_full_url,
    alias_path,
    render_alias_link,
    render_server_link,
    render_url_link,
    server_full_url,
    server_path,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def create_app(config_override: Optional[dict] = None) -> Flask:

    logger = logging.getLogger(__name__)

    logfire_available = False
    logfire_reason: Optional[str] = None
    logfire_project_url: Optional[str] = None

    if getenv("LOGFIRE_SEND_TO_LOGFIRE"):

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
        except Exception as exc:  # pragma: no cover - defensive guard
            logfire_reason = f"Unexpected Logfire error: {exc}"
            logger.exception("Unexpected Logfire configuration failure")
        else:
            instrumentation_steps = (
                ("requests", logfire.instrument_requests),
                ("aiohttp", logfire.instrument_aiohttp_client),
                ("pydantic", logfire.instrument_pydantic),
            )

            instrumentation_errors: list[str] = []

            for name, instrument in instrumentation_steps:
                try:
                    instrument()
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.warning(
                        "Logfire %s instrumentation failed: %s", name, exc
                    )
                    instrumentation_errors.append(f"{name} instrumentation failed: {exc}")
                    break

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

    """Application factory for creating configured Flask instances."""
    app = Flask(__name__)

    default_database_uri = os.environ.get("DATABASE_URL") or "sqlite:///secureapp.db"

    app.config.update(
        SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=default_database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
    )

    app.config.setdefault(
        "GITHUB_REPOSITORY_URL",
        os.environ.get("GITHUB_REPOSITORY_URL", "https://github.com/curtcox/Viewer"),
    )

    if config_override:
        app.config.update(config_override)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    app.jinja_env.globals.update(
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
    init_db(app)

    # Register application components
    from analytics import make_session_permanent, track_page_view
    from routes import main_bp

    app.before_request(make_session_permanent)
    app.after_request(track_page_view)

    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_identity() -> dict[str, Any]:
        """Expose the always-on user to templates."""

        return {"current_user": current_user}

    # Register error handlers that work even in debug mode
    from routes.core import internal_error, not_found_error

    # Force registration of custom error handlers even in debug mode
    # This ensures our enhanced error pages with source links always work
    app.register_error_handler(500, internal_error)
    app.register_error_handler(404, not_found_error)

    # Override Flask's debug mode error handling to use our custom handlers
    # This is necessary because Flask's debug mode bypasses custom error handlers
    def force_custom_error_handling() -> None:
        """Force Flask to use our custom error handlers even in debug mode."""
        def enhanced_handle_exception(e: Exception) -> Any:
            # Always use our custom error handlers, even in debug mode
            if hasattr(e, 'code') and e.code == 404:
                return not_found_error(e)
            else:
                return internal_error(e)

        # Only override in debug mode to preserve normal behavior in production
        if app.debug:
            app.handle_exception = enhanced_handle_exception

    force_custom_error_handling()

    with app.app_context():
        import models  # noqa: F401  # pylint: disable=unused-import  # ensure models are registered

        db.create_all()
        logging.info("Database tables created")

        ensure_default_user()

        # Set up observability status for template context
        logfire_enabled = logfire_available
        langsmith_enabled = bool(getenv("LANGSMITH_API_KEY"))

        app.config["OBSERVABILITY_STATUS"] = {
            "logfire_available": logfire_enabled,
            "logfire_project_url": logfire_project_url if logfire_enabled else None,
            "logfire_reason": logfire_reason,
            "langsmith_available": langsmith_enabled,
            "langsmith_project_url": getenv("LANGSMITH_PROJECT_URL") if langsmith_enabled else None,
            "langsmith_reason": None if langsmith_enabled else "LANGSMITH_API_KEY not set",
        }

        ensure_ai_stub_for_all_users()
        ensure_css_alias_for_all_users()

    return app


# Maintain module-level application for backwards compatibility
app = create_app()
