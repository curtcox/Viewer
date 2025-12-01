"""Server resolution and versioned execution logic."""

from typing import Any, Callable, Dict, Iterable, Optional

from flask import Response, jsonify, render_template

from db_access import get_server_by_name
# pylint: disable=no-name-in-module  # False positive: submodules exist
from server_execution.code_execution import (
    _auto_main_accepts_additional_path,
    execute_server_code,
    execute_server_code_from_definition,
    execute_server_function,
    execute_server_function_from_definition,
)
from server_execution.language_detection import detect_server_language
# pylint: enable=no-name-in-module


def is_potential_versioned_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could represent /{server}/{partial_cid}[/function]."""
    if not path or not path.startswith("/"):
        return False
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) not in {2, 3}:
        return False
    if f"/{parts[0]}" in existing_routes:
        return False
    return True


def try_server_execution_with_partial(
    path: str,
    history_fetcher: Callable[[str], Iterable[Dict[str, Any]]],
) -> Optional[Any]:
    """Execute a server version referenced by a partial CID."""
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) not in {2, 3}:
        return None
    server_name, partial = parts[0], parts[1]
    function_name = parts[2] if len(parts) == 3 else None

    server = get_server_by_name(server_name)
    if server and not getattr(server, "enabled", True):
        server = None
    if not server:
        return None

    history = history_fetcher(server_name)
    matches = [h for h in history if h.get("definition_cid", "").startswith(partial)]

    if not matches:
        return render_template("404.html", path=path), 404

    if len(matches) > 1:
        payload = {
            "error": "Multiple matching server versions",
            "server": server_name,
            "partial": partial,
            "matches": [
                {
                    "definition_cid": m.get("definition_cid"),
                    "snapshot_cid": m.get("snapshot_cid"),
                    "created_at": m.get("created_at").isoformat() if m.get("created_at") else None,
                }
                for m in matches
            ],
        }
        return jsonify(payload), 400

    definition_text = matches[0].get("definition", "")
    if function_name:
        return execute_server_function_from_definition(
            definition_text, server_name, function_name
        )
    return execute_server_code_from_definition(definition_text, server_name)


def is_potential_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could map to a server name or helper function."""

    if not path or not path.startswith("/"):
        return False

    if path in existing_routes:
        return False

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return False

    if f"/{parts[0]}" in existing_routes:
        return False

    return True


def try_server_execution(path: str) -> Optional[Response]:
    """Execute the server whose name matches the request path."""
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return None

    server_name = parts[0]
    server = get_server_by_name(server_name)
    if server and not getattr(server, "enabled", True):
        server = None
    if not server:
        return None

    if len(parts) == 1:
        return execute_server_code(server, server_name)

    if len(parts) > 2:
        return execute_server_code(server, server_name)

    function_name = parts[1]
    if not function_name.isidentifier():
        return execute_server_code(server, server_name)

    if detect_server_language(getattr(server, "definition", "")) != "python":
        return execute_server_code(server, server_name)

    result = execute_server_function(server, server_name, function_name)
    if result is None:
        if _auto_main_accepts_additional_path(server):
            return execute_server_code(server, server_name)
        return None

    return result
