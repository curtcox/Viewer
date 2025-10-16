"""Provide Gauge decorator shims when the real package is unavailable."""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any, Callable, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


_before_suite_hooks: list[Callable[..., Any]] = []
_before_scenario_hooks: list[Callable[..., Any]] = []
_registered_steps: list[tuple[str, Callable[..., Any]]] = []


if importlib.util.find_spec("getgauge") is not None:
    gauge_module = importlib.import_module("getgauge.python")

    def before_suite(func: T | None = None) -> Callable[[T], T] | T:
        """Register a before-suite hook with Gauge and the shim."""

        def decorator(inner: T) -> T:
            _before_suite_hooks.append(inner)
            gauge_module.before_suite(inner)  # type: ignore[attr-defined]
            return inner

        if func is None:
            return decorator

        return decorator(func)

    def before_scenario(func: T | None = None) -> Callable[[T], T] | T:
        """Register a before-scenario hook with Gauge and the shim."""

        def decorator(inner: T) -> T:
            _before_scenario_hooks.append(inner)
            gauge_module.before_scenario(inner)  # type: ignore[attr-defined]
            return inner

        if func is None:
            return decorator

        return decorator(func)

    def step(pattern: str) -> Callable[[T], T]:
        """Register a Gauge step implementation with Gauge and the shim."""

        def decorator(func: T) -> T:
            _registered_steps.append((pattern, func))
            gauge_module.step(pattern)(func)  # type: ignore[attr-defined]
            return func

        return decorator
else:
    def before_suite(func: T | None = None) -> Callable[[T], T] | T:
        """Register a function to run once before any scenarios execute."""

        def decorator(inner: T) -> T:
            _before_suite_hooks.append(inner)
            return inner

        if func is None:
            return decorator

        return decorator(func)

    def before_scenario(func: T | None = None) -> Callable[[T], T] | T:
        """Register a function to run before each scenario."""

        def decorator(inner: T) -> T:
            _before_scenario_hooks.append(inner)
            return inner

        if func is None:
            return decorator

        return decorator(func)

    def step(pattern: str) -> Callable[[T], T]:
        """Register a Gauge step implementation for the lightweight runner."""

        def decorator(func: T) -> T:
            _registered_steps.append((pattern, func))
            return func

        return decorator


def iter_before_suite_hooks() -> tuple[Callable[..., Any], ...]:
    """Return the registered before-suite hooks."""

    return tuple(_before_suite_hooks)


def iter_before_scenario_hooks() -> tuple[Callable[..., Any], ...]:
    """Return the registered before-scenario hooks."""

    return tuple(_before_scenario_hooks)


def iter_registered_steps() -> tuple[tuple[str, Callable[..., Any]], ...]:
    """Return the Gauge-style step implementations."""

    return tuple(_registered_steps)


__all__ = [
    "before_suite",
    "before_scenario",
    "step",
    "iter_before_suite_hooks",
    "iter_before_scenario_hooks",
    "iter_registered_steps",
]
