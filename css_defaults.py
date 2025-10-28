"""Helpers for provisioning the default CSS alias."""

from __future__ import annotations

from textwrap import dedent
from typing import Optional

from alias_definition import get_primary_alias_route
from db_access import get_alias_by_name, save_entity
from models import Alias

CSS_ALIAS_NAME = "CSS"
CSS_PRIMARY_PATTERN = "/css/custom.css"
CSS_PRIMARY_TARGET = "/css/default"

_CSS_ALIAS_DEFINITION = dedent(
    """
    css/custom.css -> /css/default
    css/default -> /css/lightmode
    css/lightmode -> /static/css/custom.css
    css/darkmode -> /static/css/custom.css
    """
).strip()


def _normalize_path(value: Optional[str]) -> str:
    """Return the provided path with a single leading slash."""

    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""
    return value if value.startswith("/") else f"/{value}"


def ensure_css_alias_for_user(user_id: str) -> bool:
    """Ensure the CSS alias exists for the supplied user."""

    if not user_id:
        return False

    alias = get_alias_by_name(user_id, CSS_ALIAS_NAME)
    if alias:
        primary_route = get_primary_alias_route(alias)
        if not primary_route:
            alias.definition = _CSS_ALIAS_DEFINITION
            save_entity(alias)
            return True

        target_path = _normalize_path(primary_route.target_path)
        if target_path and target_path != CSS_PRIMARY_TARGET:
            return False

        needs_update = (
            primary_route.match_type != "literal"
            or _normalize_path(primary_route.match_pattern) != CSS_PRIMARY_PATTERN
            or primary_route.ignore_case
        )
        if needs_update:
            alias.definition = _CSS_ALIAS_DEFINITION
            save_entity(alias)
            return True
        return False

    alias = Alias(name=CSS_ALIAS_NAME, user_id=user_id, definition=_CSS_ALIAS_DEFINITION)
    save_entity(alias)
    return True


def ensure_css_alias_for_all_users() -> None:
    """Ensure the default user can access the CSS alias."""

    from identity import ensure_default_user

    user = ensure_default_user()
    ensure_css_alias_for_user(user.id)


__all__ = [
    "CSS_ALIAS_NAME",
    "ensure_css_alias_for_all_users",
    "ensure_css_alias_for_user",
]
