"""Boot image vs database difference detection.

This module compares entities defined in a boot image (aliases, servers,
variables, and secrets) with their existing definitions in the database
and prints warnings for any differences found.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from db_access import (
    get_alias_by_name,
    get_server_by_name,
    get_variable_by_name,
    get_secret_by_name,
)
from routes.import_export.cid_utils import load_export_section, coerce_enabled_flag


@dataclass
class EntityDifference:
    """Represents a difference between boot image and DB for an entity."""

    entity_type: str
    name: str
    boot_definition: str
    db_definition: str
    boot_enabled: bool
    db_enabled: bool

    @property
    def has_definition_difference(self) -> bool:
        """Return True if the definitions differ."""
        return self.boot_definition != self.db_definition

    @property
    def has_enabled_difference(self) -> bool:
        """Return True if the enabled flags differ."""
        return self.boot_enabled != self.db_enabled


@dataclass
class BootImageDiffResult:
    """Result of comparing boot image to database."""

    aliases_different: list[str] = field(default_factory=list)
    servers_different: list[str] = field(default_factory=list)
    variables_different: list[str] = field(default_factory=list)
    secrets_different: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        """Return True if any differences were found."""
        return bool(
            self.aliases_different
            or self.servers_different
            or self.variables_different
            or self.secrets_different
        )


def _compare_alias(entry: dict[str, Any], cid_map: dict[str, bytes]) -> str | None:
    """Compare a single alias entry from boot image with DB.

    Returns the alias name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    # Get boot image definition
    boot_definition = entry.get('definition', '')
    if not isinstance(boot_definition, str):
        boot_definition = ''

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))

    # Check if alias exists in DB
    db_alias = get_alias_by_name(name)
    if db_alias is None:
        # Alias doesn't exist in DB yet - not a difference, it will be created
        return None

    # Compare definitions
    db_definition = db_alias.definition or ''
    db_enabled = db_alias.enabled

    if boot_definition != db_definition or boot_enabled != db_enabled:
        return name

    return None


def _compare_server(entry: dict[str, Any], cid_map: dict[str, bytes]) -> str | None:
    """Compare a single server entry from boot image with DB.

    Returns the server name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    # Get boot image definition
    boot_definition = entry.get('definition', '')
    if not isinstance(boot_definition, str):
        boot_definition = ''

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))

    # Check if server exists in DB
    db_server = get_server_by_name(name)
    if db_server is None:
        # Server doesn't exist in DB yet - not a difference, it will be created
        return None

    # Compare definitions
    db_definition = db_server.definition or ''
    db_enabled = db_server.enabled

    if boot_definition != db_definition or boot_enabled != db_enabled:
        return name

    return None


def _compare_variable(entry: dict[str, Any]) -> str | None:
    """Compare a single variable entry from boot image with DB.

    Returns the variable name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    # Get boot image definition
    boot_definition = entry.get('definition', '')
    if not isinstance(boot_definition, str):
        boot_definition = ''

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))

    # Check if variable exists in DB
    db_variable = get_variable_by_name(name)
    if db_variable is None:
        # Variable doesn't exist in DB yet - not a difference, it will be created
        return None

    # Compare definitions
    db_definition = db_variable.definition or ''
    db_enabled = db_variable.enabled

    if boot_definition != db_definition or boot_enabled != db_enabled:
        return name

    return None


def _compare_secret(entry: dict[str, Any], key: str = '') -> str | None:
    """Compare a single secret entry from boot image with DB.

    Note: We only check if the secret exists and is different based on name,
    since we cannot decrypt the secret value from the boot image without the key.
    For secrets, we check if the DB has a different definition (when key is available)
    or just check for existence.

    Returns the secret name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))

    # Check if secret exists in DB
    db_secret = get_secret_by_name(name)
    if db_secret is None:
        # Secret doesn't exist in DB yet - not a difference, it will be created
        return None

    db_enabled = db_secret.enabled

    # For secrets, we can compare enabled flags
    # We cannot easily compare definitions without decryption key
    # So we'll just note if the enabled status differs
    if boot_enabled != db_enabled:
        return name

    # If we have a ciphertext in boot image and key, we could potentially
    # decrypt and compare, but for simplicity we'll skip deep comparison
    # and just rely on enabled flag comparison for secrets
    return None


def _normalise_secret_items(value: Any) -> list[dict[str, Any]] | None:
    """Return a list of secret item dicts from either a list or an object with items."""
    if value is None:
        return None
    if isinstance(value, dict):
        items = value.get('items')
        return items if isinstance(items, list) else None
    if isinstance(value, list):
        return value
    return None


def compare_boot_image_to_db(
    payload: dict[str, Any],
    cid_lookup: dict[str, bytes],
) -> BootImageDiffResult:
    """Compare boot image payload with database and return differences.

    Args:
        payload: The parsed boot image JSON payload
        cid_lookup: CID lookup map for resolving CID references

    Returns:
        BootImageDiffResult with lists of entity names that differ
    """
    result = BootImageDiffResult()

    # Compare aliases
    if 'aliases' in payload:
        aliases_section, load_errors, fatal = load_export_section(
            payload, 'aliases', cid_lookup
        )
        result.errors.extend(load_errors)
        if not fatal and isinstance(aliases_section, list):
            for entry in aliases_section:
                if isinstance(entry, dict):
                    diff_name = _compare_alias(entry, cid_lookup)
                    if diff_name:
                        result.aliases_different.append(diff_name)

    # Compare servers
    if 'servers' in payload:
        servers_section, load_errors, fatal = load_export_section(
            payload, 'servers', cid_lookup
        )
        result.errors.extend(load_errors)
        if not fatal and isinstance(servers_section, list):
            for entry in servers_section:
                if isinstance(entry, dict):
                    diff_name = _compare_server(entry, cid_lookup)
                    if diff_name:
                        result.servers_different.append(diff_name)

    # Compare variables
    if 'variables' in payload:
        variables_section, load_errors, fatal = load_export_section(
            payload, 'variables', cid_lookup
        )
        result.errors.extend(load_errors)
        if not fatal and isinstance(variables_section, list):
            for entry in variables_section:
                if isinstance(entry, dict):
                    diff_name = _compare_variable(entry)
                    if diff_name:
                        result.variables_different.append(diff_name)

    # Compare secrets
    if 'secrets' in payload:
        secrets_section, load_errors, fatal = load_export_section(
            payload, 'secrets', cid_lookup
        )
        result.errors.extend(load_errors)
        if not fatal:
            secrets_items = _normalise_secret_items(secrets_section)
            if secrets_items:
                for entry in secrets_items:
                    if isinstance(entry, dict):
                        diff_name = _compare_secret(entry)
                        if diff_name:
                            result.secrets_different.append(diff_name)

    return result


def print_boot_image_differences(result: BootImageDiffResult) -> None:
    """Print warnings about differences between boot image and DB to stdout.

    Args:
        result: The result from compare_boot_image_to_db
    """
    if not result.has_differences:
        return

    print("\n" + "=" * 70)
    print("WARNING: Boot image definitions differ from database")
    print("=" * 70)

    if result.aliases_different:
        print(f"\nAliases with different definitions ({len(result.aliases_different)}):")
        for name in sorted(result.aliases_different):
            print(f"  - {name}")

    if result.servers_different:
        print(f"\nServers with different definitions ({len(result.servers_different)}):")
        for name in sorted(result.servers_different):
            print(f"  - {name}")

    if result.variables_different:
        print(f"\nVariables with different definitions ({len(result.variables_different)}):")
        for name in sorted(result.variables_different):
            print(f"  - {name}")

    if result.secrets_different:
        print(f"\nSecrets with different definitions ({len(result.secrets_different)}):")
        for name in sorted(result.secrets_different):
            print(f"  - {name}")

    print("\nNote: The boot image values will overwrite the database values.")
    print("=" * 70 + "\n")


__all__ = [
    'EntityDifference',
    'BootImageDiffResult',
    'compare_boot_image_to_db',
    'print_boot_image_differences',
]
