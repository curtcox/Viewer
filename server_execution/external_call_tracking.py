"""Capture outbound HTTP calls made during server execution."""

from __future__ import annotations

import contextlib
import copy
from typing import Any, Dict, Iterable, Iterator, List, Mapping, MutableMapping

import requests


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
        redacted = redacted.replace(secret_text, replacement)
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
    original_request = requests.Session.request

    def _wrapper(self, method: str, url: str, **kwargs):  # type: ignore[override]
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
            response = original_request(self, method, url, **kwargs)
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
            call_log.append(record)

    try:
        requests.Session.request = _wrapper  # type: ignore[assignment]
        yield call_log
    finally:
        requests.Session.request = original_request  # type: ignore[assignment]
