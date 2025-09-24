"""Upload-related routes and helpers."""
from flask import abort, flash, jsonify, render_template, request, url_for
from flask_login import current_user

from auth_providers import require_login
from cid_utils import (
    generate_cid,
    get_extension_from_mime_type,
    process_file_upload,
    process_text_upload,
    process_url_upload,
)
from db_access import create_cid_record, find_cids_by_prefix, get_cid_by_path, get_user_uploads
from models import ServerInvocation
from forms import EditCidForm, FileUploadForm
from upload_templates import get_upload_templates

from . import main_bp
from .history import _load_request_referers


def _shorten_cid(cid, length=6):
    """Return a shortened CID label for display."""
    if not cid:
        return None
    return f"{cid[:length]}..."


@main_bp.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    """File upload page with IPFS CID storage."""
    form = FileUploadForm()
    upload_templates = get_upload_templates()

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
            return render_template('upload.html', form=form, upload_templates=upload_templates)

        cid = generate_cid(file_content)

        existing = get_cid_by_path(f"/{cid}")
        if existing:
            flash(f'Content with this hash already exists! CID: {cid}', 'warning')
        else:
            create_cid_record(cid, file_content, current_user.id)
            flash(f'Content uploaded successfully! CID: {cid}', 'success')

        view_url_extension = ""

        if form.upload_type.data == 'text':
            view_url_extension = "txt"
        elif form.upload_type.data == 'file' and original_filename:
            if '.' in original_filename:
                view_url_extension = original_filename.rsplit('.', 1)[1].lower()
        elif detected_mime_type:
            extension = get_extension_from_mime_type(detected_mime_type)
            if extension:
                view_url_extension = extension.lstrip('.')

        return render_template(
            'upload_success.html',
            cid=cid,
            file_size=len(file_content),
            detected_mime_type=detected_mime_type,
            view_url_extension=view_url_extension,
        )

    return render_template('upload.html', form=form, upload_templates=upload_templates)


@main_bp.route('/uploads')
@require_login
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

    total_storage = sum(upload.file_size or 0 for upload in user_uploads)

    return render_template(
        'uploads.html',
        uploads=user_uploads,
        total_uploads=len(user_uploads),
        total_storage=total_storage,
    )


@main_bp.route('/edit/<cid_prefix>', methods=['GET', 'POST'])
@require_login
def edit_cid(cid_prefix):
    """Allow users to edit existing CID content as text."""
    normalized_prefix = cid_prefix.split('.')[0].lstrip('/') if cid_prefix else cid_prefix
    matches = find_cids_by_prefix(normalized_prefix)

    if not matches:
        abort(404)

    exact_match = next((match for match in matches if match.path.lstrip('/') == normalized_prefix), None)
    if exact_match:
        matches = [exact_match]

    if len(matches) > 1:
        match_values = [match.path.lstrip('/') for match in matches]
        return render_template(
            'edit_cid_choices.html',
            cid_prefix=normalized_prefix,
            matches=match_values,
        )

    cid_record = matches[0]
    form = EditCidForm()
    full_cid = cid_record.path.lstrip('/')

    if form.validate_on_submit():
        text_content = form.text_content.data or ''
        file_content = text_content.encode('utf-8')
        cid = generate_cid(file_content)
        existing = get_cid_by_path(f"/{cid}")

        if existing:
            flash(f'Content with this hash already exists! CID: {cid}', 'warning')
        else:
            create_cid_record(cid, file_content, current_user.id)
            flash(f'Content uploaded successfully! CID: {cid}', 'success')

        return render_template(
            'upload_success.html',
            cid=cid,
            file_size=len(file_content),
            detected_mime_type='text/plain',
            view_url_extension='txt',
        )

    if request.method == 'GET':
        existing_text = cid_record.file_data.decode('utf-8', errors='replace')
        form.text_content.data = existing_text

    return render_template('edit_cid.html', form=form, cid=full_cid)


@main_bp.route('/server_events')
@require_login
def server_events():
    """Display server invocation events for the current user."""
    invocations = (
        ServerInvocation.query
        .filter(ServerInvocation.user_id == current_user.id)
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )

    referer_by_request = _load_request_referers(invocations)

    for invocation in invocations:
        invocation.invocation_link = (
            f"/{invocation.invocation_cid}.json"
            if getattr(invocation, 'invocation_cid', None)
            else None
        )
        invocation.invocation_label = _shorten_cid(
            getattr(invocation, 'invocation_cid', None)
        )
        invocation.request_details_link = (
            f"/{invocation.request_details_cid}.json"
            if getattr(invocation, 'request_details_cid', None)
            else None
        )
        invocation.request_details_label = _shorten_cid(
            getattr(invocation, 'request_details_cid', None)
        )
        invocation.result_link = (
            f"/{invocation.result_cid}.txt"
            if getattr(invocation, 'result_cid', None)
            else None
        )
        invocation.result_label = _shorten_cid(
            getattr(invocation, 'result_cid', None)
        )
        invocation.server_link = url_for(
            'main.view_server',
            server_name=invocation.server_name,
        )
        invocation.servers_cid_link = (
            f"/{invocation.servers_cid}.json"
            if getattr(invocation, 'servers_cid', None)
            else None
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


def _attach_creation_sources(user_uploads):
    """Annotate uploads with information about how they were created."""
    if not user_uploads:
        return

    invocations = (
        ServerInvocation.query
        .filter(ServerInvocation.user_id == current_user.id)
        .order_by(ServerInvocation.invoked_at.desc(), ServerInvocation.id.desc())
        .all()
    )

    invocation_by_cid = {}
    for invocation in invocations:
        for attr in (
            'result_cid',
            'invocation_cid',
            'request_details_cid',
            'servers_cid',
        ):
            cid_value = getattr(invocation, attr, None)
            if cid_value and cid_value not in invocation_by_cid:
                invocation_by_cid[cid_value] = invocation

    for upload in user_uploads:
        upload.creation_method = 'upload'
        upload.server_invocation_link = None
        upload.server_invocation_server_name = None

        cid = upload.path.lstrip('/') if getattr(upload, 'path', None) else None
        if not cid:
            continue

        invocation = invocation_by_cid.get(cid)
        if invocation:
            upload.creation_method = 'server_event'
            upload.server_invocation_server_name = invocation.server_name
            if invocation.invocation_cid:
                upload.server_invocation_link = f"/{invocation.invocation_cid}.json"


__all__ = ['server_events', 'upload', 'uploads']
