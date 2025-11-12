"""Import orchestration and context management."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from flask import flash, redirect, session, url_for

from cid_presenter import format_cid
from cid_utils import generate_cid
from db_access import EntityInteractionRequest, record_entity_interaction, record_export
from forms import ExportForm, ImportForm
from identity import current_user

from .cid_utils import load_export_section, parse_cid_values_section, store_cid_from_bytes
from .change_history import import_change_history
from .export_engine import build_export_payload
from .export_preview import build_export_preview
from .filesystem_collection import APP_SOURCE_CATEGORIES
from .import_entities import (
    import_aliases_with_names,
    import_secrets_with_names,
    import_servers_with_names,
    import_variables_with_names,
)
from .import_sources import ParsedImportPayload, verify_import_source_files


@dataclass
class ImportContext:
    """Context object for managing import state."""

    form: ImportForm
    user_id: str
    change_message: str
    raw_payload: str
    data: dict[str, Any]
    cid_lookup: dict[str, bytes] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info_messages: list[str] = field(default_factory=list)
    summaries: list[str] = field(default_factory=list)
    secret_key: str = ''
    snapshot_export: dict[str, Any] | None = None
    imported_names: dict[str, list[str]] = field(default_factory=lambda: {
        'aliases': [],
        'servers': [],
        'variables': [],
        'secrets': [],
    })


@dataclass(frozen=True)
class SectionImportPlan:
    """Plan for importing a single export section."""

    include: bool
    section_key: str
    importer: Callable[[Any], tuple[int, list[str], list[str]]]
    singular_label: str
    plural_label: str


def create_import_context(
    form: ImportForm,
    change_message: str,
    parsed_payload: ParsedImportPayload,
) -> ImportContext:
    """Create an import context from form and parsed payload."""
    secret_key = (form.secret_key.data or '').strip()
    return ImportContext(
        form=form,
        user_id=current_user.id,
        change_message=change_message,
        raw_payload=parsed_payload.raw_text,
        data=parsed_payload.data,
        secret_key=secret_key,
    )


def ingest_import_cid_map(context: ImportContext) -> None:
    """Parse and optionally store CID values from the import payload."""
    parsed_cids, cid_map_errors = parse_cid_values_section(context.data.get('cid_values'))
    context.errors.extend(cid_map_errors)

    for cid_value, content_bytes in parsed_cids.items():
        expected_cid = format_cid(generate_cid(content_bytes)).lstrip('/')
        if expected_cid and cid_value != expected_cid:
            context.errors.append(
                f'CID "{cid_value}" content did not match its hash and was skipped.'
            )
            continue
        context.cid_lookup[cid_value] = content_bytes
        if context.form.process_cid_map.data:
            store_cid_from_bytes(content_bytes, context.user_id)


def import_section(context: ImportContext, plan: SectionImportPlan) -> int:
    """Load and import a selected export section if requested."""
    if not plan.include:
        return 0

    section, load_errors, fatal = load_export_section(
        context.data,
        plan.section_key,
        context.cid_lookup,
    )
    context.errors.extend(load_errors)
    if fatal:
        return 0

    result = plan.importer(section)
    if isinstance(result, tuple) and len(result) == 3:
        imported_count, import_errors, imported_names = result
    else:
        imported_count, import_errors = result
        imported_names = []
    context.errors.extend(import_errors)
    if imported_count:
        label = plan.plural_label if imported_count != 1 else plan.singular_label
        context.summaries.append(f'{imported_count} {label}')
        if plan.section_key in context.imported_names:
            context.imported_names[plan.section_key].extend(imported_names)

    return imported_count


def import_selected_sections(context: ImportContext) -> None:
    """Import all selected entity sections."""
    section_importers = [
        SectionImportPlan(
            include=context.form.include_aliases.data,
            section_key='aliases',
            importer=lambda section: import_aliases_with_names(
                context.user_id, section, context.cid_lookup
            ),
            singular_label='alias',
            plural_label='aliases',
        ),
        SectionImportPlan(
            include=context.form.include_servers.data,
            section_key='servers',
            importer=lambda section: import_servers_with_names(
                context.user_id, section, context.cid_lookup
            ),
            singular_label='server',
            plural_label='servers',
        ),
        SectionImportPlan(
            include=context.form.include_variables.data,
            section_key='variables',
            importer=lambda section: import_variables_with_names(context.user_id, section),
            singular_label='variable',
            plural_label='variables',
        ),
        SectionImportPlan(
            include=context.form.include_secrets.data,
            section_key='secrets',
            importer=lambda section: import_secrets_with_names(
                context.user_id, section, context.secret_key
            ),
            singular_label='secret',
            plural_label='secrets',
        ),
        SectionImportPlan(
            include=context.form.include_history.data,
            section_key='change_history',
            importer=lambda section: (*import_change_history(context.user_id, section), []),
            singular_label='history event',
            plural_label='history events',
        ),
    ]

    for plan in section_importers:
        import_section(context, plan)


def handle_import_source_files(context: ImportContext) -> None:
    """Verify imported source files match local versions."""
    if not context.form.include_source.data:
        return

    selected_source_categories = list(APP_SOURCE_CATEGORIES)
    app_source_section, app_source_errors, fatal = load_export_section(
        context.data,
        'app_source',
        context.cid_lookup,
    )
    context.errors.extend(app_source_errors)

    if fatal:
        return

    verify_import_source_files(
        app_source_section,
        selected_source_categories,
        context.warnings,
        context.info_messages,
    )


def generate_snapshot_export(user_id: str) -> dict[str, Any] | None:
    """Generate a snapshot export equivalent to the default export."""
    try:
        form = ExportForm()
        form.snapshot.data = True
        form.include_aliases.data = True
        form.include_servers.data = True
        form.include_variables.data = True
        form.include_secrets.data = False
        form.include_history.data = False
        form.include_source.data = False
        form.include_cid_map.data = True
        form.include_unreferenced_cid_data.data = False

        build_export_preview(form, user_id)
        export_result = build_export_payload(form, user_id, store_content=True)
        record_export(user_id, export_result['cid_value'])
        export_result['generated_at'] = datetime.now(timezone.utc).isoformat()
        return export_result
    except RuntimeError as exc:
        import logging  # pylint: disable=import-outside-toplevel  # Lazy import for error path
        logger = logging.getLogger(__name__)
        logger.warning("Failed to generate snapshot export after import: %s", exc, exc_info=True)
        return None


def finalise_import(context: ImportContext, render_form: Callable[[Any], Any]) -> Any:
    """Flash messages and finalize the import process."""
    for message in context.errors:
        flash(message, 'danger')

    for message in context.warnings:
        flash(message, 'warning')

    if context.summaries:
        summary_text = ', '.join(context.summaries)
        flash(f'Imported {summary_text}.', 'success')

    for message in context.info_messages:
        flash(message, 'success')

    snapshot_export = generate_snapshot_export(context.user_id)
    context.snapshot_export = snapshot_export

    if snapshot_export:
        session['import_snapshot_export'] = {
            'cid': snapshot_export['cid_value'],
            'generated_at': snapshot_export['generated_at'],
        }
    if any(context.imported_names.values()):
        session['import_summary_names'] = context.imported_names

    if context.errors or context.warnings or context.summaries:
        record_entity_interaction(
            EntityInteractionRequest(
                user_id=context.user_id,
                entity_type='import',
                entity_name='json',
                action='save',
                message=context.change_message,
                content=context.raw_payload,
            )
        )

        return redirect(url_for('main.import_data'))

    return render_form(snapshot_export)


def process_import_submission(
    form: ImportForm,
    change_message: str,
    render_form: Callable[[Any], Any],
    parsed_payload: ParsedImportPayload,
) -> Any:
    """Handle an import form submission and return the appropriate response."""
    context = create_import_context(form, change_message, parsed_payload)
    ingest_import_cid_map(context)
    import_selected_sections(context)
    handle_import_source_files(context)

    return finalise_import(context, render_form)
