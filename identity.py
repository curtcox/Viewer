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
    definitions_dir = Path(__file__).parent / "reference_templates" / "servers" / "definitions"

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
