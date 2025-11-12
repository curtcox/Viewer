"""Context processors for injecting variables into all templates."""

from typing import Any

from flask import current_app, has_request_context, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from db_access import (
    get_user_aliases,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    rollback_session,
)
from identity import current_user


def inject_observability_info() -> dict[str, Any]:
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


def inject_meta_inspector_link() -> dict[str, str]:
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
    return {"meta_inspector_url": meta_url}


def inject_viewer_navigation() -> dict[str, Any]:
    """
    Expose collections used by the unified Viewer navigation menu.

    Returns:
        Dictionary containing navigation data for aliases, servers, variables, and secrets
    """
    if not has_request_context():
        return {}

    user_id = getattr(current_user, "id", None)
    if not user_id:
        return {}

    try:
        aliases = get_user_aliases(user_id)
        servers = get_user_servers(user_id)
        variables = get_user_variables(user_id)
        secrets = get_user_secrets(user_id)
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


__all__ = [
    'inject_observability_info',
    'inject_meta_inspector_link',
    'inject_viewer_navigation',
]
