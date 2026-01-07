"""Helpers for validating operations and building payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class RequiredField:
    name: str
    message: str | None = None


@dataclass(frozen=True)
class OperationDefinition:
    required: tuple[RequiredField, ...] = ()
    payload_builder: Callable[..., dict[str, Any] | None] | None = None


def validate_and_build_payload(
    operation: str,
    operations: Mapping[str, OperationDefinition],
    **kwargs: Any,
) -> dict[str, Any] | None | tuple[str, str]:
    definition = operations.get(operation)
    if not definition:
        return ("Unsupported operation", "operation")

    for required in definition.required:
        if not kwargs.get(required.name):
            message = required.message or f"Missing required {required.name}"
            return (message, required.name)

    if definition.payload_builder:
        return definition.payload_builder(**kwargs)

    return None
