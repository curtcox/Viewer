import base64
import hashlib
import json
import re
import textwrap
from urllib.parse import urlparse

import requests
from flask import make_response, request

try:
    import markdown  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - exercised when dependency missing
    raise RuntimeError(
        "Missing optional dependency 'Markdown'. Run './install' or "
        "'pip install -r requirements.txt' before running the application or tests."
    ) from exc

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

_FORMDOWN_SCRIPT_URL = "https://unpkg.com/@formdown/ui@latest/dist/standalone.js"
_FORMDOWN_MARKUP_PATTERNS = [
    re.compile(r'<\s*formdown-', re.IGNORECASE),
    re.compile(r'data-formdown', re.IGNORECASE),
]

_FORMDOWN_FENCE_PATTERN = re.compile(
    r"(^|\n)```formdown\s*\n(.*?)(?:\n```)(?=\s*(\n|$))",
    re.IGNORECASE | re.DOTALL,
)


def _contains_formdown_markup(html_text: str) -> bool:
    return any(pattern.search(html_text) for pattern in _FORMDOWN_MARKUP_PATTERNS)


def _expand_formdown_fences(text: str) -> str:
    """Convert formdown code fences into embeds that the loader understands."""

    def _replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        body = textwrap.dedent(match.group(2)).strip()
        if not body:
            return prefix

        form_block = (
            "<div data-formdown>\n"
            "  <script type=\"text/formdown\">\n"
            f"{body}\n"
            "  </script>\n"
            "</div>\n"
        )
        return f"{prefix}{form_block}"

    return _FORMDOWN_FENCE_PATTERN.sub(_replace, text)

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


_GITHUB_RELATIVE_LINK_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")

_GITHUB_RELATIVE_LINK_PATH_SANITIZER = re.compile(r"[^A-Za-z0-9._/\-]+")
_GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER = re.compile(r"[^a-z0-9\-]+")


def _normalize_github_relative_link_target_v2(raw_target: str) -> str | None:
    """Normalize GitHub-style relative link targets (version 2 semantics)."""

    if not raw_target:
        return None

    target = raw_target.strip()
    if not target:
        return None

    # Allow optional pipe syntax ``[[target|label]]`` and pick the first segment
    primary = target.split('|', 1)[0].strip()
    if not primary:
        return None

    page_part, _, anchor_part = primary.partition('#')

    normalized_path = ""
    if page_part:
        preserve_trailing_slash = page_part.rstrip().endswith('/')
        prepared = re.sub(r"\s+", "-", page_part.strip())
        cleaned = _GITHUB_RELATIVE_LINK_PATH_SANITIZER.sub('', prepared)
        segments = [segment for segment in cleaned.split('/') if segment]
        if not segments:
            normalized_path = ""
        else:
            normalized_segments = [segment.lower() for segment in segments]
            normalized_path = '/' + '/'.join(normalized_segments)
            if preserve_trailing_slash:
                normalized_path += '/'

    anchor_fragment = ""
    if anchor_part:
        anchor_slug = anchor_part.strip().lower()
        anchor_slug = re.sub(r"\s+", '-', anchor_slug)
        anchor_slug = _GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER.sub('', anchor_slug)
        anchor_slug = anchor_slug.strip('-')
        if anchor_slug:
            anchor_fragment = f'#{anchor_slug}'

    if normalized_path and anchor_fragment:
        return f'{normalized_path}{anchor_fragment}'
    if normalized_path:
        return normalized_path
    if anchor_fragment:
        return anchor_fragment
    return None


def _convert_github_relative_links(text: str) -> str:
    """Rewrite GitHub-style ``[[link]]`` syntax to standard Markdown links."""

    preserved_fences: list[tuple[str, str]] = []

    def _preserve_formdown(match: re.Match[str]) -> str:
        placeholder = f"__FORMDOWN_BLOCK_{len(preserved_fences)}__"
        preserved_fences.append((placeholder, match.group(0)))
        return placeholder

    def replacement(match: re.Match[str]) -> str:
        inner = match.group(1)
        if not inner:
            return match.group(0)

        label, target = inner, inner
        if '|' in inner:
            target, label = (part.strip() for part in inner.split('|', 1))
        else:
            label = inner.strip()
            target = label

        normalized_target = _normalize_github_relative_link_target_v2(target)
        display_text = label.strip() or target.strip()
        if not normalized_target or not display_text:
            return match.group(0)

        return f"[{display_text}]({normalized_target})"

    protected_text = _FORMDOWN_FENCE_PATTERN.sub(_preserve_formdown, text)
    converted = _GITHUB_RELATIVE_LINK_PATTERN.sub(replacement, protected_text)
    for placeholder, original in preserved_fences:
        converted = converted.replace(placeholder, original, 1)
    return converted


def _render_markdown_document(text):
    """Render Markdown text to a standalone HTML document."""
    converted = _convert_github_relative_links(text)
    has_formdown_fence = bool(_FORMDOWN_FENCE_PATTERN.search(converted))
    converted = _expand_formdown_fences(converted)
    body = markdown.markdown(converted, extensions=_MARKDOWN_EXTENSIONS, output_format='html5')
    formdown_script_block = ""
    if has_formdown_fence or _contains_formdown_markup(body):
        formdown_script_block = (
            f"  <script src=\"{_FORMDOWN_SCRIPT_URL}\" async defer data-formdown-loader></script>\n"
        )
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
        f"{formdown_script_block}"
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
    explicit_markdown_request = filename_part.lower().endswith('.md.html')

    response_body = cid_content.file_data
    if explicit_markdown_request:
        text = _decode_text_safely(response_body)
        if text is not None:
            response_body = _render_markdown_document(text).encode('utf-8')
            content_type = 'text/html'
    elif content_type == 'application/octet-stream':
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
    if filename and not explicit_markdown_request:
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = cid_content.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    response.headers['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'

    return response
