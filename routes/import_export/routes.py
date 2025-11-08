"""Flask routes for import and export functionality."""
from __future__ import annotations

import json
from typing import Any

from flask import jsonify, render_template, request, session

from db_access import get_user_exports
from forms import ExportForm, ImportForm
from identity import current_user
from interaction_log import load_interaction_history

from . import main_bp
from .cid_utils import format_size
from .export_engine import build_export_payload
from .export_preview import build_export_preview
from .import_engine import (
    create_import_context,
    handle_import_source_files,
    import_selected_sections,
    ingest_import_cid_map,
    process_import_submission,
)
from .import_sources import load_import_payload, parse_import_payload


@main_bp.route('/export', methods=['GET', 'POST'])
def export_data():
    """Allow users to export selected data collections as JSON."""
    form = ExportForm()
    preview = build_export_preview(form, current_user.id)
    recent_exports = get_user_exports(current_user.id, limit=100)
    if form.validate_on_submit():
        from db_access import record_export
        export_result = build_export_payload(form, current_user.id)
        record_export(current_user.id, export_result['cid_value'])
        return render_template('export_result.html', **export_result)

    return render_template('export.html', form=form, export_preview=preview, recent_exports=recent_exports)


@main_bp.route('/export/size', methods=['POST'])
def export_size():
    """Return the size of the export JSON for the current selections."""
    form = ExportForm()
    build_export_preview(form, current_user.id)
    if form.validate():
        export_result = build_export_payload(
            form,
            current_user.id,
            store_content=False,
        )
        json_bytes = export_result['json_payload'].encode('utf-8')
        size_bytes = len(json_bytes)
        return {
            'ok': True,
            'size_bytes': size_bytes,
            'formatted_size': format_size(size_bytes),
        }

    return {'ok': False, 'errors': form.errors}, 400


@main_bp.route('/import', methods=['GET', 'POST'])
def import_data():
    """Allow users to import data collections from JSON content."""
    # Check if this is a JSON request (REST API)
    is_json_request = request.is_json or (
        request.method == 'POST'
        and request.content_type
        and 'application/json' in request.content_type.lower()
    )

    if is_json_request and request.method == 'POST':
        return _handle_json_import()

    return _handle_form_import()


def _handle_json_import():
    """Handle JSON API import requests."""
    try:
        json_data = request.get_json() or {}
        raw_payload = json.dumps(json_data) if isinstance(json_data, dict) else json_data

        parsed_payload, error_message = parse_import_payload(raw_payload)
        if error_message:
            return jsonify({'ok': False, 'error': error_message}), 400

        assert parsed_payload is not None

        form = ImportForm()
        form.include_aliases.data = 'aliases' in parsed_payload.data
        form.include_servers.data = 'servers' in parsed_payload.data
        form.include_variables.data = 'variables' in parsed_payload.data
        form.include_secrets.data = 'secrets' in parsed_payload.data
        form.include_history.data = 'change_history' in parsed_payload.data
        form.process_cid_map.data = 'cid_values' in parsed_payload.data
        form.include_source.data = False

        context = create_import_context(form, 'REST API import', parsed_payload)
        ingest_import_cid_map(context)
        import_selected_sections(context)
        handle_import_source_files(context)

        from .import_engine import generate_snapshot_export
        snapshot_export = generate_snapshot_export(context.user_id)

        response_data = {'ok': True}
        if context.errors:
            response_data['errors'] = context.errors
        if context.warnings:
            response_data['warnings'] = context.warnings
        if context.summaries:
            response_data['summaries'] = context.summaries
        if any(context.imported_names.values()):
            response_data['imported_names'] = context.imported_names
        if snapshot_export:
            response_data['snapshot'] = {
                'cid': snapshot_export['cid_value'],
                'generated_at': snapshot_export['generated_at'],
            }

        return jsonify(response_data), 200
    except RuntimeError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400


def _handle_form_import():
    """Handle HTML form import requests."""
    form = ImportForm()
    change_message = (request.form.get('change_message') or '').strip()

    def _render_import_form(snapshot_export: dict[str, Any] | None = None):
        interactions = load_interaction_history(current_user.id, 'import', 'json')
        snapshot_info = session.pop('import_snapshot_export', None) or snapshot_export
        imported_names = session.pop('import_summary_names', None)
        return render_template(
            'import.html',
            form=form,
            import_interactions=interactions,
            snapshot_export=snapshot_info,
            imported_names=imported_names
        )

    if form.validate_on_submit():
        raw_payload = load_import_payload(form)
        if raw_payload is None:
            return _render_import_form()

        parsed_payload, error_message = parse_import_payload(raw_payload)
        if error_message:
            from flask import flash
            flash(error_message, 'danger')
            return _render_import_form()

        assert parsed_payload is not None
        return process_import_submission(form, change_message, _render_import_form, parsed_payload)

    return _render_import_form()


__all__ = ['export_data', 'export_size', 'import_data']
