"""Variable resolution and prefetching for server execution."""

from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlsplit

from flask import current_app, has_app_context, has_request_context, request, session

from identity import current_user

VARIABLE_PREFETCH_SESSION_KEY = "__viewer_variable_prefetch__"
_MAX_VARIABLE_REDIRECTS = 5
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def _normalize_variable_path(value: Any) -> Optional[str]:
    """Normalize a variable value to an absolute path, or return None if invalid."""
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    return trimmed if trimmed.startswith("/") else None


def _should_skip_variable_prefetch() -> bool:
    """Check if we should skip variable prefetching (to prevent recursive fetching)."""
    if not has_request_context():
        return False

    try:
        return bool(session.get(VARIABLE_PREFETCH_SESSION_KEY))
    except (RuntimeError, KeyError, AttributeError):
        # Session access may fail outside request context or with session errors
        return False


def _resolve_redirect_target(location: str, current_path: str) -> Optional[str]:
    """Resolve a redirect Location header to an absolute path, or None if external."""
    if not location:
        return None

    parsed = urlsplit(location)
    # Reject external redirects
    if parsed.scheme or parsed.netloc:
        return None

    candidate = parsed.path or ""
    if not candidate:
        return None

    # Make relative paths absolute
    if not candidate.startswith("/"):
        candidate = urljoin(current_path, candidate)

    # Preserve query string
    if parsed.query:
        candidate = f"{candidate}?{parsed.query}"

    return candidate


def _current_user_id() -> Optional[Any]:
    """Extract the current user ID, handling callable and non-callable forms."""
    user_id = getattr(current_user, "id", None)
    if callable(user_id):
        try:
            user_id = user_id()
        except TypeError:
            user_id = None

    if user_id:
        return user_id

    # Fallback to get_id() method
    getter = getattr(current_user, "get_id", None)
    return getter() if callable(getter) else None


def _fetch_variable_via_client(client: Any, start_path: str) -> Optional[str]:
    """Fetch content from a path via test client, following redirects up to a limit."""
    visited: set[str] = set()
    target = start_path

    for _ in range(_MAX_VARIABLE_REDIRECTS):
        if target in visited:
            break  # Prevent redirect loops
        visited.add(target)

        response = client.get(target, follow_redirects=False)
        status = getattr(response, "status_code", None) or 0

        if status in _REDIRECT_STATUSES:
            next_target = _resolve_redirect_target(
                response.headers.get("Location", ""), target
            )
            if not next_target:
                break
            target = next_target
            continue

        if status != 200:
            break

        try:
            return response.get_data(as_text=True)
        except (UnicodeDecodeError, AttributeError, ValueError):
            # Handle decoding or response access errors
            return None

    return None


def _fetch_variable_content(path: str) -> Optional[str]:
    """Fetch the content at a path by executing it as the current user."""
    normalized = _normalize_variable_path(path)
    if not normalized or not has_app_context():
        return None

    # Avoid infinite recursion by not fetching the current request path
    if has_request_context() and normalized == request.path:
        return None

    user_id = _current_user_id()
    if not user_id:
        return None

    client = current_app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True
            sess[VARIABLE_PREFETCH_SESSION_KEY] = True

        return _fetch_variable_via_client(client, normalized)
    except (RuntimeError, KeyError, AttributeError, ValueError):
        # Handle session, routing, or attribute access errors
        return None
    finally:
        try:
            with client.session_transaction() as sess:
                sess.pop(VARIABLE_PREFETCH_SESSION_KEY, None)
        except (RuntimeError, KeyError):
            # Ignore cleanup failures
            pass

    return None


def _resolve_variable_values(variable_map: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve variable values, prefetching paths that look like server references."""
    if not variable_map:
        return {}

    if _should_skip_variable_prefetch():
        return dict(variable_map)

    resolved: Dict[str, Any] = {}
    for name, value in variable_map.items():
        candidate = _normalize_variable_path(value)
        if candidate:
            fetched = _fetch_variable_content(candidate)
            if fetched is not None:
                resolved[name] = fetched
                continue

        resolved[name] = value

    return resolved
