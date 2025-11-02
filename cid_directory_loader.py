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


def load_cids_from_directory(app: Flask, user_id: str) -> None:
    """Ensure the database contains CID entries for files in the directory.

    The directory defaults to ``app.root_path / "cids"`` but can be overridden via
    the ``CID_DIRECTORY`` configuration option. Each file's name must exactly match
    the generated CID for its contents. Any mismatch terminates the application
    immediately.
    """

    configured_directory = app.config.get("CID_DIRECTORY")
    directory = Path(configured_directory) if configured_directory else Path(app.root_path) / "cids"

    directory.mkdir(parents=True, exist_ok=True)

    if not directory.is_dir():
        message = f"CID directory {directory} is not a directory"
        LOGGER.error(message)
        raise SystemExit(message)

    for file_path in _iter_candidate_files(directory):
        filename = file_path.name

        if not is_normalized_cid(filename):
            message = (
                f"CID filename {filename!r} in {directory} is not a valid normalized CID"
            )
            LOGGER.error(message)
            raise SystemExit(message)

        file_bytes = file_path.read_bytes()
        generated_cid = generate_cid(file_bytes)

        if filename != generated_cid:
            message = (
                f"CID filename mismatch for {file_path}: "
                f"filename {filename} does not match generated CID {generated_cid}"
            )
            LOGGER.error(message)
            raise SystemExit(message)

        cid_path = f"/{generated_cid}"
        existing = get_cid_by_path(cid_path)

        if existing is None:
            create_cid_record(generated_cid, file_bytes, user_id)
            LOGGER.info("Loaded CID %s from %s", generated_cid, file_path)
        else:
            if existing.file_data != file_bytes:
                message = (
                    f"CID {generated_cid} already exists in the database with different content"
                )
                LOGGER.error(message)
                raise SystemExit(message)
            LOGGER.debug("CID %s already present in database; skipping", generated_cid)
