"""Entity import functions for aliases, servers, variables, and secrets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from alias_definition import (
    AliasDefinitionError,
    format_primary_alias_line,
    parse_alias_definition,
    replace_primary_definition_line,
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


@dataclass
class AliasImport:
    """Normalized alias entry produced from import payload data."""

    name: str
    definition: str
    enabled: bool
    template: bool


@dataclass
class ServerImport:
    """Normalized server entry produced from import payload data."""

    name: str
    definition: str
    enabled: bool
    template: bool


def prepare_alias_import(
    entry: Any,
    reserved_routes: set[str],
    cid_map: dict[str, bytes],
    errors: list[str],
) -> AliasImport | None:
    """Return a normalized alias import entry when the payload entry is valid."""
    if not isinstance(entry, dict):
        errors.append('Alias entries must be objects with name and definition details.')
        return None

    name_raw = entry.get('name')
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append('Alias entry must include a valid name.')
        return None

    name = name_raw.strip()

    if f'/{name}' in reserved_routes:
        errors.append(f'Alias "{name}" conflicts with an existing route and was skipped.')
        return None

    definition_text: Optional[str] = None
    raw_definition = entry.get('definition')
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Alias "{name}" definition must be text when provided.')
        return None

    definition_cid = normalise_cid(entry.get('definition_cid'))

    if definition_text is None and definition_cid:
        cid_bytes = load_cid_bytes(definition_cid, cid_map)
        if cid_bytes is None:
            errors.append(
                f'Alias "{name}" definition with CID "{definition_cid}" was not included in the import.'
            )
            return None
        try:
            definition_text = cid_bytes.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(
                f'Alias "{name}" definition for CID "{definition_cid}" must be UTF-8 text.'
            )
            return None

    if definition_text is None:
        errors.append(f'Alias "{name}" entry must include either a definition or a definition_cid.')
        return None

    try:
        parsed_definition = parse_alias_definition(definition_text, alias_name=name)
    except AliasDefinitionError as exc:
        errors.append(f'Alias "{name}" definition could not be parsed: {exc}')
        return None

    canonical_primary = format_primary_alias_line(
        parsed_definition.match_type,
        parsed_definition.match_pattern,
        parsed_definition.target_path,
        ignore_case=parsed_definition.ignore_case,
        alias_name=name,
    )
    definition_value = replace_primary_definition_line(
        definition_text,
        canonical_primary,
    )

    enabled = coerce_enabled_flag(entry.get('enabled'))
    template = coerce_enabled_flag(entry.get('template'))

    return AliasImport(
        name=name,
        definition=definition_value,
        enabled=enabled,
        template=template,
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
        errors.append(
            f'Server "{name}" definition with CID "{definition_cid}" was not included in the import.'
        )
        return None
    try:
        return cid_bytes.decode('utf-8')
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
        errors.append('Server entries must be objects with name and definition details.')
        return None

    name_raw = entry.get('name')
    if not isinstance(name_raw, str) or not name_raw.strip():
        errors.append('Server entry must include a valid name.')
        return None

    name = name_raw.strip()
    definition_text: str | None = None
    raw_definition = entry.get('definition')
    if isinstance(raw_definition, str):
        definition_text = raw_definition
    elif raw_definition is not None:
        errors.append(f'Server "{name}" definition must be text.')
        return None

    definition_cid = normalise_cid(entry.get('definition_cid'))
    if definition_text is None and definition_cid:
        definition_text = load_server_definition_from_cid(name, definition_cid, cid_map, errors)

    if definition_text is None:
        errors.append(
            f'Server "{name}" entry must include either a definition or a definition_cid.'
        )
        return None

    enabled = coerce_enabled_flag(entry.get('enabled'))
    template = coerce_enabled_flag(entry.get('template'))

    return ServerImport(
        name=name,
        definition=definition_text,
        enabled=enabled,
        template=template,
    )


def impl_import_aliases(
    user_id: str,
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Implementation of alias import with name tracking."""
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    if raw_aliases is None:
        return 0, ['No alias data found in import file.'], []
    if not isinstance(raw_aliases, list):
        return 0, ['Aliases in import file must be a list.'], []
    reserved_routes = get_existing_routes_safe()
    cid_map = cid_map or {}
    for entry in raw_aliases:
        prepared = prepare_alias_import(entry, reserved_routes, cid_map, errors)
        if prepared is None:
            continue
        existing = get_alias_by_name(user_id, prepared.name)
        if existing:
            existing.definition = prepared.definition
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = prepared.enabled
            existing.template = prepared.template
            save_entity(existing)
        else:
            alias = Alias(
                name=prepared.name,
                user_id=user_id,
                definition=prepared.definition,
                enabled=prepared.enabled,
                template=prepared.template,
            )
            save_entity(alias)
        imported += 1
        names.append(prepared.name)
    return imported, errors, names


def import_aliases_with_names(
    user_id: str,
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Import aliases and return count, errors, and imported names."""
    return impl_import_aliases(user_id, raw_aliases, cid_map)


def import_aliases(
    user_id: str,
    raw_aliases: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str]]:
    """Import aliases and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_aliases(user_id, raw_aliases, cid_map)
    return count, errors


def impl_import_servers(
    user_id: str,
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Implementation of server import with name tracking."""
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    if raw_servers is None:
        return 0, ['No server data found in import file.'], []
    if not isinstance(raw_servers, list):
        return 0, ['Servers in import file must be a list.'], []
    cid_map = cid_map or {}
    for entry in raw_servers:
        prepared = prepare_server_import(entry, cid_map, errors)
        if prepared is None:
            continue
        definition_cid = save_server_definition_as_cid(prepared.definition, user_id)
        existing = get_server_by_name(user_id, prepared.name)
        if existing:
            existing.definition = prepared.definition
            existing.definition_cid = definition_cid
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = prepared.enabled
            existing.template = prepared.template
            save_entity(existing)
        else:
            server = Server(
                name=prepared.name,
                definition=prepared.definition,
                user_id=user_id,
                definition_cid=definition_cid,
                enabled=prepared.enabled,
                template=prepared.template,
            )
            save_entity(server)
        imported += 1
        names.append(prepared.name)
    if imported:
        update_server_definitions_cid_safe(user_id)
    return imported, errors, names


def import_servers_with_names(
    user_id: str,
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str], list[str]]:
    """Import servers and return count, errors, and imported names."""
    return impl_import_servers(user_id, raw_servers, cid_map)


def import_servers(
    user_id: str,
    raw_servers: Any,
    cid_map: dict[str, bytes] | None = None,
) -> tuple[int, list[str]]:
    """Import servers and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_servers(user_id, raw_servers, cid_map)
    return count, errors


def impl_import_variables(user_id: str, raw_variables: Any) -> tuple[int, list[str], list[str]]:
    """Implementation of variable import with name tracking."""
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    if raw_variables is None:
        return 0, ['No variable data found in import file.'], []
    if not isinstance(raw_variables, list):
        return 0, ['Variables in import file must be a list.'], []
    for entry in raw_variables:
        if not isinstance(entry, dict):
            errors.append('Variable entries must be objects with name and definition.')
            continue
        name = entry.get('name')
        definition = entry.get('definition')
        if not name or definition is None:
            errors.append('Variable entry must include both name and definition.')
            continue
        enabled = coerce_enabled_flag(entry.get('enabled'))
        template = coerce_enabled_flag(entry.get('template'))
        existing = get_variable_by_name(user_id, name)
        if existing:
            existing.definition = definition
            existing.updated_at = datetime.now(timezone.utc)
            existing.enabled = enabled
            existing.template = template
            save_entity(existing)
        else:
            variable = Variable(
                name=name,
                definition=definition,
                user_id=user_id,
                enabled=enabled,
                template=template,
            )
            save_entity(variable)
        imported += 1
        names.append(name)
    if imported:
        update_variable_definitions_cid_safe(user_id)
    return imported, errors, names


def import_variables_with_names(user_id: str, raw_variables: Any) -> tuple[int, list[str], list[str]]:
    """Import variables and return count, errors, and imported names."""
    return impl_import_variables(user_id, raw_variables)


def import_variables(user_id: str, raw_variables: Any) -> tuple[int, list[str]]:
    """Import variables and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_variables(user_id, raw_variables)
    return count, errors


def impl_import_secrets(user_id: str, raw_secrets: Any, key: str) -> tuple[int, list[str], list[str]]:
    """Implementation of secret import with name tracking."""

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

    items = _normalise_secret_items(raw_secrets)
    if items is None:
        return 0, ['No secret data found in import file.'], []
    errors: list[str] = []
    imported = 0
    names: list[str] = []
    try:
        for entry in items:
            if not isinstance(entry, dict):
                errors.append('Secret entries must be objects with name and encrypted value.')
                continue
            name = entry.get('name')
            ciphertext = entry.get('ciphertext') or entry.get('definition')
            if not name or not ciphertext:
                errors.append('Secret entries must include name and encrypted value.')
                continue
            plaintext = decrypt_secret_value(ciphertext, key)
            enabled = coerce_enabled_flag(entry.get('enabled'))
            template = coerce_enabled_flag(entry.get('template'))
            existing = get_secret_by_name(user_id, name)
            if existing:
                existing.definition = plaintext
                existing.updated_at = datetime.now(timezone.utc)
                existing.enabled = enabled
                existing.template = template
                save_entity(existing)
            else:
                secret = Secret(
                    name=name,
                    definition=plaintext,
                    user_id=user_id,
                    enabled=enabled,
                    template=template,
                )
                save_entity(secret)
            imported += 1
            names.append(name)
    except ValueError:
        return 0, ['Invalid decryption key for secrets.'], []
    if imported:
        update_secret_definitions_cid_safe(user_id)
    return imported, errors, names


def import_secrets_with_names(user_id: str, raw_secrets: Any, key: str) -> tuple[int, list[str], list[str]]:
    """Import secrets and return count, errors, and imported names."""
    return impl_import_secrets(user_id, raw_secrets, key)


def import_secrets(user_id: str, raw_secrets: Any, key: str) -> tuple[int, list[str]]:
    """Import secrets and return count and errors (legacy interface)."""
    count, errors, _names = impl_import_secrets(user_id, raw_secrets, key)
    return count, errors
