import base64
import binascii
import html
import io
import hashlib
import json
import re
import textwrap
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from flask import make_response, render_template, request

try:
    import qrcode  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover - exercised when dependency missing
    qrcode = None  # type: ignore[assignment]
    _qrcode_import_error = exc
else:
    _qrcode_import_error = None

from cid_presenter import cid_path, format_cid
from formdown_renderer import render_formdown_html


CID_CHARACTER_CLASS = "A-Za-z0-9_-"
CID_LENGTH_PREFIX_BYTES = 6
CID_LENGTH_PREFIX_CHARS = 8
SHA512_DIGEST_SIZE = hashlib.sha512().digest_size
CID_SHA512_CHARS = 86
CID_LENGTH = CID_LENGTH_PREFIX_CHARS + CID_SHA512_CHARS
CID_MIN_REFERENCE_LENGTH = 6
CID_STRICT_MIN_LENGTH = 30

MAX_CONTENT_LENGTH = (1 << (CID_LENGTH_PREFIX_BYTES * 8)) - 1

CID_NORMALIZED_PATTERN = re.compile(rf"^[{CID_CHARACTER_CLASS}]{{{CID_LENGTH}}}$")
CID_REFERENCE_PATTERN = re.compile(rf"^[{CID_CHARACTER_CLASS}]{{{CID_MIN_REFERENCE_LENGTH},}}$")
CID_STRICT_PATTERN = re.compile(rf"^[{CID_CHARACTER_CLASS}]{{{CID_STRICT_MIN_LENGTH},}}$")
CID_PATH_CAPTURE_PATTERN = re.compile(
    rf"/([{CID_CHARACTER_CLASS}]{{{CID_MIN_REFERENCE_LENGTH},}})(?:\\.[A-Za-z0-9]+)?"
)

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


def _normalize_component(value: Optional[str]) -> str:
    """Return a normalized CID component without leading slashes or whitespace."""
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    normalized = normalized.lstrip("/")
    if "/" in normalized:
        return ""
    return normalized


def is_probable_cid_component(value: Optional[str]) -> bool:
    """Return True if the value could be a CID or CID prefix."""
    normalized = _normalize_component(value)
    if not normalized or "." in normalized:
        return False
    return bool(CID_REFERENCE_PATTERN.fullmatch(normalized))


def is_strict_cid_candidate(value: Optional[str]) -> bool:
    """Return True if the value is a strong candidate for a generated CID."""
    normalized = _normalize_component(value)
    if not normalized or "." in normalized:
        return False
    return bool(CID_STRICT_PATTERN.fullmatch(normalized))


def is_normalized_cid(value: Optional[str]) -> bool:
    """Return True if the value is exactly formatted like a generated CID."""
    normalized = _normalize_component(value)
    if not normalized or "." in normalized:
        return False
    return bool(CID_NORMALIZED_PATTERN.fullmatch(normalized))


def split_cid_path(value: Optional[str]) -> Optional[Tuple[str, Optional[str]]]:
    """Return the CID value and optional extension extracted from a path."""
    if value is None:
        return None

    slug = value.strip()
    if not slug:
        return None

    slug = slug.split("?", 1)[0]
    slug = slug.split("#", 1)[0]
    if not slug:
        return None

    if slug.startswith("/"):
        slug = slug[1:]

    if not slug or "/" in slug:
        return None

    cid_part = slug
    extension: Optional[str] = None
    if "." in slug:
        cid_part, extension = slug.split(".", 1)
        extension = extension or None

    if not is_probable_cid_component(cid_part):
        return None

    return cid_part, extension

# ============================================================================
# CID GENERATION AND STORAGE HELPERS
# ============================================================================

def _base64url_encode(data: bytes) -> str:
    """Return URL-safe base64 representation without padding."""

    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    """Decode URL-safe base64 data that may omit padding."""

    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encode_cid_length(length: int) -> str:
    """Encode the content length into the CID prefix."""

    if length < 0 or length > MAX_CONTENT_LENGTH:
        raise ValueError(
            f"CID content length must be between 0 and {MAX_CONTENT_LENGTH} bytes"
        )

    encoded = _base64url_encode(length.to_bytes(CID_LENGTH_PREFIX_BYTES, "big"))
    if len(encoded) != CID_LENGTH_PREFIX_CHARS:
        raise ValueError("Encoded length prefix must be 8 characters long")
    return encoded


def parse_cid_components(cid: str) -> Tuple[int, bytes]:
    """Return the encoded content length and SHA-512 digest for a CID.

    Raises ValueError if the CID is malformed or not in the normalized format.
    """

    normalized = _normalize_component(cid)
    if len(normalized) != CID_LENGTH:
        raise ValueError("CID must be normalized to 94 characters")

    length_part = normalized[:CID_LENGTH_PREFIX_CHARS]
    digest_part = normalized[CID_LENGTH_PREFIX_CHARS:]

    try:
        length_bytes = _base64url_decode(length_part)
        digest_bytes = _base64url_decode(digest_part)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("CID contains invalid base64 encoding") from exc

    if len(length_bytes) != CID_LENGTH_PREFIX_BYTES:
        raise ValueError("CID length prefix has an unexpected size")
    if len(digest_bytes) != SHA512_DIGEST_SIZE:
        raise ValueError("CID digest has an unexpected size")

    return int.from_bytes(length_bytes, "big"), digest_bytes


def generate_cid(file_data):
    """Generate a CID consisting of a length prefix and SHA-512 digest."""

    content_length = len(file_data)
    length_part = encode_cid_length(content_length)

    digest = hashlib.sha512(file_data).digest()
    digest_part = _base64url_encode(digest)

    if len(digest_part) != CID_SHA512_CHARS:
        raise ValueError("SHA-512 digest must encode to 86 characters")

    return f"{length_part}{digest_part}"


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
    cid_value = format_cid(generate_cid(definition_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not content:
        create_cid_record(cid_value, definition_bytes, user_id)

    return cid_value


def store_cid_from_json(json_content, user_id):
    """Store JSON content in a CID record and return the CID"""
    json_bytes = json_content.encode('utf-8')
    return store_cid_from_bytes(json_bytes, user_id)

def store_cid_from_bytes(bytes, user_id):
    """Store content in a CID record and return the CID"""
    _ensure_db_access()
    cid_value = format_cid(generate_cid(bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not content:
        create_cid_record(cid_value, bytes, user_id)

    return cid_value

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
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if content:
        return cid_value
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
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if content:
        return cid_value
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
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not content:
        create_cid_record(cid_value, json_bytes, user_id)

    return cid_value


def get_current_secret_definitions_cid(user_id):
    """Get the CID path for the current secret definitions JSON"""
    _ensure_db_access()
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if content:
        return cid_value

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
    'elm': 'text/plain',
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


_ELM_INDICATOR_PATTERNS = [
    re.compile(r'^\s*module\s+[A-Z][A-Za-z0-9_.]*\s+exposing', re.MULTILINE),
    re.compile(r'^\s*import\s+Html(?:\s+exposing\b|\s*$)', re.MULTILINE),
    re.compile(r'^\s*import\s+Browser', re.MULTILINE),
    re.compile(r'^\s*main\s*=\s*', re.MULTILINE),
    re.compile(r'Html\.text\s*"', re.MULTILINE),
]


def _looks_like_elm(text: str) -> bool:
    """Heuristically determine if the provided text resembles Elm source."""

    normalized = (text or "").strip()
    if not normalized:
        return False

    # Simple guardrail to avoid mis-classifying HTML documents as Elm programs.
    if normalized.lstrip().startswith("<!DOCTYPE"):
        return False

    matches = sum(1 for pattern in _ELM_INDICATOR_PATTERNS if pattern.search(normalized))
    return matches >= 2


def _render_elm_document(source: str) -> str:
    """Return HTML that attempts to compile and render Elm source code."""

    escaped_source = html.escape(source)
    source_json = json.dumps(source)

    template = textwrap.dedent(
        """\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <title>Elm Viewer</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            body {
              font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              margin: 0;
              background: #0f172a;
              color: #e2e8f0;
              padding: 2.5rem 1.75rem;
            }
            .elm-layout {
              display: grid;
              gap: 1.5rem;
              max-width: 960px;
              margin: 0 auto;
            }
            .elm-card {
              background: rgba(15, 23, 42, 0.72);
              border-radius: 16px;
              padding: 1.75rem;
              box-shadow: 0 24px 55px rgba(15, 23, 42, 0.45);
            }
            .elm-output {
              background: rgba(15, 23, 42, 0.45);
              border-radius: 12px;
              border: 1px solid rgba(148, 163, 184, 0.2);
              min-height: 200px;
              display: grid;
              place-items: center;
              text-align: center;
              padding: 1.25rem;
              color: #0f172a;
              background-image: radial-gradient(circle at top left, rgba(59, 130, 246, 0.18), transparent 55%),
                                radial-gradient(circle at bottom right, rgba(236, 72, 153, 0.18), transparent 45%);
            }
            .elm-source {
              background: #0f172a;
              border-radius: 12px;
              border: 1px solid rgba(148, 163, 184, 0.35);
              padding: 1.25rem;
              overflow-x: auto;
              font-family: "JetBrains Mono", "Fira Code", "Source Code Pro", monospace;
              line-height: 1.6;
            }
            .elm-actions {
              margin-top: 1rem;
              display: flex;
              flex-wrap: wrap;
              gap: 0.75rem;
            }
            .elm-actions a {
              padding: 0.55rem 1.1rem;
              border-radius: 999px;
              text-decoration: none;
              font-weight: 600;
              color: #cbd5f5;
              background: rgba(59, 130, 246, 0.28);
              border: 1px solid rgba(59, 130, 246, 0.35);
            }
            .elm-actions a:hover {
              background: rgba(59, 130, 246, 0.38);
            }
            .elm-status {
              margin-bottom: 1rem;
              font-size: 0.95rem;
              color: rgba(226, 232, 240, 0.85);
            }
            .elm-error {
              margin-top: 1rem;
              padding: 1rem 1.25rem;
              border-radius: 12px;
              background: rgba(248, 113, 113, 0.14);
              border: 1px solid rgba(248, 113, 113, 0.28);
              color: #fecaca;
              font-size: 0.95rem;
            }
            iframe.elm-frame {
              width: 100%;
              min-height: 220px;
              border: none;
              border-radius: 12px;
              background: #fff;
            }
          </style>
        </head>
        <body>
          <main class="elm-layout">
            <section class="elm-card">
              <h1>Elm Output</h1>
              <p id="elm-status" class="elm-status" role="status">Attempting to compile Elm source…</p>
              <div id="elm-app" class="elm-output">The Elm application will appear here.</div>
            </section>
            <section class="elm-card">
              <h2>Elm Source</h2>
              <pre class="elm-source"><code>__ESCAPED_SOURCE__</code></pre>
              <div class="elm-actions">
                <a href="https://ellie-app.com/new" target="_blank" rel="noopener">Open Ellie Playground</a>
                <a href="https://elm-lang.org/examples" target="_blank" rel="noopener">Explore Elm Examples</a>
              </div>
            </section>
          </main>
          <script type="module">
            const source = __SOURCE_JSON__;
            const statusNode = document.getElementById("elm-status");
            const container = document.getElementById("elm-app");

            async function renderElm() {
              if (!window.fetch) {
                statusNode.textContent = "This browser does not support the Fetch API needed to compile Elm automatically.";
                return;
              }

              statusNode.textContent = "Contacting the Ellie compiler service…";
              try {
                const response = await fetch("https://ellie-app.com/api/compile", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ code: source, optimize: true })
                });

                if (!response.ok) {
                  throw new Error(`Compiler request failed with status ${response.status}`);
                }

                const payload = await response.json();
                const generatedHtml = payload?.generatedFiles?.["index.html"] || payload?.output?.html || payload?.output;
                const compiledJs = payload?.generatedFiles?.["elm.js"] || payload?.output?.js || payload?.code;

                if (generatedHtml) {
                  const frame = document.createElement("iframe");
                  frame.className = "elm-frame";
                  frame.srcdoc = generatedHtml;
                  container.replaceChildren(frame);
                  statusNode.textContent = "Rendered Elm output using Ellie.";
                  return;
                }

                if (compiledJs) {
                  const frame = document.createElement("iframe");
                  frame.className = "elm-frame";
                  container.replaceChildren(frame);
                  const doc = frame.contentDocument;
                  if (!doc) {
                    throw new Error("Unable to access iframe document for Elm output.");
                  }
                  doc.open();
                  doc.write("<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body><div id=\"elm-app\"></div></body></html>");
                  doc.close();
                  const script = doc.createElement("script");
                  script.type = "text/javascript";
                  script.textContent = `${compiledJs}\nElm.Main.init({ node: doc.getElementById('elm-app') });`;
                  doc.body.appendChild(script);
                  statusNode.textContent = "Rendered Elm output.";
                  return;
                }

                throw new Error("Ellie compiler returned an unexpected response.");
              } catch (error) {
                console.error("Elm rendering failed:", error);
                statusNode.textContent = "Unable to render Elm automatically.";
                const message = document.createElement("div");
                message.className = "elm-error";
                message.innerHTML = `Copy the Elm source below into <a href="https://ellie-app.com/new" target="_blank" rel="noopener">ellie-app.com/new</a> to run it manually.<br><br><strong>Details:</strong> ${error?.message || "Unknown error."}`;
                container.after(message);
              }
            }

            renderElm();
          </script>
        </body>
        </html>
        """
    )

    return (
        template
        .replace("__ESCAPED_SOURCE__", escaped_source)
        .replace("__SOURCE_JSON__", source_json)
    )

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

    return _GITHUB_RELATIVE_LINK_PATTERN.sub(replacement, text)


_FORMDOWN_FENCE_RE = re.compile(r"(^|\n)[ \t]*```formdown\s*\n(.*?)```", re.DOTALL)
_MERMAID_FENCE_RE = re.compile(r"(^|\n)([ \t]*)```mermaid\s*\n(.*?)```", re.DOTALL)


class MermaidRenderingError(RuntimeError):
    """Raised when a Mermaid diagram cannot be rendered."""


@dataclass
class MermaidRenderLocation:
    """Represents where a rendered Mermaid diagram is stored."""

    is_cid: bool
    value: str

    def img_src(self) -> str:
        if self.is_cid:
            path = cid_path(self.value, "svg") or f"/{self.value}.svg"
            return path
        return self.value


class _MermaidRenderer:
    """Render Mermaid diagrams through mermaid.ink and store them as CIDs."""

    _API_ENDPOINT = "https://mermaid.ink/svg"
    _REMOTE_SVG_BASE = "https://mermaid.ink/svg/"

    def __init__(self) -> None:
        self._session = requests.Session()
        self._cache: Dict[str, MermaidRenderLocation] = {}

    def render_html(self, source: str) -> str:
        normalized = (source or "").strip()
        if not normalized:
            raise MermaidRenderingError("Mermaid diagram was empty")

        cached = self._cache.get(normalized)
        if cached is not None:
            return self._build_html(cached, normalized)

        location: Optional[MermaidRenderLocation]
        try:
            svg_bytes = self._fetch_svg(normalized)
        except Exception:
            location = self._remote_location(normalized)
        else:
            if not svg_bytes:
                raise MermaidRenderingError("Mermaid renderer returned no data")

            location = self._store_svg(svg_bytes)
            if location is None:
                data_url = self._build_data_url(svg_bytes)
                location = MermaidRenderLocation(is_cid=False, value=data_url)

        if location is None:
            raise MermaidRenderingError("Mermaid renderer failed to produce an image")

        self._cache[normalized] = location
        return self._build_html(location, normalized)

    def _fetch_svg(self, source: str) -> bytes:
        response = self._session.post(
            self._API_ENDPOINT,
            data=source.encode("utf-8"),
            timeout=20,
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()
        return response.content

    def _store_svg(self, svg_bytes: bytes) -> Optional[MermaidRenderLocation]:
        try:
            _ensure_db_access()
            cid_value = format_cid(generate_cid(svg_bytes))
            path = cid_path(cid_value)
            if path and get_cid_by_path and get_cid_by_path(path):
                return MermaidRenderLocation(is_cid=True, value=cid_value)

            if create_cid_record is not None:
                create_cid_record(cid_value, svg_bytes, None)

            return MermaidRenderLocation(is_cid=True, value=cid_value)
        except Exception:
            return None

    @staticmethod
    def _build_data_url(svg_bytes: bytes) -> str:
        encoded = base64.b64encode(svg_bytes).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

    @staticmethod
    def _encode_source(source: str) -> str:
        return base64.urlsafe_b64encode(source.encode("utf-8")).decode("ascii")

    @classmethod
    def _remote_location(cls, source: str) -> Optional[MermaidRenderLocation]:
        encoded = cls._encode_source(source)
        remote_url = f"{cls._REMOTE_SVG_BASE}{encoded}"
        return MermaidRenderLocation(is_cid=False, value=remote_url)

    @classmethod
    def _build_html(cls, location: MermaidRenderLocation, source: str) -> str:
        escaped_src = html.escape(location.img_src(), quote=True)
        encoded_diagram = cls._encode_source(source)
        return (
            f'<figure class="mermaid-diagram" data-mermaid-source="{encoded_diagram}">\n'
            f'  <img src="{escaped_src}" alt="Mermaid diagram" loading="lazy" decoding="async">\n'
            f"</figure>\n"
        )


_mermaid_renderer = _MermaidRenderer()


def _replace_formdown_fences(text):
    """Replace ```formdown fences with rendered HTML forms."""

    found = False

    def _replacement(match):
        nonlocal found
        found = True
        prefix = match.group(1)
        inner = match.group(2).rstrip("\n")
        html = render_formdown_html(inner)
        if prefix:
            return f"{prefix}{html}"
        return html

    converted = _FORMDOWN_FENCE_RE.sub(_replacement, text)
    return converted, found


def _replace_mermaid_fences(text: str) -> Tuple[str, bool]:
    """Replace ```mermaid fences with rendered diagram figures."""

    found = False

    def _replacement(match: re.Match[str]) -> str:
        nonlocal found
        prefix = match.group(1)
        indent = match.group(2)
        diagram_source = (match.group(3) or "").rstrip("\n")
        try:
            figure_html = _mermaid_renderer.render_html(diagram_source)
        except MermaidRenderingError:
            return match.group(0)
        except Exception:
            return match.group(0)
        found = True
        return f"{prefix}{indent}{figure_html}"

    replaced = _MERMAID_FENCE_RE.sub(_replacement, text)
    return replaced, found


def _render_markdown_document(text):
    """Render Markdown text to a standalone HTML document."""
    converted = _convert_github_relative_links(text)
    converted, _ = _replace_mermaid_fences(converted)
    converted, has_formdown = _replace_formdown_fences(converted)
    body = markdown.markdown(converted, extensions=_MARKDOWN_EXTENSIONS, output_format='html5')
    title = _extract_markdown_title(text)
    formdown_script = ""
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        f"  <title>{title}</title>\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"{formdown_script}"
        "  <style>\n"
        "    body {\n"
        "      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;\n"
        "      margin: 0;\n"
        "      padding: 2rem;\n"
        "      background: #f7f7f8;\n"
        "      color: #111827;\n"
        "    }\n"
        "    .markdown-body {\n"
        "      max-width: none;\n"
        "      width: 100%;\n"
        "      margin: 0;\n"
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
        "    .mermaid-diagram {\n"
        "      margin: 2rem 0;\n"
        "      text-align: center;\n"
        "    }\n"
        "    .mermaid-diagram img {\n"
        "      display: inline-block;\n"
        "    }\n"
        "    .formdown-document {\n"
        "      margin: 2rem 0;\n"
        "      display: flex;\n"
        "      flex-direction: column;\n"
        "      gap: 1.5rem;\n"
        "    }\n"
        "    .formdown-form {\n"
        "      display: flex;\n"
        "      flex-direction: column;\n"
        "      gap: 1.5rem;\n"
        "      padding: 1.5rem;\n"
        "      border: 1px solid rgba(148, 163, 184, 0.35);\n"
        "      border-radius: 12px;\n"
        "      background: #f8fafc;\n"
        "    }\n"
        "    .formdown-field {\n"
        "      display: flex;\n"
        "      flex-direction: column;\n"
        "      gap: 0.5rem;\n"
        "    }\n"
        "    .formdown-field--choices {\n"
        "      gap: 0.75rem;\n"
        "    }\n"
        "    .formdown-heading {\n"
        "      font-weight: 600;\n"
        "      color: #0f172a;\n"
        "    }\n"
        "    .formdown-heading--form {\n"
        "      margin-bottom: 0;\n"
        "    }\n"
        "    .formdown-paragraph {\n"
        "      color: #475569;\n"
        "    }\n"
        "    .formdown-paragraph--form {\n"
        "      margin: 0;\n"
        "    }\n"
        "    .formdown-label {\n"
        "      font-weight: 600;\n"
        "      color: #0f172a;\n"
        "    }\n"
        "    .formdown-input {\n"
        "      display: block;\n"
        "      width: 100%;\n"
        "      padding: 0.5rem 0.75rem;\n"
        "      border-radius: 8px;\n"
        "      border: 1px solid rgba(148, 163, 184, 0.5);\n"
        "      font-size: 1rem;\n"
        "      color: #0f172a;\n"
        "      background: #fff;\n"
        "    }\n"
        "    .formdown-input:focus {\n"
        "      outline: 2px solid #3b82f6;\n"
        "      outline-offset: 1px;\n"
        "    }\n"
        "    .formdown-options {\n"
        "      display: flex;\n"
        "      flex-wrap: wrap;\n"
        "      gap: 0.75rem;\n"
        "    }\n"
        "    .formdown-options--vertical {\n"
        "      flex-direction: column;\n"
        "    }\n"
        "    .formdown-option {\n"
        "      display: inline-flex;\n"
        "      align-items: center;\n"
        "      gap: 0.5rem;\n"
        "      font-weight: 500;\n"
        "      color: #0f172a;\n"
        "    }\n"
        "    .formdown-option-label {\n"
        "      display: inline-block;\n"
        "    }\n"
        "    .formdown-help {\n"
        "      font-size: 0.875rem;\n"
        "      color: #64748b;\n"
        "    }\n"
        "    .formdown-separator {\n"
        "      border: none;\n"
        "      border-top: 1px solid rgba(148, 163, 184, 0.35);\n"
        "      margin: 0;\n"
        "    }\n"
        "    .formdown-button {\n"
        "      display: inline-flex;\n"
        "      align-items: center;\n"
        "      justify-content: center;\n"
        "      gap: 0.5rem;\n"
        "      border-radius: 8px;\n"
        "      padding: 0.5rem 1.25rem;\n"
        "      font-weight: 600;\n"
        "      cursor: pointer;\n"
        "      border: none;\n"
        "    }\n"
        "    .formdown-button--submit {\n"
        "      background: #2563eb;\n"
        "      color: #f8fafc;\n"
        "    }\n"
        "    .formdown-button--reset {\n"
        "      background: #e2e8f0;\n"
        "      color: #0f172a;\n"
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


def _generate_qr_data_url(target_url: str) -> str:
    """Return a data URL representing a QR code that encodes ``target_url``."""

    if qrcode is None:
        raise RuntimeError(
            "Missing optional dependency 'qrcode'. Run './install' or "
            "'pip install qrcode[pil]' before generating QR codes."
        ) from _qrcode_import_error

    qr_code = qrcode.QRCode(box_size=12, border=4)
    qr_code.add_data(target_url)
    qr_code.make(fit=True)
    qr_image = qr_code.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    qr_png_bytes = buffer.getvalue()
    return "data:image/png;base64," + base64.b64encode(qr_png_bytes).decode("ascii")


def serve_cid_content(cid_content, path):
    """Serve CID content with appropriate headers and caching"""
    if cid_content is None or cid_content.file_data is None:
        return None

    cid = path[1:] if path.startswith('/') else path

    content_type = get_mime_type_from_extension(path)
    filename_part = path.rsplit('/', 1)[-1]
    lower_filename = filename_part.lower()
    has_extension = '.' in filename_part
    explicit_markdown_request = lower_filename.endswith('.md.html')
    is_text_extension_request = lower_filename.endswith('.txt')
    is_qr_request = lower_filename.endswith('.qr')
    is_elm_source_request = lower_filename.endswith('.elm') and not lower_filename.endswith('.elm.html')
    force_elm_render_request = lower_filename.endswith('.elm.html')

    cid_path_attr = getattr(cid_content, 'path', None)
    normalized_cid = (cid_path_attr or '').lstrip('/')
    qr_cid = normalized_cid or (cid.rsplit('.qr', 1)[0] if is_qr_request else '')
    etag_source = normalized_cid or cid.split('.')[0]

    response_body = cid_content.file_data
    text_content = _decode_text_safely(response_body)

    if is_qr_request and qr_cid:
        qr_target_url = f"https://256t.org/{qr_cid}"
        qr_image_url = _generate_qr_data_url(qr_target_url)
        html = render_template(
            'cid_qr.html',
            title='CID QR Code',
            cid=qr_cid,
            qr_value=qr_target_url,
            qr_image_url=qr_image_url,
            cid_href=cid_path(qr_cid),
        )
        response_body = html.encode('utf-8')
        content_type = 'text/html; charset=utf-8'
    elif explicit_markdown_request:
        if text_content is not None:
            response_body = _render_markdown_document(text_content).encode('utf-8')
            content_type = 'text/html'
    elif is_elm_source_request:
        if text_content is not None:
            response_body = text_content.encode('utf-8')
            content_type = 'text/plain; charset=utf-8'
        else:
            content_type = 'application/octet-stream'
    elif is_text_extension_request:
        if text_content is not None:
            response_body = text_content.encode('utf-8')
            content_type = 'text/plain; charset=utf-8'
        else:
            content_type = 'application/octet-stream'
    else:
        should_render_elm = False
        elm_source = text_content

        if force_elm_render_request:
            if elm_source is None:
                elm_source = response_body.decode('utf-8', errors='replace')
            should_render_elm = True
        elif not has_extension and text_content is not None and _looks_like_elm(text_content):
            should_render_elm = True

        if should_render_elm and elm_source is not None:
            response_body = _render_elm_document(elm_source).encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        elif content_type == 'application/octet-stream':
            response_body, rendered = _maybe_render_markdown(response_body, path_has_extension=has_extension)
            if rendered:
                content_type = 'text/html'
            elif not has_extension:
                if text_content is not None:
                    response_body = text_content.encode('utf-8')
                    content_type = 'text/plain; charset=utf-8'
        elif content_type == 'text/plain':
            if text_content is not None:
                response_body = text_content.encode('utf-8')
                content_type = 'text/plain; charset=utf-8'

    etag = f'"{etag_source}"'
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
