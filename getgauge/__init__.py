"""Lightweight Gauge compatibility layer for offline test execution."""

from .python import after_scenario, before_scenario, before_suite, registry, step

__all__ = [
    "after_scenario",
    "before_scenario",
    "before_suite",
    "registry",
    "step",
]
