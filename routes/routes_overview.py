"""Routes overview page with built-ins, aliases, and servers."""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from flask import current_app, render_template, url_for
from identity import current_user

from db_access import get_user_aliases, get_user_servers

from . import main_bp


@dataclass
class RouteEntry:
    """A single route entry rendered in the overview."""

    category: str
    path: str
    name: str
    definition_label: str
    definition_url: str
    extra_detail: Optional[str] = None
    is_duplicate: bool = False
    is_catch_all: bool = False

    @property
    def category_label(self) -> str:
        return {
            "builtin": "Built-in",
            "alias": "Alias",
            "server": "Server",
            "not_found": "Not Found",
        }.get(self.category, self.category.title())

    @property
    def icon_class(self) -> str:
        return {
            "builtin": "fa-code",
            "alias": "fa-link",
            "server": "fa-server",
            "not_found": "fa-triangle-exclamation",
        }.get(self.category, "fa-circle")

    @property
    def badge_class(self) -> str:
        return {
            "builtin": "text-bg-info",
            "alias": "text-bg-primary",
            "server": "text-bg-success",
            "not_found": "text-bg-danger",
        }.get(self.category, "text-bg-secondary")


def _relative_path(candidate: Path, root: Path) -> Optional[str]:
    """Return the repository relative path when available."""

    try:
        return candidate.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def _builtin_routes(root: Path) -> Iterable[RouteEntry]:
    """Collect built-in Flask routes defined inside the application."""

    collected: List[RouteEntry] = []
    for rule in current_app.url_map.iter_rules():
        view_func = current_app.view_functions.get(rule.endpoint)
        if not view_func:
            continue

        view_func = inspect.unwrap(view_func)

        code = getattr(view_func, "__code__", None)
        if not code:
            continue

        file_path = Path(inspect.getsourcefile(view_func) or code.co_filename)
        relative = _relative_path(file_path, root)
        if not relative:
            continue

        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        extra_detail = ", ".join(methods)
        definition_url = url_for("main.source_browser", requested_path=relative)

        collected.append(
            RouteEntry(
                category="builtin",
                path=rule.rule,
                name=rule.endpoint,
                definition_label=relative,
                definition_url=definition_url,
                extra_detail=extra_detail,
            )
        )

    return collected


def _alias_routes() -> Iterable[RouteEntry]:
    """Collect alias definitions for the current user."""

    aliases = get_user_aliases(current_user.id)
    entries: List[RouteEntry] = []
    for alias in aliases:
        pattern = getattr(alias, "get_effective_pattern", lambda: None)()
        pattern = pattern or f"/{getattr(alias, 'name', '')}"

        entries.append(
            RouteEntry(
                category="alias",
                path=pattern,
                name=alias.name,
                definition_label=f"Alias: {alias.name}",
                definition_url=url_for("main.view_alias", alias_name=alias.name),
                extra_detail=getattr(alias, "match_type", "literal"),
            )
        )

    return entries


def _server_routes() -> Iterable[RouteEntry]:
    """Collect server definitions for the current user."""

    servers = get_user_servers(current_user.id)
    entries: List[RouteEntry] = []
    for server in servers:
        entries.append(
            RouteEntry(
                category="server",
                path=f"/{server.name}",
                name=server.name,
                definition_label=f"Server: {server.name}",
                definition_url=url_for("main.view_server", server_name=server.name),
            )
        )

    return entries


def _not_found_entry(root: Path) -> RouteEntry:
    """Create a catch-all entry describing the 404 handler."""

    from .core import not_found_error

    handler = inspect.unwrap(not_found_error)
    code = getattr(handler, "__code__", None)
    handler_path = Path(inspect.getsourcefile(handler) or (code.co_filename if code else ""))
    relative_handler = _relative_path(handler_path, root)

    definition_label = (
        f"{relative_handler} · not_found_error" if relative_handler else "404 handler"
    )
    definition_url = (
        url_for("main.source_browser", requested_path=relative_handler)
        if relative_handler
        else "#"
    )

    template_path = Path(current_app.root_path) / "templates" / "404.html"
    relative_template = _relative_path(template_path, root)

    detail_parts = [
        "Returns a 404 response when no route, alias, server, or CID matches.",
    ]
    if relative_template:
        detail_parts.append(f"Template: {relative_template}")

    return RouteEntry(
        category="not_found",
        path="/(any unmatched path)",
        name="not_found_error",
        definition_label=definition_label,
        definition_url=definition_url,
        extra_detail=" ".join(detail_parts),
        is_catch_all=True,
    )


def _mark_duplicates(entries: List[RouteEntry]) -> None:
    """Flag entries that share the same path across or within categories."""

    path_map: dict[str, List[RouteEntry]] = {}
    for entry in entries:
        path_map.setdefault(entry.path, []).append(entry)

    for siblings in path_map.values():
        if len(siblings) > 1:
            for entry in siblings:
                entry.is_duplicate = True


@main_bp.route("/routes")
def routes_overview():
    """Render a comprehensive list of routes, aliases, and servers."""

    repository_root = Path(current_app.root_path)

    entries: List[RouteEntry] = []
    entries.extend(_builtin_routes(repository_root))
    entries.extend(_alias_routes())
    entries.extend(_server_routes())
    entries.append(_not_found_entry(repository_root))

    _mark_duplicates(entries)

    entries.sort(key=lambda item: (item.is_catch_all, item.path, item.category, item.name))

    return render_template(
        "routes_overview.html",
        entries=entries,
    )


__all__ = ["routes_overview"]
