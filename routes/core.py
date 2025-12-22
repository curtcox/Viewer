"""Core application routes and helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from flask import abort, current_app, redirect, render_template, url_for

from db_access import (
    count_aliases,
    count_secrets,
    count_servers,
    count_variables,
    get_first_alias_name,
    get_first_secret_name,
    get_first_server_name,
    get_first_variable_name,
)
from content_rendering import render_markdown_document
from routes.context_processors import (
    inject_meta_inspector_link,
    inject_observability_info,
    inject_viewer_navigation,
)
from routes.error_handlers import get_existing_routes, internal_error, not_found_error
from utils.cross_reference import build_cross_reference_data

# Import these for backward compatibility with tests that mock them at routes.core
# These are re-exported so utils/cross_reference.py and tests can access them via routes.core
from alias_definition import get_primary_alias_route  # noqa: F401
from entity_references import (  # noqa: F401
    extract_references_from_bytes,
    extract_references_from_target,
    extract_references_from_text,
)

from . import main_bp


_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


# Alias for backward compatibility
_build_cross_reference_data = build_cross_reference_data


def derive_name_from_path(path: str) -> Optional[str]:
    """
    Return the first path segment when it is safe for use as a name.

    Args:
        path: The URL path to extract a name from

    Returns:
        The extracted name or None if not valid
    """
    if not path:
        return None

    remainder = path.lstrip("/")
    if not remainder:
        return None

    segment = remainder.split("/", 1)[0]
    if not segment:
        return None

    if not _NAME_PATTERN.fullmatch(segment):
        return None

    return segment


# Register context processors
main_bp.app_context_processor(inject_observability_info)
main_bp.app_context_processor(inject_meta_inspector_link)
main_bp.app_context_processor(inject_viewer_navigation)


@main_bp.route("/")
def index():
    """Landing page with marketing and observability information."""
    cross_reference = build_cross_reference_data()

    return render_template("index.html", cross_reference=cross_reference)


@main_bp.route("/dashboard")
def dashboard():
    """User dashboard - directs members to their profile overview."""
    return redirect(url_for("main.profile"))


@main_bp.route("/profile")
def profile():
    """User profile placeholder for future external account management."""
    return render_template("profile.html")


@main_bp.route("/settings")
def settings():
    """Settings page with links to servers, variables, aliases, and secrets."""
    counts = get_settings_counts()
    return render_template("settings.html", **counts)


@main_bp.route("/help")
def help_page():
    """Help documentation page."""
    docs_dir = Path(current_app.root_path) / "docs"
    docs_files = _list_markdown_docs(docs_dir)

    return render_template("help.html", docs_files=docs_files)


@main_bp.route("/help/<path:doc_path>")
def help_markdown(doc_path: str):
    """Render markdown documentation files from the docs directory."""

    docs_dir = Path(current_app.root_path) / "docs"
    docs_files = _list_markdown_docs(docs_dir)
    resolved_path = _resolve_markdown_doc_path(doc_path, docs_dir)
    if resolved_path is None:
        abort(404)

    try:
        markdown_source = resolved_path.read_text(encoding="utf-8")
    except OSError:
        abort(404)

    help_content = render_markdown_document(markdown_source)
    return render_template(
        "help.html",
        help_content=help_content,
        docs_files=docs_files,
    )


def _list_markdown_docs(docs_dir: Path) -> list[str]:
    """Return sorted markdown filenames from docs directory."""

    try:
        return sorted(
            entry.name
            for entry in docs_dir.iterdir()
            if entry.is_file()
            and not entry.name.startswith(".")
            and entry.suffix.lower() == ".md"
        )
    except OSError:
        return []


def _resolve_markdown_doc_path(doc_path: str, docs_dir: Path) -> Optional[Path]:
    """Resolve a markdown doc path safely within docs directory."""

    candidate = Path(doc_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None

    resolved = (docs_dir / candidate).resolve()
    try:
        resolved.relative_to(docs_dir)
    except ValueError:
        return None

    if resolved.suffix.lower() != ".md" or not resolved.is_file():
        return None

    return resolved


def get_settings_counts():
    """Return counts of globally saved resources for settings display."""
    return {
        "alias_count": count_aliases(),
        "server_count": count_servers(),
        "variable_count": count_variables(),
        "secret_count": count_secrets(),
        "alias_example_name": get_first_alias_name(),
        "server_example_name": get_first_server_name(),
        "variable_example_name": get_first_variable_name(),
        "secret_example_name": get_first_secret_name(),
    }


__all__ = [
    "dashboard",
    "get_existing_routes",
    "get_settings_counts",
    "help_markdown",
    "help_page",
    "index",
    "inject_observability_info",
    "inject_meta_inspector_link",
    "inject_viewer_navigation",
    "not_found_error",
    "internal_error",
    "profile",
    "settings",
    # Backward compatibility exports
    "_build_cross_reference_data",
    # Re-exported functions for backward compatibility
    "get_primary_alias_route",
    "extract_references_from_bytes",
    "extract_references_from_target",
    "extract_references_from_text",
]
