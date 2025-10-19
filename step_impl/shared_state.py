"""Shared state for Gauge step implementations."""
from __future__ import annotations

from typing import Any

# Global state shared across all step implementations
_scenario_state: dict[str, Any] = {}


def get_scenario_state() -> dict[str, Any]:
    """Get the shared scenario state."""
    return _scenario_state


def clear_scenario_state() -> None:
    """Clear the shared scenario state."""
    _scenario_state.clear()
