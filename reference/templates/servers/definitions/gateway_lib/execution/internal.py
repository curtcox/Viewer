"""Internal target execution for gateway requests.

This module handles executing requests against internal servers
without making external HTTP requests.
"""

import json
from urllib.parse import urljoin
from typing import Optional


class TargetExecutor:
    """Executes requests against internal targets."""

    def __init__(self, redirect_follower):
        """Initialize with redirect follower.
        
        Args:
            redirect_follower: RedirectFollower instance for handling redirects
        """
        self.redirect_follower = redirect_follower

    def execute_target_request(self, target, request_details):
        """Execute a request to the target server.

        The gateway server is internal-only: it always executes another internal
        server and never performs outbound HTTP requests.
        
        Args:
            target: Target configuration (dict with mode/url or string path)
            request_details: Request details dict
            
        Returns:
            Response object from internal server execution
            
        Raises:
            ValueError: If target is external or has unsupported mode
            TypeError: If target type is not supported
        """
        if isinstance(request_details, dict):
            explicit_url = request_details.get("url")
            if isinstance(explicit_url, str) and explicit_url and not explicit_url.startswith("/"):
                raise ValueError("Gateway requests must not specify an external URL")

        if isinstance(target, dict):
            mode = target.get("mode")
            if mode != "internal":
                raise ValueError(f"Unsupported target mode: {mode!r}")
            return self._execute_internal_target(target, request_details)

        if isinstance(target, str):
            if not target.startswith("/"):
                raise ValueError("Gateway target must be an internal path")
            return self._execute_internal_target({"mode": "internal", "url": target}, request_details)

        raise TypeError(f"Unsupported target type: {type(target).__name__}")

    def _execute_internal_target(self, target: dict, request_details: dict):
        """Execute an internal target (server/alias/CID) without making HTTP requests.
        
        Args:
            target: Target dict with 'url' key
            request_details: Request details dict with path, query_string, method, headers, etc.
            
        Returns:
            Response object from internal server
            
        Raises:
            ValueError: If internal path is invalid
            LookupError: If no internal target handles the path
        """
        internal_path = target.get("url")
        if not isinstance(internal_path, str) or not internal_path.startswith("/"):
            raise ValueError(f"Invalid internal target: {internal_path!r}")

        path = internal_path
        extra_path = request_details.get("path")
        if isinstance(extra_path, str) and extra_path:
            path = urljoin(path.rstrip("/") + "/", extra_path.lstrip("/"))

        query_string = request_details.get("query_string")
        if isinstance(query_string, str) and query_string:
            path = f"{path}?{query_string.lstrip('?')}"

        method = request_details.get("method", "GET")

        # Import here to avoid circular dependencies
        from flask import current_app, request as flask_request
        import server_execution

        # Create a nested request context so server execution that depends on
        # request.path sees the intended internal path (e.g. /man/grep).
        with current_app.test_request_context(
            path,
            method=method,
            headers=request_details.get("headers") or {},
            data=request_details.get("data"),
            json=request_details.get("json"),
        ):
            result = server_execution.try_server_execution(flask_request.path)
            if result is None:
                raise LookupError(f"No internal target handled path: {flask_request.path}")

            adapted = as_requests_like_response(result)
            resolved = self.redirect_follower.follow_redirects(adapted)
            return resolved


def resolve_target(config: dict, server_name: str, request_details: dict) -> dict:
    """Resolve the final gateway target.

    The gateway server is internal-only and always targets an internal server.
    
    Args:
        config: Gateway configuration dict
        server_name: Gateway server name
        request_details: Request details dict
        
    Returns:
        Target dict with mode="internal" and url
        
    Raises:
        ValueError: If explicit URL is not an internal path
    """
    explicit_url = request_details.get("url")
    if isinstance(explicit_url, str) and explicit_url:
        if explicit_url.startswith("/"):
            return {"mode": "internal", "url": explicit_url}
        raise ValueError("Gateway target must be an internal path")

    return {"mode": "internal", "url": f"/{server_name}"}


def as_requests_like_response(result):
    """Convert a Flask Response or server result dict into a requests-like object.
    
    Args:
        result: Flask Response object or dict with 'output' key
        
    Returns:
        Object with status_code, headers, content, text, and json() method
        
    Raises:
        TypeError: If result type is not supported
    """
    if hasattr(result, "status_code") and hasattr(result, "headers"):
        class _FlaskResponseAdapter:
            def __init__(self, response):
                self._response = response
                self.status_code = getattr(response, "status_code", 200)
                self.headers = dict(getattr(response, "headers", {}) or {})
                self.content = getattr(response, "data", b"")
                try:
                    self.text = self.content.decode("utf-8", errors="replace")
                except Exception:
                    self.text = ""

            def json(self):
                return json.loads(self.text)

        return _FlaskResponseAdapter(result)

    if isinstance(result, dict) and "output" in result:
        class _DictResponseAdapter:
            def __init__(self, payload):
                self.status_code = 200
                self.headers = {
                    "Content-Type": payload.get("content_type", "text/html")
                }
                output = payload.get("output", "")
                self.content = (
                    output
                    if isinstance(output, (bytes, bytearray))
                    else str(output).encode("utf-8")
                )
                self.text = self.content.decode("utf-8", errors="replace")

            def json(self):
                return json.loads(self.text)

        return _DictResponseAdapter(result)

    raise TypeError(f"Unsupported internal execution result type: {type(result).__name__}")
