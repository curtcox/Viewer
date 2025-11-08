"""Minimal Gauge compatibility layer used for executing specs offline."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from uuid import uuid4


@dataclass
class StepDefinition:
    """Store metadata for a registered Gauge step."""

    pattern: str
    func: Callable[..., Any]
    regex: re.Pattern[str]
    positional_groups: List[int]
    named_groups: Dict[str, int]

    def match(self, step_text: str) -> Optional["StepMatch"]:
        match = self.regex.fullmatch(step_text)  # pylint: disable=no-member  # re.Pattern has fullmatch
        if match is None:
            return None
        args = [match.group(index) for index in self.positional_groups]
        kwargs = {name: match.group(index) for name, index in self.named_groups.items()}
        return StepMatch(self.func, args, kwargs)


@dataclass
class StepMatch:
    """Represent a successful match between a step definition and a step text."""

    func: Callable[..., Any]
    args: List[str]
    kwargs: Dict[str, str]

    def execute(self) -> None:
        self.func(*self.args, **self.kwargs)


class StepRegistry:
    """Book-keeping for hooks and step definitions."""

    def __init__(self) -> None:
        self._before_suite: List[Callable[[], Any]] = []
        self._before_scenario: List[Callable[[], Any]] = []
        self._after_scenario: List[Callable[[], Any]] = []
        self._steps: List[StepDefinition] = []

    @property
    def before_suite_hooks(self) -> Iterable[Callable[[], Any]]:
        return tuple(self._before_suite)

    @property
    def before_scenario_hooks(self) -> Iterable[Callable[[], Any]]:
        return tuple(self._before_scenario)

    @property
    def after_scenario_hooks(self) -> Iterable[Callable[[], Any]]:
        return tuple(self._after_scenario)

    @property
    def step_definitions(self) -> Iterable[StepDefinition]:
        return tuple(self._steps)

    def add_before_suite(self, func: Callable[[], Any]) -> Callable[[], Any]:
        self._before_suite.append(func)
        return func

    def add_before_scenario(self, func: Callable[[], Any]) -> Callable[[], Any]:
        self._before_scenario.append(func)
        return func

    def add_after_scenario(self, func: Callable[[], Any]) -> Callable[[], Any]:
        self._after_scenario.append(func)
        return func

    def add_step(self, pattern: str, func: Callable[..., Any]) -> Callable[..., Any]:
        regex, positional_groups, named_groups = _parse_pattern(pattern)
        definition = StepDefinition(
            pattern=pattern,
            func=func,
            regex=regex,
            positional_groups=positional_groups,
            named_groups=named_groups,
        )
        self._steps.append(definition)
        return func


registry = StepRegistry()


def before_suite() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function to run once before any scenarios execute."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return registry.add_before_suite(func)

    return decorator


def before_scenario() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function to run before each scenario begins."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return registry.add_before_scenario(func)

    return decorator


def after_scenario() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function to run after each scenario completes."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return registry.add_after_scenario(func)

    return decorator


def step(pattern: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a Gauge step definition."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return registry.add_step(pattern, func)

    return decorator


def _parse_pattern(pattern: str) -> Tuple[re.Pattern[str], List[int], Dict[str, int]]:
    parts: List[str] = []
    positional_indices: List[int] = []
    named_indices: Dict[str, int] = {}
    index = 0
    group_index = 0

    while index < len(pattern):
        if pattern.startswith("{}", index):
            group_index += 1
            positional_indices.append(group_index)
            parts.append("(.+?)")
            index += 2
            continue
        if pattern[index] == "<":
            end = pattern.find(">", index + 1)
            if end == -1:
                raise ValueError(f"Unmatched '<' in pattern: {pattern}")
            name = pattern[index + 1 : end].strip()
            group_index += 1
            named_indices[name] = group_index
            parts.append("(.+?)")
            index = end + 1
            continue
        parts.append(re.escape(pattern[index]))
        index += 1

    regex = re.compile("^" + "".join(parts) + "$")
    return regex, positional_indices, named_indices
class Messages:
    """Minimal Gauge Messages implementation used by the local stub."""

    @staticmethod
    def write_message(message: str) -> None:
        print(f"[Gauge] {message}")

    @staticmethod
    def attach_binary(data: bytes, mime_type: str, file_name: str) -> None:
        path = Messages._persist_bytes(data, file_name)
        print(f"[Gauge] Saved attachment to {path} ({mime_type})")

    @staticmethod
    def add_attachment(file_path: str, description: str | None = None) -> None:
        source = Path(file_path)
        if not source.exists():
            raise FileNotFoundError(f"Attachment not found: {file_path}")

        target = Messages._persist_bytes(source.read_bytes(), source.name)
        suffix = f" ({description})" if description else ""
        print(f"[Gauge] Registered attachment {target}{suffix}")

    @staticmethod
    def _persist_bytes(data: bytes, file_name: str) -> Path:
        directory = Path(os.environ.get("GAUGE_ARTIFACT_DIR", "gauge-artifacts"))
        directory.mkdir(parents=True, exist_ok=True)

        sanitized = file_name.replace("/", "-").replace("\\", "-").strip()
        if not sanitized:
            sanitized = f"attachment-{uuid4().hex}.bin"

        path = directory / sanitized
        path.write_bytes(data)
        return path
