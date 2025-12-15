"""Capture outbound HTTP calls made during server execution."""

from __future__ import annotations

import contextlib
import copy
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping
import threading
import urllib.parse

import requests

_THREAD_STATE = threading.local()
_PATCH_STATE: Dict[str, Any] = {"original_request": requests.Session.request, "depth": 0}


def _make_json_safe(value: Any) -> Any:
    """Convert values to JSON-friendly representations."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, Mapping):
        return {str(k): _make_json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set, frozenset)):
        return [_make_json_safe(v) for v in value]

    return str(value)


def _redact_string(text: str, secrets: Mapping[str, Any]) -> str:
    redacted = text
    for name, secret in secrets.items():
        if secret is None:
            continue
        replacement = f"<secret:{name}>"
        secret_text = str(secret)
        if not secret_text:
            continue
        variants = [secret_text]
        quoted = urllib.parse.quote(secret_text)
        if quoted != secret_text:
            variants.append(quoted)
        quoted_plus = urllib.parse.quote_plus(secret_text)
        if quoted_plus not in (secret_text, quoted):
            variants.append(quoted_plus)

        for variant in variants:
            redacted = redacted.replace(variant, replacement)
    return redacted


def _redact_value(value: Any, secrets: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        return _redact_string(value, secrets)

    if isinstance(value, Mapping):
        return {k: _redact_value(v, secrets) for k, v in value.items()}

    if isinstance(value, list):
        return [_redact_value(v, secrets) for v in value]

    return value


def sanitize_external_calls(
    calls: Iterable[Mapping[str, Any]] | None, secrets: Mapping[str, Any] | None
) -> List[Dict[str, Any]]:
    """Return JSON-serializable, redacted external call details."""

    secrets = secrets or {}
    sanitized: List[Dict[str, Any]] = []

    for entry in calls or []:
        normalized = _make_json_safe(copy.deepcopy(entry))
        sanitized.append(_redact_value(normalized, secrets))

    return sanitized


def _extract_response_body(response: requests.Response) -> Any:
    try:
        return response.text
    except Exception:  # pragma: no cover - defensive
        try:
            return response.content.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - defensive
            return str(response)


@contextlib.contextmanager
def capture_external_calls() -> Iterator[List[MutableMapping[str, Any]]]:
    """Collect HTTP requests performed via ``requests`` during execution."""

    call_log: List[MutableMapping[str, Any]] = []

    def _get_log_stack() -> List[List[MutableMapping[str, Any]]]:
        stack = getattr(_THREAD_STATE, "call_log_stack", None)
        if stack is None:
            stack = []
            _THREAD_STATE.call_log_stack = stack
        return stack

    def _wrapper(self, method: str, url: str, **kwargs):  # type: ignore[override]
        stack = getattr(_THREAD_STATE, "call_log_stack", [])
        if not stack:
            return _PATCH_STATE["original_request"](self, method, url, **kwargs)

        record: MutableMapping[str, Any] = {
            "request": {
                "method": method,
                "url": url,
                "headers": _make_json_safe(kwargs.get("headers", {})),
                "params": _make_json_safe(kwargs.get("params")),
                "json": _make_json_safe(kwargs.get("json")),
                "data": _make_json_safe(kwargs.get("data")),
                "timeout": kwargs.get("timeout"),
            }
        }

        try:
            response = _PATCH_STATE["original_request"](self, method, url, **kwargs)
            record["response"] = {
                "status_code": getattr(response, "status_code", None),
                "headers": _make_json_safe(getattr(response, "headers", {})),
                "body": _make_json_safe(_extract_response_body(response)),
                "url": getattr(response, "url", None),
            }
            return response
        except Exception as exc:  # pragma: no cover - defensive
            record["exception"] = _make_json_safe(str(exc))
            raise
        finally:
            # Propagate record to ALL captures in the stack, not just innermost.
            # This allows outer captures (like test fixtures) to see calls made
            # during inner captures (like code_execution).
            for log in stack:
                log.append(copy.deepcopy(record))

    try:
        log_stack = _get_log_stack()
        log_stack.append(call_log)
        if _PATCH_STATE["depth"] == 0:
            _PATCH_STATE["original_request"] = requests.Session.request
            requests.Session.request = _wrapper  # type: ignore[assignment]
        _PATCH_STATE["depth"] += 1
        yield call_log
    finally:
        log_stack = getattr(_THREAD_STATE, "call_log_stack", [])
        if log_stack:
            log_stack.pop()
        _PATCH_STATE["depth"] = max(_PATCH_STATE["depth"] - 1, 0)
        if _PATCH_STATE["depth"] == 0:
            requests.Session.request = _PATCH_STATE["original_request"]  # type: ignore[assignment]
