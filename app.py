import os
from os import getenv
import logging
from typing import Any, Optional

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

import logfire
from logfire.exceptions import LogfireConfigError
from sqlalchemy import inspect, text
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from alias_definition import format_primary_alias_line, replace_primary_definition_line
from alias_matching import PatternError, normalise_pattern
from database import db, init_db
from ai_defaults import ensure_ai_stub_for_all_users
from identity import current_user, ensure_default_user
from cid_presenter import (
    cid_full_url,
    cid_path,
    extract_cid_from_path,
    format_cid,
    format_cid_short,
    is_probable_cid_path,
    render_cid_link,
)
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


def _build_definition_from_legacy_row(row: dict[str, Any]) -> str:
    name = (row.get("name") or "").strip()
    target_path = (row.get("target_path") or "").strip()
    if not target_path:
        existing_definition = row.get("definition")
        return existing_definition or ""

    match_type = (row.get("match_type") or "literal").lower()
    match_pattern = row.get("match_pattern")
    ignore_case = bool(row.get("ignore_case"))

    try:
        normalised_pattern = normalise_pattern(match_type, match_pattern, name)
        canonical_match_type = match_type
    except PatternError:
        canonical_match_type = "literal"
        normalised_pattern = None

    primary_line = format_primary_alias_line(
        canonical_match_type,
        normalised_pattern,
        target_path,
        ignore_case=ignore_case,
        alias_name=name,
    )

    existing_definition = row.get("definition")
    if existing_definition:
        return replace_primary_definition_line(existing_definition, primary_line)
    return primary_line


def _migrate_legacy_alias_table(engine, logger: logging.Logger, columns: set[str]) -> None:
    from models import Alias

    logger.info("Upgrading legacy alias table to definition-based schema")

    select_columns = [
        "id",
        "name",
        "user_id",
        "created_at",
        "updated_at",
        "target_path",
        "match_type",
        "match_pattern",
        "ignore_case",
    ]
    if "definition" in columns:
        select_columns.append("definition")
    else:
        select_columns.append("NULL AS definition")

    query = f"SELECT {', '.join(select_columns)} FROM alias ORDER BY id"

    with engine.begin() as connection:
        rows = connection.execute(text(query)).mappings().all()

        connection.execute(text("ALTER TABLE alias RENAME TO alias_legacy"))
        Alias.__table__.create(connection)

        insert_stmt = Alias.__table__.insert()

        for row in rows:
            row_dict = dict(row)
            definition_text = _build_definition_from_legacy_row(row_dict)
            connection.execute(
                insert_stmt,
                {
                    "id": row_dict.get("id"),
                    "name": row_dict.get("name"),
                    "definition": definition_text,
                    "user_id": row_dict.get("user_id"),
                    "created_at": row_dict.get("created_at"),
                    "updated_at": row_dict.get("updated_at"),
                },
            )

        connection.execute(text("DROP TABLE alias_legacy"))


def _ensure_alias_definition_column(engine, logger: logging.Logger) -> None:
    """Ensure existing databases have the alias definition column."""

    try:
        inspector = inspect(engine)
        columns = {column_info["name"] for column_info in inspector.get_columns("alias")}
    except NoSuchTableError:
        logger.debug("Alias table not found; skipping definition column check")
        return

    legacy_columns = {"target_path", "match_type", "match_pattern", "ignore_case"}
    if legacy_columns & columns:
        _migrate_legacy_alias_table(engine, logger, columns)
        return

    if "definition" in columns:
        return

    logger.info("Adding missing alias.definition column to existing database")

    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE alias ADD COLUMN definition TEXT"))
    except SQLAlchemyError as exc:  # pragma: no cover - defensive guard
        logger.warning("Failed to add alias.definition column: %s", exc)



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
    def inject_identity():
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
    def force_custom_error_handling():
        """Force Flask to use our custom error handlers even in debug mode."""
        def enhanced_handle_exception(e):
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
        import models  # noqa: F401 ensure models are registered

        db.create_all()
        logging.info("Database tables created")

        _ensure_alias_definition_column(db.engine, logger)

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

    return app


# Maintain module-level application for backwards compatibility
app = create_app()
