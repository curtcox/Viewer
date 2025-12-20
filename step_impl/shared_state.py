"""Shared state for Gauge step implementations."""
from __future__ import annotations

from typing import Any

# Global state shared across all step implementations
_scenario_state: dict[str, Any] = {}


class _ScenarioStore:
    def __getattr__(self, name: str) -> Any:
        try:
            return _scenario_state[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        _scenario_state[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del _scenario_state[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


store = _ScenarioStore()


def get_scenario_state() -> dict[str, Any]:
    """Get the shared scenario state."""
    return _scenario_state


def clear_scenario_state() -> None:
    """Clear the shared scenario state."""
    _scenario_state.clear()
