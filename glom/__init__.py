"""Minimal glom-compatible helpers for template execution tests."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


class GlomError(Exception):
    """Exception raised when a glom lookup fails."""


def _coerce_sequence_index(key: str) -> int:
    try:
        return int(key)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise GlomError(f"Expected an integer index for sequence access, got {key!r}.") from exc


def _descend(target: Any, key: Any) -> Any:
    if isinstance(target, Mapping):
        if key in target:
            return target[key]
        raise GlomError(f"Key {key!r} was not found while traversing {target!r}.")

    if isinstance(target, Sequence) and not isinstance(target, (str, bytes, bytearray)):
        index = _coerce_sequence_index(str(key))
        try:
            return target[index]
        except IndexError as exc:  # pragma: no cover - defensive
            raise GlomError(f"Index {index} out of range for sequence access.") from exc

    if hasattr(target, key):
        return getattr(target, key)

    raise GlomError(f"Cannot access key {key!r} on object of type {type(target).__name__}.")


def _normalize_spec(spec: Any) -> list[Any]:
    if spec is None:
        return []

    if isinstance(spec, str):
        parts = [part for part in spec.split(".") if part]
        return parts

    if isinstance(spec, Iterable) and not isinstance(spec, (str, bytes, bytearray)):
        return list(spec)

    raise GlomError(f"Unsupported glom specification: {spec!r}")


def glom(target: Any, spec: Any) -> Any:
    """Traverse ``target`` according to ``spec`` and return the resolved value."""

    steps = _normalize_spec(spec)
    current = target

    for step in steps:
        if callable(step):
            current = step(current)
            continue

        current = _descend(current, step)

    return current


__all__ = ["GlomError", "glom"]
