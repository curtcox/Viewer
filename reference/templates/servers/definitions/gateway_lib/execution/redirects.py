"""Redirect following logic for gateway internal requests.

This module handles following redirect responses from internal servers
to their final CID-backed content.
"""

import json
from typing import Optional


class RedirectFollower:
    """Follows internal redirect responses to final content."""

    def __init__(self, cid_resolver):
        """Initialize with CID resolver for content lookup.
        
        Args:
            cid_resolver: CIDResolver instance for resolving redirect locations
        """
        self.cid_resolver = cid_resolver

    def follow_redirects(self, response, max_hops: int = 3):
        """Resolve internal redirect responses into final CID-backed content.
        
        Args:
            response: Response object with status_code, headers, content attributes
            max_hops: Maximum number of redirects to follow (default: 3)
            
        Returns:
            Final response object after following redirects
        """
        current = response
        for _ in range(max_hops):
            status = getattr(current, "status_code", 200)
            if status not in (301, 302, 303, 307, 308):
                return current

            headers = getattr(current, "headers", {}) or {}
            location = headers.get("Location") or headers.get("location")
            if not isinstance(location, str) or not location:
                return current

            cid_value, content_type = self._try_resolve_location_to_content(location)
            if cid_value is None:
                return current

            class _ResolvedResponse:
                def __init__(self, *, body: bytes, content_type: str):
                    self.status_code = 200
                    self.headers = {"Content-Type": content_type}
                    self.content = body
                    self.text = body.decode("utf-8", errors="replace")

                def json(self):
                    return json.loads(self.text)

            return _ResolvedResponse(body=cid_value, content_type=content_type)

        return current

    def _try_resolve_location_to_content(self, location: str) -> tuple[Optional[bytes], str]:
        """Try to resolve a redirect Location to CID content bytes and content type.
        
        Args:
            location: Redirect location header value
            
        Returns:
            Tuple of (content_bytes, content_type) or (None, "text/plain") if not resolvable
        """
        if not isinstance(location, str):
            return None, "text/plain"

        raw_path = location.split("?", 1)[0]
        raw_path = raw_path.lstrip("/")
        if not raw_path:
            return None, "text/plain"

        if "/" in raw_path:
            # Not a simple /{cid}[.ext] path.
            return None, "text/plain"

        if "." in raw_path:
            cid_candidate, ext = raw_path.split(".", 1)
        else:
            cid_candidate, ext = raw_path, ""

        cid_body = self.cid_resolver.resolve(cid_candidate, as_bytes=True)
        if cid_body is None:
            return None, "text/plain"

        body = bytes(cid_body) if isinstance(cid_body, (bytes, bytearray)) else str(cid_body).encode("utf-8")

        content_type = {
            "html": "text/html",
            "txt": "text/plain",
            "json": "application/json",
            "md": "text/markdown",
        }.get(ext.lower() if isinstance(ext, str) else "", "text/html")

        return body, content_type


def extract_internal_target_path_from_server_args_json(server_args_json: Optional[str]) -> Optional[str]:
    """Extract internal target path from server args JSON string.
    
    Args:
        server_args_json: JSON string containing server arguments
        
    Returns:
        Extracted internal target path or None if not found
    """
    if not isinstance(server_args_json, str) or not server_args_json.strip():
        return None

    try:
        payload = json.loads(server_args_json)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    target = payload.get("target")
    if isinstance(target, dict):
        url = target.get("url")
        if isinstance(url, str) and url:
            return url
    if isinstance(target, str) and target:
        return target
    return None
