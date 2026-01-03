# ruff: noqa: F821, F706
# pylint: disable=undefined-variable
"""CIDS server for parsing and serving CID archive files.

CIDS archive format:
- Plain text file
- One path per line
- Each line: <path> <CID>
- CIDs can have extensions to specify MIME type (.txt, .html, .jpg, etc.)
- Duplicate paths are an error

For more information, see https://github.com/curtcox/256t.org
"""


import json


def main(archive=None, path=None, *, context=None):
    """Parse and serve CIDS archive files.

    Args:
        archive: CIDS archive string (required)
        path: File path within the archive (optional)
        context: Server execution context (optional)

    Returns:
        Dictionary with 'output' and 'content_type' keys

    Raises:
        ValueError: If archive is not provided or path is not found
    """
    from cid_storage import resolve_cid_text

    # Resolve CID-or-text input.
    resolved_text = resolve_cid_text(archive)
    if resolved_text is not None:
        archive = resolved_text

    # Validate that archive is provided
    if archive is None or (isinstance(archive, str) and not archive.strip()):
        raise ValueError(
            "CIDS archive is required. Usage: cids(archive, path) where archive is the CIDS string."
        )

    # Parse the archive
    try:
        cids_map, directories = _parse_cids_archive(archive)
    except ValueError as e:
        raise ValueError(f"Invalid CIDS archive: {e}") from e

    def _list_directory(prefix: str) -> list[str]:
        normalized = (prefix or "").lstrip("/")
        if normalized and not normalized.endswith("/"):
            normalized += "/"

        entries: set[str] = set()
        for file_path in cids_map.keys():
            if normalized and not file_path.startswith(normalized):
                continue

            remainder = file_path[len(normalized):] if normalized else file_path
            if not remainder:
                continue

            first = remainder.split("/", 1)[0]
            if "/" in remainder:
                entries.add(first + "/")
            else:
                entries.add(first)

        return sorted(entries)

    # If no path specified, return list of files
    if path is None or (isinstance(path, str) and not path.strip()):
        entries = _list_directory("")
        return {
            "output": "\n".join(entries) if entries else "",
            "content_type": "text/plain",
        }

    requested = str(path)
    normalized_requested = requested.lstrip("/")

    # Check if this is a file
    if normalized_requested in cids_map:
        cid_with_ext = cids_map[normalized_requested]
        content, content_type = _resolve_cid_with_extension(cid_with_ext)
        
        if content is None:
            return {
                "output": json.dumps({
                    "error": "CID not found",
                    "requested_path": requested,
                    "cid": cid_with_ext,
                }, indent=2, sort_keys=True),
                "content_type": "application/json",
                "status": 404,
            }

        return {
            "output": content,
            "content_type": content_type,
        }

    # Check if this is a directory
    directory_entries = _list_directory(normalized_requested)
    if directory_entries:
        return {
            "output": "\n".join(directory_entries),
            "content_type": "text/plain",
        }

    # Path not found
    root_entries = _list_directory("")
    payload = {
        "error": "Path not found",
        "requested_path": requested,
        "root_entries": root_entries,
    }

    return {
        "output": json.dumps(payload, indent=2, sort_keys=True),
        "content_type": "application/json",
        "status": 404,
    }


def _parse_cids_archive(archive_text: str) -> tuple[dict[str, str], set[str]]:
    """Parse a CIDS archive into a map of paths to CIDs.
    
    Args:
        archive_text: The CIDS archive content
        
    Returns:
        Tuple of (cids_map, directories) where:
        - cids_map: Dict mapping normalized paths to CIDs (with extensions)
        - directories: Set of directory paths
        
    Raises:
        ValueError: If the archive has duplicate paths or invalid format
    """
    if not archive_text or not archive_text.strip():
        raise ValueError("Archive is empty")
    
    cids_map = {}
    directories = set()
    seen_paths = set()
    
    for line_num, line in enumerate(archive_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue  # Skip empty lines
            
        parts = line.split(None, 1)  # Split on whitespace, max 2 parts
        if len(parts) != 2:
            raise ValueError(f"Line {line_num}: Invalid format. Expected '<path> <CID>', got: {line}")
        
        path, cid = parts
        
        # Normalize path (remove leading slash)
        normalized_path = path.lstrip("/")
        
        if not normalized_path:
            raise ValueError(f"Line {line_num}: Empty path")
        
        if not cid:
            raise ValueError(f"Line {line_num}: Empty CID")
        
        # Check for duplicate paths
        if normalized_path in seen_paths:
            raise ValueError(f"Line {line_num}: Duplicate path '{path}'")
        
        seen_paths.add(normalized_path)
        cids_map[normalized_path] = cid
        
        # Track parent directories
        path_parts = normalized_path.split("/")
        for i in range(len(path_parts) - 1):
            dir_path = "/".join(path_parts[:i+1])
            if dir_path:
                directories.add(dir_path)
    
    return cids_map, directories


def _resolve_cid_with_extension(cid_with_ext: str) -> tuple[bytes | None, str]:
    """Resolve a CID (possibly with extension) to its content and MIME type.
    
    Args:
        cid_with_ext: CID string, possibly with extension like "AAAA.txt"
        
    Returns:
        Tuple of (content, mime_type) or (None, mime_type) if not found
    """
    from cid_storage import get_cid_content
    from pathlib import Path
    
    # Split CID and extension
    if "." in cid_with_ext:
        cid, ext = cid_with_ext.rsplit(".", 1)
        ext = ext.lower()
    else:
        cid, ext = cid_with_ext, ""
    
    # Determine MIME type from extension
    mime_types = {
        "txt": "text/plain",
        "html": "text/html",
        "htm": "text/html",
        "md": "text/markdown",
        "json": "application/json",
        "xml": "application/xml",
        "css": "text/css",
        "js": "application/javascript",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }
    mime_type = mime_types.get(ext, "application/octet-stream")
    
    # Try database first
    cid_path = f"/{cid}" if not cid.startswith("/") else cid
    try:
        content = get_cid_content(cid_path)
        if content:
            if hasattr(content, "file_data"):
                data = content.file_data
                return (bytes(data) if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8")), mime_type
            if hasattr(content, "data"):
                data = content.data
                return (bytes(data) if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8")), mime_type
            return (content if isinstance(content, (bytes, bytearray)) else str(content).encode("utf-8")), mime_type
    except Exception:
        pass
    
    # Try file system as fallback
    try:
        bare_cid = cid.lstrip("/")
        cid_file = Path("cids") / bare_cid
        if cid_file.exists():
            return cid_file.read_bytes(), mime_type
    except Exception:
        pass
    
    return None, mime_type
