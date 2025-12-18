"""Utilities for loading CID fixtures from the filesystem."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from flask import Flask

from cid_utils import generate_cid, is_normalized_cid
from db_access import create_cid_record, get_cid_by_path

LOGGER = logging.getLogger(__name__)


def _iter_candidate_files(directory: Path) -> Iterable[Path]:
    """Yield files from the directory that could contain CID fixtures."""

    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            # Hidden files (such as .gitignore) are not CID fixtures.
            continue
        if not entry.is_file():
            continue
        yield entry


def load_cids_from_directory(app: Flask) -> None:
    """Ensure the database contains CID entries for files in the directory.

    The directory defaults to ``app.root_path / "cids"`` but can be overridden via
    the ``CID_DIRECTORY`` configuration option. Each file's name must exactly match
    the generated CID for its contents. Any mismatch terminates the application
    immediately.

    The CID directory must exist (it can be read-only). If the directory does not
    exist, a RuntimeError is raised with the message "No CID directory", which will
    be displayed as a 500 error page.
    """

    configured_directory = app.config.get("CID_DIRECTORY")
    directory = Path(configured_directory) if configured_directory else Path(app.root_path) / "cids"

    # Check if directory exists - it must exist (can be read-only, but must exist)
    if not directory.exists():
        message = "No CID directory"
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
            message = (
                f"CID filename {filename!r} in {directory} is not a valid normalized CID"
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
            LOGGER.info("Loaded CID %s from %s", generated_cid, file_path)
        else:
            if existing.file_data != file_bytes:
                message = (
                    f"CID {generated_cid} already exists in the database with different content"
                )
                LOGGER.error(message)
                raise RuntimeError(message)
            LOGGER.debug("CID %s already present in database; skipping", generated_cid)
