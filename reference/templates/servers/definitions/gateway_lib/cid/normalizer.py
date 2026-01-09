"""CID normalization utilities.

Functions for cleaning and normalizing CID values from various sources.
"""

from typing import Optional


def normalize_cid_lookup(value: str | None) -> str | None:
    """Normalize a CID value for lookup.
    
    Handles various input formats:
    - None or empty string -> None
    - Whitespace-only -> None
    - CID with leading slash -> preserved
    - CID without leading slash -> slash added
    - Path containing CID -> CID extracted and slash added
    
    Args:
        value: Raw CID value to normalize
        
    Returns:
        Normalized CID with leading slash, or None if invalid
    """
    if not isinstance(value, str) or not value:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    # Import here to avoid circular dependency
    from cid_presenter import extract_cid_from_path
    
    cid_value = extract_cid_from_path(cleaned)
    if cid_value:
        return f"/{cid_value}"

    return cleaned


def parse_hrx_gateway_args(rest_path: str | None) -> tuple[str, str]:
    """Parse HRX gateway arguments from a path.
    
    Splits a path like "archive/file/path" into archive name and file path.
    
    Args:
        rest_path: Path to parse
        
    Returns:
        Tuple of (archive_name, file_path)
    """
    if not isinstance(rest_path, str):
        return "", ""

    parts = rest_path.strip("/").split("/", 1)
    archive = parts[0] if parts and parts[0] else ""
    file_path = parts[1] if len(parts) > 1 else ""
    return archive, file_path
