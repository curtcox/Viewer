"""Pipeline request recognition and routing.

This module provides functions to recognize pipeline requests and extract
pipeline-related information from request paths.

A pipeline URL is one that involves at least one server accepting input from
something in the URL other than the HTTP request. Pipeline requests can
optionally include a debug=true query parameter to receive detailed
information about each path segment.
"""

from typing import List, Optional, Set
from urllib.parse import unquote

from flask import Request

from alias_routing import find_matching_alias
from cid_core import is_probable_cid_component, split_cid_path
from db_access import get_server_by_name


# Truthy values for the debug query parameter (case-insensitive)
_DEBUG_TRUTHY_VALUES: Set[str] = {"true", "1", "yes", "on"}


def parse_pipeline_path(path: str) -> List[str]:
    """Parse a URL path into individual pipeline segments.

    Filters out empty segments and decodes URL-encoded characters.

    Args:
        path: The URL path to parse (e.g., "/server/input/data")

    Returns:
        List of path segments, excluding empty strings

    Example:
        >>> parse_pipeline_path("/this/has/four/segments")
        ['this', 'has', 'four', 'segments']
        >>> parse_pipeline_path("/a//b/")
        ['a', 'b']
        >>> parse_pipeline_path("/hello%20world")
        ['hello world']
    """
    if not path:
        return []

    # Split on slashes and filter empty segments
    segments = [seg for seg in path.split("/") if seg]

    # URL-decode each segment
    return [unquote(seg) for seg in segments]


def get_final_extension(path: str) -> Optional[str]:
    """Extract the final extension from the base URL (before query params).

    Only considers the extension of the final path segment.

    Args:
        path: The URL path (may include query string and fragment)

    Returns:
        The extension (without dot) or None if no extension

    Example:
        >>> get_final_extension("/server/data.json?debug=true")
        'json'
        >>> get_final_extension("/path/file.tar.gz")
        'gz'
        >>> get_final_extension("/server.py/input")
        None
        >>> get_final_extension("/path/file")
        None
    """
    if not path:
        return None

    # Remove query string and fragment
    base_path = path.split("?")[0].split("#")[0]

    segments = parse_pipeline_path(base_path)
    if not segments:
        return None

    final_segment = segments[-1]

    # Find the last dot in the final segment
    if "." not in final_segment:
        return None

    extension = final_segment.rsplit(".", 1)[-1]
    return extension if extension else None


def should_return_debug_response(req: Request) -> bool:
    """Check if the request includes a truthy debug query parameter.

    Accepts: true, 1, yes, on (case-insensitive)

    Args:
        req: The Flask request object

    Returns:
        True if debug mode is requested

    Example:
        # With request having ?debug=true
        >>> should_return_debug_response(request)
        True
        # With request having ?debug=false
        >>> should_return_debug_response(request)
        False
    """
    debug_value = req.args.get("debug", "").lower()
    return debug_value in _DEBUG_TRUTHY_VALUES


def _is_server_segment(segment: str) -> bool:
    """Check if a segment corresponds to an enabled server.

    Args:
        segment: The path segment to check (may include extension)

    Returns:
        True if the segment (without extension) is an enabled server
    """
    # Strip extension if present
    base_segment = segment.split(".")[0] if "." in segment else segment

    server = get_server_by_name(base_segment)
    if server and getattr(server, "enabled", True):
        return True
    return False


def _is_cid_segment(segment: str) -> bool:
    """Check if a segment looks like a CID.

    Args:
        segment: The path segment to check (may include extension)

    Returns:
        True if the segment appears to be a CID
    """
    # Try with extension stripped
    cid_parts = split_cid_path(f"/{segment}")
    if cid_parts:
        return True

    # Try the base segment directly
    base_segment = segment.split(".")[0] if "." in segment else segment
    return is_probable_cid_component(base_segment)


def _is_alias_segment(segment: str) -> bool:
    """Check if a segment matches an alias.

    Args:
        segment: The path segment to check

    Returns:
        True if the segment matches an enabled alias
    """
    alias_match = find_matching_alias(f"/{segment}")
    return alias_match is not None


def _could_be_executed(segment: str) -> bool:
    """Check if a segment could be executed as a server or CID.

    A segment could be executed if it's:
    - A named server
    - A CID (potentially with an executable extension)
    - An alias that resolves to something executable

    Args:
        segment: The path segment to check

    Returns:
        True if the segment could be executed
    """
    return _is_server_segment(segment) or _is_cid_segment(segment) or _is_alias_segment(segment)


def is_pipeline_request(path: str) -> bool:
    """Determine if a request path constitutes a pipeline request.

    A pipeline involves at least one server accepting input from
    something in the URL other than the HTTP request. This occurs when:
    - There are 2+ path segments
    - At least the first segment is an executable (server, CID, or alias)

    Args:
        path: The request path to analyze

    Returns:
        True if this is a pipeline request

    Example:
        >>> is_pipeline_request("/server/input")
        True
        >>> is_pipeline_request("/s2/s1")
        True
        >>> is_pipeline_request("/single")
        False
    """
    segments = parse_pipeline_path(path)

    # Need at least 2 segments for a pipeline
    if len(segments) < 2:
        return False

    # The first segment must be something that can accept chained input
    first_segment = segments[0]
    if not _could_be_executed(first_segment):
        return False

    return True


def get_segment_base_and_extension(segment: str) -> tuple[str, Optional[str]]:
    """Split a segment into its base name and extension.

    Args:
        segment: The path segment (e.g., "script.py", "data")

    Returns:
        Tuple of (base_name, extension) where extension may be None

    Example:
        >>> get_segment_base_and_extension("script.py")
        ('script', 'py')
        >>> get_segment_base_and_extension("data")
        ('data', None)
    """
    if "." not in segment:
        return segment, None

    base, ext = segment.rsplit(".", 1)
    return base, ext if ext else None


__all__ = [
    "get_final_extension",
    "get_segment_base_and_extension",
    "is_pipeline_request",
    "parse_pipeline_path",
    "should_return_debug_response",
]
