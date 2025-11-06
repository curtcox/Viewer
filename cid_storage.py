"""CID storage operations and database helpers.

This module provides functions for storing and retrieving CID records from
the database, including support for server, variable, and secret definitions.
"""

import json
from typing import Any, Optional

from cid_core import generate_cid
from cid_presenter import cid_path, format_cid
from db_access import (
    create_cid_record,
    get_cid_by_path,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
)


# ============================================================================
# CID STORAGE HELPERS
# ============================================================================

def ensure_cid_exists(cid_value: str, content_bytes: bytes, user_id: Optional[str]) -> None:
    """Ensure a CID record exists in the database, creating it if needed.

    Args:
        cid_value: CID string
        content_bytes: Content to store
        user_id: User ID for ownership (optional)
    """
    cid_record_path = cid_path(cid_value)
    content = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not content:
        create_cid_record(cid_value, content_bytes, user_id)


def get_cid_content(path: str) -> Any:
    """Get CID content from database by path.

    Args:
        path: CID path

    Returns:
        CID content record or None if not found
    """
    return get_cid_by_path(path)


def store_cid_from_bytes(content_bytes: bytes, user_id: Optional[int]) -> str:
    """Store content in a CID record and return the CID.

    Args:
        content_bytes: Content to store
        user_id: User ID for ownership

    Returns:
        CID string

    Example:
        >>> cid = store_cid_from_bytes(b"hello", user_id=1)
        >>> isinstance(cid, str)
        True
    """
    cid_value = format_cid(generate_cid(content_bytes))
    ensure_cid_exists(cid_value, content_bytes, user_id)
    return cid_value


def store_cid_from_json(json_content: str, user_id: Optional[int]) -> str:
    """Store JSON content in a CID record and return the CID.

    Args:
        json_content: JSON string to store
        user_id: User ID for ownership

    Returns:
        CID string

    Example:
        >>> cid = store_cid_from_json('{"key": "value"}', user_id=1)
        >>> isinstance(cid, str)
        True
    """
    json_bytes = json_content.encode('utf-8')
    return store_cid_from_bytes(json_bytes, user_id)


# ============================================================================
# SERVER DEFINITIONS
# ============================================================================

def generate_all_server_definitions_json(user_id: int) -> str:
    """Generate JSON containing all server definitions for a user.

    Args:
        user_id: User ID

    Returns:
        JSON string with server definitions

    Example:
        >>> json_str = generate_all_server_definitions_json(1)
        >>> isinstance(json_str, str)
        True
    """
    servers = get_user_servers(user_id)

    server_definitions = {}
    for server in servers:
        if not getattr(server, "enabled", True):
            continue
        server_definitions[server.name] = server.definition

    return json.dumps(server_definitions, indent=2, sort_keys=True)


def store_server_definitions_cid(user_id: int) -> str:
    """Store all server definitions as JSON in a CID and return the CID.

    Args:
        user_id: User ID

    Returns:
        CID string
    """
    json_content = generate_all_server_definitions_json(user_id)
    return store_cid_from_json(json_content, user_id)


def get_current_server_definitions_cid(user_id: int) -> str:
    """Get the CID for the current server definitions JSON.

    Creates the CID if it doesn't exist.

    Args:
        user_id: User ID

    Returns:
        CID string
    """
    json_content = generate_all_server_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_content(cid_record_path) if cid_record_path else None
    if content:
        return cid_value
    return store_server_definitions_cid(user_id)


# ============================================================================
# VARIABLE DEFINITIONS
# ============================================================================

def generate_all_variable_definitions_json(user_id: int) -> str:
    """Generate JSON containing all variable definitions for a user.

    Args:
        user_id: User ID

    Returns:
        JSON string with variable definitions
    """
    variables = get_user_variables(user_id)

    variable_definitions = {}
    for variable in variables:
        if not getattr(variable, "enabled", True):
            continue
        variable_definitions[variable.name] = variable.definition

    return json.dumps(variable_definitions, indent=2, sort_keys=True)


def store_variable_definitions_cid(user_id: int) -> str:
    """Store all variable definitions as JSON in a CID and return the CID.

    Args:
        user_id: User ID

    Returns:
        CID string
    """
    json_content = generate_all_variable_definitions_json(user_id)
    return store_cid_from_json(json_content, user_id)


def get_current_variable_definitions_cid(user_id: int) -> str:
    """Get the CID for the current variable definitions JSON.

    Creates the CID if it doesn't exist.

    Args:
        user_id: User ID

    Returns:
        CID string
    """
    json_content = generate_all_variable_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_content(cid_record_path) if cid_record_path else None
    if content:
        return cid_value
    return store_variable_definitions_cid(user_id)


# ============================================================================
# SECRET DEFINITIONS
# ============================================================================

def generate_all_secret_definitions_json(user_id: int) -> str:
    """Generate JSON containing all secret definitions for a user.

    Args:
        user_id: User ID

    Returns:
        JSON string with secret definitions
    """
    secrets = get_user_secrets(user_id)

    secret_definitions = {}
    for secret in secrets:
        if not getattr(secret, "enabled", True):
            continue
        secret_definitions[secret.name] = secret.definition

    return json.dumps(secret_definitions, indent=2, sort_keys=True)


def store_secret_definitions_cid(user_id: int) -> str:
    """Store all secret definitions as JSON in a CID and return the CID.

    Args:
        user_id: User ID

    Returns:
        CID string
    """
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid_value = format_cid(generate_cid(json_bytes))

    ensure_cid_exists(cid_value, json_bytes, user_id)
    return cid_value


def get_current_secret_definitions_cid(user_id: int) -> str:
    """Get the CID for the current secret definitions JSON.

    Creates the CID if it doesn't exist.

    Args:
        user_id: User ID

    Returns:
        CID string
    """
    json_content = generate_all_secret_definitions_json(user_id)
    json_bytes = json_content.encode('utf-8')
    cid_value = format_cid(generate_cid(json_bytes))

    cid_record_path = cid_path(cid_value)
    content = get_cid_content(cid_record_path) if cid_record_path else None
    if content:
        return cid_value
    return store_secret_definitions_cid(user_id)
