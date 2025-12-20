"""Compatibility shim for cid_utils module.

This module maintains backward compatibility by re-exporting all functions
from the newly refactored modules.

DEPRECATED: This module is deprecated. Import from the specific modules instead:
- cid_core: CID generation, parsing, validation
- cid_storage: Database operations and storage helpers
- content_rendering: Markdown, Mermaid, Formdown rendering
- mime_utils: MIME type detection and extension mapping
- upload_handlers: File/text/URL upload processing
- content_serving: HTTP response generation
"""

# ruff: noqa: F401, F811
# Re-export everything from the new modules for backward compatibility

# pylint: disable=unused-import,wildcard-import

# Core CID functionality
from cid_core import (
    CID_CHARACTER_CLASS,
    CID_LENGTH,
    CID_LENGTH_PREFIX_BYTES,
    CID_LENGTH_PREFIX_CHARS,
    CID_MIN_LENGTH,
    CID_MIN_REFERENCE_LENGTH,
    CID_NORMALIZED_PATTERN,
    CID_PATH_CAPTURE_PATTERN,
    CID_REFERENCE_PATTERN,
    CID_SHA512_CHARS,
    CID_STRICT_MIN_LENGTH,
    CID_STRICT_PATTERN,
    DIRECT_CONTENT_EMBED_LIMIT,
    MAX_CONTENT_LENGTH,
    SHA512_DIGEST_SIZE,
    base64url_decode as _base64url_decode,
    base64url_encode as _base64url_encode,
    encode_cid_length,
    generate_cid,
    is_normalized_cid,
    is_probable_cid_component,
    is_strict_cid_candidate,
    normalize_component as _normalize_component,
    parse_cid_components,
    split_cid_path,
)

# MIME utilities
from mime_utils import (
    EXTENSION_TO_MIME,
    MIME_TO_EXTENSION,
    extract_filename_from_cid_path,
    get_extension_from_mime_type,
    get_mime_type_from_extension,
)

# Content rendering
from content_rendering import (
    GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER as _GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER,
    GITHUB_RELATIVE_LINK_PATTERN as _GITHUB_RELATIVE_LINK_PATTERN,
    GITHUB_RELATIVE_LINK_PATH_SANITIZER as _GITHUB_RELATIVE_LINK_PATH_SANITIZER,
    INLINE_BOLD_PATTERN as _INLINE_BOLD_PATTERN,
    INLINE_CODE_PATTERN as _INLINE_CODE_PATTERN,
    INLINE_ITALIC_PATTERN as _INLINE_ITALIC_PATTERN,
    MARKDOWN_EXTENSIONS as _MARKDOWN_EXTENSIONS,
    MARKDOWN_INDICATOR_PATTERNS as _MARKDOWN_INDICATOR_PATTERNS,
    MermaidRenderLocation,
    MermaidRenderer,
    MermaidRenderingError,
    convert_github_relative_links as _convert_github_relative_links,
    count_bullet_lines as _count_bullet_lines,
    decode_text_safely as _decode_text_safely,
    extract_markdown_title as _extract_markdown_title,
    looks_like_markdown as _looks_like_markdown,
    normalize_github_relative_link_target as _normalize_github_relative_link_target_v2,
    render_markdown_document as _render_markdown_document,
    replace_formdown_fences as _replace_formdown_fences,
    replace_mermaid_fences as _replace_mermaid_fences,
)

# Storage operations
from cid_storage import (
    ensure_cid_exists,
    generate_all_secret_definitions_json,
    generate_all_server_definitions_json,
    generate_all_variable_definitions_json,
    get_cid_content,
    get_current_secret_definitions_cid,
    get_current_server_definitions_cid,
    get_current_variable_definitions_cid,
    store_cid_from_bytes,
    store_cid_from_json,
    store_secret_definitions_cid,
    store_server_definitions_cid,
    store_variable_definitions_cid,
)

# Upload handlers
from upload_handlers import (
    DOWNLOAD_CHUNK_SIZE_BYTES,
    MAX_UPLOAD_SIZE_BYTES,
    URL_DOWNLOAD_TIMEOUT_SECONDS,
    process_file_upload,
    process_text_upload,
    process_url_upload,
)

# Content serving
from content_serving import (
    generate_qr_data_url as _generate_qr_data_url,
    serve_cid_content,
)

# Create a singleton Mermaid renderer for backward compatibility
_mermaid_renderer = MermaidRenderer()

# Also import things that might be needed
try:
    import markdown  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    markdown = None  # type: ignore[assignment]

try:
    import qrcode  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover
    qrcode = None  # type: ignore[assignment]
    _qrcode_import_error = exc
else:
    _qrcode_import_error = None

# Import for compatibility with historical APIs. These symbols are no longer
# required by :mod:`cid_storage`, but they remain available so imports from
# legacy extensions continue to resolve without raising ImportError.
try:
    from db_access import (
        create_cid_record,
        get_cid_by_path,
        get_secrets,
        get_servers,
        get_variables,
    )
except (RuntimeError, ImportError):
    create_cid_record = None
    get_cid_by_path = None
    get_servers = None
    get_variables = None
    get_secrets = None


# Legacy pattern support for save_server_definition_as_cid
def save_server_definition_as_cid(definition: str) -> str:
    """Save server definition as CID and return the CID string.

    DEPRECATED: Use store_cid_from_bytes or store_cid_from_json instead.

    Args:
        definition: Server definition string

    Returns:
        CID string
    """
    return store_cid_from_bytes(definition.encode("utf-8"))
