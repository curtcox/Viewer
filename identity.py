"""Provide default application resources initialization."""
from __future__ import annotations


_resources_initialized = False


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
    """Ensure default application resources (AI stub and CSS alias) exist.

    This is called during application initialization to set up required resources.
    """
    # pylint: disable=global-statement
    global _resources_initialized

    if not _resources_initialized:
        ensure_ai_stub()
        ensure_css_alias()
        _resources_initialized = True


__all__ = [
    "ensure_default_resources",
    "ensure_ai_stub",
    "ensure_css_alias",
]
