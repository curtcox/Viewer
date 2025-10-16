"""Provide Gauge decorator shims when the real package is unavailable."""
from __future__ import annotations

import importlib
import importlib.util
from typing import Any, Callable, TypeVar

T = TypeVar("T", bound=Callable[..., Any])


def _optional_identity_decorator(func: T | None = None) -> Callable[[T], T] | T:
    """Support decorators that may be invoked with or without parentheses."""

    if func is None:
        def decorator(inner: T) -> T:
            return inner

        return decorator

    return func


if importlib.util.find_spec("getgauge") is not None:
    gauge_module = importlib.import_module("getgauge.python")

    before_suite = gauge_module.before_suite  # type: ignore[attr-defined]
    before_scenario = gauge_module.before_scenario  # type: ignore[attr-defined]
    step = gauge_module.step  # type: ignore[attr-defined]
else:
    def before_suite(func: T | None = None) -> Callable[[T], T] | T:
        return _optional_identity_decorator(func)

    def before_scenario(func: T | None = None) -> Callable[[T], T] | T:
        return _optional_identity_decorator(func)

    def step(_pattern: str) -> Callable[[T], T]:
        def decorator(func: T) -> T:
            return func

        return decorator


__all__ = ["before_suite", "before_scenario", "step"]
