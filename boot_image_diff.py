"""Boot image vs database difference detection.

This module compares entities defined in a boot image (aliases, servers,
variables, and secrets) with their existing definitions in the database
and prints warnings for any differences found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cid_core import generate_cid
from db_access import (
    get_alias_by_name,
    get_server_by_name,
    get_variable_by_name,
    get_secret_by_name,
)
from routes.import_export.cid_utils import (
    load_export_section,
    coerce_enabled_flag,
    normalise_cid,
)


@dataclass
class BootEntityDifference:
    """Metadata about a differing entity between boot image and database."""

    name: str
    boot_cid: str | None = None
    db_cid: str | None = None


@dataclass
class BootImageDiffResult:
    """Result of comparing boot image to database."""

    aliases_different: list[BootEntityDifference] = field(default_factory=list)
    servers_different: list[BootEntityDifference] = field(default_factory=list)
    variables_different: list[BootEntityDifference] = field(default_factory=list)
    secrets_different: list[BootEntityDifference] = field(default_factory=list)
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


def _normalize_db_cid(value: Any) -> str | None:
    """Return a normalized CID string or None."""

    normalized = normalise_cid(value)
    return normalized or None


def _compute_definition_cid(definition: str | None) -> str | None:
    """Return the CID for a definition string when available."""

    if not isinstance(definition, str):
        return None
    return generate_cid(definition.encode('utf-8'))


def _definitions_match(
    boot_definition: str,
    db_definition: str,
    boot_cid: str | None,
    db_cid: str | None,
) -> bool:
    """Return True when boot and DB definitions are equivalent."""

    if boot_cid and db_cid:
        return boot_cid == db_cid
    return boot_definition == db_definition


def _entry_definition(entry: dict[str, Any]) -> str:
    """Return the definition text from an entry (empty string when absent)."""

    value = entry.get('definition')
    if isinstance(value, str):
        return value
    return ''


def _entry_boot_cid(entry: dict[str, Any]) -> str | None:
    """Return the CID supplied by the boot entry or one derived from its text."""

    entry_cid = _normalize_db_cid(entry.get('definition_cid'))
    if entry_cid:
        return entry_cid
    definition = entry.get('definition')
    if isinstance(definition, str):
        return _compute_definition_cid(definition)
    return None


def _compare_alias(entry: dict[str, Any]) -> BootEntityDifference | None:
    """Compare a single alias entry from boot image with DB.

    Returns the alias name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    # Get boot image definition
    boot_definition = _entry_definition(entry)

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))
    boot_cid = _entry_boot_cid(entry)

    # Check if alias exists in DB
    db_alias = get_alias_by_name(name)
    if db_alias is None:
        # Alias doesn't exist in DB yet - not a difference, it will be created
        return None

    # Compare definitions
    db_definition = db_alias.definition or ''
    db_enabled = db_alias.enabled
    db_cid = _compute_definition_cid(db_alias.definition)

    definitions_match = _definitions_match(
        boot_definition,
        db_definition,
        boot_cid,
        db_cid,
    )

    if not definitions_match or boot_enabled != db_enabled:
        return BootEntityDifference(
            name=name,
            boot_cid=boot_cid,
            db_cid=db_cid,
        )

    return None


def _compare_server(entry: dict[str, Any]) -> BootEntityDifference | None:
    """Compare a single server entry from boot image with DB.

    Returns the server name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    # Get boot image definition
    boot_definition = _entry_definition(entry)

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))
    boot_cid = _entry_boot_cid(entry)

    # Check if server exists in DB
    db_server = get_server_by_name(name)
    if db_server is None:
        # Server doesn't exist in DB yet - not a difference, it will be created
        return None

    # Compare definitions
    db_definition = db_server.definition or ''
    db_enabled = db_server.enabled

    db_cid = _normalize_db_cid(getattr(db_server, 'definition_cid', None))
    if not db_cid:
        db_cid = _compute_definition_cid(db_definition)

    definitions_match = _definitions_match(
        boot_definition,
        db_definition,
        boot_cid,
        db_cid,
    )

    if not definitions_match or boot_enabled != db_enabled:
        return BootEntityDifference(
            name=name,
            boot_cid=boot_cid,
            db_cid=db_cid,
        )

    return None


def _compare_variable(entry: dict[str, Any]) -> BootEntityDifference | None:
    """Compare a single variable entry from boot image with DB.

    Returns the variable name if there's a difference, None otherwise.
    """
    name = entry.get('name')
    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()

    # Get boot image definition
    boot_definition = _entry_definition(entry)

    boot_enabled = coerce_enabled_flag(entry.get('enabled'))
    boot_cid = _entry_boot_cid(entry)

    # Check if variable exists in DB
    db_variable = get_variable_by_name(name)
    if db_variable is None:
        # Variable doesn't exist in DB yet - not a difference, it will be created
        return None

    # Compare definitions
    db_definition = db_variable.definition or ''
    db_enabled = db_variable.enabled
    db_cid = _compute_definition_cid(db_definition)

    definitions_match = _definitions_match(
        boot_definition,
        db_definition,
        boot_cid,
        db_cid,
    )

    if not definitions_match or boot_enabled != db_enabled:
        return BootEntityDifference(
            name=name,
            boot_cid=boot_cid,
            db_cid=db_cid,
        )

    return None


def _compare_secret(entry: dict[str, Any]) -> BootEntityDifference | None:
    """Compare a single secret entry from boot image with DB.

    Note: We only compare enabled flags for secrets since we cannot decrypt
    the secret value from the boot image without the encryption key.

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

    # For secrets, we can only compare enabled flags since values are encrypted
    if boot_enabled != db_enabled:
        return BootEntityDifference(name=name)

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
                    diff = _compare_alias(entry)
                    if diff:
                        result.aliases_different.append(diff)

    # Compare servers
    if 'servers' in payload:
        servers_section, load_errors, fatal = load_export_section(
            payload, 'servers', cid_lookup
        )
        result.errors.extend(load_errors)
        if not fatal and isinstance(servers_section, list):
            for entry in servers_section:
                if isinstance(entry, dict):
                    diff = _compare_server(entry)
                    if diff:
                        result.servers_different.append(diff)

    # Compare variables
    if 'variables' in payload:
        variables_section, load_errors, fatal = load_export_section(
            payload, 'variables', cid_lookup
        )
        result.errors.extend(load_errors)
        if not fatal and isinstance(variables_section, list):
            for entry in variables_section:
                if isinstance(entry, dict):
                    diff = _compare_variable(entry)
                    if diff:
                        result.variables_different.append(diff)

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
                        diff = _compare_secret(entry)
                        if diff:
                            result.secrets_different.append(diff)

    return result


def _print_difference_entries(entries: list[BootEntityDifference]) -> None:
    """Print each entry with its boot and DB CIDs."""

    for entry in sorted(entries, key=lambda item: item.name):
        boot_cid = entry.boot_cid or 'unknown'
        db_cid = entry.db_cid or 'unknown'
        print(f"  - {entry.name}")
        print(f"      boot CID: {boot_cid}")
        print(f"      db CID:   {db_cid}")


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
        _print_difference_entries(result.aliases_different)

    if result.servers_different:
        print(f"\nServers with different definitions ({len(result.servers_different)}):")
        _print_difference_entries(result.servers_different)

    if result.variables_different:
        print(f"\nVariables with different definitions ({len(result.variables_different)}):")
        _print_difference_entries(result.variables_different)

    if result.secrets_different:
        print(f"\nSecrets with different definitions ({len(result.secrets_different)}):")
        _print_difference_entries(result.secrets_different)

    print("\nNote: The boot image values will overwrite the database values.")
    print("=" * 70 + "\n")


__all__ = [
    'BootEntityDifference',
    'BootImageDiffResult',
    'compare_boot_image_to_db',
    'print_boot_image_differences',
]
