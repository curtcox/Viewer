"""Detailed routing explorer for individual request paths."""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from flask import current_app, render_template, url_for
from markupsafe import Markup
from werkzeug.exceptions import MethodNotAllowed, NotFound

from alias_routing import is_potential_alias_path, resolve_alias_target
from cid_presenter import extract_cid_from_path, format_cid, render_cid_link
from db_access import get_cid_by_path, get_server_by_name
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
)

from . import main_bp
from .core import get_existing_routes


@dataclass
class RouteStep:
    """Single step in the routing chain."""

    category: str
    title: str
    description: str
    request_path: str
    title_url: Optional[str] = None
    link_label: Optional[str] = None
    link_url: Optional[str] = None
    cid_markup: Optional[Markup] = None
    extra_details: Optional[str] = None
    redirect_target: Optional[str] = None
    definition_excerpt: Optional[str] = None

    _CATEGORY_LABELS = {
        "alias": "Alias",
        "server": "Server",
        "cid": "CID",
        "builtin": "Built-in",
        "not_found": "Not Found",
    }

    _ICON_CLASSES = {
        "alias": "fa-link",
        "server": "fa-server",
        "cid": "fa-database",
        "builtin": "fa-code",
        "not_found": "fa-triangle-exclamation",
    }

    _BADGE_CLASSES = {
        "alias": "text-bg-primary",
        "server": "text-bg-success",
        "cid": "text-bg-dark",
        "builtin": "text-bg-info",
        "not_found": "text-bg-danger",
    }

    @property
    def category_label(self) -> str:
        return self._CATEGORY_LABELS.get(self.category, self.category.title())

    @property
    def icon_class(self) -> str:
        return self._ICON_CLASSES.get(self.category, "fa-circle")

    @property
    def badge_class(self) -> str:
        return self._BADGE_CLASSES.get(self.category, "text-bg-secondary")

    @property
    def request_url(self) -> str:
        return self.request_path


@dataclass
class RouteResolution:
    """Structured description of how a path is handled."""

    normalized_path: str
    final_status: Optional[int]
    final_summary: str
    redirect_target: Optional[str]
    steps: List[RouteStep]
    redirects_followed: int = 0
    chain_limited: bool = False
    loop_detected: bool = False


def _normalize_requested_path(raw: str) -> str:
    candidate = (raw or "").strip()
    if not candidate:
        return "/"
    candidate = candidate.split("?", 1)[0]
    candidate = candidate.split("#", 1)[0]
    if not candidate.startswith("/"):
        candidate = f"/{candidate}"
    while "//" in candidate:
        candidate = candidate.replace("//", "/")
    if len(candidate) > 1 and candidate.endswith("/"):
        candidate = candidate.rstrip("/")
    return candidate or "/"


def _relative_path(candidate: Path, root: Path) -> Optional[str]:
    try:
        return candidate.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def _truncate_line(line: str, limit: int = 100) -> str:
    if len(line) <= limit:
        return line
    return f"{line[:limit].rstrip()}…"


def _extract_main_signature(definition: str) -> Optional[str]:
    if not definition:
        return None

    for raw_line in definition.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("def main") or stripped.startswith("async def main"):
            return stripped
    return None


def _first_non_empty_line(definition: str) -> Optional[str]:
    if not definition:
        return None

    for raw_line in definition.splitlines():
        stripped = raw_line.strip()
        if stripped:
            return stripped
    return None


def _describe_builtin_route(path: str) -> Optional[RouteResolution]:
    binder = current_app.url_map.bind("", url_scheme="http")
    try:
        endpoint, _ = binder.match(path, method="GET")
        allowed_methods: Optional[list[str]] = None
        status_code = 200
        warning: Optional[str] = None
    except MethodNotAllowed as exc:  # pragma: no cover - defensive fallback
        allowed_methods = sorted(exc.valid_methods or [])
        status_code = 405
        try:
            fallback_method = allowed_methods[0] if allowed_methods else "GET"
            endpoint, _ = binder.match(path, method=fallback_method)
        except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover - fallback for any routing issue
            endpoint = exc.description or "unknown"
        methods_text = ", ".join(allowed_methods) if allowed_methods else "(unknown)"
        warning = f"GET not allowed. Allowed methods: {methods_text}."
    except NotFound:
        return None

    view_func = current_app.view_functions.get(endpoint)
    definition_label: Optional[str] = None
    definition_url: Optional[str] = None
    if view_func is not None:
        code = getattr(view_func, "__code__", None)
        source_path = Path(inspect.getsourcefile(view_func) or (code.co_filename if code else ""))
        repository_root = Path(current_app.root_path)
        relative = _relative_path(source_path, repository_root)
        if relative:
            definition_label = relative
            definition_url = url_for("main.source_browser", requested_path=relative)

    description = "Handled directly by the Flask route."
    if warning:
        description = warning

    step = RouteStep(
        category="builtin",
        title=endpoint,
        description=description,
        request_path=path,
        link_label="View source" if definition_url else None,
        link_url=definition_url,
        extra_details=definition_label,
    )

    summary = f"Handled by Flask endpoint {endpoint}" if status_code == 200 else description
    return RouteResolution(
        normalized_path=path,
        final_status=status_code,
        final_summary=summary,
        redirect_target=None,
        steps=[step],
    )


def _alias_definition_excerpt(alias: object, route: object) -> Optional[str]:
    source = getattr(route, "source", None)
    if source is not None:
        text = getattr(source, "text", None)
        if text:
            return _truncate_line(text.strip())

    definition = getattr(alias, "definition", None)
    if not definition:
        return None

    for raw_line in definition.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "->" in stripped:
            return _truncate_line(stripped)
    return None


def _alias_step_for(path: str, existing_routes: set[str]) -> Optional[RouteResolution]:
    if not is_potential_alias_path(path, existing_routes):
        return None

    resolution = resolve_alias_target(path)
    if resolution is None or not resolution.is_relative:
        return None

    alias = resolution.match.alias
    route = resolution.match.route
    alias_name = getattr(alias, "name", "(unnamed alias)")
    definition_url = url_for("main.view_alias", alias_name=alias_name)

    match_type = (route.match_type or "literal").replace("_", " ").title()
    pattern = route.match_pattern or f"/{alias_name}"
    target = resolution.target or "(no target)"
    description = f"{match_type} match using pattern {pattern!r}."
    target_cid = extract_cid_from_path(target)
    cid_markup = render_cid_link(target_cid) if target_cid else None

    definition_excerpt = _alias_definition_excerpt(alias, route)

    step = RouteStep(
        category="alias",
        title=alias_name,
        description=description,
        request_path=path,
        title_url=definition_url,
        definition_excerpt=definition_excerpt,
        redirect_target=target,
        cid_markup=cid_markup,
    )

    summary = f"Redirects to {target}" if target else "Redirect generated by alias."
    return RouteResolution(
        normalized_path=path,
        final_status=302,
        final_summary=summary,
        redirect_target=target,
        steps=[step],
    )


def _server_definition_excerpt(server: object) -> Optional[str]:
    definition = getattr(server, "definition", None)
    if not definition:
        return None

    signature = _extract_main_signature(definition)
    if signature:
        return _truncate_line(signature)

    first_line = _first_non_empty_line(definition)
    if first_line:
        return _truncate_line(first_line)
    return None


def _server_step_for(path: str, existing_routes: set[str]) -> Optional[RouteResolution]:
    if not is_potential_server_path(path, existing_routes):
        return None

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return None

    server_name = segments[0]
    server = get_server_by_name(server_name)
    if not server or not getattr(server, "enabled", True):
        return None

    link_url = url_for("main.view_server", server_name=server.name)
    function_part = segments[1] if len(segments) > 1 else None

    if function_part is None:
        description = "Executes the server's main() function with the current request context."
    elif len(segments) > 2:
        description = (
            "Extra path segments are treated as additional context. "
            "The server falls back to main() execution."
        )
    elif function_part.isidentifier():
        description = (
            f"Attempts to execute helper function `{function_part}`. "
            "Falls back to main() when the helper returns no response."
        )
    else:
        description = (
            f"Treats `{function_part}` as part of the path and executes main()."
        )

    definition_cid = format_cid(getattr(server, "definition_cid", ""))
    cid_markup = render_cid_link(definition_cid) if definition_cid else None

    definition_excerpt = _server_definition_excerpt(server)

    step = RouteStep(
        category="server",
        title=server.name,
        description=description,
        request_path=path,
        title_url=link_url,
        extra_details="Response redirects to generated CID content.",
        cid_markup=cid_markup,
        definition_excerpt=definition_excerpt,
    )

    summary = "Executes server code and redirects to generated CID output."
    return RouteResolution(
        normalized_path=path,
        final_status=302,
        final_summary=summary,
        redirect_target=None,
        steps=[step],
    )


def _versioned_server_step_for(path: str, existing_routes: set[str]) -> Optional[RouteResolution]:
    if not is_potential_versioned_server_path(path, existing_routes):
        return None

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2:
        return None

    server_name, partial = segments[0], segments[1]
    server = get_server_by_name(server_name)
    if not server or not getattr(server, "enabled", True):
        return None

    try:
        from .servers import get_server_definition_history  # lazy import to avoid cycles
    except ImportError:  # pragma: no cover - defensive guard
        get_server_definition_history = None  # type: ignore[assignment]

    matches = []
    if get_server_definition_history is not None:
        history = get_server_definition_history(server_name)
        matches = [
            entry
            for entry in history
            if entry.get("definition_cid", "").startswith(partial)
        ]

    if not matches:
        description = "No server versions match this CID prefix. The request returns 404."
        summary = "No historical server version matched the requested prefix."
        status = 404
        cid_markup = None
    elif len(matches) > 1:
        description = "Multiple server versions share this prefix. The request returns a 400 detail payload."
        summary = "Multiple historical definitions match the prefix."
        status = 400
        cid_markup = None
    else:
        match = matches[0]
        description = (
            "Loads historical server definition from uploaded snapshot and executes it."
        )
        summary = "Executes a historical server definition matching the requested prefix."
        status = 302
        snapshot_cid = format_cid(match.get("snapshot_cid"))
        cid_markup = render_cid_link(snapshot_cid) if snapshot_cid else None

    link_url = url_for("main.view_server", server_name=server.name)
    extra_details = f"CID prefix: {partial}" if partial else None

    step = RouteStep(
        category="server",
        title=f"{server.name} (historical)",
        description=description,
        request_path=path,
        title_url=link_url,
        extra_details=extra_details,
        cid_markup=cid_markup,
        definition_excerpt=_server_definition_excerpt(server),
    )

    return RouteResolution(
        normalized_path=path,
        final_status=status,
        final_summary=summary,
        redirect_target=None,
        steps=[step],
    )


def _cid_step_for(path: str) -> Optional[RouteResolution]:
    base_path = path.split(".", 1)[0] if "." in path else path
    cid_record = get_cid_by_path(base_path)
    if cid_record is None:
        return None

    cid_value = format_cid(cid_record.path)
    cid_markup = render_cid_link(cid_value)

    description = "Served directly from stored CID content."
    extra = None
    if path != base_path:
        extension = path[len(base_path) :]
        if extension:
            extra = f"Requested extension: {extension}"

    file_data = getattr(cid_record, "file_data", b"") or b""
    try:
        rendered = file_data.decode("utf-8", errors="replace")
    except (AttributeError, UnicodeDecodeError):  # pragma: no cover - defensive decoding guard
        rendered = ""
    first_line = rendered.splitlines()[0].strip() if rendered else ""
    definition_excerpt = _truncate_line(first_line) if first_line else None

    step = RouteStep(
        category="cid",
        title=cid_value,
        description=description,
        request_path=path,
        cid_markup=cid_markup,
        extra_details=extra,
        definition_excerpt=definition_excerpt,
    )

    summary = "Served from CID storage."
    return RouteResolution(
        normalized_path=path,
        final_status=200,
        final_summary=summary,
        redirect_target=None,
        steps=[step],
    )


def _not_found_resolution(path: str) -> RouteResolution:
    step = RouteStep(
        category="not_found",
        title="No matching handler",
        description="No alias, server, or CID matched the requested path.",
        request_path=path,
    )
    return RouteResolution(
        normalized_path=path,
        final_status=404,
        final_summary="Request results in a 404 response.",
        redirect_target=None,
        steps=[step],
    )


def _describe_single_step(path: str, existing_routes: set[str]) -> RouteResolution:
    builtin_resolution = _describe_builtin_route(path)
    if builtin_resolution is not None:
        return builtin_resolution

    alias_resolution = _alias_step_for(path, existing_routes)
    if alias_resolution is not None:
        return alias_resolution

    server_resolution = _server_step_for(path, existing_routes)
    if server_resolution is not None:
        return server_resolution

    versioned_resolution = _versioned_server_step_for(path, existing_routes)
    if versioned_resolution is not None:
        return versioned_resolution

    cid_resolution = _cid_step_for(path)
    if cid_resolution is not None:
        return cid_resolution

    return _not_found_resolution(path)


def describe_request_path(path: str) -> RouteResolution:
    """Return a structured description of how ``path`` is handled."""

    normalized = _normalize_requested_path(path)

    existing_routes = set(get_existing_routes())
    steps: list[RouteStep] = []
    visited: set[str] = set()
    current_path = normalized
    final_status: Optional[int] = None
    final_summary: str = ""
    redirect_target: Optional[str] = None
    redirects_followed = 0
    chain_limited = False
    loop_detected = False

    while True:
        if current_path in visited:
            loop_detected = True
            chain_limited = True
            break

        visited.add(current_path)

        resolution = _describe_single_step(current_path, existing_routes)
        steps.extend(resolution.steps)
        final_status = resolution.final_status
        final_summary = resolution.final_summary
        redirect_target = resolution.redirect_target

        if not redirect_target:
            break

        redirects_followed += 1
        next_path = _normalize_requested_path(redirect_target)

        if redirects_followed >= 20:
            chain_limited = True
            break

        if next_path in visited:
            loop_detected = True
            chain_limited = True
            break

        current_path = next_path

    summary_text = final_summary or ""
    if chain_limited:
        suffix = (
            f" Redirect loop detected after {redirects_followed} redirects."
            if loop_detected
            else f" Redirect chain truncated after {redirects_followed} redirects."
        )
        summary_text = (summary_text + suffix).strip()

    return RouteResolution(
        normalized_path=normalized,
        final_status=final_status,
        final_summary=summary_text,
        redirect_target=redirect_target,
        steps=steps,
        redirects_followed=redirects_followed,
        chain_limited=chain_limited,
        loop_detected=loop_detected,
    )


@main_bp.route("/routes/", defaults={"requested_path": ""})
@main_bp.route("/routes/<path:requested_path>")
def route_details(requested_path: str) -> str:
    """Render a detailed explanation for a specific request path."""

    resolution = describe_request_path(requested_path)
    return render_template(
        "route_details.html",
        resolution=resolution,
    )


__all__ = ["describe_request_path", "route_details"]
