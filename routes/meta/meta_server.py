"""Server execution path resolution for meta route."""
from __future__ import annotations

from typing import Any, Dict, Optional

from db_access import get_server_by_name

from .meta_path_utils import dedupe_links

META_SOURCE_LINK = "/source/routes/meta.py"


def resolve_server_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for server execution paths."""
    parts = [segment for segment in path.strip("/").split("/") if segment]
    if not parts:
        return None

    server_name = parts[0]
    function_name = parts[1] if len(parts) > 1 else None
    payload: Dict[str, Any] = {
        "path": path,
        "source_links": dedupe_links([
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

    server = get_server_by_name(server_name)
    if not server:
        return None

    # Add server metadata for urleditor. We currently assume Python implementations
    # support chaining, which matches the common case for server definitions.
    payload["resolution"].update({
        "enabled": server.enabled,
        "supports_chaining": True,  # Python servers typically support chaining
        "language": "python",  # Most server definitions are Python
    })

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


def resolve_versioned_server_path(path: str) -> Optional[Dict[str, Any]]:
    """Return metadata for versioned server execution paths."""
    parts = [segment for segment in path.strip("/").split("/") if segment]
    if len(parts) not in {2, 3}:
        return None

    server_name, partial_cid = parts[0], parts[1]
    function_name = parts[2] if len(parts) == 3 else None
    payload: Dict[str, Any] = {
        "path": path,
        "source_links": dedupe_links([
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

    server = get_server_by_name(server_name)
    if not server:
        return None

    from routes.servers import get_server_definition_history

    history = get_server_definition_history(server_name)
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
