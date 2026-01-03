"""Entity import functions for aliases, servers, variables, and secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from alias_definition import (
    AliasDefinitionError,
    parse_alias_definition,
)
from cid_utils import save_server_definition_as_cid
from db_access import (
    get_alias_by_name,
    get_secret_by_name,
    get_server_by_name,
    get_variable_by_name,
    save_entity,
)
from encryption import decrypt_secret_value
from models import Alias, Secret, Server, Variable

from .cid_utils import coerce_enabled_flag, load_cid_bytes, normalise_cid
from .routes_integration import (
    get_existing_routes_safe,
    update_secret_definitions_cid_safe,
    update_server_definitions_cid_safe,
    update_variable_definitions_cid_safe,
)


def _has_flask_app_context() -> bool:
    try:
        from flask import has_app_context
    except ModuleNotFoundError:
        return False
    try:
        return bool(has_app_context())
    except RuntimeError:
        return False


@dataclass
class AliasImport:
    """Normalized alias entry produced from import payload data."""

    name: str
    definition: str
    enabled: bool


@dataclass
class ServerImport:
    """Normalized server entry produced from import payload data."""

    name: str
    definition: str
    enabled: bool


@dataclass
class VariableImport:
    """Normalized variable entry produced from import payload data."""

    name: str
    definition: str
    enabled: bool


def prepare_alias_import(
    entry: Any,
    reserved_routes: set[str],
    cid_map: dict[str, bytes],
    errors: list[str],
) -> AliasImport | None:
    """Return a normalized alias import entry when the payload entry is valid."""
    if not isinstance(entry, dict):
        errors.append("Alias entries must be objects with name and definition details.")
        return None

    name_raw = entry.get("name")
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append("Alias entry must include a valid name.")
        return None

    name = name_raw.strip()

    if f"/{name}" in reserved_routes:
        errors.append(
            f'Alias "{name}" conflicts with an existing route and was skipped.'
        )
        return None

    definition_text: Optional[str] = None
    raw_definition = entry.get("definition")
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Alias "{name}" definition must be text when provided.')
        return None

    definition_cid = normalise_cid(entry.get("definition_cid"))

    if definition_text is None and definition_cid:
        cid_bytes = load_cid_bytes(definition_cid, cid_map)
        if cid_bytes is None:
            errors.append(
                f'Alias "{name}" definition with CID "{definition_cid}" was not included in the import.'
            )
            return None
        try:
            definition_text = cid_bytes.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(
                f'Alias "{name}" definition for CID "{definition_cid}" must be UTF-8 text.'
            )
            return None

    if definition_text is None:
        errors.append(
            f'Alias "{name}" entry must include either a definition or a definition_cid.'
        )
        return None

    try:
        # Validate the definition (raises AliasDefinitionError if invalid)
        _ = parse_alias_definition(definition_text, alias_name=name)
    except AliasDefinitionError as exc:
        errors.append(f'Alias "{name}" definition could not be parsed: {exc}')
        return None

    # Preserve the original definition format during import
    definition_value = definition_text

    enabled = coerce_enabled_flag(entry.get("enabled"))

    return AliasImport(
        name=name,
        definition=definition_value,
        enabled=enabled,
    )


def load_server_definition_from_cid(
    name: str,
    definition_cid: str,
    cid_map: dict[str, bytes],
    errors: list[str],
) -> str | None:
    """Load server definition from CID map or database."""
    cid_bytes = load_cid_bytes(definition_cid, cid_map)
    if cid_bytes is None:
        details: list[str] = []
        normalised = normalise_cid(definition_cid)
        details.append("Import step: importing a server entry from the 'servers' section.")
        details.append(
            "Expected input: server entry must contain either a text 'definition' field or a 'definition_cid' that can be resolved to UTF-8 text."
        )
        details.append("CID resolution: this importer does NOT read raw CID files from disk directly.")
        details.append("Lookup order: 1) import payload top-level cid_values map (if present), 2) database.")
        details.append(f"cid_values entries provided: {len(cid_map)}")
        if normalised:
            details.append(f"database path checked: /{normalised}")
        if _has_flask_app_context() and normalised:
            try:
                from flask import current_app  # pylint: disable=import-outside-toplevel

                cid_directory = current_app.config.get("CID_DIRECTORY")
                if isinstance(cid_directory, str) and cid_directory.strip():
                    cid_file_path = os.path.join(cid_directory, normalised)
                    if os.path.exists(cid_file_path):
                        details.append(
                            f"CID file exists on disk but was not found in the database: {cid_file_path}"
                        )
                        details.append(
                            "Likely cause: CID loading from CID_DIRECTORY did not run (or ran with a different database), so the file never got imported into the database."
                        )
                    else:
                        details.append(
                            f"CID file was not found on disk at: {cid_file_path}"
                        )
            except Exception:
                pass

        detail_text = "\n".join(f"  - {line}" for line in details)
        errors.append(
            (
                f"While importing server {name!r}, the definition CID {definition_cid!r} could not be resolved.\n"
                "This means the import payload referenced a CID but did not include its content, and the CID was not available in the database.\n"
                f"Details:\n{detail_text}\n"
                "Fix options:\n"
                "  - Make the import payload self-contained: include the CID content under the top-level cid_values map (key=the CID, value=the UTF-8 source text).\n"
                "  - Or ensure the CID is present in the database before import: verify CID_DIRECTORY points to the correct cids folder and that startup loads those CIDs into the same database used for boot import."
            )
        )
        return None
    try:
        return cid_bytes.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(
            f'Server "{name}" definition for CID "{definition_cid}" must be UTF-8 text.'
        )
        return None


def prepare_server_import(
    entry: Any,
    cid_map: dict[str, bytes],
    errors: list[str],
) -> ServerImport | None:
    """Return a normalized server import entry when the payload entry is valid."""
    if not isinstance(entry, dict):
        errors.append(
            "Server entries must be objects with name and definition details."
        )
        return None

    name_raw = entry.get("name")
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append("Server entry must include a valid name.")
        return None

    name = name_raw.strip()
    definition_text: str | None = None
    raw_definition = entry.get("definition")
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Server "{name}" definition must be text.')
        return None

    definition_cid = normalise_cid(entry.get("definition_cid"))
    if definition_text is None and definition_cid:
        definition_text = load_server_definition_from_cid(
            name, definition_cid, cid_map, errors
        )

    if definition_text is None:
        errors.append(
            f'Server "{name}" entry must include either a definition or a definition_cid.'
        )
        return None

    enabled = coerce_enabled_flag(entry.get("enabled"))

    return ServerImport(
        name=name,
        definition=definition_text,
        enabled=enabled,
    )


def prepare_variable_import(
    entry: Any,
    cid_map: dict[str, bytes],
    errors: list[str],
    index: int,
) -> VariableImport | None:
    """Return a normalized variable import entry when the payload entry is valid."""
    if not isinstance(entry, dict):
        errors.append(
            f"Variable entry at index {index} must be an object; got {type(entry).__name__}."
        )
        return None

    name_raw = entry.get("name")
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append(
            f"Variable entry at index {index} must include a valid name; keys={sorted(entry.keys())}."
        )
        return None

    name = name_raw.strip()

    definition_text: str | None = None
    raw_definition = entry.get("definition")
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Variable "{name}" definition must be text.')
        return None

    definition_cid = normalise_cid(entry.get("definition_cid"))
    definition_file = normalise_cid(entry.get("definition_file"))
    resolved_definition_cid = definition_cid or definition_file

    if definition_text is None and resolved_definition_cid:
        cid_bytes = load_cid_bytes(resolved_definition_cid, cid_map)
        if cid_bytes is None:
            errors.append(
                (
                    f'Variable "{name}" definition with CID "{resolved_definition_cid}" '
                    "was not included in the import."
                )
            )
            return None
        try:
            definition_text = cid_bytes.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(
                f'Variable "{name}" definition for CID "{resolved_definition_cid}" must be UTF-8 text.'
            )
            return None

    if definition_text is None:
        errors.append(
            (
                f"Variable entry at index {index} must include a definition or a definition_cid/definition_file; "
                f"name={name!r}, keys={sorted(entry.keys())}, entry={entry!r}"
            )
        )
        return None

    enabled = coerce_enabled_flag(entry.get("enabled"))

    return VariableImport(
        name=name,
        definition=definition_text,
        enabled=enabled,
    )


def impl_import_aliases(
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Implementation of alias import with name tracking."""
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    if raw_aliases is None:
        return 0, ["No alias data found in import file."], []
    if not isinstance(raw_aliases, list):
        return 0, ["Aliases in import file must be a list."], []
    reserved_routes = get_existing_routes_safe()
    cid_map = cid_map or {}
    for entry in raw_aliases:
        prepared = prepare_alias_import(entry, reserved_routes, cid_map, errors)
        if prepared is None:
            continue
        existing = get_alias_by_name(prepared.name)
        if existing:
            existing.definition = prepared.definition
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = prepared.enabled
            save_entity(existing)
        else:
            alias = Alias(
                name=prepared.name,
                definition=prepared.definition,
                enabled=prepared.enabled,
            )
            save_entity(alias)
        imported += 1
        names.append(prepared.name)
    return imported, errors, names


def import_aliases_with_names(
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Import aliases and return count, errors, and imported names."""
    return impl_import_aliases(raw_aliases, cid_map)


def import_aliases(
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str]]:
    """Import aliases and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_aliases(raw_aliases, cid_map)
    return count, errors


def impl_import_servers(
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Implementation of server import with name tracking."""
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    if raw_servers is None:
        return 0, ["No server data found in import file."], []
    if not isinstance(raw_servers, list):
        return 0, ["Servers in import file must be a list."], []
    cid_map = cid_map or {}
    for entry in raw_servers:
        prepared = prepare_server_import(entry, cid_map, errors)
        if prepared is None:
            continue
        definition_cid = save_server_definition_as_cid(prepared.definition)
        existing = get_server_by_name(prepared.name)
        if existing:
            existing.definition = prepared.definition
            existing.definition_cid = definition_cid
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = prepared.enabled
            save_entity(existing)
        else:
            server = Server(
                name=prepared.name,
                definition=prepared.definition,
                definition_cid=definition_cid,
                enabled=prepared.enabled,
            )
            save_entity(server)
        imported += 1
        names.append(prepared.name)
    if imported:
        update_server_definitions_cid_safe()
    return imported, errors, names


def import_servers_with_names(
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Import servers and return count, errors, and imported names."""
    return impl_import_servers(raw_servers, cid_map)


def import_servers(
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str]]:
    """Import servers and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_servers(raw_servers, cid_map)
    return count, errors


def impl_import_variables(
    raw_variables: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Implementation of variable import with name tracking."""
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    allow_persistence = _has_flask_app_context()
    if raw_variables is None:
        return 0, ["No variable data found in import file."], []
    if not isinstance(raw_variables, list):
        return 0, ["Variables in import file must be a list."], []
    cid_map = cid_map or {}
    for index, entry in enumerate(raw_variables):
        prepared = prepare_variable_import(entry, cid_map, errors, index)
        if prepared is None:
            continue
        if allow_persistence:
            existing = get_variable_by_name(prepared.name)
            if existing:
                existing.definition = prepared.definition
                existing.updated_at = datetime.now(timezone.utc)
                existing.enabled = prepared.enabled
                save_entity(existing)
            else:
                variable = Variable(
                    name=prepared.name,
                    definition=prepared.definition,
                    enabled=prepared.enabled,
                )
                save_entity(variable)
        imported += 1
        names.append(prepared.name)
    if imported and allow_persistence:
        update_variable_definitions_cid_safe()
    return imported, errors, names


def import_variables_with_names(
    raw_variables: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Import variables and return count, errors, and imported names."""
    return impl_import_variables(raw_variables, cid_map)


def import_variables(
    raw_variables: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str]]:
    """Import variables and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_variables(raw_variables, cid_map)
    return count, errors


def impl_import_secrets(raw_secrets: Any, key: str) -> tuple[int, list[str], list[str]]:
    """Implementation of secret import with name tracking."""

    def _normalise_secret_items(value: Any) -> list[dict[str, Any]] | None:
        """Return a list of secret item dicts from either a list or an object with items."""
        if value is None:
            return None
        if isinstance(value, dict):
            items = value.get("items")
            return items if isinstance(items, list) else None
        if isinstance(value, list):
            return value
        return None

    items = _normalise_secret_items(raw_secrets)
    if items is None:
        return 0, ["No secret data found in import file."], []
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    try:
        for entry in items:
            if not isinstance(entry, dict):
                errors.append(
                    "Secret entries must be objects with name and encrypted value."
                )
                continue
            name = entry.get("name")
            ciphertext = entry.get("ciphertext") or entry.get("definition")
            if not name or not ciphertext:
                errors.append("Secret entries must include name and encrypted value.")
                continue
            plaintext = decrypt_secret_value(ciphertext, key)
            enabled = coerce_enabled_flag(entry.get("enabled"))
            existing = get_secret_by_name(name)
            if existing:
                existing.definition = plaintext
                existing.updated_at = datetime.now(timezone.utc)
                existing.enabled = enabled
                save_entity(existing)
            else:
                secret = Secret(
                    name=name,
                    definition=plaintext,
                    enabled=enabled,
                )
                save_entity(secret)
            imported += 1
            names.append(name)
    except ValueError:
        return 0, ["Invalid decryption key for secrets."], []
    if imported:
        update_secret_definitions_cid_safe()
    return imported, errors, names


def import_secrets_with_names(
    raw_secrets: Any, key: str
) -> tuple[int, list[str], list[str]]:
    """Import secrets and return count, errors, and imported names."""
    return impl_import_secrets(raw_secrets, key)


def import_secrets(raw_secrets: Any, key: str) -> tuple[int, list[str]]:
    """Import secrets and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_secrets(raw_secrets, key)
    return count, errors
