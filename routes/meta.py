"""Routes for inspecting how application paths are served."""
from __future__ import annotations

import ast
import inspect
import os
import textwrap
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import Response, current_app, jsonify, url_for
from flask_login import current_user
from sqlalchemy import or_
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from alias_routing import find_matching_alias, is_potential_alias_path, try_alias_redirect
from db_access import get_cid_by_path, get_server_by_name
from models import ServerInvocation
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
)

from markupsafe import Markup, escape

from . import main_bp
from .core import get_existing_routes

META_SOURCE_LINK = "/source/routes/meta.py"


def _normalize_target_path(requested_path: str) -> str:
    """Convert the requested metadata path into an absolute target path."""
    if not requested_path:
        return "/"

    stripped = requested_path.strip()
    if not stripped:
        return "/"

    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    return stripped


def _dedupe_links(links: Iterable[str]) -> List[str]:
    """Return links without duplicates while preserving order."""
    seen: set[str] = set()
    result: List[str] = []
    for link in links:
        if not link or link in seen:
            continue
        seen.add(link)
        result.append(link)
    return result


def _collect_source_links(obj: Any) -> List[str]:
    """Return /source links associated with the supplied callable if available."""
    if obj is None:
        return []

    candidates: List[str] = []
    repo_root = os.path.abspath(current_app.root_path)

    for target in {obj, inspect.unwrap(obj)}:
        try:
            source_path = inspect.getsourcefile(target) or inspect.getfile(target)  # type: ignore[arg-type]
        except (TypeError, OSError):
            continue

        if not source_path:
            continue

        abs_path = os.path.abspath(source_path)
        try:
            common = os.path.commonpath([repo_root, abs_path])
        except ValueError:
            continue

        if common != repo_root:
            continue

        relative_path = os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
        candidates.append(f"/source/{relative_path}")

    return _dedupe_links(candidates)


def _collect_template_links(obj: Any) -> List[str]:
    """Return /source links for templates rendered by the supplied callable."""
    if obj is None:
        return []

    try:
        source = inspect.getsource(obj)
    except (OSError, TypeError):
        return []

    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return []

    template_names: List[str] = []

    class TemplateVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # pragma: no cover - simple traversal
            func = node.func
            func_name: Optional[str] = None
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name == "render_template" and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    template_names.append(first_arg.value)

            self.generic_visit(node)

    TemplateVisitor().visit(tree)

    if not template_names:
        return []

    repo_root = os.path.abspath(current_app.root_path)
    links: List[str] = []

    loader = getattr(current_app, "jinja_loader", None)
    search_paths: List[str] = []
    if loader is not None:
        search_paths.extend(getattr(loader, "searchpath", []) or [])

    default_templates = os.path.join(current_app.root_path, "templates")
    if default_templates not in search_paths:
        search_paths.append(default_templates)

    for template_name in template_names:
        found_path: Optional[str] = None
        for base in search_paths:
            candidate = os.path.abspath(os.path.join(base, template_name))
            if os.path.isfile(candidate):
                found_path = candidate
                break

        if not found_path:
            continue

        try:
            relative_path = os.path.relpath(found_path, repo_root).replace(os.sep, "/")
        except ValueError:
            continue

        links.append(f"/source/{relative_path}")

    return _dedupe_links(links)


def _build_route_resolution(path: str, rule, values: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """Return metadata for a matched Flask route."""
    endpoint = getattr(rule, "endpoint", None)
    methods = sorted(m for m in (getattr(rule, "methods", None) or []) if m not in {"HEAD", "OPTIONS"})
    view_func = current_app.view_functions.get(endpoint) if endpoint else None
    unwrapped = inspect.unwrap(view_func) if view_func else None

    resolution: Dict[str, Any] = {
        "path": path,
        "status_code": status_code,
        "resolution": {
            "type": "route",
            "endpoint": endpoint,
            "rule": getattr(rule, "rule", None),
            "arguments": values,
            "methods": methods,
            "blueprint": endpoint.split(".", 1)[0] if endpoint and "." in endpoint else None,
            "callable": f"{unwrapped.__module__}.{unwrapped.__name__}" if unwrapped else None,
            "docstring": inspect.getdoc(unwrapped) if unwrapped else None,
        },
        "source_links": _dedupe_links(
            _collect_source_links(view_func)
            + _collect_template_links(view_func)
            + [META_SOURCE_LINK]
        ),
    }

    return resolution


def _extract_alias_name(path: str) -> Optional[str]:
    """Return the alias segment from a path."""
    if not path or not path.startswith("/"):
        return None
    remainder = path[1:]
    if not remainder:
        return None
    return remainder.split("/", 1)[0]


def _resolve_alias_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for alias-based routes if applicable."""
    base_payload: Dict[str, Any] = {
        "path": path,
        "source_links": _dedupe_links(["/source/alias_routing.py", META_SOURCE_LINK]),
        "resolution": {
            "type": "alias_redirect",
            "requires_authentication": True,
        },
    }

    if not getattr(current_user, "is_authenticated", False):
        return None

    alias_obj = find_matching_alias(path)
    if not alias_obj:
        return None

    base_payload["resolution"]["alias"] = alias_obj.name

    redirect_response = try_alias_redirect(path)
    if redirect_response is None:
        return None

    base_payload["status_code"] = redirect_response.status_code
    base_payload["resolution"].update(
        {
            "available": True,
            "target_path": getattr(alias_obj, "target_path", None),
            "redirect_location": redirect_response.location,
        }
    )
    return base_payload


def _resolve_server_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for server execution paths."""
    server_name = path.lstrip("/")
    payload: Dict[str, Any] = {
        "path": path,
        "source_links": _dedupe_links([
            "/source/routes/core.py",
            "/source/server_execution.py",
            META_SOURCE_LINK,
        ]),
        "resolution": {
            "type": "server_execution",
            "server_name": server_name,
            "requires_authentication": True,
        },
    }

    if not getattr(current_user, "is_authenticated", False):
        return None

    server = get_server_by_name(current_user.id, server_name)
    if not server:
        return None

    payload["status_code"] = 302
    payload["resolution"].update({"available": True})
    return payload


def _resolve_versioned_server_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for versioned server execution paths."""
    parts = [segment for segment in path.strip("/").split("/") if segment]
    if len(parts) != 2:
        return None

    server_name, partial_cid = parts
    payload: Dict[str, Any] = {
        "path": path,
        "source_links": _dedupe_links([
            "/source/routes/core.py",
            "/source/server_execution.py",
            "/source/routes/servers.py",
            META_SOURCE_LINK,
        ]),
        "resolution": {
            "type": "server_version_execution",
            "server_name": server_name,
            "partial_cid": partial_cid,
            "requires_authentication": True,
        },
    }

    if not getattr(current_user, "is_authenticated", False):
        return None

    server = get_server_by_name(current_user.id, server_name)
    if not server:
        return None

    from .servers import get_server_definition_history

    history = get_server_definition_history(current_user.id, server_name)
    matches = [
        entry
        for entry in history
        if entry.get("definition_cid", "").startswith(partial_cid)
    ]

    if not matches:
        payload["status_code"] = 404
        payload["resolution"].update({"available": False, "matches": []})
        return payload

    if len(matches) > 1:
        payload["status_code"] = 400
        payload["resolution"].update(
            {
                "available": False,
                "matches": [
                    {
                        "definition_cid": m.get("definition_cid"),
                        "snapshot_cid": m.get("snapshot_cid"),
                        "created_at": m.get("created_at").isoformat() if m.get("created_at") else None,
                    }
                    for m in matches
                ],
            }
        )
        return payload

    match = matches[0]
    payload["status_code"] = 302
    payload["resolution"].update(
        {
            "available": True,
            "definition_cid": match.get("definition_cid"),
            "snapshot_cid": match.get("snapshot_cid"),
            "created_at": match.get("created_at").isoformat() if match.get("created_at") else None,
        }
    )
    return payload


def _split_extension(path: str) -> Tuple[str, Optional[str]]:
    """Return the base path and optional extension."""
    if "/" in path:
        last_segment = path.rsplit("/", 1)[-1]
    else:
        last_segment = path

    if "." in last_segment:
        base, extension = path.rsplit(".", 1)
        return base, extension
    return path, None


def _server_events_for_cid(cid_value: str) -> List[Dict[str, Any]]:
    """Return server invocation metadata for the supplied CID."""
    if not cid_value:
        return []

    filters = [
        ServerInvocation.result_cid == cid_value,
        ServerInvocation.invocation_cid == cid_value,
        ServerInvocation.request_details_cid == cid_value,
        ServerInvocation.servers_cid == cid_value,
        ServerInvocation.variables_cid == cid_value,
        ServerInvocation.secrets_cid == cid_value,
    ]

    invocations = ServerInvocation.query.filter(or_(*filters)).all()
    if not invocations:
        return []

    events: List[Dict[str, Any]] = []
    cid_fields = {
        "result_cid": "result",
        "invocation_cid": "invocation",
        "request_details_cid": "request_details",
        "servers_cid": "servers",
        "variables_cid": "variables",
        "secrets_cid": "secrets",
    }

    for invocation in invocations:
        related_meta_links: List[str] = []
        related_cids: Dict[str, str] = {}
        for field, label in cid_fields.items():
            value = getattr(invocation, field, None)
            if not value:
                continue
            related_cids[label] = value
            related_meta_links.append(f"/meta/{value}")

        events.append(
            {
                "server_name": invocation.server_name,
                "event_page": url_for("main.server_events"),
                "invoked_at": invocation.invoked_at.isoformat() if invocation.invoked_at else None,
                "related_cids": related_cids,
                "related_cid_meta_links": _dedupe_links(related_meta_links),
            }
        )

    return events


def _resolve_cid_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for CID-backed content."""
    base_path, extension = _split_extension(path)
    if not base_path.startswith("/"):
        return None

    cid_record = get_cid_by_path(base_path)
    if not cid_record:
        return None

    cid_value = base_path.lstrip("/")
    record: Dict[str, Any] = {
        "cid": cid_value,
        "path": cid_record.path,
        "file_size": cid_record.file_size,
        "created_at": cid_record.created_at.isoformat() if cid_record.created_at else None,
        "uploaded_by_user_id": cid_record.uploaded_by_user_id,
    }

    uploader = getattr(cid_record, "uploaded_by", None)
    if uploader:
        record["uploaded_by"] = {
            "user_id": uploader.id,
            "username": uploader.username,
            "email": uploader.email,
        }

    metadata: Dict[str, Any] = {
        "path": path,
        "status_code": 200,
        "resolution": {
            "type": "cid",
            "cid": cid_value,
            "extension": extension,
            "record": record,
        },
        "source_links": _dedupe_links([
            "/source/routes/core.py",
            "/source/cid_utils.py",
            META_SOURCE_LINK,
        ]),
    }

    server_events = _server_events_for_cid(cid_value)
    if server_events:
        metadata["server_events"] = server_events
        metadata["source_links"] = _dedupe_links(metadata["source_links"] + ["/source/server_execution.py"])

    return metadata


def _metadata_status(metadata: Dict[str, Any]) -> int:
    """Return the HTTP status code that should accompany metadata."""
    status = metadata.get("status_code", 200)
    if status in {301, 302, 303, 307, 308}:
        return 200
    return status


def _render_scalar_html(value: Any) -> Markup:
    """Return HTML for a scalar metadata value."""
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.startswith("/") or trimmed.startswith("http://") or trimmed.startswith("https://"):
            escaped_value = escape(value)
            return Markup(f'<a href="{escaped_value}"><code>{escaped_value}</code></a>')
        return Markup(f"<code>{escape(value)}</code>")

    if value is None:
        return Markup("<code>null</code>")

    if isinstance(value, bool):
        return Markup(f"<code>{str(value).lower()}</code>")

    if isinstance(value, (int, float)):
        return Markup(f"<code>{value}</code>")

    return Markup(f"<code>{escape(str(value))}</code>")


def _render_value_html(value: Any) -> Markup:
    """Recursively render metadata as HTML."""
    if isinstance(value, dict):
        items = []
        for key, child in value.items():
            items.append(
                Markup("<li><span class=\"meta-key\">{}</span>: {}</li>").format(
                    escape(key), _render_value_html(child)
                )
            )
        return Markup("<ul class=\"meta-dict\">{}</ul>").format(Markup("".join(items)))

    if isinstance(value, (list, tuple, set)):
        items = [Markup("<li>{}</li>").format(_render_value_html(child)) for child in value]
        return Markup("<ol class=\"meta-list\">{}</ol>").format(Markup("".join(items)))

    return _render_scalar_html(value)


def _render_metadata_html(metadata: Dict[str, Any]) -> str:
    """Return an HTML page for the supplied metadata."""
    body = _render_value_html(metadata)
    styles = """
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 1rem; }
    ul.meta-dict, ol.meta-list { list-style: none; padding-left: 1.25rem; }
    ul.meta-dict > li { margin-bottom: 0.5rem; }
    ul.meta-dict ul.meta-dict, ul.meta-dict ol.meta-list { margin-top: 0.5rem; }
    .meta-key { font-weight: 600; }
    code { background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 0.25rem; }
    a code { color: inherit; }
    """
    return f"""<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Meta Inspector</title><style>{styles}</style></head><body><h1>Meta inspector</h1>{body}</body></html>"""


def _handle_not_found(path: str) -> Tuple[Optional[Dict[str, Any]], int]:
    """Return metadata for paths that fall through to the 404 handler."""
    existing_routes = get_existing_routes()

    if is_potential_alias_path(path, existing_routes):
        alias_metadata = _resolve_alias_path(path)
        if alias_metadata:
            return alias_metadata, _metadata_status(alias_metadata)

    if is_potential_versioned_server_path(path, existing_routes):
        versioned_metadata = _resolve_versioned_server_path(path)
        if versioned_metadata:
            return versioned_metadata, _metadata_status(versioned_metadata)

    if is_potential_server_path(path, existing_routes):
        server_metadata = _resolve_server_path(path)
        if server_metadata:
            return server_metadata, _metadata_status(server_metadata)

    cid_metadata = _resolve_cid_path(path)
    if cid_metadata:
        return cid_metadata, _metadata_status(cid_metadata)

    return None, 404


def _gather_metadata(path: str) -> Tuple[Optional[Dict[str, Any]], int]:
    """Return metadata for the requested application path."""
    adapter = current_app.url_map.bind("")
    try:
        rule, values = adapter.match(path, method="GET", return_rule=True)
    except RequestRedirect as redirect_exc:
        metadata = {
            "path": path,
            "status_code": redirect_exc.code,
            "resolution": {
                "type": "redirect",
                "location": redirect_exc.new_url,
            },
            "source_links": [META_SOURCE_LINK],
        }
        return metadata, 200
    except MethodNotAllowed as exc:
        allowed = sorted(exc.valid_methods or [])
        metadata = {
            "path": path,
            "status_code": 405,
            "resolution": {
                "type": "method_not_allowed",
                "allowed_methods": allowed,
            },
            "source_links": [META_SOURCE_LINK],
        }
        if allowed:
            rule, values = adapter.match(path, method=allowed[0], return_rule=True)
            route_metadata = _build_route_resolution(path, rule, values, status_code=405)
            metadata.update({
                "resolution": {
                    **route_metadata["resolution"],
                    "type": "method_not_allowed",
                    "allowed_methods": allowed,
                },
                "source_links": _dedupe_links(metadata["source_links"] + route_metadata["source_links"]),
            })
        return metadata, 200
    except NotFound:
        return _handle_not_found(path)

    metadata = _build_route_resolution(path, rule, values)
    return metadata, 200


@main_bp.route("/meta", defaults={"requested_path": ""}, strict_slashes=False)
@main_bp.route("/meta/<path:requested_path>")
def meta_route(requested_path: str):
    """Return diagnostic information about how a path is served."""
    html_format = False
    effective_path = requested_path
    if requested_path.endswith(".html"):
        html_format = True
        effective_path = requested_path[: -len(".html")]

    target_path = _normalize_target_path(effective_path)
    metadata, status_code = _gather_metadata(target_path)

    if not metadata:
        return jsonify({"error": "Path not found"}), status_code

    metadata.setdefault("source_links", []).append(META_SOURCE_LINK)
    metadata["source_links"] = _dedupe_links(metadata["source_links"])
    metadata.setdefault("path", target_path)

    if html_format:
        html = _render_metadata_html(metadata)
        return Response(html, status=status_code, mimetype="text/html")

    return jsonify(metadata), status_code


__all__ = ["meta_route"]
