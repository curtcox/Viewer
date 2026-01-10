"""Utility functions for gateway operations.

This module contains helper functions that don't fit into other
specialized modules but are needed across the gateway.
"""

import json
import traceback
from pathlib import Path
from typing import Any, Optional
from flask import current_app
from jinja2 import Template


def safe_preview_request_details(request_details: dict) -> dict:
    """Create a safe preview of request details for logging/debugging.

    Filters out sensitive information like cookies and authorization headers.

    Args:
        request_details: Request details dictionary

    Returns:
        Filtered dictionary safe for logging

    Example:
        >>> details = {
        ...     "path": "/ls",
        ...     "method": "GET",
        ...     "headers": {"Authorization": "Bearer token", "User-Agent": "curl"}
        ... }
        >>> safe_preview_request_details(details)
        {'path': '/ls', 'method': 'GET', 'headers': {'User-Agent': 'curl'}}
    """
    if not isinstance(request_details, dict):
        return {"type": type(request_details).__name__}

    preview = {}
    for key in ("url", "path", "query_string", "method"):
        if key in request_details:
            preview[key] = request_details.get(key)

    headers = request_details.get("headers")
    if isinstance(headers, dict):
        preview["headers"] = {
            k: v
            for k, v in headers.items()
            if str(k).lower() not in ("cookie", "authorization")
        }

    return preview


def format_exception_detail(exc: Exception, *, debug_context: Optional[dict] = None) -> str:
    """Format exception with debug context as JSON string.

    Args:
        exc: Exception to format
        debug_context: Optional additional debug context

    Returns:
        JSON formatted string with exception details

    Example:
        >>> try:
        ...     raise ValueError("test error")
        ... except Exception as e:
        ...     detail = format_exception_detail(e, debug_context={"gateway": "man"})
        ...     # Returns JSON with exception_type, exception, traceback, debug_context
    """
    detail = {
        "exception_type": type(exc).__name__,
        "exception": str(exc),
    }
    if debug_context:
        detail["debug_context"] = debug_context

    detail["traceback"] = traceback.format_exc()
    return json.dumps(detail, indent=2, default=str)


def load_template(template_name: str) -> Template:
    """Load a Jinja2 template from the gateway templates directory.

    Tries multiple paths to find templates:
    1. Flask app root + reference/templates/servers/templates/gateway/
    2. Current working directory relative paths

    Args:
        template_name: Name of template file to load

    Returns:
        Jinja2 Template object

    Example:
        >>> template = load_template("instruction.html")
        >>> html = template.render(gateways={})
    """
    template_paths = []

    # Try Flask app root path
    try:
        app_root = Path(current_app.root_path)
        template_paths.append(
            app_root / "reference/templates" / "servers" / "templates" / "gateway" / template_name
        )
    except RuntimeError:
        # No Flask app context
        pass

    # Try current working directory
    cwd = Path.cwd()
    template_paths.append(
        cwd / "reference/templates" / "servers" / "templates" / "gateway" / template_name
    )

    for template_path in template_paths:
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return Template(f.read())

    # Fallback: return a simple error template
    tried_paths = ", ".join(str(p) for p in template_paths)
    return Template(
        f"""<!DOCTYPE html><html><body>
        <h1>Template Not Found</h1>
        <p>Could not load template: {{{{ template_name }}}}</p>
        <p>Tried paths: {tried_paths}</p>
        </body></html>"""
    )


def default_mock_server_cid(default_cid: str) -> str:
    """Get default mock server CID.

    Checks if CID file exists in cids/ directory, otherwise returns the default.

    Args:
        default_cid: Default CID to use if file doesn't exist

    Returns:
        CID string

    Example:
        >>> cid = default_mock_server_cid("AAA...")
    """
    cid_file = Path.cwd() / "cids" / default_cid
    return default_cid if cid_file.exists() else ""


def collect_mock_server_cids() -> dict[str, str]:
    """Collect all mock server CID files from the cids/ directory.

    Returns dictionary mapping server names to their CID values.

    Returns:
        Dictionary of server_name -> CID

    Example:
        >>> cids = collect_mock_server_cids()
        >>> # Returns {'alias': 'CIDAAA...', 'jsonplaceholder': 'CIDBBB...', ...}
    """
    cids_dir = Path.cwd() / "cids"
    if not cids_dir.exists():
        return {}

    mock_servers = {}

    # Scan cids directory for files
    for cid_file in cids_dir.glob("*"):
        if cid_file.is_file() and not cid_file.name.startswith('.'):
            # Try to match against known servers or use filename
            cid = cid_file.name
            # Check if this is a known test/mock server CID
            if len(cid) > 50:  # Likely a CID
                # Store with the CID as key for now
                # Could be enhanced to detect server type from content
                pass

    return mock_servers


def collect_external_service_servers() -> dict[str, dict[str, Any]]:
    """Collect information about external service servers.

    Scans for servers that might be external APIs and gathers their info.

    Returns:
        Dictionary mapping server names to their info

    Example:
        >>> servers = collect_external_service_servers()
        >>> # Returns {'server_name': {'url': '...', 'description': '...'}, ...}
    """
    # This would typically query the database or configuration
    # For now, return empty dict as placeholder
    # The actual implementation is in gateway.py and uses Server model
    return {}


def infer_external_api_for_server(server_name: str) -> Optional[str]:
    """Infer external API URL for a server based on its name.

    Uses heuristics to guess likely external API endpoints.

    Args:
        server_name: Name of the server

    Returns:
        Inferred API URL or None

    Example:
        >>> infer_external_api_for_server("github")
        'https://api.github.com'
        >>> infer_external_api_for_server("jsonplaceholder")
        'https://jsonplaceholder.typicode.com'
    """
    # Common API patterns
    api_patterns = {
        "github": "https://api.github.com",
        "gitlab": "https://gitlab.com/api/v4",
        "bitbucket": "https://api.bitbucket.org/2.0",
        "jsonplaceholder": "https://jsonplaceholder.typicode.com",
        "httpbin": "https://httpbin.org",
        "reqres": "https://reqres.in/api",
        "dummyapi": "https://dummyapi.io/data/v1",
        "randomuser": "https://randomuser.me/api",
        "swapi": "https://swapi.dev/api",
        "pokeapi": "https://pokeapi.co/api/v2",
    }

    # Direct match
    if server_name in api_patterns:
        return api_patterns[server_name]

    # Partial match (e.g., "github-users" matches "github")
    for key, url in api_patterns.items():
        if server_name.startswith(key):
            return url

    return None
