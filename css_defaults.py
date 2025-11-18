"""Helpers for provisioning the default CSS alias."""

from __future__ import annotations

from textwrap import dedent

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


def _css_alias_needs_upgrade(definition: str | None) -> bool:
    """Return True when the stored definition lacks the theme redirects."""

    if not definition:
        return True

    lines = [line.strip() for line in definition.splitlines() if line.strip()]
    if "css/custom.css -> /css/default" not in lines:
        return False

    has_light = any(line.startswith("css/lightmode ->") for line in lines)
    has_dark = any(line.startswith("css/darkmode ->") for line in lines)
    outdated_default = any(line == "css/default -> /static/css/custom.css" for line in lines)

    if outdated_default:
        return True

    return not has_light or not has_dark


def ensure_css_alias() -> bool:
    """Ensure the CSS alias exists."""

    from db_access import (  # pylint: disable=import-outside-toplevel
        get_alias_by_name,
        save_entity,
    )

    alias = get_alias_by_name(CSS_ALIAS_NAME)
    if alias:
        needs_upgrade = _css_alias_needs_upgrade(getattr(alias, "definition", None))
        if alias.definition and alias.definition.strip() and not needs_upgrade:
            return False
        alias.definition = _CSS_ALIAS_DEFINITION
        save_entity(alias)
        return True

    alias = Alias(name=CSS_ALIAS_NAME, definition=_CSS_ALIAS_DEFINITION)
    save_entity(alias)
    return True


__all__ = [
    "CSS_ALIAS_NAME",
    "ensure_css_alias",
]
