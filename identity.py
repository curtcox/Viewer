"""Provide default application resources initialization."""

from __future__ import annotations

from pathlib import Path


def ensure_ai_stub() -> bool:
    """Ensure the default AI stub server exists."""

    from ai_defaults import (  # pylint: disable=import-outside-toplevel
        ensure_ai_stub,
    )

    return ensure_ai_stub()


def ensure_css_alias() -> bool:
    """Ensure the CSS alias exists."""

    from css_defaults import (  # pylint: disable=import-outside-toplevel
        ensure_css_alias,
    )

    return ensure_css_alias()


def ensure_default_resources() -> None:
    """Ensure default application resources (AI stub and CSS alias) exist."""

    ensure_ai_stub()
    ensure_css_alias()
    _ensure_cookie_editor_alias()
    _ensure_editor_servers()


__all__ = [
    "ensure_default_resources",
    "ensure_ai_stub",
    "ensure_css_alias",
]


def _ensure_editor_servers() -> None:
    """Ensure the AI and URL editor servers are available and enabled."""

    from database import db  # pylint: disable=import-outside-toplevel
    from models import Server  # pylint: disable=import-outside-toplevel

    editor_names = ("ai_editor", "urleditor")
    definitions_dir = (
        Path(__file__).parent / "reference/templates" / "servers" / "definitions"
    )

    changed = False

    for server_name in editor_names:
        definition_path = definitions_dir / f"{server_name}.py"
        if not definition_path.exists():
            continue

        definition = definition_path.read_text(encoding="utf-8")
        server = Server.query.filter_by(name=server_name).first()

        if server:
            updated = False
            if server.definition != definition:
                server.definition = definition
                updated = True
            if not getattr(server, "enabled", False):
                server.enabled = True
                updated = True
            changed = changed or updated
        else:
            db.session.add(
                Server(
                    name=server_name,
                    definition=definition,
                    enabled=True,
                )
            )
            changed = True

    if changed:
        db.session.commit()


def _ensure_cookie_editor_alias() -> None:
    from db_access import get_alias_by_name, save_entity  # pylint: disable=import-outside-toplevel
    from models import Alias  # pylint: disable=import-outside-toplevel

    alias_path = (
        Path(__file__).parent / "reference/templates" / "aliases" / "cookies.txt"
    )
    if not alias_path.exists():
        return

    desired_definition = alias_path.read_text(encoding="utf-8").strip()
    if not desired_definition:
        return

    alias_name = "cookies"
    alias = get_alias_by_name(alias_name)
    if alias:
        if (alias.definition or "").strip() != desired_definition:
            alias.definition = desired_definition
            save_entity(alias)
        return

    save_entity(Alias(name=alias_name, definition=desired_definition))
