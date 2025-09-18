"""Upload-related routes and helpers."""
from flask import flash, jsonify, render_template
from flask_login import current_user

from auth_providers import require_login
from cid_utils import (
    generate_cid,
    get_extension_from_mime_type,
    process_file_upload,
    process_text_upload,
    process_url_upload,
)
from db_access import create_cid_record, get_cid_by_path, get_user_uploads
from forms import FileUploadForm

from . import main_bp


@main_bp.route('/upload', methods=['GET', 'POST'])
@require_login
def upload():
    """File upload page with IPFS CID storage."""
    form = FileUploadForm()

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
            return render_template('upload.html', form=form)

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

    return render_template('upload.html', form=form)


@main_bp.route('/uploads')
@require_login
def uploads():
    """Display user's uploaded files."""
    user_uploads = get_user_uploads(current_user.id)

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


@main_bp.route('/meta/<cid>')
def meta_cid(cid):
    """Serve metadata about a CID as JSON."""
    cid_record = get_cid_by_path(f"/{cid}")

    if not cid_record:
        return jsonify({'error': 'CID not found'}), 404

    metadata = {
        'cid': cid,
        'path': cid_record.path,
        'file_size': cid_record.file_size,
        'created_at': cid_record.created_at.isoformat() if cid_record.created_at else None,
        'uploaded_by_user_id': cid_record.uploaded_by_user_id,
    }

    if cid_record.uploaded_by:
        metadata['uploaded_by'] = {
            'user_id': cid_record.uploaded_by.id,
            'username': cid_record.uploaded_by.username,
            'email': cid_record.uploaded_by.email,
        }

    return jsonify(metadata)


__all__ = ['meta_cid', 'upload', 'uploads']
