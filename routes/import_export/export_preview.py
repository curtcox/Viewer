"""Export preview generation and selection management."""
from __future__ import annotations

from typing import Any

from db_access import get_user_aliases, get_user_secrets, get_user_servers, get_user_variables
from forms import ExportForm
from wtforms import SelectMultipleField

from .export_helpers import (
    SELECTION_SENTINEL,
    filter_preview_items,
    preview_item_entries,
)


def build_export_preview(form: ExportForm, user_id: str) -> dict[str, dict[str, Any]]:
    """Return metadata describing which items are currently selected for export."""
    alias_entries = preview_item_entries(get_user_aliases(user_id))
    server_entries = preview_item_entries(get_user_servers(user_id))
    variable_entries = preview_item_entries(get_user_variables(user_id))
    secret_entries = preview_item_entries(get_user_secrets(user_id))

    return {
        'aliases': _build_section(
            alias_entries,
            bool(form.include_aliases.data),
            bool(form.include_disabled_aliases.data),
            bool(form.include_template_aliases.data),
            'aliases',
            form.selected_aliases,
        ),
        'servers': _build_section(
            server_entries,
            bool(form.include_servers.data),
            bool(form.include_disabled_servers.data),
            bool(form.include_template_servers.data),
            'servers',
            form.selected_servers,
        ),
        'variables': _build_section(
            variable_entries,
            bool(form.include_variables.data),
            bool(form.include_disabled_variables.data),
            bool(form.include_template_variables.data),
            'variables',
            form.selected_variables,
        ),
        'secrets': _build_section(
            secret_entries,
            bool(form.include_secrets.data),
            bool(form.include_disabled_secrets.data),
            bool(form.include_template_secrets.data),
            'secrets',
            form.selected_secrets,
        ),
    }


def _initialise_selection(
    field: SelectMultipleField,
    entries: list[dict[str, Any]],
) -> set[str]:
    """Initialize field choices and selection state."""
    available_names: list[str] = []
    for entry in entries:
        name = entry.get('name')
        if not isinstance(name, str):
            continue
        cleaned = name.strip()
        if not cleaned:
            continue
        available_names.append(cleaned)

    field.choices = [(name, name) for name in available_names]

    raw_data = list(field.raw_data or [])
    submitted = bool(raw_data)
    cleaned_values: list[str] = []
    for value in field.data or []:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned == SELECTION_SENTINEL:
            continue
        cleaned_values.append(cleaned)

    if not submitted:
        cleaned_values = list(available_names)

    field.data = cleaned_values
    return set(cleaned_values)


def _build_section(
    entries: list[dict[str, Any]],
    include_collection: bool,
    include_disabled: bool,
    include_templates: bool,
    label: str,
    field: SelectMultipleField,
) -> dict[str, Any]:
    """Build a single preview section with selection metadata."""
    capitalised_label = label.title()
    selected_names = _initialise_selection(field, entries)
    filtered_items = (
        filter_preview_items(
            entries,
            include_disabled=include_disabled,
            include_templates=include_templates,
        )
        if include_collection
        else []
    )
    filtered_names = {
        item.get('name')
        for item in filtered_items
        if isinstance(item.get('name'), str) and item.get('name')
    }

    return {
        'label': label,
        'include': include_collection,
        'available': entries,
        'selected': filtered_items,
        'selected_names': sorted(selected_names & filtered_names, key=str.casefold),
        'known_names': sorted(filtered_names, key=str.casefold),
        'field_name': field.name,
        'selection_sentinel': SELECTION_SENTINEL,
        'empty_message': f'No {label} available for export.',
        'not_selected_message': f'{capitalised_label} are not selected for export.',
    }
