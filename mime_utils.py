"""MIME type detection and extension mapping utilities.

This module provides functions for mapping between file extensions and MIME types,
and for detecting content types from file paths.
"""

from typing import Dict, Optional


# ============================================================================
# MIME TYPE MAPPINGS
# ============================================================================

# Mapping from file extension to MIME type
EXTENSION_TO_MIME: Dict[str, str] = {
    # Text formats
    'html': 'text/html',
    'htm': 'text/html',
    'txt': 'text/plain',
    'css': 'text/css',
    'csv': 'text/csv',
    'md': 'text/markdown',

    # Application formats
    'js': 'application/javascript',
    'json': 'application/json',
    'xml': 'application/xml',
    'pdf': 'application/pdf',
    'zip': 'application/zip',
    'tar': 'application/x-tar',
    'gz': 'application/gzip',
    'sh': 'application/x-sh',
    'bat': 'application/x-msdos-program',
    'exe': 'application/x-msdownload',
    'dmg': 'application/x-apple-diskimage',
    'deb': 'application/vnd.debian.binary-package',
    'rpm': 'application/x-rpm',

    # Image formats
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
    'webp': 'image/webp',
    'ico': 'image/x-icon',

    # Audio formats
    'mp3': 'audio/mpeg',
    'wav': 'audio/wav',
    'ogg': 'audio/ogg',

    # Video formats
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'avi': 'video/x-msvideo',
    'mov': 'video/quicktime',

    # Source code formats
    'py': 'text/x-python',
    'java': 'text/x-java-source',
    'c': 'text/x-c',
    'cpp': 'text/x-c++',
    'h': 'text/x-c',
    'hpp': 'text/x-c++',
}

# Reverse mapping from MIME type to preferred extension
# Built automatically, taking the first extension for each MIME type
MIME_TO_EXTENSION: Dict[str, str] = {}
for ext, mime in EXTENSION_TO_MIME.items():
    if mime not in MIME_TO_EXTENSION:
        MIME_TO_EXTENSION[mime] = ext


# ============================================================================
# MIME TYPE DETECTION FUNCTIONS
# ============================================================================

def get_mime_type_from_extension(path: str) -> str:
    """Determine MIME type from file extension in a path.

    Args:
        path: File path or URL path containing an extension

    Returns:
        MIME type string, or 'application/octet-stream' if unknown

    Example:
        >>> get_mime_type_from_extension('document.txt')
        'text/plain'
        >>> get_mime_type_from_extension('/path/to/file.json')
        'application/json'
        >>> get_mime_type_from_extension('unknown.xyz')
        'application/octet-stream'
    """
    if '.' in path:
        extension = path.split('.')[-1].lower()
        return EXTENSION_TO_MIME.get(extension, 'application/octet-stream')
    return 'application/octet-stream'


def get_extension_from_mime_type(content_type: str) -> str:
    """Get file extension from MIME type.

    Args:
        content_type: MIME type string (may include parameters like charset)

    Returns:
        File extension (without dot), or empty string if unknown

    Example:
        >>> get_extension_from_mime_type('text/plain')
        'txt'
        >>> get_extension_from_mime_type('application/json; charset=utf-8')
        'json'
        >>> get_extension_from_mime_type('application/unknown')
        ''
    """
    # Extract base MIME type (ignore parameters like charset)
    base_mime = content_type.split(';')[0].strip().lower()
    return MIME_TO_EXTENSION.get(base_mime, '')


def extract_filename_from_cid_path(path: str) -> Optional[str]:
    """Extract filename from CID path for content disposition header.

    This function extracts the filename portion from paths like:
    - /CID.filename.ext -> filename.ext
    - /CID.document.pdf -> document.pdf
    - /CID.txt -> None (single extension, no filename)

    Args:
        path: CID path string

    Returns:
        Extracted filename or None if path doesn't contain a filename

    Example:
        >>> extract_filename_from_cid_path('/CID123.document.pdf')
        'document.pdf'
        >>> extract_filename_from_cid_path('/CID123.txt')
        None
        >>> extract_filename_from_cid_path('/CID123.my.file.txt')
        'my.file.txt'
    """
    if path.startswith('/'):
        path = path[1:]

    if not path or path in ['.', '..']:
        return None

    parts = path.split('.')

    # Need at least CID.filename.extension (3 parts)
    if len(parts) < 3:
        return None

    # Join everything after the CID (first part)
    filename_parts = parts[1:]
    filename = '.'.join(filename_parts)

    return filename
