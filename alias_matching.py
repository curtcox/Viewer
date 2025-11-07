"""Utilities for validating and matching alias patterns."""
from __future__ import annotations

import fnmatch
import re
from typing import Iterable

from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import Map, RequestRedirect, Rule


class PatternError(ValueError):
    """Raised when an alias pattern cannot be normalised."""


_TYPE_PRIORITY = {
    "literal": 0,
    "flask": 1,
    "glob": 2,
    "regex": 3,
}


def _ensure_leading_slash(value: str) -> str:
    """Return the value with a single leading slash."""

    if not value:
        return "/"
    return "/" + value.lstrip("/")


def _normalize_literal_path(value: str) -> str:
    """Return the literal path without a trailing slash (except for root)."""

    if value == "/":
        return "/"
    return value.rstrip("/") or "/"


def normalise_pattern(match_type: str, pattern: str | None, fallback_name: str | None = None) -> str:
    """Return a cleaned version of the provided pattern or raise PatternError."""

    match_type = (match_type or "literal").lower()
    raw_pattern = (pattern or "").strip()
    fallback_name = (fallback_name or "").strip()

    if match_type == "literal":
        if not raw_pattern:
            if not fallback_name:
                raise PatternError("Literal aliases require a pattern or name.")
            raw_pattern = fallback_name
        if "\n" in raw_pattern:
            raise PatternError("Literal patterns must be a single line.")
        return _normalize_literal_path(_ensure_leading_slash(raw_pattern))

    if match_type == "glob":
        if not raw_pattern:
            raise PatternError("Glob aliases require a pattern.")
        # fnmatch handles validation implicitly; translate will raise for invalid groups.
        fnmatch.translate(raw_pattern)
        return _ensure_leading_slash(raw_pattern)

    if match_type == "regex":
        if not raw_pattern:
            raise PatternError("Regular expression aliases require a pattern.")
        try:
            re.compile(raw_pattern)
        except re.error as exc:  # pragma: no cover - defensive guard
            raise PatternError(f"Invalid regular expression: {exc}") from exc
        return raw_pattern

    if match_type == "flask":
        if not raw_pattern:
            raise PatternError("Flask-style aliases require a pattern.")
        cleaned = _ensure_leading_slash(raw_pattern)
        try:
            Rule(cleaned)
        except (ValueError, TypeError) as exc:  # pragma: no cover - werkzeug provides descriptive errors
            raise PatternError(f"Invalid Flask pattern: {exc}") from exc
        return cleaned

    raise PatternError(f"Unknown match type: {match_type}")


def matches_path(match_type: str, pattern: str, path: str, ignore_case: bool = False) -> bool:
    """Return True when the given path satisfies the pattern for the match type."""

    if not path:
        return False

    match_type = (match_type or "literal").lower()
    candidate = path if path.startswith("/") else "/" + path

    if match_type == "literal":
        cleaned_pattern = _ensure_leading_slash(pattern)
        if ignore_case:
            candidate_cf = candidate.casefold()
            pattern_cf = cleaned_pattern.casefold()
            if candidate_cf == pattern_cf:
                return True
            return (
                _normalize_literal_path(candidate).casefold()
                == _normalize_literal_path(cleaned_pattern).casefold()
            )
        if candidate == cleaned_pattern:
            return True
        return _normalize_literal_path(candidate) == _normalize_literal_path(cleaned_pattern)

    if match_type == "glob":
        cleaned_pattern = _ensure_leading_slash(pattern)
        translated = fnmatch.translate(cleaned_pattern)
        flags = re.IGNORECASE if ignore_case else 0
        compiled = re.compile(translated, flags)
        return compiled.fullmatch(candidate) is not None

    if match_type == "regex":
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error:
            return False
        return compiled.fullmatch(candidate) is not None

    if match_type == "flask":
        cleaned_pattern = _ensure_leading_slash(pattern)
        try:
            url_map = Map([Rule(cleaned_pattern)])
            adapter = url_map.bind("", url_scheme="http")
            adapter.match(candidate, method="GET")
        except (NotFound, MethodNotAllowed):
            return False
        except (ValueError, RuntimeError, AttributeError, RequestRedirect):  # pragma: no cover - defensive guard for malformed patterns and redirects
            return False
        return True

    return False


def alias_sort_key(match_type: str, pattern: str) -> tuple[int, int]:
    """Return a tuple for consistent alias prioritisation during matching."""

    match_type = (match_type or "literal").lower()
    priority = _TYPE_PRIORITY.get(match_type, len(_TYPE_PRIORITY))
    return (priority, -len(pattern or ""))


def evaluate_test_strings(
    match_type: str,
    pattern: str,
    values: Iterable[str],
    ignore_case: bool = False,
) -> list[tuple[str, bool]]:
    """Return the evaluation results for the provided set of values."""

    results: list[tuple[str, bool]] = []
    for raw_value in values:
        value = raw_value.strip()
        if not value:
            continue
        candidate = value if value.startswith("/") else "/" + value
        matches = matches_path(match_type, pattern, candidate, ignore_case)
        results.append((raw_value, matches))
    return results


__all__ = [
    "PatternError",
    "alias_sort_key",
    "evaluate_test_strings",
    "matches_path",
    "normalise_pattern",
]
