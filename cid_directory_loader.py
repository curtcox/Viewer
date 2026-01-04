"""Utilities for loading CID fixtures from the filesystem."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable

from flask import Flask

from cid_utils import generate_cid, is_normalized_cid
from db_access import create_cid_record, get_cid_by_path

LOGGER = logging.getLogger(__name__)


def _describe_invalid_cid_filename(filename: str) -> str:
    """Return a detailed diagnostic for why a CID filename is invalid."""
    try:
        from cid_core import (  # pylint: disable=import-outside-toplevel
            CID_CHARACTER_CLASS,
            CID_LENGTH,
            CID_LENGTH_PREFIX_CHARS,
            CID_MIN_LENGTH,
            DIRECT_CONTENT_EMBED_LIMIT,
            parse_cid_components,
        )
    except Exception:
        # Fall back to a simple diagnostic when CID internals are unavailable.
        return "Could not load CID format details; the filename does not pass is_normalized_cid()."

    raw = filename
    stripped = (raw or "").strip()
    normalized = stripped.lstrip("/")

    lines: list[str] = []
    lines.append("CID format spec: https://256t.org/index.html")
    lines.append("What this loader expects:")
    lines.append(
        "  - CID filenames must be Viewer-generated CIDs using base64url characters (A-Z a-z 0-9 '_' '-')."
    )
    lines.append(
        f"  - Length must be between {CID_MIN_LENGTH} and {CID_LENGTH} characters (inclusive)."
    )
    lines.append(
        f"  - The first {CID_LENGTH_PREFIX_CHARS} characters encode the original content length."
    )
    lines.append(
        f"  - If content length <= {DIRECT_CONTENT_EMBED_LIMIT}, the remaining characters embed the content bytes."
    )
    lines.append(
        "  - If content length > 64 bytes, the remaining characters must be an 86-character SHA-512 digest."
    )

    if stripped != raw:
        lines.append(f"Filename has leading/trailing whitespace; stripped={stripped!r}.")
    if normalized != stripped:
        lines.append(
            "Filename starts with '/', but CID filenames must not include leading slashes."
        )
    if "/" in normalized:
        lines.append("Filename contains '/', but CID filenames must be a single path component.")

    allowed = re.compile(rf"^[{CID_CHARACTER_CLASS}]+$")
    if not normalized:
        lines.append("Filename is empty after normalization.")
        return "\n".join(lines)

    if not allowed.fullmatch(normalized):
        illegal_chars = sorted({ch for ch in normalized if not re.fullmatch(rf"[{CID_CHARACTER_CLASS}]", ch)})
        illegal_preview = "".join(illegal_chars) if illegal_chars else "(unknown)"
        lines.append(
            f"Filename contains characters outside base64url set; illegal characters: {illegal_preview!r}."
        )

    length = len(normalized)
    if length < CID_MIN_LENGTH or length > CID_LENGTH:
        lines.append(
            f"Filename length is {length}, but must be between {CID_MIN_LENGTH} and {CID_LENGTH}."
        )
        return "\n".join(lines)

    try:
        content_length, _payload = parse_cid_components(normalized)
        lines.append(
            f"Parsed length prefix indicates original content length = {content_length} bytes."
        )
    except ValueError as exc:
        # This is the most common failure when the file looks CID-ish but is not in
        # the canonical Viewer CID format (e.g., from a different CID scheme).
        lines.append(
            "Filename matches the basic character/length constraints, but it is not a canonical Viewer CID."
        )
        lines.append(f"CID structural validation failed: {exc}.")
        lines.append(
            "This usually means the file was created using a different CID format and should not be placed in CID_DIRECTORY."
        )

    lines.append("How to fix:")
    lines.append(
        "  - If this file is not meant to be a CID fixture, move it out of the cids/ directory (CID_DIRECTORY)."
    )
    lines.append(
        "  - If it is meant to be a CID fixture, regenerate it with Viewer so the filename equals generate_cid(file_bytes)."
    )
    lines.append(
        "  - If you intentionally use a different CID scheme, the loader must be updated to support it (currently only Viewer CIDs are supported)."
    )
    return "\n".join(lines)


def _iter_candidate_files(directory: Path) -> Iterable[Path]:
    """Yield files from the directory that could contain CID fixtures."""

    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            # Hidden files (such as .gitignore) are not CID fixtures.
            continue
        if not entry.is_file():
            continue
        yield entry


def load_cids_from_directory(app: Flask, allow_missing: bool = False) -> None:
    """Ensure the database contains CID entries for files in the directory.

    The directory defaults to ``app.root_path / "cids"`` but can be overridden via
    the ``CID_DIRECTORY`` configuration option. Each file's name must exactly match
    the generated CID for its contents. Any mismatch terminates the application
    immediately.

    Args:
        app: Flask application instance
        allow_missing: If True, missing directory is treated as empty (no error).
                      If False, raises RuntimeError when directory doesn't exist.
                      Defaults to False for backward compatibility.

    Raises:
        RuntimeError: If directory doesn't exist and allow_missing=False, or if
                     there are validation errors with CID files.
    """

    configured_directory = app.config.get("CID_DIRECTORY")
    directory = (
        Path(configured_directory)
        if configured_directory
        else Path(app.root_path) / "cids"
    )

    # Check if directory exists - it must exist (can be read-only, but must exist)
    if not directory.exists():
        if allow_missing:
            LOGGER.info(
                "CID directory %s does not exist, skipping CID loading (allow_missing=True)",
                directory,
            )
            return
        message = f"No CID directory: {directory}"
        LOGGER.error("CID directory %s does not exist: %s", directory, message)
        raise RuntimeError(message)

    if not directory.is_dir():
        message = f"CID directory {directory} is not a directory"
        LOGGER.error(message)
        raise RuntimeError(message)

    # Try to iterate files from the directory (read-only is fine)
    try:
        candidate_files = list(_iter_candidate_files(directory))
    except (OSError, PermissionError) as e:
        # Directory exists but we can't read from it
        message = f"Cannot read from CID directory {directory}: {e}"
        LOGGER.error(message)
        raise RuntimeError(message) from e

    # If directory is empty, that's fine - just skip loading
    if not candidate_files:
        LOGGER.debug("CID directory %s is empty, skipping CID loading", directory)
        return

    for file_path in candidate_files:
        filename = file_path.name

        if not is_normalized_cid(filename):
            diagnostic = _describe_invalid_cid_filename(filename)
            message = (
                f"CID filename {filename!r} in {directory} is not a valid normalized CID.\n"
                f"{diagnostic}"
            )
            LOGGER.error(message)
            raise RuntimeError(message)

        file_bytes = file_path.read_bytes()
        generated_cid = generate_cid(file_bytes)

        if filename != generated_cid:
            message = (
                f"CID filename mismatch for {file_path}: "
                f"filename {filename} does not match generated CID {generated_cid}"
            )
            LOGGER.error(message)
            raise RuntimeError(message)

        cid_path = f"/{generated_cid}"
        existing = get_cid_by_path(cid_path)

        if existing is None:
            create_cid_record(generated_cid, file_bytes)
            LOGGER.debug("Loaded CID %s from %s", generated_cid, file_path)
        else:
            if existing.file_data != file_bytes:
                message = f"CID {generated_cid} already exists in the database with different content"
                LOGGER.error(message)
                raise RuntimeError(message)
            LOGGER.debug("CID %s already present in database; skipping", generated_cid)
