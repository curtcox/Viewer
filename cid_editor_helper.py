"""Helper functions for CID editor conversion functionality.

This module provides functions to detect if content is a CID, resolve CID contents,
and generate CIDs from content for use in the editor UI.
"""

from __future__ import annotations

from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from cid_core import (
    generate_cid,
    is_normalized_cid,
    parse_cid_components,
    DIRECT_CONTENT_EMBED_LIMIT,
)
from cid_presenter import format_cid
from cid_storage import store_cid_from_bytes
import db_access


class CidContentStatus(Enum):
    """Status of CID content resolution."""

    NOT_A_CID = "not_a_cid"
    CONTENT_EMBEDDED = "content_embedded"
    CONTENT_FOUND = "content_found"
    CONTENT_NOT_FOUND = "content_not_found"


@dataclass
class CidCheckResult:
    """Result of checking if content is a CID."""

    is_cid: bool
    status: CidContentStatus
    cid_value: Optional[str] = None
    content: Optional[bytes] = None
    content_text: Optional[str] = None


def check_cid_content(value: str) -> CidCheckResult:
    """Check if the given content is a CID and resolve its contents.

    Args:
        value: The content to check (may be a CID or regular content)

    Returns:
        CidCheckResult with status and resolved content if available
    """
    if not value:
        return CidCheckResult(
            is_cid=False,
            status=CidContentStatus.NOT_A_CID,
        )

    # Normalize and check if it looks like a CID
    stripped = value.strip()
    if not stripped:
        return CidCheckResult(
            is_cid=False,
            status=CidContentStatus.NOT_A_CID,
        )

    # Check if it's a normalized CID
    if not is_normalized_cid(stripped):
        return CidCheckResult(
            is_cid=False,
            status=CidContentStatus.NOT_A_CID,
        )

    # It's a valid CID - try to parse and get content
    try:
        content_length, payload = parse_cid_components(stripped)
    except ValueError:
        return CidCheckResult(
            is_cid=False,
            status=CidContentStatus.NOT_A_CID,
        )

    # Check if content is directly embedded in the CID
    if content_length <= DIRECT_CONTENT_EMBED_LIMIT:
        # Content is embedded directly in the CID
        try:
            content_text = payload.decode("utf-8")
        except UnicodeDecodeError:
            content_text = None

        return CidCheckResult(
            is_cid=True,
            status=CidContentStatus.CONTENT_EMBEDDED,
            cid_value=stripped,
            content=payload,
            content_text=content_text,
        )

    # Content is hashed, need to look up in database
    try:
        cid_record = db_access.get_cid_by_path(f"/{stripped}")
    except RuntimeError:
        cid_record = None

    if cid_record and hasattr(cid_record, "file_data") and cid_record.file_data:
        content = cid_record.file_data
        try:
            content_text = content.decode("utf-8")
        except UnicodeDecodeError:
            content_text = None

        return CidCheckResult(
            is_cid=True,
            status=CidContentStatus.CONTENT_FOUND,
            cid_value=stripped,
            content=content,
            content_text=content_text,
        )

    # CID is valid but content not found in database
    return CidCheckResult(
        is_cid=True,
        status=CidContentStatus.CONTENT_NOT_FOUND,
        cid_value=stripped,
    )


def generate_cid_from_content(content: str) -> Tuple[str, bytes]:
    """Generate a CID from the given content.

    Args:
        content: The text content to generate a CID for

    Returns:
        Tuple of (cid_value, content_bytes)
    """
    content_bytes = content.encode("utf-8")
    cid_value = format_cid(generate_cid(content_bytes))
    return cid_value, content_bytes


def store_content_as_cid(content: str) -> str:
    """Store content and return its CID.

    Args:
        content: The text content to store

    Returns:
        The CID value for the stored content
    """
    content_bytes = content.encode("utf-8")
    return store_cid_from_bytes(content_bytes)


__all__ = [
    "CidContentStatus",
    "CidCheckResult",
    "check_cid_content",
    "generate_cid_from_content",
    "store_content_as_cid",
]
