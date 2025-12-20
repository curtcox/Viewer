"""Alias resolution and metadata for meta route."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from alias_definition import collect_alias_routes, get_primary_alias_route
from alias_routing import find_matching_alias, try_alias_redirect
from db_access import get_aliases

from .meta_path_utils import (
    dedupe_links,
    normalize_alias_target_path,
    normalize_target_path,
)

META_SOURCE_LINK = "/source/routes/meta.py"


def serialize_alias(alias, route=None) -> Dict[str, Any]:
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


def aliases_targeting_path(path: str) -> List[Dict[str, Any]]:
    """Return aliases that target the supplied path."""
    normalized = normalize_target_path(path)
    aliases = []
    for alias in get_aliases():
        for route in collect_alias_routes(alias):
            target_path = normalize_alias_target_path(route.target_path)
            if not target_path:
                continue
            if target_path != normalized:
                continue

            serialized = serialize_alias(alias, route=route)
            serialized["meta_link"] = (
                f"/meta/{serialized['name']}" if serialized.get("name") else None
            )
            serialized["alias_path"] = route.alias_path
            aliases.append(serialized)

    return aliases


def attach_alias_targeting_metadata(metadata: Dict[str, Any], path: str) -> None:
    """Annotate metadata with aliases targeting the supplied path."""
    aliases = aliases_targeting_path(path)
    if not aliases:
        return

    metadata["aliases_targeting_path"] = aliases


def resolve_alias_path(
    path: str, *, include_target_metadata: bool = True
) -> Optional[Dict[str, Any]]:
    """Return metadata for alias-based routes if applicable."""
    # Import here to avoid circular dependency
    from .meta_core import gather_metadata

    base_payload: Dict[str, Any] = {
        "path": path,
        "source_links": dedupe_links(["/source/alias_routing.py", META_SOURCE_LINK]),
        "resolution": {
            "type": "alias_redirect",
            "requires_authentication": False,
        },
    }

    alias_match = find_matching_alias(path)
    if not alias_match:
        return None

    alias_name = alias_match.route.alias_path or getattr(
        alias_match.alias, "name", None
    )
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

    normalized_target = normalize_alias_target_path(target_path)
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

    nested_metadata, status_code = gather_metadata(
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
