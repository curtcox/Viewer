"""Routes for inspecting how application paths are served."""
from __future__ import annotations

import ast
import inspect
import os
import textwrap
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlsplit

from flask import Response, current_app, jsonify, url_for
from markupsafe import Markup, escape
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from alias_definition import collect_alias_routes, get_primary_alias_route
from alias_routing import find_matching_alias, is_potential_alias_path, try_alias_redirect
from cid_presenter import cid_path, format_cid
from db_access import (
    find_server_invocations_by_cid,
    get_cid_by_path,
    get_server_by_name,
    get_user_aliases,
)
from entity_references import extract_references_from_bytes
from identity import current_user
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
)

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


def _normalize_alias_target_path(target: Optional[str]) -> Optional[str]:
    """Return a normalized local path for an alias target if available."""
    if not target:
        return None

    stripped = target.strip()
    if not stripped:
        return None

    parsed = urlsplit(stripped)
    if parsed.scheme or parsed.netloc:
        return None

    candidate = parsed.path or ""
    if not candidate:
        return None

    if not candidate.startswith("/"):
        candidate = f"/{candidate}"

    return candidate


def _serialize_alias(alias, route=None) -> Dict[str, Any]:
    """Return a JSON-serializable representation of an alias."""
    selected_route = route or get_primary_alias_route(alias)
    effective_pattern = None
    if selected_route and selected_route.match_pattern:
        effective_pattern = selected_route.match_pattern
    elif hasattr(alias, "get_effective_pattern"):
        effective_pattern = alias.get_effective_pattern()
    else:
        effective_pattern = getattr(alias, "match_pattern", None)

    target_path = selected_route.target_path if selected_route else None
    return {
        "id": getattr(alias, "id", None),
        "name": getattr(alias, "name", None),
        "match_type": selected_route.match_type if selected_route else None,
        "match_pattern": effective_pattern,
        "ignore_case": selected_route.ignore_case if selected_route else False,
        "target_path": target_path,
        "definition": getattr(alias, "definition", None),
    }


def _aliases_targeting_path(path: str) -> List[Dict[str, Any]]:
    """Return aliases owned by the current user that target the supplied path."""
    normalized = _normalize_target_path(path)
    aliases = []
    for alias in get_user_aliases(current_user.id):
        for route in collect_alias_routes(alias):
            target_path = _normalize_alias_target_path(route.target_path)
            if not target_path:
                continue
            if target_path != normalized:
                continue

            serialized = _serialize_alias(alias, route=route)
            serialized["meta_link"] = f"/meta/{serialized['name']}" if serialized.get("name") else None
            serialized["alias_path"] = route.alias_path
            aliases.append(serialized)

    return aliases


def _attach_alias_targeting_metadata(metadata: Dict[str, Any], path: str) -> None:
    """Annotate metadata with aliases targeting the supplied path."""
    aliases = _aliases_targeting_path(path)
    if not aliases:
        return

    metadata["aliases_targeting_path"] = aliases


def _resolve_alias_path(path: str, *, include_target_metadata: bool = True) -> Optional[Dict[str, Any]]:
    """Return metadata for alias-based routes if applicable."""
    base_payload: Dict[str, Any] = {
        "path": path,
        "source_links": _dedupe_links(["/source/alias_routing.py", META_SOURCE_LINK]),
        "resolution": {
            "type": "alias_redirect",
            "requires_authentication": False,
        },
    }

    alias_match = find_matching_alias(path)
    if not alias_match:
        return None

    alias_name = alias_match.route.alias_path or getattr(alias_match.alias, "name", None)
    base_payload["resolution"]["alias"] = alias_name

    redirect_response = try_alias_redirect(path, alias_match=alias_match)
    if redirect_response is None:
        return None

    base_payload["status_code"] = redirect_response.status_code
    target_path = alias_match.route.target_path
    base_payload["resolution"].update(
        {
            "available": True,
            "target_path": target_path,
            "redirect_location": redirect_response.location,
        }
    )

    if not include_target_metadata:
        return base_payload

    normalized_target = _normalize_alias_target_path(target_path)
    target_metadata: Dict[str, Any] = {
        "path": normalized_target or target_path,
    }

    if not normalized_target:
        target_metadata.update({"available": False, "reason": "external_or_invalid"})
        base_payload["resolution"]["target_metadata"] = target_metadata
        return base_payload

    if normalized_target == path:
        target_metadata.update({"available": False, "reason": "self_referential"})
        base_payload["resolution"]["target_metadata"] = target_metadata
        return base_payload

    target_metadata["meta_link"] = f"/meta/{normalized_target.lstrip('/')}"

    nested_metadata, status_code = _gather_metadata(
        normalized_target,
        include_alias_relations=False,
        include_alias_target_metadata=False,
    )

    if nested_metadata:
        target_metadata.update(
            {
                "available": True,
                "status_code": nested_metadata.get("status_code", status_code),
                "resolution": nested_metadata.get("resolution"),
                "source_links": nested_metadata.get("source_links"),
                "path": nested_metadata.get("path", normalized_target),
            }
        )
    else:
        target_metadata.update({"available": False})

    base_payload["resolution"]["target_metadata"] = target_metadata
    return base_payload


def _resolve_server_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for server execution paths."""
    parts = [segment for segment in path.strip("/").split("/") if segment]
    if not parts:
        return None

    server_name = parts[0]
    function_name = parts[1] if len(parts) > 1 else None
    payload: Dict[str, Any] = {
        "path": path,
        "source_links": _dedupe_links([
            "/source/routes/core.py",
            "/source/server_execution.py",
            META_SOURCE_LINK,
        ]),
        "resolution": {
            "type": "server_function_execution"
            if function_name
            else "server_execution",
            "server_name": server_name,
            "requires_authentication": False,
        },
    }

    if function_name:
        payload["resolution"]["function_name"] = function_name

    server = get_server_by_name(current_user.id, server_name)
    if not server:
        return None

    if function_name:
        from server_execution import describe_function_parameters

        details = describe_function_parameters(server.definition, function_name)
        if not details:
            return None

        payload["status_code"] = 302
        payload["resolution"].update(
            {
                "available": True,
                "function_parameters": details.get("parameters"),
            }
        )
        return payload

    payload["status_code"] = 302
    payload["resolution"].update({"available": True})
    return payload


def _resolve_versioned_server_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for versioned server execution paths."""
    parts = [segment for segment in path.strip("/").split("/") if segment]
    if len(parts) not in {2, 3}:
        return None

    server_name, partial_cid = parts[0], parts[1]
    function_name = parts[2] if len(parts) == 3 else None
    payload: Dict[str, Any] = {
        "path": path,
        "source_links": _dedupe_links([
            "/source/routes/core.py",
            "/source/server_execution.py",
            "/source/routes/servers.py",
            META_SOURCE_LINK,
        ]),
        "resolution": {
            "type": "versioned_server_function_execution"
            if function_name
            else "versioned_server_execution",
            "server_name": server_name,
            "partial_cid": partial_cid,
            "requires_authentication": False,
        },
    }

    if function_name:
        payload["resolution"]["function_name"] = function_name

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
    base_details = {
        "definition_cid": match.get("definition_cid"),
        "snapshot_cid": match.get("snapshot_cid"),
        "created_at": match.get("created_at").isoformat()
        if match.get("created_at")
        else None,
    }

    if function_name:
        from server_execution import describe_function_parameters

        details = describe_function_parameters(match.get("definition", ""), function_name)
        if not details:
            payload["status_code"] = 404
            payload["resolution"].update({"available": False, **base_details})
            return payload

        payload["status_code"] = 302
        payload["resolution"].update(
            {
                "available": True,
                **base_details,
                "function_parameters": details.get("parameters"),
            }
        )
        return payload

    payload["status_code"] = 302
    payload["resolution"].update({"available": True, **base_details})
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

    invocations = find_server_invocations_by_cid(cid_value)
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
            formatted_value = format_cid(value)
            if not formatted_value:
                continue
            related_cids[label] = formatted_value
            related_meta_links.append(
                url_for("main.meta_route", requested_path=formatted_value)
            )

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

    cid_value = format_cid(base_path)
    cid_record_path = cid_path(cid_value)
    if not cid_record_path:
        return None

    cid_record = get_cid_by_path(cid_record_path)
    if not cid_record:
        return None

    record: Dict[str, Any] = {
        "cid": cid_value,
        "path": cid_record_path,
        "file_size": cid_record.file_size,
        "created_at": cid_record.created_at.isoformat() if cid_record.created_at else None,
        "uploaded_by_user_id": cid_record.uploaded_by_user_id,
    }

    if cid_record.uploaded_by_user_id:
        record["uploaded_by"] = {
            "user_id": cid_record.uploaded_by_user_id,
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

    user_id = current_user.id
    references = extract_references_from_bytes(
        getattr(cid_record, "file_data", None),
        user_id,
    )
    if any(references.values()):
        metadata["referenced_entities"] = references

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


@lru_cache()
def _load_page_test_cross_reference(app_root: str) -> Dict[str, Dict[str, List[str]]]:
    """Return a mapping of templates to their documented automated checks."""

    doc_path = Path(app_root) / "docs" / "page_test_cross_reference.md"
    if not doc_path.is_file():
        return {}

    sections = {
        "routes": "routes",
        "unit tests": "unit_tests",
        "integration tests": "integration_tests",
        "specs": "specs",
    }

    mapping: Dict[str, Dict[str, List[str]]] = {}
    current_template: Optional[str] = None
    current_section: Optional[str] = None

    with doc_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("## "):
                template_name = line[3:].strip()
                current_template = template_name
                mapping[current_template] = {key: [] for key in sections.values()}
                current_section = None
                continue

            if line.startswith("**") and line.endswith("**"):
                header_text = line[2:-2].strip()
                if header_text.endswith(":"):
                    header_text = header_text[:-1]
                current_section = sections.get(header_text.lower())
                continue

            if not line.startswith("- ") or not current_template or not current_section:
                continue

            value = line[2:].strip()
            if value == "_None_":
                continue

            if value.startswith("`") and value.endswith("`"):
                value = value[1:-1]

            mapping[current_template][current_section].append(value)

    return mapping


def _templates_for_metadata(metadata: Dict[str, Any]) -> List[str]:
    """Return templates referenced by the supplied metadata in declaration order."""

    templates: List[str] = []
    for link in metadata.get("source_links", []) or []:
        if not isinstance(link, str):
            continue
        if not link.startswith("/source/"):
            continue
        relative = link[len("/source/") :]
        if not relative.startswith("templates/"):
            continue
        if relative not in templates:
            templates.append(relative)

    return templates


def _reference_to_source_link(reference: str, category: str) -> Optional[str]:
    """Return a /source URL for the supplied reference if available."""

    if category in {"unit_tests", "integration_tests"}:
        file_part = reference.split("::", 1)[0]
        if file_part.endswith(".py"):
            return f"/source/{file_part}"
        return None

    if category == "specs":
        file_part = reference.split(" — ", 1)[0].strip()
        if file_part and not file_part.startswith("specs/"):
            file_part = f"specs/{file_part}"
        if file_part:
            return f"/source/{file_part}"

    return None


def _render_reference_item(reference: str, category: str) -> Markup:
    """Return HTML for a single documented automated check."""

    href = _reference_to_source_link(reference, category)
    if category == "specs" and " — " in reference:
        name, description = reference.split(" — ", 1)
        link_html = Markup(f"<code>{escape(name)}</code>")
        if href:
            link_html = Markup(f'<a href="{escape(href)}">{link_html}</a>')
        return Markup(f"{link_html} — {escape(description)}")

    content = Markup(f"<code>{escape(reference)}</code>")
    if href:
        return Markup(f'<a href="{escape(href)}">{content}</a>')
    return content


def _render_related_tests_section(metadata: Dict[str, Any]) -> str:
    """Return an HTML section linking to tests that exercise the page."""

    templates = _templates_for_metadata(metadata)
    if not templates:
        return ""

    cross_reference = _load_page_test_cross_reference(current_app.root_path)
    categories = [
        ("unit_tests", "Unit tests"),
        ("integration_tests", "Integration tests"),
        ("specs", "Specs"),
    ]

    aggregated: Dict[str, List[str]] = {key: [] for key, _ in categories}
    for template in templates:
        data = cross_reference.get(template)
        if not data:
            continue
        for key, _ in categories:
            aggregated[key].extend(data.get(key, []))

    if not any(aggregated[key] for key, _ in categories):
        return ""

    for key in aggregated:
        aggregated[key] = list(dict.fromkeys(aggregated[key]))

    template_links = [
        Markup('<li><a href="{href}"><code>{label}</code></a></li>').format(
            href=escape(f"/source/{template}"), label=escape(template)
        )
        for template in templates
    ]

    sections_html: List[str] = [
        '<section class="meta-related-tests">',
        '<h2>Related automated coverage</h2>',
        '<p>Tests below are sourced from <code>docs/page_test_cross_reference.md</code> for templates rendered by this page.</p>',
        '<h3>Templates</h3>',
        '<ul class="meta-related-tests-templates">',
        "".join(str(item) for item in template_links),
        "</ul>",
    ]

    for key, label in categories:
        sections_html.append(f'<h3>{escape(label)}</h3>')
        items = aggregated[key]
        if items:
            sections_html.append('<ul class="meta-related-tests-list">')
            for reference in items:
                rendered = _render_reference_item(reference, key)
                sections_html.append(f"<li>{rendered}</li>")
            sections_html.append("</ul>")
        else:
            sections_html.append('<p><em>None documented.</em></p>')

    sections_html.append("</section>")
    return "".join(sections_html)


def _render_metadata_html(metadata: Dict[str, Any]) -> str:
    """Return an HTML page for the supplied metadata."""
    body = _render_value_html(metadata)
    related_tests = _render_related_tests_section(metadata)
    styles = """
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 1rem; }
    ul.meta-dict, ol.meta-list { list-style: none; padding-left: 1.25rem; }
    ul.meta-dict > li { margin-bottom: 0.5rem; }
    ul.meta-dict ul.meta-dict, ul.meta-dict ol.meta-list { margin-top: 0.5rem; }
    .meta-key { font-weight: 600; }
    code { background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 0.25rem; }
    a code { color: inherit; }
    .meta-related-tests { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; }
    .meta-related-tests h2 { margin-bottom: 0.5rem; }
    .meta-related-tests h3 { margin-top: 1.25rem; margin-bottom: 0.5rem; }
    .meta-related-tests ul { list-style: disc; padding-left: 1.5rem; }
    .meta-related-tests-templates { list-style: none; padding-left: 0; display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
    .meta-related-tests-templates li { list-style: none; }
    """
    return f"""<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Meta Inspector</title><style>{styles}</style></head><body><h1>Meta inspector</h1>{body}{related_tests}</body></html>"""


def _handle_not_found(
    path: str,
    *,
    include_alias_target_metadata: bool,
) -> Tuple[Optional[Dict[str, Any]], int]:
    """Return metadata for paths that fall through to the 404 handler."""
    existing_routes = get_existing_routes()

    if is_potential_alias_path(path, existing_routes):
        alias_metadata = _resolve_alias_path(path, include_target_metadata=include_alias_target_metadata)
        if alias_metadata:
            return alias_metadata, _metadata_status(alias_metadata)

    if is_potential_server_path(path, existing_routes):
        server_metadata = _resolve_server_path(path)
        if server_metadata:
            return server_metadata, _metadata_status(server_metadata)

    if is_potential_versioned_server_path(path, existing_routes):
        versioned_metadata = _resolve_versioned_server_path(path)
        if versioned_metadata:
            return versioned_metadata, _metadata_status(versioned_metadata)

    cid_metadata = _resolve_cid_path(path)
    if cid_metadata:
        return cid_metadata, _metadata_status(cid_metadata)

    return None, 404


def _gather_metadata(
    path: str,
    *,
    include_alias_relations: bool = True,
    include_alias_target_metadata: bool = True,
) -> Tuple[Optional[Dict[str, Any]], int]:
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
        if include_alias_relations:
            _attach_alias_targeting_metadata(metadata, metadata.get("path", path))
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
        if include_alias_relations:
            _attach_alias_targeting_metadata(metadata, metadata.get("path", path))
        return metadata, 200
    except NotFound:
        metadata, status = _handle_not_found(
            path,
            include_alias_target_metadata=include_alias_target_metadata,
        )
        if metadata and include_alias_relations:
            _attach_alias_targeting_metadata(metadata, metadata.get("path", path))
        return metadata, status

    metadata = _build_route_resolution(path, rule, values)
    if metadata and include_alias_relations:
        _attach_alias_targeting_metadata(metadata, metadata.get("path", path))
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


def inspect_path_metadata(
    requested_path: str,
    *,
    include_alias_relations: bool = True,
    include_alias_target_metadata: bool = True,
):
    """Expose metadata gathering for reuse outside the /meta route."""

    normalized = _normalize_target_path(requested_path)
    return _gather_metadata(
        normalized,
        include_alias_relations=include_alias_relations,
        include_alias_target_metadata=include_alias_target_metadata,
    )


__all__ = ["inspect_path_metadata", "meta_route"]
