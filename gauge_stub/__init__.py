"""Lightweight Gauge compatibility layer for offline test execution."""

from .python import (
    Messages,
    after_scenario,
    before_scenario,
    before_suite,
    registry,
    step,
)

__all__ = [
    "Messages",
    "after_scenario",
    "before_scenario",
    "before_suite",
    "registry",
    "step",
]
