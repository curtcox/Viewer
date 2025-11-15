"""Collection functions for individual export sections."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from db_access import get_aliases, get_secrets, get_servers, get_variables
from encryption import SECRET_ENCRYPTION_SCHEME, encrypt_secret_value
from forms import ExportForm

from .cid_utils import CidWriter
from .export_helpers import selected_name_set, should_export_entry
from .filesystem_collection import APP_SOURCE_CATEGORIES, APP_SOURCE_COLLECTORS


def collect_project_files_section(
    base_path: Path,
    cid_writer: CidWriter,
) -> dict[str, dict[str, str]]:
    """Return CID metadata for key project files when available."""
    project_files_payload: dict[str, dict[str, str]] = {}
    for relative_name in ('pyproject.toml', 'requirements.txt'):
        absolute_path = base_path / relative_name
        try:
            file_content = absolute_path.read_bytes()
        except OSError:
            continue

        cid_value = cid_writer.cid_for_content(file_content)
        project_files_payload[relative_name] = {'cid': cid_value}

    return project_files_payload


def collect_alias_section(
    form: ExportForm,
    user_id: str = "",  # Kept for backward compatibility, no longer used  # pylint: disable=unused-argument
    cid_writer: CidWriter = None,  # type: ignore[assignment]  # Required but has default for backward compatibility
) -> list[dict[str, Any]]:
    """Return alias export entries including CID references."""
    aliases = list(get_aliases())
    selected_names = selected_name_set(form.selected_aliases.data)
    if not selected_names and not getattr(form.selected_aliases, 'raw_data', None):
        selected_names = {
            alias.name
            for alias in aliases
            if isinstance(getattr(alias, 'name', None), str) and alias.name
        }
    alias_payload: list[dict[str, Any]] = []
    for alias in aliases:
        name = getattr(alias, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        definition_text = alias.definition or ''
        definition_bytes = definition_text.encode('utf-8')
        definition_cid = cid_writer.cid_for_content(definition_bytes)
        enabled = bool(getattr(alias, 'enabled', True))

        if not should_export_entry(
            enabled,
            False,  # Templates no longer stored as entity attribute
            include_disabled=form.include_disabled_aliases.data,
            include_templates=form.include_template_aliases.data,
        ):
            continue

        alias_payload.append(
            {
                'name': name,
                'definition_cid': definition_cid,
                'enabled': enabled,
            }
        )

    return alias_payload


def collect_server_section(
    form: ExportForm,
    user_id: str = "",  # Kept for backward compatibility, no longer used  # pylint: disable=unused-argument
    cid_writer: CidWriter = None,  # type: ignore[assignment]  # Required but has default for backward compatibility
) -> list[dict[str, str]]:
    """Return server export entries including CID references."""
    servers = list(get_servers())
    selected_names = selected_name_set(form.selected_servers.data)
    if not selected_names and not getattr(form.selected_servers, 'raw_data', None):
        selected_names = {
            server.name
            for server in servers
            if isinstance(getattr(server, 'name', None), str) and server.name
        }
    servers_payload: list[dict[str, str]] = []
    for server in servers:
        name = getattr(server, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        definition_text = server.definition or ''
        definition_bytes = definition_text.encode('utf-8')
        definition_cid = cid_writer.cid_for_content(definition_bytes)
        enabled = bool(getattr(server, 'enabled', True))

        if not should_export_entry(
            enabled,
            False,  # Templates no longer stored as entity attribute
            include_disabled=form.include_disabled_servers.data,
            include_templates=form.include_template_servers.data,
        ):
            continue

        servers_payload.append(
            {
                'name': name,
                'definition_cid': definition_cid,
                'enabled': enabled,
            }
        )

    return servers_payload


def collect_variables_section(
    form: ExportForm,
    user_id: str = "",  # Kept for backward compatibility, no longer used  # pylint: disable=unused-argument
) -> list[dict[str, str]]:
    """Return variable export entries."""
    variables = list(get_variables())
    selected_names = selected_name_set(form.selected_variables.data)
    if not selected_names and not getattr(form.selected_variables, 'raw_data', None):
        selected_names = {
            variable.name
            for variable in variables
            if isinstance(getattr(variable, 'name', None), str) and variable.name
        }
    variable_payload: list[dict[str, str]] = []
    for variable in variables:
        name = getattr(variable, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        enabled = bool(getattr(variable, 'enabled', True))

        if not should_export_entry(
            enabled,
            False,  # Templates no longer stored as entity attribute
            include_disabled=form.include_disabled_variables.data,
            include_templates=form.include_template_variables.data,
        ):
            continue

        variable_payload.append(
            {
                'name': name,
                'definition': variable.definition,
                'enabled': enabled,
            }
        )

    return variable_payload


def collect_secrets_section(
    form: ExportForm,
    user_id: str = "",  # Kept for backward compatibility, no longer used  # pylint: disable=unused-argument
    key: str = "",
    include_disabled: bool = False,
    include_templates: bool = False,
) -> dict[str, Any]:
    """Return encrypted secret entries using the provided key."""
    secrets = list(get_secrets())
    selected_names = selected_name_set(form.selected_secrets.data)
    if not selected_names and not getattr(form.selected_secrets, 'raw_data', None):
        selected_names = {
            secret.name
            for secret in secrets
            if isinstance(getattr(secret, 'name', None), str) and secret.name
        }
    items: list[dict[str, Any]] = []
    for secret in secrets:
        name = getattr(secret, 'name', '')
        if not isinstance(name, str) or not name or name not in selected_names:
            continue

        enabled = bool(getattr(secret, 'enabled', True))

        if not should_export_entry(
            enabled,
            False,  # Templates no longer stored as entity attribute
            include_disabled=include_disabled,
            include_templates=include_templates,
        ):
            continue

        items.append(
            {
                'name': name,
                'ciphertext': encrypt_secret_value(secret.definition, key),
                'enabled': enabled,
            }
        )

    return {
        'encryption': SECRET_ENCRYPTION_SCHEME,
        'items': items,
    }


def collect_app_source_section(
    _form: ExportForm,
    base_path: Path,
    cid_writer: CidWriter,
) -> dict[str, list[dict[str, str]]]:
    """Return exported application source entries based on the selected categories."""
    app_source_payload: dict[str, list[dict[str, str]]] = {}
    for category, _label in APP_SOURCE_CATEGORIES:
        collector = APP_SOURCE_COLLECTORS.get(category)
        if not collector:
            continue

        entries: list[dict[str, str]] = []
        for relative_path in collector():
            absolute_path = base_path / relative_path
            try:
                content_bytes = absolute_path.read_bytes()
            except OSError:
                continue

            cid_value = cid_writer.cid_for_content(content_bytes)
            entries.append({'path': relative_path.as_posix(), 'cid': cid_value})

        if entries:
            app_source_payload[category] = entries

    return app_source_payload
