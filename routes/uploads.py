"""Upload-related routes and helpers."""

from flask import abort, flash, render_template, request, url_for
from identity import current_user

from markupsafe import Markup

from cid_presenter import cid_path, format_cid, format_cid_short, render_cid_link
from cid_utils import (
    generate_cid,
    get_extension_from_mime_type,
    process_file_upload,
    process_text_upload,
    process_url_upload,
)
from entity_references import (
    extract_references_from_bytes,
)
from db_access import (
    create_cid_record,
    find_cids_by_prefix,
    get_alias_by_name,
    get_aliases_by_target_path,
    get_cid_by_path,
    get_user_server_invocations,
    get_user_uploads,
    record_entity_interaction,
    save_entity,
    update_alias_cid_reference,
    update_cid_references,
)
from models import Alias
from forms import EditCidForm, FileUploadForm
from upload_templates import get_upload_templates
from interaction_log import load_interaction_history

from . import main_bp
from .history import _load_request_referers
import logfire

def _shorten_cid(cid, length=6):
    """Return a shortened CID label for display."""
    return format_cid_short(cid, length)


@logfire.instrument("uploads._persist_alias_from_upload({alias=})", extract_args=True, record_return=True)
def _persist_alias_from_upload(alias: Alias) -> Alias:
    """Persist alias changes that originate from upload workflows."""

    save_entity(alias)
    return alias


@main_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """File upload page with IPFS CID storage."""
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
        try:
            detected_mime_type = None
            original_filename = None

            if form.upload_type.data == 'file':
                file_content, original_filename = process_file_upload(form)
            elif form.upload_type.data == 'text':
                file_content = process_text_upload(form)
            else:
                file_content, detected_mime_type = process_url_upload(form)
        except ValueError as exc:
            flash(str(exc), 'error')
            return _render_form()

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

        view_url_extension = ""

        if form.upload_type.data == 'text':
            view_url_extension = "txt"
            record_entity_interaction(
                current_user.id,
                'upload',
                'text',
                'save',
                change_message,
                form.text_content.data or '',
            )
        elif form.upload_type.data == 'file' and original_filename:
            if '.' in original_filename:
                view_url_extension = original_filename.rsplit('.', 1)[1].lower()
        elif detected_mime_type:
            extension = get_extension_from_mime_type(detected_mime_type)
            if extension:
                view_url_extension = extension.lstrip('.')

        return render_template(
            'upload_success.html',
            cid=cid_value,
            file_size=len(file_content),
            detected_mime_type=detected_mime_type,
            view_url_extension=view_url_extension,
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

    for upload in user_uploads:
        if upload.file_data:
            try:
                content_text = upload.file_data.decode('utf-8', errors='replace')
                upload.content_preview = content_text[:20].replace('\n', ' ').replace('\r', ' ')
            except Exception:
                upload.content_preview = upload.file_data[:10].hex()
        else:
            upload.content_preview = ""

        upload.referenced_entities = extract_references_from_bytes(
            getattr(upload, 'file_data', None),
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
    aliases_for_cid = get_aliases_by_target_path(current_user.id, cid_record.path)
    existing_alias_names = [alias.name for alias in aliases_for_cid]
    existing_alias_set = set(existing_alias_names)
    existing_alias_string = " ".join(existing_alias_names)

    form = EditCidForm()
    submit_label = (
        f"Save {existing_alias_names[0]}"
        if len(existing_alias_names) == 1
        else 'Save Changes'
    )

    interaction_history = load_interaction_history(current_user.id, 'cid', full_cid)
    content_references = extract_references_from_bytes(
        getattr(cid_record, 'file_data', None),
        current_user.id,
    )
    original_text_content = cid_record.file_data.decode('utf-8', errors='replace')

    if form.validate_on_submit():
        submitted_alias_names = getattr(form, 'alias_names_list', [])
        alias_values_present = bool(submitted_alias_names)
        alias_changes = set(submitted_alias_names) != existing_alias_set
        new_alias_names = []

        if alias_changes and submitted_alias_names:
            new_alias_names = [
                name for name in submitted_alias_names if name not in existing_alias_set
            ]

            for alias_name in new_alias_names:
                existing_alias = get_alias_by_name(current_user.id, alias_name)
                if existing_alias and existing_alias.target_path != cid_record.path:
                    form.alias_names.errors.append(
                        f'Alias "{alias_name}" already exists.'
                    )
                    return render_template(
                        'edit_cid.html',
                        form=form,
                        cid=full_cid,
                        submit_label=submit_label,
                        existing_alias_names=existing_alias_names,
                        interaction_history=interaction_history,
                        content_references=content_references,
                        original_text=original_text_content,
                        original_aliases=existing_alias_string,
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

        if alias_changes:
            if submitted_alias_names:
                for alias_name in new_alias_names:
                    new_alias = Alias(
                        name=alias_name,
                        target_path=new_target_path,
                        user_id=current_user.id,
                        match_type='literal',
                        ignore_case=False,
                    )
                    _persist_alias_from_upload(new_alias)

                for alias_name in submitted_alias_names:
                    update_alias_cid_reference(full_cid, cid_value, alias_name)
            elif existing_alias_names:
                update_cid_references(full_cid, cid_value)
        elif alias_values_present:
            update_cid_references(full_cid, cid_value)

        record_entity_interaction(
            current_user.id,
            'cid',
            full_cid,
            'save',
            change_message,
            text_content,
        )

        return render_template(
            'upload_success.html',
            cid=cid_value,
            file_size=len(file_content),
            detected_mime_type='text/plain',
            view_url_extension='txt',
        )

    if request.method == 'GET':
        form.text_content.data = original_text_content
        form.alias_names.data = existing_alias_string

    return render_template(
        'edit_cid.html',
        form=form,
        cid=full_cid,
        submit_label=submit_label,
        existing_alias_names=existing_alias_names,
        interaction_history=interaction_history,
        content_references=content_references,
        original_text=original_text_content,
        original_aliases=existing_alias_string,
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

    for upload in user_uploads:
        upload.creation_method = 'upload'
        upload.server_invocation_link = None
        upload.server_invocation_server_name = None

        cid = format_cid(getattr(upload, 'path', None)) if getattr(upload, 'path', None) else None
        if not cid:
            continue

        invocation = invocation_by_cid.get(cid)
        if invocation:
            upload.creation_method = 'server_event'
            upload.server_invocation_server_name = invocation.server_name
            if invocation.invocation_cid:
                upload.server_invocation_link = cid_path(
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
