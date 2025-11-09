"""Core metadata gathering and coordination for meta route."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from flask import Response, current_app, jsonify
from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from alias_routing import is_potential_alias_path
from server_execution import (
    is_potential_server_path,
    is_potential_versioned_server_path,
)

from routes.core import get_existing_routes
from routes import main_bp

from .meta_alias import attach_alias_targeting_metadata, resolve_alias_path
from .meta_cid import resolve_cid_path
from .meta_introspection import build_route_resolution
from .meta_path_utils import dedupe_links, normalize_target_path
from .meta_rendering import render_metadata_html
from .meta_server import resolve_server_path, resolve_versioned_server_path

META_SOURCE_LINK = "/source/routes/meta.py"


def metadata_status(metadata: Dict[str, Any]) -> int:
    """Return the HTTP status code that should accompany metadata."""
    status = metadata.get("status_code", 200)
    if status in {301, 302, 303, 307, 308}:
        return 200
    return status


def handle_not_found(
    path: str,
    *,
    include_alias_target_metadata: bool,
) -> Tuple[Optional[Dict[str, Any]], int]:
    """Return metadata for paths that fall through to the 404 handler."""
    existing_routes = get_existing_routes()

    if is_potential_alias_path(path, existing_routes):
        alias_metadata = resolve_alias_path(path, include_target_metadata=include_alias_target_metadata)
        if alias_metadata:
            return alias_metadata, metadata_status(alias_metadata)

    if is_potential_server_path(path, existing_routes):
        server_metadata = resolve_server_path(path)
        if server_metadata:
            return server_metadata, metadata_status(server_metadata)

    if is_potential_versioned_server_path(path, existing_routes):
        versioned_metadata = resolve_versioned_server_path(path)
        if versioned_metadata:
            return versioned_metadata, metadata_status(versioned_metadata)

    cid_metadata = resolve_cid_path(path)
    if cid_metadata:
        return cid_metadata, metadata_status(cid_metadata)

    return None, 404


def gather_metadata(
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
            attach_alias_targeting_metadata(metadata, metadata.get("path", path))
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
            route_metadata = build_route_resolution(path, rule, values, status_code=405, meta_source_link=META_SOURCE_LINK)
            metadata.update({
                "resolution": {
                    **route_metadata["resolution"],
                    "type": "method_not_allowed",
                    "allowed_methods": allowed,
                },
                "source_links": dedupe_links(metadata["source_links"] + route_metadata["source_links"]),
            })
        if include_alias_relations:
            attach_alias_targeting_metadata(metadata, metadata.get("path", path))
        return metadata, 200
    except NotFound:
        metadata, status = handle_not_found(
            path,
            include_alias_target_metadata=include_alias_target_metadata,
        )
        if metadata and include_alias_relations:
            attach_alias_targeting_metadata(metadata, metadata.get("path", path))
        return metadata, status

    metadata = build_route_resolution(path, rule, values, meta_source_link=META_SOURCE_LINK)
    if metadata and include_alias_relations:
        attach_alias_targeting_metadata(metadata, metadata.get("path", path))
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

    target_path = normalize_target_path(effective_path)
    metadata, status_code = gather_metadata(target_path)

    if not metadata:
        return jsonify({"error": "Path not found"}), status_code

    metadata.setdefault("source_links", []).append(META_SOURCE_LINK)
    metadata["source_links"] = dedupe_links(metadata["source_links"])
    metadata.setdefault("path", target_path)

    if html_format:
        html = render_metadata_html(metadata)
        return Response(html, status=status_code, mimetype="text/html")

    return jsonify(metadata), status_code


def inspect_path_metadata(
    requested_path: str,
    *,
    include_alias_relations: bool = True,
    include_alias_target_metadata: bool = True,
):
    """Expose metadata gathering for reuse outside the /meta route."""

    normalized = normalize_target_path(requested_path)
    return gather_metadata(
        normalized,
        include_alias_relations=include_alias_relations,
        include_alias_target_metadata=include_alias_target_metadata,
    )
