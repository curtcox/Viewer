"""Shared helpers for handling enabled/disabled toggles across routes."""

from __future__ import annotations

from typing import Any

from flask import request

_TRUE_ENABLED_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_ENABLED_VALUES = {"0", "false", "f", "no", "n", "off", ""}


def coerce_enabled_value(raw_value: Any) -> bool:
    """Interpret an enabled value from form or JSON submissions."""

    if isinstance(raw_value, bool):
        return raw_value
    if raw_value is None:
        raise ValueError("Missing enabled value")

    text = str(raw_value).strip().lower()
    if text in _TRUE_ENABLED_VALUES:
        return True
    if text in _FALSE_ENABLED_VALUES:
        return False
    raise ValueError(f"Unrecognized enabled value: {raw_value}")


def extract_enabled_value_from_request() -> bool:
    """Return the desired enabled value from the current request payload."""

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        if "enabled" not in payload:
            raise ValueError("Missing enabled value")
        return coerce_enabled_value(payload.get("enabled"))

    values = request.form.getlist("enabled")
    if not values:
        raise ValueError("Missing enabled value")
    return coerce_enabled_value(values[-1])


def request_prefers_json() -> bool:
    """Return True when the current request expects a JSON response."""

    if request.is_json:
        return True

    best = request.accept_mimetypes.best
    if best == "application/json" and (
        request.accept_mimetypes["application/json"]
        > request.accept_mimetypes["text/html"]
    ):
        return True

    return False


__all__ = [
    "coerce_enabled_value",
    "extract_enabled_value_from_request",
    "request_prefers_json",
]
