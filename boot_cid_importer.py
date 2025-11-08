"""Boot-time CID import utilities."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from flask import Flask

from cid_presenter import cid_path, format_cid
from cid_utils import is_normalized_cid
from db_access import get_cid_by_path
from models import CID

LOGGER = logging.getLogger(__name__)


def get_all_cid_paths_from_db() -> set[str]:
    """Return all CID paths currently in the database."""
    all_cids = CID.query.all()
    return {cid.path for cid in all_cids if cid.path}


def extract_cid_references_from_payload(payload: dict[str, Any]) -> set[str]:
    """Extract all CID references from an import payload.

    This includes CID references in section keys (aliases, servers, variables, secrets, etc.)
    that are NOT already provided in the cid_values section.

    Returns:
        A set of normalized CID paths (with leading slash) that must exist in the database
    """
    cid_refs = set()

    # Get CIDs that are already provided in cid_values
    provided_cids = set()
    cid_values = payload.get('cid_values', {})
    if isinstance(cid_values, dict):
        for cid_key in cid_values.keys():
            normalized = format_cid(cid_key)
            if normalized:
                path = cid_path(normalized)
                if path:
                    provided_cids.add(path)

    # Extract CID references from section keys
    section_keys = [
        'aliases', 'servers', 'variables', 'secrets', 'change_history',
        'app_source', 'metadata'
    ]

    for section_key in section_keys:
        section_value = payload.get(section_key)
        if isinstance(section_value, str):
            # Section references a CID
            normalized = format_cid(section_value)
            if normalized:
                path = cid_path(normalized)
                if path and path not in provided_cids:
                    # Only add to required set if not already provided
                    cid_refs.add(path)

    return cid_refs


def find_missing_cids(required_cids: set[str]) -> list[str]:
    """Find which CIDs from the required set are missing from the database.

    Args:
        required_cids: Set of CID paths (with leading slash) that are required

    Returns:
        List of missing CID paths, sorted for consistent output
    """
    available_cids = get_all_cid_paths_from_db()
    missing = required_cids - available_cids
    return sorted(missing)


def load_and_validate_boot_cid(boot_cid: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Load boot CID from database and validate it's a valid JSON payload.

    Args:
        boot_cid: The CID value to load (will be normalized)

    Returns:
        A tuple of (parsed_payload, error_message)
        If successful, returns (payload, None)
        If error, returns (None, error_message)
    """
    # Normalize the CID
    normalized = format_cid(boot_cid)
    if not normalized or not is_normalized_cid(normalized):
        return None, f"Invalid CID format: {boot_cid}"

    # Get CID path
    path = cid_path(normalized)
    if not path:
        return None, f"Could not determine path for CID: {normalized}"

    # Load from database
    cid_record = get_cid_by_path(path)
    if not cid_record:
        return None, f"Boot CID not found in database: {normalized}\nMake sure the CID file exists in the cids directory."

    # Decode content
    if not cid_record.file_data:
        return None, f"Boot CID has no content: {normalized}"

    try:
        content = bytes(cid_record.file_data).decode('utf-8')
    except UnicodeDecodeError as e:
        return None, f"Boot CID content is not valid UTF-8: {normalized}\nError: {e}"

    # Parse JSON
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as e:
        return None, f"Boot CID content is not valid JSON: {normalized}\nError: {e}"

    if not isinstance(payload, dict):
        return None, f"Boot CID content must be a JSON object, got {type(payload).__name__}"

    return payload, None


def verify_boot_cid_dependencies(boot_cid: str) -> tuple[bool, Optional[str]]:
    """Verify that all CIDs referenced by the boot CID are available in the database.

    Args:
        boot_cid: The CID value to verify

    Returns:
        A tuple of (success, error_message)
        If successful, returns (True, None)
        If missing CIDs, returns (False, error_message with list of missing CIDs)
        If other error, returns (False, error_message)
    """
    payload, error = load_and_validate_boot_cid(boot_cid)
    if error:
        return False, error

    assert payload is not None  # For type checker

    # Extract all CID references
    required_cids = extract_cid_references_from_payload(payload)

    if not required_cids:
        LOGGER.info("Boot CID %s does not reference any other CIDs", boot_cid)
        return True, None

    # Find missing CIDs
    missing = find_missing_cids(required_cids)

    if missing:
        missing_list = '\n  '.join(missing)
        error_msg = (
            f"Boot CID import failed: The following referenced CIDs are missing from the database:\n"
            f"  {missing_list}\n\n"
            f"Please ensure all required CID files are present in the cids directory before starting."
        )
        return False, error_msg

    LOGGER.info("All CID dependencies for boot CID %s are satisfied", boot_cid)
    return True, None


def import_boot_cid(app: Flask, boot_cid: str, user_id: str) -> tuple[bool, Optional[str]]:
    """Import a boot CID using the same mechanism as the /import page.

    Note: This function must be called within an app.app_context().

    Args:
        app: Flask application instance
        boot_cid: The CID value to import
        user_id: The user ID to associate with the import

    Returns:
        A tuple of (success, error_message)
        If successful, returns (True, None)
        If error, returns (False, error_message)
    """
    # First verify dependencies
    success, error = verify_boot_cid_dependencies(boot_cid)
    if not success:
        return False, error

    # Load the payload
    payload, error = load_and_validate_boot_cid(boot_cid)
    if error:
        return False, error

    assert payload is not None  # For type checker

    # Perform the import using the existing import mechanism
    from routes.import_export.import_engine import (
        ImportContext,
        ingest_import_cid_map,
        import_selected_sections,
    )
    from forms import ImportForm

    # Create a form with only the sections that exist in the payload enabled
    form = ImportForm()
    form.include_aliases.data = 'aliases' in payload
    form.include_servers.data = 'servers' in payload
    form.include_variables.data = 'variables' in payload
    form.include_secrets.data = 'secrets' in payload
    form.include_history.data = 'change_history' in payload
    form.process_cid_map.data = 'cid_values' in payload
    form.include_source.data = False  # Don't verify source files on boot

    # Create import context
    raw_payload = json.dumps(payload, indent=2)

    context = ImportContext(
        form=form,
        user_id=user_id,
        change_message=f"Boot import from CID {boot_cid}",
        raw_payload=raw_payload,
        data=payload,
        secret_key='',  # Empty secret key for boot import
    )

    # Ingest CID map
    ingest_import_cid_map(context)

    # Check for CID map errors
    if context.errors:
        error_msg = '\n'.join(context.errors)
        return False, f"Boot CID import failed during CID map ingestion:\n{error_msg}"

    # Import selected sections
    import_selected_sections(context)

    # Check for import errors
    if context.errors:
        error_msg = '\n'.join(context.errors)
        return False, f"Boot CID import failed:\n{error_msg}"

    # Generate snapshot export after import completes
    from routes.import_export.import_engine import generate_snapshot_export
    snapshot_export = generate_snapshot_export(user_id)

    # Log success
    if context.summaries:
        summary_text = ', '.join(context.summaries)
        LOGGER.info("Boot CID import successful: Imported %s", summary_text)
    else:
        LOGGER.info("Boot CID import completed (no changes)")

    if context.warnings:
        for warning in context.warnings:
            LOGGER.warning("Boot CID import warning: %s", warning)

    # Display snapshot info on stdout
    if snapshot_export:
        print("\nSnapshot export generated:")
        print(f"  CID: {snapshot_export['cid_value']}")
        print(f"  Timestamp: {snapshot_export['generated_at']}")
    else:
        print("\nWarning: Failed to generate snapshot export after import")

    return True, None


__all__ = [
    'get_all_cid_paths_from_db',
    'extract_cid_references_from_payload',
    'find_missing_cids',
    'load_and_validate_boot_cid',
    'verify_boot_cid_dependencies',
    'import_boot_cid',
]
