"""Context processors for injecting variables into all templates."""

from datetime import datetime, timezone

from flask import current_app, has_request_context, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from history_filters import format_history_timestamp

from db_access import (
    get_aliases,
    get_secrets,
    get_servers,
    get_variables,
    rollback_session,
)


def inject_observability_info():
    """
    Expose Logfire and LangSmith availability to all templates.

    Returns:
        Dictionary containing observability status information
    """
    status = current_app.config.get("OBSERVABILITY_STATUS") or {}
    return {
        "LOGFIRE_AVAILABLE": bool(status.get("logfire_available")),
        "LOGFIRE_PROJECT_URL": status.get("logfire_project_url"),
        "LOGFIRE_UNAVAILABLE_REASON": status.get("logfire_reason"),
        "LANGSMITH_AVAILABLE": bool(status.get("langsmith_available")),
        "LANGSMITH_PROJECT_URL": status.get("langsmith_project_url"),
        "LANGSMITH_UNAVAILABLE_REASON": status.get("langsmith_reason"),
    }


def inject_meta_inspector_link():
    """
    Expose the per-page /meta inspector link to templates.

    Returns:
        Dictionary containing the meta inspector URL
    """
    if has_request_context():
        path = request.path or "/"
    else:
        path = "/"

    stripped = path.strip("/")
    if stripped:
        requested_path = f"{stripped}.html"
    else:
        requested_path = ".html"

    meta_url = url_for("main.meta_route", requested_path=requested_path)
    loaded_at = datetime.now(timezone.utc)
    history_since_url = url_for("main.history", start=format_history_timestamp(loaded_at))

    return {
        "meta_inspector_url": meta_url,
        "history_since_url": history_since_url,
    }


def inject_viewer_navigation():
    """
    Expose collections used by the unified Viewer navigation menu.

    Returns:
        Dictionary containing navigation data for aliases, servers, variables, and secrets
    """
    if not has_request_context():
        return {}

    try:
        aliases = get_aliases()
        servers = get_servers()
        variables = get_variables()
        secrets = get_secrets()
    except SQLAlchemyError:
        rollback_session()
        aliases = []
        servers = []
        variables = []
        secrets = []

    return {
        "nav_aliases": aliases,
        "nav_servers": servers,
        "nav_variables": variables,
        "nav_secrets": secrets,
    }


def inject_template_helpers():
    """
    Expose template management helpers to all templates.

    Returns:
        Dictionary containing template helper functions
    """
    from template_status import get_template_link_info, generate_template_status_label

    return {
        'get_template_link_info': get_template_link_info,
        'generate_template_status_label': generate_template_status_label,
    }


__all__ = [
    'inject_observability_info',
    'inject_meta_inspector_link',
    'inject_viewer_navigation',
    'inject_template_helpers',
]
