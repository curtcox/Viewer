"""Helpers for serializing SQLAlchemy models into simple dictionaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, MutableMapping, Optional


def model_to_dict(
    instance: Any, extras: Optional[Mapping[str, Any]] = None
) -> MutableMapping[str, Any]:
    """Return a dictionary of column values for a SQLAlchemy model instance."""

    table = getattr(instance, "__table__", None)
    if table is None:
        raise AttributeError("Instance does not declare a SQLAlchemy table")

    columns = getattr(table, "columns", None)
    if columns is None:
        raise AttributeError("Model table does not expose columns for serialization")

    serialized: MutableMapping[str, Any] = {}

    for column in columns:
        name = getattr(column, "name", None)
        if not name:
            continue
        value = getattr(instance, name)
        if isinstance(value, datetime):
            serialized[name] = value.isoformat()
        else:
            serialized[name] = value

    if extras:
        serialized.update(extras)

    return serialized


__all__ = ["model_to_dict"]
