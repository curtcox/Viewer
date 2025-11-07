"""Helper functions for export operations."""
from __future__ import annotations

from typing import Any, Iterable


SELECTION_SENTINEL = '__none__'


def should_export_entry(
    enabled: bool,
    template: bool,
    *,
    include_disabled: bool,
    include_templates: bool,
) -> bool:
    """Return True when the entry should be included in the export."""
    if template:
        if not include_templates:
            return False
        return True

    if not enabled:
        return include_disabled

    return True


def preview_item_entries(records: Iterable[Any]) -> list[dict[str, Any]]:
    """Return serialisable preview entries for export-capable records."""
    entries: list[dict[str, Any]] = []
    for record in records:
        name = getattr(record, 'name', '') or ''
        enabled = bool(getattr(record, 'enabled', True))
        template = bool(getattr(record, 'template', False))
        entries.append({'name': name, 'enabled': enabled, 'template': template})

    entries.sort(key=lambda entry: entry['name'].casefold())
    return entries


def selected_name_set(raw_values: Iterable[Any]) -> set[str]:
    """Return a cleaned set of user-selected entry names."""
    selected: set[str] = set()
    for value in raw_values or []:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned == SELECTION_SENTINEL:
            continue
        selected.add(cleaned)

    return selected


def filter_preview_items(
    items: Iterable[dict[str, Any]],
    *,
    include_disabled: bool,
    include_templates: bool,
) -> list[dict[str, Any]]:
    """Return preview entries that satisfy the current export filters."""
    filtered: list[dict[str, Any]] = []
    for item in items:
        enabled = bool(item.get('enabled', True))
        template = bool(item.get('template', False))

        if not should_export_entry(
            enabled,
            template,
            include_disabled=include_disabled,
            include_templates=include_templates,
        ):
            continue

        filtered.append(item)

    return filtered
