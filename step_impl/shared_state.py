"""Shared state for Gauge step implementations."""
from __future__ import annotations

from typing import Any


class Store:
    """Simple storage object for test state."""
    pass


# Global state shared across all step implementations
_scenario_state: dict[str, Any] = {}

# Global store object for attribute-based state storage
store = Store()


def get_scenario_state() -> dict[str, Any]:
    """Get the shared scenario state."""
    return _scenario_state


def clear_scenario_state() -> None:
    """Clear the shared scenario state."""
    _scenario_state.clear()
    # Clear store attributes
    for attr in list(vars(store).keys()):
        delattr(store, attr)
