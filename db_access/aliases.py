"""Alias CRUD operations and CID reference management."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from models import Alias
from database import db
from alias_definition import (
    AliasDefinitionError,
    ParsedAliasDefinition,
    collect_alias_routes,
    format_primary_alias_line,
    parse_alias_definition,
    replace_primary_definition_line,
)
from db_access._common import (
    DEFAULT_AI_ALIAS_NAME,
    DEFAULT_CSS_ALIAS_NAME,
    normalize_cid_value,
    save_entity,
)
from db_access.variables import get_user_variables
from identity import ensure_default_user

logger = logging.getLogger(__name__)

# Result dictionary keys
RESULT_KEY_CREATED = "created"
RESULT_KEY_UPDATED = "updated"


def get_user_aliases(user_id: str) -> List[Alias]:
    """Return all aliases for a user ordered by name."""
    return Alias.query.filter_by(user_id=user_id).order_by(Alias.name).all()


def get_user_template_aliases(user_id: str) -> List[Alias]:
    """Return template aliases for a user ordered by name."""
    return (
        Alias.query.filter_by(user_id=user_id, template=True)
        .order_by(Alias.name)
        .all()
    )


def get_alias_by_name(user_id: str, name: str) -> Optional[Alias]:
    """Return an alias by name for a user."""
    return Alias.query.filter_by(user_id=user_id, name=name).first()


def get_first_alias_name(user_id: str) -> Optional[str]:
    """Return the first alias name for a user ordered alphabetically."""
    # Prefer user-created aliases over the default AI helper when available.
    preferred = (
        Alias.query.filter_by(user_id=user_id)
        .filter(Alias.name.notin_([DEFAULT_AI_ALIAS_NAME, DEFAULT_CSS_ALIAS_NAME]))
        .order_by(Alias.name.asc())
        .first()
    )
    if preferred is not None:
        return preferred.name

    fallback = (
        Alias.query.filter_by(user_id=user_id)
        .order_by(Alias.name.asc())
        .first()
    )
    return fallback.name if fallback else None


def _get_variable_map(user_id: str) -> Dict[str, str]:
    """Get enabled variables as a name->definition map."""
    try:
        variables = get_user_variables(user_id)
    except SQLAlchemyError as exc:
        logger.warning("Failed to load variables for user %s: %s", user_id, exc)
        return {}

    return {
        variable.name: variable.definition
        for variable in variables
        if variable.enabled and variable.name and variable.definition is not None
    }


def get_alias_by_target_path(user_id: str, target_path: str) -> Optional[Alias]:
    """Return an alias that matches the target path."""
    normalized = (target_path or "").strip()
    if not normalized:
        return None

    candidates = {normalized}
    alternate = f"/{normalized.lstrip('/')}"
    candidates.add(alternate)

    aliases = (
        Alias.query.filter_by(user_id=user_id)
        .order_by(Alias.id.asc())
        .all()
    )

    variable_map = _get_variable_map(user_id)

    for alias in aliases:
        for route in collect_alias_routes(alias, variables=variable_map):
            if route.match_type != "literal":
                continue
            route_target = (route.target_path or "").strip()
            if not route_target:
                continue
            if route_target in candidates:
                return alias

    return None


def count_user_aliases(user_id: str) -> int:
    """Return the count of aliases for a user."""
    return Alias.query.filter_by(user_id=user_id).count()


@dataclass
class AliasUpdateResult:
    """Result of an alias CID reference update operation."""

    created: bool
    updated: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format for backward compatibility."""
        return {RESULT_KEY_CREATED: self.created, RESULT_KEY_UPDATED: self.updated}


def _safe_parse_definition(
    definition: Optional[str], alias_name: str
) -> Optional[ParsedAliasDefinition]:
    """Parse alias definition, returning None on error."""
    if not definition:
        return None
    try:
        return parse_alias_definition(definition, alias_name=alias_name)
    except AliasDefinitionError:
        return None


def _create_new_alias(alias_name: str, cid: str) -> AliasUpdateResult:
    """Create a new alias pointing to the given CID."""
    owner = ensure_default_user()
    primary_line = format_primary_alias_line(
        "literal",
        None,
        f"/{cid}",
        alias_name=alias_name,
    )
    alias = Alias(
        name=alias_name,
        user_id=owner.id,
        definition=primary_line,
    )

    save_entity(alias)
    return AliasUpdateResult(created=True, updated=1)


def _update_existing_aliases(
    aliases: List[Alias], old_cid: str, new_cid: str
) -> AliasUpdateResult:
    """Update existing aliases to point to new CID."""
    if old_cid and old_cid == new_cid:
        return AliasUpdateResult(created=False, updated=0)

    new_path = f"/{new_cid}"
    old_path = f"/{old_cid}" if old_cid else None
    now = datetime.now(timezone.utc)
    updated_count = 0

    for alias in aliases:
        alias_changed = False

        original_definition = alias.definition
        updated_definition = original_definition
        definition_changed = False

        existing_ignore_case = False
        parsed_existing = _safe_parse_definition(
            original_definition, alias_name=alias.name
        )

        if parsed_existing:
            existing_ignore_case = parsed_existing.ignore_case

        if old_cid:
            updated_definition, definition_changed = _replace_cid_text(
                original_definition,
                old_path,
                new_path,
                old_cid,
                new_cid,
            )

        desired_target_path = new_path
        parsed_current = _safe_parse_definition(updated_definition, alias_name=alias.name)
        if parsed_current:
            existing_ignore_case = parsed_current.ignore_case
            if parsed_current.target_path:
                desired_target_path = parsed_current.target_path

        if new_path:
            primary_line = format_primary_alias_line(
                "literal",
                None,
                desired_target_path,
                ignore_case=existing_ignore_case,
                alias_name=alias.name,
            )
            current_definition = updated_definition or ""
            updated_definition = replace_primary_definition_line(
                updated_definition,
                primary_line,
            )
            if updated_definition != current_definition:
                definition_changed = True

        if definition_changed:
            alias.definition = updated_definition
            alias_changed = True

        if alias_changed:
            alias.updated_at = now
            updated_count += 1

    if updated_count:
        db.session.commit()

    return AliasUpdateResult(created=False, updated=updated_count)


def update_alias_cid_reference(
    old_cid: str,
    new_cid: str,
    alias_name: str,
) -> Dict[str, int]:
    """Ensure an alias points to the supplied CID and update its definition.

    Parameters
    ----------
    old_cid:
        The previous CID value associated with the alias. Leading slashes are
        ignored. When empty no text replacement is attempted.
    new_cid:
        The CID that should replace the previous value. Leading slashes are
        ignored.
    alias_name:
        The alias to update. When no alias exists a new record is created for
        the default user.

    Returns
    -------
    Dict[str, int]
        A mapping describing whether an alias was created and how many existing
        aliases were updated.
    """
    normalized_alias = (alias_name or "").strip()
    normalized_new = normalize_cid_value(new_cid)

    if not normalized_alias or not normalized_new:
        return AliasUpdateResult(created=False, updated=0).to_dict()

    aliases: List[Alias] = Alias.query.filter_by(name=normalized_alias).all()

    if not aliases:
        return _create_new_alias(normalized_alias, normalized_new).to_dict()

    normalized_old = normalize_cid_value(old_cid)
    return _update_existing_aliases(aliases, normalized_old, normalized_new).to_dict()


def _replace_cid_text(
    text: Optional[str],
    old_path: str,
    new_path: str,
    old_value: str,
    new_value: str,
) -> Tuple[Optional[str], bool]:
    """Return text with CID references replaced and whether a change occurred."""
    if text is None:
        return None, False

    updated = text.replace(old_path, new_path).replace(old_value, new_value)
    if updated == text:
        return text, False
    return updated, True
