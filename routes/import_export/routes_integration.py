"""Integration layer to avoid circular imports with routes modules."""

from __future__ import annotations

from typing import Set


def get_existing_routes_safe() -> Set[str]:
    """Get existing routes without circular imports."""
    try:
        from ..core import get_existing_routes

        return get_existing_routes()
    except ImportError:
        return set()


def update_server_definitions_cid_safe() -> None:
    """Update server definitions CID without circular imports."""
    try:
        from ..servers import update_server_definitions_cid

        update_server_definitions_cid()
    except ImportError:
        pass


def update_variable_definitions_cid_safe() -> None:
    """Update variable definitions CID without circular imports."""
    try:
        from ..variables import update_variable_definitions_cid

        update_variable_definitions_cid()
    except ImportError:
        pass


def update_secret_definitions_cid_safe() -> None:
    """Update secret definitions CID without circular imports."""
    try:
        from ..secrets import update_secret_definitions_cid

        update_secret_definitions_cid()
    except ImportError:
        pass
