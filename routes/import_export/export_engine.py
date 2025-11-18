"""Main export engine for building complete export payloads."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable

from cid_presenter import cid_path, format_cid
from cid_utils import generate_cid
from db_access import get_uploads
from forms import ExportForm

from .cid_utils import CidWriter, encode_section_content, normalise_cid, serialise_cid_value
from .change_history import gather_change_history
from .dependency_analyzer import build_runtime_section
from .export_sections import (
    collect_alias_section,
    collect_app_source_section,
    collect_project_files_section,
    collect_secrets_section,
    collect_server_section,
    collect_variables_section,
)
from .filesystem_collection import app_root_path


def include_unreferenced_cids(
    form: ExportForm,
    cid_map_entries: dict[str, str],
) -> None:
    """Record uploaded CID content when the user requests unreferenced data."""
    if not form.include_cid_map.data or not form.include_unreferenced_cid_data.data:
        return

    for record in get_uploads():
        normalised = normalise_cid(record.path)
        if not normalised or normalised in cid_map_entries:
            continue
        file_content = record.file_data
        if file_content is None:
            continue
        cid_map_entries[normalised] = serialise_cid_value(bytes(file_content))


def add_optional_section(
    sections: dict[str, Any],
    include_section: bool,
    section_key: str,
    builder: Callable[[], Any],
    *,
    require_truthy: bool = True,
) -> None:
    """Conditionally add an export section produced by a builder callback."""
    if not include_section:
        return

    section_value = builder()
    if section_value or not require_truthy:
        sections[section_key] = section_value


def build_export_payload(
    form: ExportForm,
    *,
    store_content: bool = True,
) -> dict[str, Any]:
    """Return rendered export payload data for the user's selected collections."""
    payload: dict[str, Any] = {'version': 6}
    sections: dict[str, Any] = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'runtime': build_runtime_section(),
    }
    base_path = app_root_path()
    cid_writer = CidWriter(
        include_optional=form.include_cid_map.data,
        store_content=store_content,
    )

    add_optional_section(
        sections,
        True,
        'project_files',
        partial(collect_project_files_section, base_path, cid_writer),
    )

    add_optional_section(
        sections,
        form.include_aliases.data,
        'aliases',
        partial(collect_alias_section, form, cid_writer),
    )

    add_optional_section(
        sections,
        form.include_servers.data,
        'servers',
        partial(collect_server_section, form, cid_writer),
    )

    add_optional_section(
        sections,
        form.include_variables.data,
        'variables',
        partial(collect_variables_section, form),
        require_truthy=False,
    )

    secret_key = (form.secret_key.data or '').strip()

    add_optional_section(
        sections,
        form.include_secrets.data,
        'secrets',
        partial(
            collect_secrets_section,
            form,
            secret_key,
            form.include_disabled_secrets.data,
            form.include_template_secrets.data,
        ),
        require_truthy=False,
    )

    add_optional_section(
        sections,
        form.include_history.data,
        'change_history',
        gather_change_history,
    )

    add_optional_section(
        sections,
        form.include_source.data,
        'app_source',
        partial(collect_app_source_section, form, base_path, cid_writer),
    )

    include_unreferenced_cids(form, cid_writer.cid_map_entries)

    for section_name, section_value in sections.items():
        section_bytes = encode_section_content(section_value)
        section_cid = cid_writer.cid_for_content(section_bytes, optional=False)
        payload[section_name] = section_cid

    if form.include_cid_map.data and cid_writer.cid_map_entries:
        payload['cid_values'] = {
            cid: cid_writer.cid_map_entries[cid] for cid in sorted(cid_writer.cid_map_entries)
        }

    ordered_keys = sorted(key for key in payload if key != 'cid_values')
    if 'cid_values' in payload:
        ordered_keys.append('cid_values')

    ordered_payload = {key: payload[key] for key in ordered_keys}
    json_payload = json.dumps(ordered_payload, indent=2)
    json_bytes = json_payload.encode('utf-8')

    if store_content:
        cid_value = cid_writer.cid_for_content(json_bytes, optional=False, include_in_map=False)
        download_path = cid_path(cid_value, 'json') or ''
    else:
        cid_value = format_cid(generate_cid(json_bytes))
        download_path = ''

    return {
        'cid_value': cid_value,
        'download_path': download_path,
        'json_payload': json_payload,
    }
