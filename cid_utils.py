import base64
import hashlib
import html
import json
import re
from types import SimpleNamespace
from urllib.parse import urlparse

import requests
from flask import make_response, request

try:
    import markdown  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised when dependency missing
    def _fallback_inline(text):
        text = html.escape(text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        return text

    def _render_list_item(content):
        content = content.strip()
        content = re.sub(r'^\[[ xX]\]\s*', '', content)
        return _fallback_inline(content)

    def _fallback_markdown(text, extensions=None, output_format=None):
        lines = text.splitlines()
        html_lines = []
        paragraph_lines = []
        in_list = False
        in_code = False
        code_lang = ''

        def flush_paragraph():
            nonlocal paragraph_lines
            if paragraph_lines:
                html_lines.append(f'<p>{_fallback_inline(" ".join(paragraph_lines))}</p>')
                paragraph_lines = []

        def flush_list():
            nonlocal in_list
            if in_list:
                html_lines.append('</ul>')
                in_list = False

        def close_code_block():
            nonlocal in_code
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False

        for raw_line in lines:
            line = raw_line.rstrip('\n')

            if in_code:
                if line.strip().startswith('```'):
                    close_code_block()
                else:
                    html_lines.append(html.escape(raw_line))
                continue

            stripped = line.lstrip()

            if not stripped:
                flush_paragraph()
                flush_list()
                continue

            if stripped.startswith('```'):
                flush_paragraph()
                flush_list()
                code_lang = stripped.strip('`').strip()
                lang = code_lang.split(None, 1)[0] if code_lang else ''
                lang_attr = f' class="language-{lang}"' if lang else ''
                html_lines.append(f'<pre><code{lang_attr}>')
                in_code = True
                continue

            if stripped.startswith('#'):
                flush_paragraph()
                flush_list()
                level = min(len(stripped.split(' ')[0]), 6)
                content = stripped[level:].strip()
                html_lines.append(f'<h{level}>{_fallback_inline(content)}</h{level}>')
                continue

            if stripped.startswith('>'):
                flush_paragraph()
                flush_list()
                html_lines.append(f'<blockquote>{_fallback_inline(stripped[1:].strip())}</blockquote>')
                continue

            if stripped.startswith(('-', '*')) and len(stripped) > 2 and stripped[1] == ' ':
                flush_paragraph()
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                html_lines.append(f'<li>{_render_list_item(stripped[2:])}</li>')
                continue

            paragraph_lines.append(line.strip())

        close_code_block()
        flush_paragraph()
        flush_list()

        return '\n'.join(html_lines)

    markdown = SimpleNamespace(markdown=_fallback_markdown)

try:
    from db_access import (
        create_cid_record,
        get_cid_by_path,
        get_user_servers,
        get_user_variables,
        get_user_secrets,
    )
except (RuntimeError, ImportError):
    create_cid_record = None
    get_cid_by_path = None
    get_user_servers = None
    get_user_variables = None
    get_user_secrets = None


def _ensure_db_access():
    global create_cid_record, get_cid_by_path, get_user_servers, get_user_variables, get_user_secrets
    if None in (create_cid_record, get_cid_by_path, get_user_servers, get_user_variables, get_user_secrets):
        from db_access import (
            create_cid_record as _create_cid_record,
            get_cid_by_path as _get_cid_by_path,
            get_user_servers as _get_user_servers,
            get_user_variables as _get_user_variables,
            get_user_secrets as _get_user_secrets,
        )

        if create_cid_record is None:
            create_cid_record = _create_cid_record
        if get_cid_by_path is None:
            get_cid_by_path = _get_cid_by_path
        if get_user_servers is None:
            get_user_servers = _get_user_servers
        if get_user_variables is None:
            get_user_variables = _get_user_variables
        if get_user_secrets is None:
            get_user_secrets = _get_user_secrets

# ============================================================================
# CID GENERATION AND STORAGE HELPERS
# ============================================================================

def generate_cid(file_data):
    """Generate a simple CID-like hash from file data only"""
    hasher = hashlib.sha256()
    hasher.update(file_data)
    sha256_hash = hasher.digest()

    # Use URL-safe base64 without padding as the CID string
    encoded = base64.urlsafe_b64encode(sha256_hash).decode('ascii').rstrip('=')
    return encoded


def process_file_upload(form):
    """Process file upload from form and return file content and filename"""
    uploaded_file = form.file.data
    file_content = uploaded_file.read()
    filename = uploaded_file.filename or 'upload'
    return file_content, filename


def process_text_upload(form):
    """Process text upload from form and return file content"""
    text_content = form.text_content.data
    file_content = text_content.encode('utf-8')
    return file_content


def process_url_upload(form):
    """Process URL upload from form by downloading content and return file content and MIME type"""
    url = form.url.data.strip()

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, timeout=30, headers=headers, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('content-type', 'application/octet-stream')
        mime_type = content_type.split(';')[0].strip().lower()

        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 100 * 1024 * 1024:
            raise ValueError("File too large (>100MB)")

        file_content = b''
        downloaded_size = 0
        max_size = 100 * 1024 * 1024

        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                downloaded_size += len(chunk)
                if downloaded_size > max_size:
                    raise ValueError("File too large (>100MB)")
                file_content += chunk

        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]

        if not filename or '.' not in filename:
            extension = get_extension_from_mime_type(mime_type)
            if extension:
                filename = f"download{extension}"
            else:
                filename = "download"

        return file_content, mime_type

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to download from URL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing URL: {str(e)}")


def save_server_definition_as_cid(definition, user_id):
    """Save server definition as CID and return the CID string"""
    _ensure_db_access()
    definition_bytes = definition.encode('utf-8')
    cid = generate_cid(definition_bytes)

    content = get_cid_by_path(f"/{cid}")
    if not content:
        create_cid_record(cid, definition_bytes, user_id)

    return cid


def store_cid_from_json(json_content, user_id):
    """Store JSON content in a CID record and return the CID"""
    json_bytes = json_content.encode('utf-8')
    return store_cid_from_bytes(json_bytes, user_id)

def store_cid_from_bytes(bytes, user_id):
    """Store content in a CID record and return the CID"""
    _ensure_db_access()
    cid = generate_cid(bytes)

    content = get_cid_by_path(f"/{cid}")
    if not content:
        create_cid_record(cid, bytes, user_id)

    return cid

# ============================================================================
# DEFINITIONS CID HELPERS
# ============================================================================

def generate_all_server_definitions_json(user_id):
    """Generate JSON containing all server definitions for a user"""
    _ensure_db_access()
    servers = get_user_servers(user_id)

    server_definitions = {}
    for server in servers:
        server_definitions[server.name] = server.definition

    return json.dumps(server_definitions, indent=2, sort_keys=True)


def store_server_definitions_cid(user_id):
    """Store all server definitions as JSON in a CID and return the CID path"""
    _ensure_db_access()
    json_content = generate_all_server_definitions_json(user_id)
    return store_cid_from_json(json_content, user_id)


def get_current_server_definitions_cid(user_id):
    """Get the CID path for the current server definitions JSON"""
    _ensure_db_access()
    json_content = generate_all_server_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid = generate_cid(json_bytes)

    content = get_cid_by_path(f"/{cid}")
    if content:
        return cid
    return store_server_definitions_cid(user_id)


def generate_all_variable_definitions_json(user_id):
    """Generate JSON containing all variable definitions for a user"""
    _ensure_db_access()
    variables = get_user_variables(user_id)

    variable_definitions = {}
    for variable in variables:
        variable_definitions[variable.name] = variable.definition

    return json.dumps(variable_definitions, indent=2, sort_keys=True)


def store_variable_definitions_cid(user_id):
    """Store all variable definitions as JSON in a CID and return the CID path"""
    _ensure_db_access()
    json_content = generate_all_variable_definitions_json(user_id)
    return store_cid_from_json(json_content, user_id)


def get_current_variable_definitions_cid(user_id):
    """Get the CID path for the current variable definitions JSON"""
    _ensure_db_access()
    json_content = generate_all_variable_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid = generate_cid(json_bytes)

    content = get_cid_by_path(f"/{cid}")
    if content:
        return cid
    return store_variable_definitions_cid(user_id)


def generate_all_secret_definitions_json(user_id):
    """Generate JSON containing all secret definitions for a user"""
    _ensure_db_access()
    secrets = get_user_secrets(user_id)

    secret_definitions = {}
    for secret in secrets:
        secret_definitions[secret.name] = secret.definition

    return json.dumps(secret_definitions, indent=2, sort_keys=True)


def store_secret_definitions_cid(user_id):
    """Store all secret definitions as JSON in a CID and return the CID path"""
    _ensure_db_access()
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid = generate_cid(json_bytes)

    content = get_cid_by_path(f"/{cid}")
    if not content:
        create_cid_record(cid, json_bytes, user_id)

    return cid


def get_current_secret_definitions_cid(user_id):
    """Get the CID path for the current secret definitions JSON"""
    _ensure_db_access()
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid = generate_cid(json_bytes)

    content = get_cid_by_path(f"/{cid}")
    if content:
        return cid

    return store_secret_definitions_cid(user_id)


# ============================================================================
# MIME TYPE AND CID SERVING HELPERS
# ============================================================================

EXTENSION_TO_MIME = {
    'html': 'text/html',
    'htm': 'text/html',
    'txt': 'text/plain',
    'css': 'text/css',
    'js': 'application/javascript',
    'json': 'application/json',
    'xml': 'application/xml',
    'pdf': 'application/pdf',
    'zip': 'application/zip',
    'tar': 'application/x-tar',
    'gz': 'application/gzip',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'ogg': 'audio/ogg',
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'avi': 'video/x-msvideo',
    'mov': 'video/quicktime',
    'md': 'text/markdown',
    'csv': 'text/csv',
    'py': 'text/x-python',
    'java': 'text/x-java-source',
    'c': 'text/x-c',
    'cpp': 'text/x-c++',
    'h': 'text/x-c',
    'hpp': 'text/x-c++',
    'sh': 'application/x-sh',
    'bat': 'application/x-msdos-program',
    'exe': 'application/x-msdownload',
    'dmg': 'application/x-apple-diskimage',
    'deb': 'application/vnd.debian.binary-package',
    'rpm': 'application/x-rpm'
}

MIME_TO_EXTENSION = {}
for ext, mime in EXTENSION_TO_MIME.items():
    if mime not in MIME_TO_EXTENSION:
        MIME_TO_EXTENSION[mime] = ext


_MARKDOWN_EXTENSIONS = [
    'extra',
    'admonition',
    'sane_lists',
]

_MARKDOWN_INDICATOR_PATTERNS = [
    re.compile(r'(^|\n)#{1,6}\s+\S'),
    re.compile(r'(^|\n)(?:\*|-|\+)\s+\S'),
    re.compile(r'(^|\n)\d+\.\s+\S'),
    re.compile(r'(^|\n)>\s+\S'),
    re.compile(r'```'),
    re.compile(r'\[[^\]]+\]\([^\)]+\)'),
    re.compile(r'!\[[^\]]*\]\([^\)]+\)'),
    re.compile(r'(^|\n)[^\n]+\n[=-]{3,}\s*(\n|$)'),
]

_INLINE_BOLD_PATTERN = re.compile(r'\*\*(?=\S)(.+?)(?<=\S)\*\*')
_INLINE_ITALIC_PATTERN = re.compile(r'(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)')
_INLINE_CODE_PATTERN = re.compile(r'`[^`\n]+`')


def _decode_text_safely(data):
    """Decode bytes as UTF-8 if possible, returning None on failure."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return None


def _count_bullet_lines(lines):
    return sum(1 for line in lines if line.lstrip().startswith(('- ', '* ', '+ ')))


def _looks_like_markdown(text):
    """Heuristically determine whether text is likely Markdown content."""
    if not text or not text.strip():
        return False

    if '\x00' in text:
        return False

    indicator_hits = sum(1 for pattern in _MARKDOWN_INDICATOR_PATTERNS if pattern.search(text))

    inline_format_score = sum(
        1
        for pattern in (_INLINE_BOLD_PATTERN, _INLINE_ITALIC_PATTERN, _INLINE_CODE_PATTERN)
        if pattern.search(text)
    )

    if indicator_hits + inline_format_score >= 2:
        return True

    lines = text.strip().splitlines()
    if not lines:
        return False

    if lines[0].startswith('# '):
        return True

    if len(lines) > 1 and set(lines[1].strip()) in ({'='}, {'-'}):
        return True

    if _count_bullet_lines(lines) >= 2:
        return True

    return False


def _extract_markdown_title(text):
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            return stripped.lstrip('#').strip() or 'Document'
    return 'Document'


def _render_markdown_document(text):
    """Render Markdown text to a standalone HTML document."""
    body = markdown.markdown(text, extensions=_MARKDOWN_EXTENSIONS, output_format='html5')
    title = _extract_markdown_title(text)
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        f"  <title>{title}</title>\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "  <style>\n"
        "    body {\n"
        "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;\n"
        "      margin: 0;\n"
        "      padding: 2rem;\n"
        "      background: #f7f7f8;\n"
        "      color: #111827;\n"
        "    }\n"
        "    .markdown-body {\n"
        "      max-width: 860px;\n"
        "      margin: 0 auto;\n"
        "      background: #fff;\n"
        "      padding: 2rem 3rem;\n"
        "      border-radius: 12px;\n"
        "      box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);\n"
        "    }\n"
        "    pre {\n"
        "      background: #0f172a;\n"
        "      color: #f8fafc;\n"
        "      padding: 1rem;\n"
        "      border-radius: 8px;\n"
        "      overflow-x: auto;\n"
        "    }\n"
        "    code {\n"
        "      background: rgba(15, 23, 42, 0.08);\n"
        "      padding: 0.15rem 0.35rem;\n"
        "      border-radius: 4px;\n"
        "      font-size: 0.95em;\n"
        "    }\n"
        "    table {\n"
        "      border-collapse: collapse;\n"
        "      width: 100%;\n"
        "      margin: 1.5rem 0;\n"
        "    }\n"
        "    th, td {\n"
        "      border: 1px solid #e2e8f0;\n"
        "      padding: 0.6rem 0.75rem;\n"
        "      text-align: left;\n"
        "    }\n"
        "    blockquote {\n"
        "      border-left: 4px solid #3b82f6;\n"
        "      padding-left: 1rem;\n"
        "      color: #1f2937;\n"
        "      background: rgba(59, 130, 246, 0.08);\n"
        "    }\n"
        "    .admonition {\n"
        "      border-left: 4px solid #7c3aed;\n"
        "      background: rgba(124, 58, 237, 0.08);\n"
        "      padding: 1rem 1.25rem;\n"
        "      border-radius: 8px;\n"
        "      margin: 1.5rem 0;\n"
        "    }\n"
        "    .admonition-title {\n"
        "      font-weight: 600;\n"
        "      margin-bottom: 0.5rem;\n"
        "    }\n"
        "    img, iframe {\n"
        "      max-width: 100%;\n"
        "      border-radius: 8px;\n"
        "      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.12);\n"
        "    }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <main class=\"markdown-body\">\n"
        f"  {body}\n"
        "  </main>\n"
        "</body>\n"
        "</html>\n"
    )


def _maybe_render_markdown(data, *, path_has_extension):
    if path_has_extension:
        return data, False

    text = _decode_text_safely(data)
    if text is None:
        return data, False

    if not _looks_like_markdown(text):
        return data, False

    html_document = _render_markdown_document(text)
    return html_document.encode('utf-8'), True


def get_mime_type_from_extension(path):
    """Determine MIME type from file extension in URL path"""
    if '.' in path:
        extension = path.split('.')[-1].lower()
        return EXTENSION_TO_MIME.get(extension, 'application/octet-stream')
    return 'application/octet-stream'


def get_extension_from_mime_type(content_type):
    """Get file extension from MIME type"""
    base_mime = content_type.split(';')[0].strip().lower()
    return MIME_TO_EXTENSION.get(base_mime, '')


def extract_filename_from_cid_path(path):
    """Extract filename from CID path for content disposition header."""
    if path.startswith('/'):
        path = path[1:]

    if not path or path in ['.', '..']:
        return None

    parts = path.split('.')

    if len(parts) < 3:
        return None

    filename_parts = parts[1:]
    filename = '.'.join(filename_parts)

    return filename


def serve_cid_content(cid_content, path):
    """Serve CID content with appropriate headers and caching"""
    if cid_content is None or cid_content.file_data is None:
        return None

    cid = path[1:] if path.startswith('/') else path

    content_type = get_mime_type_from_extension(path)
    filename_part = path.rsplit('/', 1)[-1]
    has_extension = '.' in filename_part

    response_body = cid_content.file_data
    if content_type == 'application/octet-stream':
        response_body, rendered = _maybe_render_markdown(response_body, path_has_extension=has_extension)
        if rendered:
            content_type = 'text/html'

    etag = f'"{cid.split(".")[0]}"'
    if request.headers.get('If-None-Match') == etag:
        response = make_response('', 304)
        response.headers['ETag'] = etag
        return response

    if request.headers.get('If-Modified-Since'):
        response = make_response('', 304)
        response.headers['ETag'] = etag
        response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return response

    response = make_response(response_body)
    response.headers['Content-Type'] = content_type
    response.headers['Content-Length'] = len(response_body)

    filename = extract_filename_from_cid_path(path)
    if filename:
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    response.headers['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'

    return response
