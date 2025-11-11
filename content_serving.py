"""HTTP response generation for CID content serving.

This module handles creating HTTP responses for serving CID content,
including caching, content type detection, and special rendering modes.
"""

import base64
import io
from dataclasses import dataclass
from typing import Optional

from flask import Response, make_response, render_template, request

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
# CONSTANTS
# ============================================================================

# File extension constants for special handling
MARKDOWN_HTML_EXT = '.md.html'
TEXT_EXT = '.txt'
QR_EXT = '.qr'

# HTTP header constants
HEADER_IF_NONE_MATCH = 'If-None-Match'
HEADER_IF_MODIFIED_SINCE = 'If-Modified-Since'

# Content type constants
CONTENT_TYPE_HTML_UTF8 = 'text/html; charset=utf-8'
CONTENT_TYPE_TEXT_UTF8 = 'text/plain; charset=utf-8'
CONTENT_TYPE_HTML = 'text/html'
CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
CONTENT_TYPE_TEXT_PLAIN = 'text/plain'

# QR code configuration
QR_CODE_BOX_SIZE = 12
QR_CODE_BORDER = 4

# Caching configuration
# CIDs are content-addressed (immutable), so we can cache them indefinitely
CACHE_CONTROL_IMMUTABLE = 'public, max-age=31536000, immutable'
CACHE_EXPIRES_HEADER = 'Thu, 31 Dec 2037 23:55:55 GMT'


# ============================================================================
# PATH ANALYSIS
# ============================================================================

@dataclass
class PathInfo:
    """Parsed information about a CID request path.

    Attributes:
        is_qr: True if path requests QR code generation (.qr extension)
        is_markdown_html: True if path requests markdown rendering (.md.html extension)
        is_text: True if path requests text/plain rendering (.txt extension)
        has_extension: True if filename has any extension
        normalized_cid: The stored CID path (without leading slash)
        target_cid: The CID to use for QR codes or etags
    """
    is_qr: bool
    is_markdown_html: bool
    is_text: bool
    has_extension: bool
    normalized_cid: str
    target_cid: str

    @classmethod
    def from_path(cls, path: str, cid_content) -> 'PathInfo':
        """Parse request path and extract CID information.

        Args:
            path: Request path (e.g., "/CID.filename.ext")
            cid_content: CID content record with optional path attribute

        Returns:
            PathInfo object with parsed information

        Example:
            >>> info = PathInfo.from_path("/abc123.md.html", cid_record)
            >>> info.is_markdown_html
            True
        """
        # Extract CID from path
        cid = path[1:] if path.startswith('/') else path

        # Get filename part for extension checks
        filename_part = path.rsplit('/', 1)[-1]
        filename_lower = filename_part.lower()

        # Check for special rendering modes
        is_qr = filename_lower.endswith(QR_EXT)
        is_markdown_html = filename_lower.endswith(MARKDOWN_HTML_EXT)
        is_text = filename_lower.endswith(TEXT_EXT)
        has_extension = '.' in filename_part

        # Extract normalized CID for etag (from stored path)
        stored_cid_path = getattr(cid_content, 'path', None)
        normalized_cid = (stored_cid_path or '').lstrip('/')

        # Determine target CID (for QR codes or etags)
        if normalized_cid:
            target_cid = normalized_cid
        elif is_qr:
            target_cid = cid.rsplit(QR_EXT, 1)[0]
        else:
            target_cid = cid.split('.')[0]

        return cls(
            is_qr=is_qr,
            is_markdown_html=is_markdown_html,
            is_text=is_text,
            has_extension=has_extension,
            normalized_cid=normalized_cid,
            target_cid=target_cid,
        )


# ============================================================================
# QR CODE GENERATION
# ============================================================================

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
# CONTENT TYPE DETERMINATION
# ============================================================================

def _determine_content_type(path: str, path_info: PathInfo) -> str:
    """Determine the content type for a given path and request mode.

    Args:
        path: Request path
        path_info: Parsed path information

    Returns:
        MIME type string (may include charset)

    Example:
        >>> _determine_content_type("/test.md.html", PathInfo(...))
        'text/html; charset=utf-8'
    """
    if path_info.is_qr:
        return CONTENT_TYPE_HTML_UTF8
    elif path_info.is_markdown_html:
        return CONTENT_TYPE_HTML
    elif path_info.is_text:
        return CONTENT_TYPE_TEXT_UTF8
    else:
        return get_mime_type_from_extension(path)


def _ensure_utf8_text(data: bytes) -> Optional[bytes]:
    """Decode and re-encode data as UTF-8 text if possible.

    Args:
        data: Raw bytes to process

    Returns:
        UTF-8 encoded bytes, or None if data is not text

    Example:
        >>> _ensure_utf8_text(b'hello')
        b'hello'
    """
    text = decode_text_safely(data)
    if text is not None:
        return text.encode('utf-8')
    return None


def _process_content_body(
    response_body: bytes,
    content_type: str,
    path_info: PathInfo
) -> tuple[bytes, str]:
    """Process content body based on content type and request mode.

    Args:
        response_body: Raw content bytes
        content_type: Current content type
        path_info: Parsed path information

    Returns:
        Tuple of (processed_body, final_content_type)

    Example:
        >>> body, ct = _process_content_body(b'# Hello', 'text/plain', path_info)
        >>> ct
        'text/html; charset=utf-8'
    """
    # Handle QR code generation
    if path_info.is_qr and path_info.target_cid:
        return _serve_qr_code(path_info.target_cid), CONTENT_TYPE_HTML_UTF8

    # Handle markdown rendering
    if path_info.is_markdown_html:
        rendered = _serve_markdown_html(response_body)
        if rendered:
            return rendered, CONTENT_TYPE_HTML

    # Handle forced text rendering
    if path_info.is_text:
        utf8_text = _ensure_utf8_text(response_body)
        if utf8_text is not None:
            return utf8_text, CONTENT_TYPE_TEXT_UTF8
        return response_body, CONTENT_TYPE_TEXT_UTF8

    # Handle auto-detection for binary files without extension
    if content_type == CONTENT_TYPE_OCTET_STREAM and not path_info.has_extension:
        utf8_text = _ensure_utf8_text(response_body)
        if utf8_text is not None:
            return utf8_text, CONTENT_TYPE_TEXT_UTF8

    # Handle text/plain with charset
    if content_type == CONTENT_TYPE_TEXT_PLAIN:
        utf8_text = _ensure_utf8_text(response_body)
        if utf8_text is not None:
            return utf8_text, CONTENT_TYPE_TEXT_UTF8

    return response_body, content_type


def _add_response_headers(
    response: Response,
    etag: str,
    cid_content,
    filename: Optional[str],
    path_info: PathInfo
) -> None:
    """Add HTTP headers to the response.

    Args:
        response: Flask response object to modify
        etag: ETag value for caching
        cid_content: CID content record
        filename: Optional filename for Content-Disposition
        path_info: Parsed path information

    Note:
        CIDs are content-addressed (immutable), so we can safely cache
        them indefinitely with the 'immutable' directive.
    """
    # Add Content-Disposition for downloads (but not for rendered markdown)
    if filename and not path_info.is_markdown_html:
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Add caching headers
    # Since CIDs are content-addressed, the content is immutable
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime(
        '%a, %d %b %Y %H:%M:%S GMT'
    )
    response.headers['Cache-Control'] = CACHE_CONTROL_IMMUTABLE
    response.headers['Expires'] = CACHE_EXPIRES_HEADER


# ============================================================================
# CONTENT SERVING
# ============================================================================

def serve_cid_content(cid_content, path: str) -> Optional[Response]:
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

    Note:
        This function implements HTTP conditional requests (304 Not Modified)
        for efficient bandwidth usage. Since CIDs are content-addressed,
        we can cache them indefinitely.
    """
    # Validate input
    if cid_content is None or cid_content.file_data is None:
        return None

    # Parse path information
    path_info = PathInfo.from_path(path, cid_content)

    # Determine content type
    content_type = _determine_content_type(path, path_info)

    # Process content body based on request mode
    response_body, final_content_type = _process_content_body(
        cid_content.file_data,
        content_type,
        path_info
    )

    # Handle conditional requests (304 Not Modified)
    etag = f'"{path_info.target_cid}"'
    if request.headers.get(HEADER_IF_NONE_MATCH) == etag:
        return _make_304_response(etag, cid_content)

    if request.headers.get(HEADER_IF_MODIFIED_SINCE):
        return _make_304_response(etag, cid_content)

    # Build full response
    response = make_response(response_body)
    response.headers['Content-Type'] = final_content_type
    response.headers['Content-Length'] = len(response_body)

    # Add caching and download headers
    filename = extract_filename_from_cid_path(path)
    _add_response_headers(response, etag, cid_content, filename, path_info)

    return response


def _serve_qr_code(target_cid: str) -> bytes:
    """Generate QR code page for a CID.

    Args:
        target_cid: CID string

    Returns:
        HTML page as bytes
    """
    qr_target_url = f"https://256t.org/{target_cid}"
    qr_image_url = generate_qr_data_url(qr_target_url)
    html = render_template(
        'cid_qr.html',
        title='CID QR Code',
        cid=target_cid,
        qr_value=qr_target_url,
        qr_image_url=qr_image_url,
        cid_href=cid_path(target_cid),
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


def _make_304_response(etag: str, cid_content) -> Response:
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
