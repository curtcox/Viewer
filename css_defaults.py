"""Helpers for provisioning the default CSS alias."""

from __future__ import annotations

from textwrap import dedent

from db_access import get_alias_by_name, save_entity
from models import Alias

CSS_ALIAS_NAME = "CSS"

_CSS_ALIAS_DEFINITION = dedent(
    """
    css/custom.css -> /css/default
    css/default -> /css/lightmode
    css/lightmode -> /static/css/custom.css
    css/darkmode -> /static/css/custom.css
    """
).strip()


def ensure_css_alias_for_user(user_id: str) -> bool:
    """Ensure the CSS alias exists for the supplied user."""

    if not user_id:
        return False

    alias = get_alias_by_name(user_id, CSS_ALIAS_NAME)
    if alias:
        if alias.definition and alias.definition.strip():
            return False
        alias.definition = _CSS_ALIAS_DEFINITION
        save_entity(alias)
        return True

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
