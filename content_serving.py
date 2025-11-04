"""HTTP response generation for CID content serving.

This module handles creating HTTP responses for serving CID content,
including caching, content type detection, and special rendering modes.
"""

import base64
import io
from typing import Optional

from flask import make_response, render_template, request

try:
    import qrcode  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover
    qrcode = None  # type: ignore[assignment]
    _qrcode_import_error = exc
else:
    _qrcode_import_error = None

from content_rendering import decode_text_safely, render_markdown_document
from cid_presenter import cid_path
from mime_utils import extract_filename_from_cid_path, get_mime_type_from_extension


# ============================================================================
# QR CODE GENERATION
# ============================================================================

# QR code configuration
QR_CODE_BOX_SIZE = 12
QR_CODE_BORDER = 4


def generate_qr_data_url(target_url: str) -> str:
    """Generate a data URL representing a QR code that encodes target_url.

    Args:
        target_url: URL to encode in the QR code

    Returns:
        Data URL with PNG image

    Raises:
        RuntimeError: If qrcode library is not installed

    Example:
        >>> url = generate_qr_data_url("https://example.com")
        >>> url.startswith("data:image/png;base64,")
        True
    """
    if qrcode is None:
        raise RuntimeError(
            "Missing optional dependency 'qrcode'. Run './install' or "
            "'pip install qrcode[pil]' before generating QR codes."
        ) from _qrcode_import_error

    qr_code = qrcode.QRCode(box_size=QR_CODE_BOX_SIZE, border=QR_CODE_BORDER)
    qr_code.add_data(target_url)
    qr_code.make(fit=True)
    qr_image = qr_code.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_png_bytes = buffer.getvalue()
    return "data:image/png;base64," + base64.b64encode(qr_png_bytes).decode("ascii")


# ============================================================================
# CONTENT SERVING
# ============================================================================

def serve_cid_content(cid_content, path: str):
    """Serve CID content with appropriate headers and caching.

    Handles various content types and rendering modes:
    - .qr extension: Generate QR code page
    - .md.html extension: Render markdown as HTML
    - .txt extension: Force text/plain
    - Auto-detection for other content

    Args:
        cid_content: CID content record with file_data and created_at
        path: Request path (e.g., "/CID.filename.ext")

    Returns:
        Flask response object or None if content is invalid

    Example:
        >>> response = serve_cid_content(cid_record, "/CID.txt")
        >>> response.status_code
        200
    """
    if cid_content is None or cid_content.file_data is None:
        return None

    # Extract CID from path
    cid = path[1:] if path.startswith('/') else path

    # Determine content type from extension
    content_type = get_mime_type_from_extension(path)
    filename_part = path.rsplit('/', 1)[-1]
    has_extension = '.' in filename_part

    # Check for special rendering modes
    explicit_markdown_request = filename_part.lower().endswith('.md.html')
    is_text_extension_request = filename_part.lower().endswith('.txt')
    is_qr_request = filename_part.lower().endswith('.qr')

    # Extract normalized CID for etag
    cid_path_attr = getattr(cid_content, 'path', None)
    normalized_cid = (cid_path_attr or '').lstrip('/')
    qr_cid = normalized_cid or (cid.rsplit('.qr', 1)[0] if is_qr_request else '')
    etag_source = normalized_cid or cid.split('.')[0]

    # Process content based on mode
    response_body = cid_content.file_data

    if is_qr_request and qr_cid:
        # Generate QR code page
        response_body = _serve_qr_code(qr_cid)
        content_type = 'text/html; charset=utf-8'
    elif explicit_markdown_request:
        # Render markdown to HTML
        response_body = _serve_markdown_html(response_body)
        if response_body:
            content_type = 'text/html'
    elif content_type == 'application/octet-stream':
        # Auto-detect text content if no extension
        if not has_extension:
            text = decode_text_safely(response_body)
            if text is not None:
                response_body = text.encode('utf-8')
                content_type = 'text/plain; charset=utf-8'
    elif is_text_extension_request:
        # Force text rendering
        text = decode_text_safely(response_body)
        if text is not None:
            response_body = text.encode('utf-8')
        content_type = 'text/plain; charset=utf-8'
    elif content_type == 'text/plain':
        # Ensure UTF-8 encoding
        text = decode_text_safely(response_body)
        if text is not None:
            response_body = text.encode('utf-8')
            content_type = 'text/plain; charset=utf-8'

    # Handle conditional requests (304 Not Modified)
    etag = f'"{etag_source}"'
    if request.headers.get('If-None-Match') == etag:
        return _make_304_response(etag, cid_content)

    if request.headers.get('If-Modified-Since'):
        return _make_304_response(etag, cid_content)

    # Build full response
    response = make_response(response_body)
    response.headers['Content-Type'] = content_type
    response.headers['Content-Length'] = len(response_body)

    # Add Content-Disposition for downloads
    filename = extract_filename_from_cid_path(path)
    if filename and not explicit_markdown_request:
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Add caching headers
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime(
        '%a, %d %b %Y %H:%M:%S GMT'
    )
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    response.headers['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'

    return response


def _serve_qr_code(qr_cid: str) -> bytes:
    """Generate QR code page for a CID.

    Args:
        qr_cid: CID string

    Returns:
        HTML page as bytes
    """
    qr_target_url = f"https://256t.org/{qr_cid}"
    qr_image_url = generate_qr_data_url(qr_target_url)
    html = render_template(
        'cid_qr.html',
        title='CID QR Code',
        cid=qr_cid,
        qr_value=qr_target_url,
        qr_image_url=qr_image_url,
        cid_href=cid_path(qr_cid),
    )
    return html.encode('utf-8')


def _serve_markdown_html(response_body: bytes) -> Optional[bytes]:
    """Render markdown content to HTML.

    Args:
        response_body: Raw markdown bytes

    Returns:
        Rendered HTML bytes or None if decode fails
    """
    text = decode_text_safely(response_body)
    if text is not None:
        return render_markdown_document(text).encode('utf-8')
    return None


def _make_304_response(etag: str, cid_content) -> object:
    """Create a 304 Not Modified response.

    Args:
        etag: ETag value
        cid_content: CID content record

    Returns:
        Flask response with 304 status
    """
    response = make_response('', 304)
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime(
        '%a, %d %b %Y %H:%M:%S GMT'
    )
    return response
