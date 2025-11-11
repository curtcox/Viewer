"""Upload-related routes and helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import logfire
from flask import abort, flash, redirect, render_template, request, url_for
from markupsafe import Markup

from alias_definition import (
    format_primary_alias_line,
    get_primary_alias_route,
    replace_primary_definition_line,
)
from cid_presenter import cid_path, format_cid, format_cid_short, render_cid_link
from cid_utils import (
    generate_cid,
    get_extension_from_mime_type,
    process_file_upload,
    process_text_upload,
    process_url_upload,
)
from db_access import (
    EntityInteractionRequest,
    create_cid_record,
    find_cids_by_prefix,
    get_alias_by_name,
    get_alias_by_target_path,
    get_cid_by_path,
    get_user_server_invocations,
    get_user_uploads,
    get_user_variables,
    get_variable_by_name,
    record_entity_interaction,
    save_entity,
)
from entity_references import (
    extract_references_from_bytes,
)
from forms import EditCidForm, FileUploadForm
from identity import current_user
from interaction_log import load_interaction_history
from models import Alias, Variable
from upload_templates import get_upload_templates

from . import main_bp
from .cid_helper import CidHelper
from .history import _load_request_referers

# Display constants
CONTENT_PREVIEW_LENGTH: int = 20

_VARIABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _shorten_cid(cid: Optional[str], length: int = 6) -> str:
    """Return a shortened CID label for display."""
    return format_cid_short(cid, length)


def _collect_variable_assignment(cid_value: str, user_id: str) -> tuple[list[Variable], Variable | None]:
    """Return the user's variables and the one currently pointing at ``cid_value``."""

    variables = get_user_variables(user_id)
    normalized = CidHelper.normalize(cid_value)
    if not normalized:
        return variables, None

    candidate_values = {value for value in (cid_path(normalized), normalized) if value}
    assigned = None

    if candidate_values:
        for variable in variables:
            definition = (getattr(variable, "definition", "") or "").strip()
            if definition in candidate_values:
                assigned = variable
                break

    return variables, assigned


def _render_upload_success(
    cid_value: str,
    *,
    file_size: int | None = None,
    detected_mime_type: str | None = None,
    view_url_extension: str | None = None,
    filename: str | None = None,
    assignment_variable_name: str | None = None,
):
    """Render the upload success page with variable assignment helpers."""

    normalized = CidHelper.normalize(cid_value)
    record = CidHelper.get_record(cid_value)
    resolved_size = CidHelper.resolve_size(record, file_size if file_size is not None else 0)
    variables, assigned_variable = _collect_variable_assignment(normalized, current_user.id)

    return render_template(
        'upload_success.html',
        cid=normalized,
        file_size=resolved_size,
        detected_mime_type=detected_mime_type,
        view_url_extension=view_url_extension,
        filename=filename,
        variables=variables,
        assigned_variable=assigned_variable,
        assignment_variable_name=assignment_variable_name or '',
    )


@logfire.instrument("uploads._persist_alias_from_upload({alias=})", extract_args=True, record_return=True)
def _persist_alias_from_upload(alias: Alias) -> Alias:
    """Persist alias changes that originate from upload workflows."""

    save_entity(alias)
    return alias


def _process_upload_by_type(form) -> tuple[bytes, Optional[str], Optional[str]]:
    """Process upload based on upload_type field.

    Args:
        form: The FileUploadForm instance

    Returns:
        tuple: (file_content, detected_mime_type, original_filename)

    Raises:
        ValueError: If upload processing fails
    """
    detected_mime_type: Optional[str] = None
    original_filename: Optional[str] = None

    if form.upload_type.data == 'file':
        file_content, original_filename = process_file_upload(form)
    elif form.upload_type.data == 'text':
        file_content = process_text_upload(form)
    elif form.upload_type.data == 'url':
        file_content, detected_mime_type = process_url_upload(form)
    else:
        raise ValueError(f"Unknown upload type: {form.upload_type.data}")

    return file_content, detected_mime_type, original_filename


def _determine_view_extension(
    upload_type: str,
    original_filename: Optional[str],
    detected_mime_type: Optional[str]
) -> str:
    """Determine the view URL extension based on upload type and metadata."""
    if upload_type == 'text':
        return "txt"

    if upload_type == 'file' and original_filename and '.' in original_filename:
        return original_filename.rsplit('.', 1)[1].lower()

    if detected_mime_type:
        extension = get_extension_from_mime_type(detected_mime_type)
        if extension:
            return extension.lstrip('.')

    return ""


def _determine_filename(upload_type: str, original_filename: Optional[str], form) -> Optional[str]:
    """Determine the filename based on upload type."""
    if upload_type == 'file':
        return original_filename
    if upload_type == 'url':
        return form.url.data or None
    return None


@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """File upload page with CID storage."""
    form = FileUploadForm()
    upload_templates = get_upload_templates()

    change_message = (request.form.get('change_message') or '').strip()

    def _render_form():
        interactions = load_interaction_history(current_user.id, 'upload', 'text')
        return render_template(
            'upload.html',
            form=form,
            upload_templates=upload_templates,
            upload_interactions=interactions,
        )

    if form.validate_on_submit():
        # Process upload
        try:
            file_content, detected_mime_type, original_filename = _process_upload_by_type(form)
        except ValueError as exc:
            flash(str(exc), 'error')
            return _render_form()

        # Generate CID and check for existing record
        cid_value = format_cid(generate_cid(file_content))
        cid_record_path = cid_path(cid_value)
        existing = get_cid_by_path(cid_record_path) if cid_record_path else None

        if existing:
            flash(
                Markup(f"Content with this hash already exists! {render_cid_link(cid_value)}"),
                'warning',
            )
        else:
            create_cid_record(cid_value, file_content, current_user.id)
            flash(
                Markup(f"Content uploaded successfully! {render_cid_link(cid_value)}"),
                'success',
            )

        # Record interaction for text uploads
        if form.upload_type.data == 'text':
            record_entity_interaction(
                EntityInteractionRequest(
                    user_id=current_user.id,
                    entity_type='upload',
                    entity_name='text',
                    action='save',
                    message=change_message,
                    content=form.text_content.data or '',
                )
            )

        # Determine view extension and filename
        view_url_extension = _determine_view_extension(
            form.upload_type.data,
            original_filename,
            detected_mime_type
        )
        filename = _determine_filename(form.upload_type.data, original_filename, form)

        return _render_upload_success(
            cid_value,
            file_size=len(file_content),
            detected_mime_type=detected_mime_type,
            view_url_extension=view_url_extension,
            filename=filename,
        )

    return _render_form()


@main_bp.route('/uploads')
def uploads():
    """Display user's uploaded files."""
    user_uploads = get_user_uploads(current_user.id)

    _attach_creation_sources(user_uploads)

    user_uploads = [
        upload
        for upload in user_uploads
        if getattr(upload, 'creation_method', 'upload') != 'server_event'
    ]

    for upload_record in user_uploads:
        if upload_record.file_data:
            try:
                content_text = upload_record.file_data.decode('utf-8', errors='replace')
                upload_record.content_preview = content_text[:CONTENT_PREVIEW_LENGTH].replace('\n', ' ').replace('\r', ' ')
            except (AttributeError, UnicodeDecodeError):
                upload_record.content_preview = upload_record.file_data[:10].hex()
        else:
            upload_record.content_preview = ""

        upload_record.referenced_entities = extract_references_from_bytes(
            getattr(upload_record, 'file_data', None),
            current_user.id,
        )

    total_storage = sum(upload.file_size or 0 for upload in user_uploads)

    return render_template(
        'uploads.html',
        uploads=user_uploads,
        total_uploads=len(user_uploads),
        total_storage=total_storage,
    )


@main_bp.route('/_screenshot/uploads')
def screenshot_uploads_demo():
    abort(404)


@main_bp.route('/edit/<cid_prefix>', methods=['GET', 'POST'])
def edit_cid(cid_prefix):
    """Allow users to edit existing CID content as text."""
    normalized_prefix = format_cid(cid_prefix.split('.')[0] if cid_prefix else cid_prefix)
    matches = find_cids_by_prefix(normalized_prefix)

    if not matches:
        abort(404)

    exact_match = next(
        (
            match
            for match in matches
            if format_cid(match.path) == normalized_prefix
        ),
        None,
    )
    if exact_match:
        matches = [exact_match]

    if len(matches) > 1:
        match_values = [format_cid(match.path) for match in matches]
        return render_template(
            'edit_cid_choices.html',
            cid_prefix=normalized_prefix,
            matches=match_values,
        )

    cid_record = matches[0]
    full_cid = format_cid(cid_record.path)
    alias_for_cid = get_alias_by_target_path(current_user.id, cid_record.path)
    form = EditCidForm()
    submit_label = f"Save {alias_for_cid.name}" if alias_for_cid else 'Save Changes'

    interaction_history = load_interaction_history(current_user.id, 'cid', full_cid)
    content_references = extract_references_from_bytes(
        getattr(cid_record, 'file_data', None),
        current_user.id,
    )

    if form.validate_on_submit():
        alias_name_input = ''
        if not alias_for_cid:
            alias_name_input = form.alias_name.data or ''
            if alias_name_input:
                existing_alias = get_alias_by_name(current_user.id, alias_name_input)
                if existing_alias:
                    form.alias_name.errors.append('Alias with this name already exists.')
                    return render_template(
                        'edit_cid.html',
                        form=form,
                        cid=full_cid,
                        submit_label=submit_label,
                        current_alias_name=getattr(alias_for_cid, 'name', None),
                        show_alias_field=alias_for_cid is None,
                        interaction_history=interaction_history,
                        content_references=content_references,
                    )

        text_content = form.text_content.data or ''
        change_message = (request.form.get('change_message') or '').strip()
        file_content = text_content.encode('utf-8')
        cid_value = format_cid(generate_cid(file_content))
        cid_record_path = cid_path(cid_value)
        existing = get_cid_by_path(cid_record_path) if cid_record_path else None

        if existing:
            flash(
                Markup(
                    f"Content with this hash already exists! {render_cid_link(cid_value)}"
                ),
                'warning',
            )
        else:
            create_cid_record(cid_value, file_content, current_user.id)
            flash(
                Markup(
                    f"Content uploaded successfully! {render_cid_link(cid_value)}"
                ),
                'success',
            )

        new_target_path = cid_path(cid_value)
        if alias_for_cid:
            primary_route = get_primary_alias_route(alias_for_cid)
            if primary_route:
                primary_line = format_primary_alias_line(
                    primary_route.match_type,
                    primary_route.match_pattern,
                    new_target_path,
                    ignore_case=primary_route.ignore_case,
                    alias_name=getattr(alias_for_cid, "name", None),
                )
            else:
                primary_line = format_primary_alias_line(
                    "literal",
                    None,
                    new_target_path,
                    alias_name=getattr(alias_for_cid, "name", None),
                )
            alias_for_cid.definition = replace_primary_definition_line(
                getattr(alias_for_cid, "definition", None),
                primary_line,
            )
            _persist_alias_from_upload(alias_for_cid)
        elif alias_name_input:
            primary_line = format_primary_alias_line(
                "literal",
                None,
                new_target_path,
                alias_name=alias_name_input,
            )
            new_alias = Alias(
                name=alias_name_input,
                user_id=current_user.id,
                definition=primary_line,
            )
            _persist_alias_from_upload(new_alias)

        record_entity_interaction(
            EntityInteractionRequest(
                user_id=current_user.id,
                entity_type='cid',
                entity_name=full_cid,
                action='save',
                message=change_message,
                content=text_content,
            )
        )

        return _render_upload_success(
            cid_value,
            file_size=len(file_content),
            detected_mime_type='text/plain',
            view_url_extension='txt',
            filename=None,
        )

    if request.method == 'GET':
        existing_text = cid_record.file_data.decode('utf-8', errors='replace')
        form.text_content.data = existing_text

    return render_template(
        'edit_cid.html',
        form=form,
        cid=full_cid,
        submit_label=submit_label,
        current_alias_name=getattr(alias_for_cid, 'name', None),
        show_alias_field=alias_for_cid is None,
        interaction_history=interaction_history,
        content_references=content_references,
    )


@main_bp.route('/upload/assign-variable', methods=['POST'])
def assign_cid_variable():
    """Assign the supplied CID to an existing or new variable."""

    cid_value = format_cid(request.form.get('cid'))
    variable_name = (request.form.get('variable_name') or '').strip()
    view_url_extension = (request.form.get('view_url_extension') or '').strip() or None
    filename = (request.form.get('filename') or '').strip() or None
    detected_mime_type = (request.form.get('detected_mime_type') or '').strip() or None

    if not cid_value:
        flash('A CID is required to assign it to a variable.', 'error')
        return redirect(url_for('main.upload'))

    cid_record = get_cid_by_path(cid_path(cid_value))
    if not cid_record:
        flash('CID not found. Upload content before assigning it to a variable.', 'error')
        return redirect(url_for('main.upload'))

    file_size = CidHelper.resolve_size(cid_record)
    assignment_value = cid_path(cid_value) or cid_value

    if not variable_name:
        flash('Enter a variable name to assign this CID.', 'error')
        return _render_upload_success(
            cid_value,
            file_size=file_size,
            detected_mime_type=detected_mime_type,
            view_url_extension=view_url_extension,
            filename=filename,
            assignment_variable_name=variable_name,
        )

    if not _VARIABLE_NAME_PATTERN.fullmatch(variable_name):
        flash(
            'Variable names may only contain letters, numbers, dots, hyphens, and underscores.',
            'error',
        )
        return _render_upload_success(
            cid_value,
            file_size=file_size,
            detected_mime_type=detected_mime_type,
            view_url_extension=view_url_extension,
            filename=filename,
            assignment_variable_name=variable_name,
        )

    existing_variable = get_variable_by_name(current_user.id, variable_name)
    assignment_message = None

    if existing_variable:
        current_value = (existing_variable.definition or '').strip()
        if current_value == assignment_value:
            flash(f'CID already assigned to variable "{variable_name}".', 'info')
        else:
            existing_variable.definition = assignment_value
            existing_variable.updated_at = datetime.now(timezone.utc)
            save_entity(existing_variable)
            assignment_message = f'Updated variable "{variable_name}" to use the CID.'
    else:
        new_variable = Variable(
            name=variable_name,
            definition=assignment_value,
            user_id=current_user.id,
        )
        save_entity(new_variable)
        assignment_message = f'Created variable "{variable_name}" using this CID.'

    if assignment_message:
        from .variables import update_variable_definitions_cid

        update_variable_definitions_cid(current_user.id)
        record_entity_interaction(
            EntityInteractionRequest(
                user_id=current_user.id,
                entity_type='variable',
                entity_name=variable_name,
                action='save',
                message='Assigned CID from upload page',
                content=assignment_value,
            )
        )
        flash(assignment_message, 'success')

    return _render_upload_success(
        cid_value,
        file_size=file_size,
        detected_mime_type=detected_mime_type,
        view_url_extension=view_url_extension,
        filename=filename,
    )


@main_bp.route('/server_events')
def server_events():
    """Display server invocation events for the current user."""
    invocations = get_user_server_invocations(current_user.id)

    referer_by_request = _load_request_referers(invocations)

    for invocation in invocations:
        invocation.invocation_link = cid_path(
            getattr(invocation, 'invocation_cid', None),
            'json',
        )
        invocation.invocation_label = _shorten_cid(
            getattr(invocation, 'invocation_cid', None)
        )
        invocation.request_details_link = cid_path(
            getattr(invocation, 'request_details_cid', None),
            'json',
        )
        invocation.request_details_label = _shorten_cid(
            getattr(invocation, 'request_details_cid', None)
        )
        invocation.result_link = cid_path(
            getattr(invocation, 'result_cid', None),
            'txt',
        )
        invocation.result_label = _shorten_cid(
            getattr(invocation, 'result_cid', None)
        )
        invocation.server_link = url_for(
            'main.view_server',
            server_name=invocation.server_name,
        )
        invocation.servers_cid_link = cid_path(
            getattr(invocation, 'servers_cid', None),
            'json',
        )
        invocation.servers_cid_label = _shorten_cid(
            getattr(invocation, 'servers_cid', None)
        )
        request_cid = getattr(invocation, 'request_details_cid', None)
        invocation.request_referer = referer_by_request.get(request_cid) if request_cid else None

    return render_template(
        'server_events.html',
        events=invocations,
        total_events=len(invocations),
    )


@main_bp.route('/_screenshot/server-events')
def screenshot_server_events_demo():
    abort(404)


def _attach_creation_sources(user_uploads):
    """Annotate uploads with information about how they were created."""
    if not user_uploads:
        return

    invocations = get_user_server_invocations(current_user.id)

    invocation_by_cid = {}
    for invocation in invocations:
        for attr in (
            'result_cid',
            'invocation_cid',
            'request_details_cid',
            'servers_cid',
        ):
            cid_value = getattr(invocation, attr, None)
            cid_key = format_cid(cid_value)
            if cid_key and cid_key not in invocation_by_cid:
                invocation_by_cid[cid_key] = invocation

    for upload_record in user_uploads:
        upload_record.creation_method = 'upload'
        upload_record.server_invocation_link = None
        upload_record.server_invocation_server_name = None

        cid = format_cid(getattr(upload_record, 'path', None)) if getattr(upload_record, 'path', None) else None
        if not cid:
            continue

        invocation = invocation_by_cid.get(cid)
        if invocation:
            upload_record.creation_method = 'server_event'
            upload_record.server_invocation_server_name = invocation.server_name
            if invocation.invocation_cid:
                upload_record.server_invocation_link = cid_path(
                    invocation.invocation_cid,
                    'json',
                )


__all__ = [
    'server_events',
    'upload',
    'uploads',
    'screenshot_server_events_demo',
    'screenshot_uploads_demo',
]
