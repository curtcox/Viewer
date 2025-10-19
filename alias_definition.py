"""Helpers for parsing and formatting alias definitions."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Optional
from urllib.parse import urlsplit

from alias_matching import PatternError, normalise_pattern


class AliasDefinitionError(ValueError):
    """Raised when an alias definition cannot be interpreted."""


@dataclass(frozen=True)
class ParsedAliasDefinition:
    """Structured representation of the primary alias definition line."""

    match_type: str
    match_pattern: str
    target_path: str
    ignore_case: bool
    pattern_text: str


_COMMENT_PATTERN = re.compile(r"\s+#.*$")
_MATCH_TYPE_OPTIONS = {"literal", "glob", "regex", "flask"}
_IGNORE_CASE_OPTIONS = {"ignore-case", "ignorecase"}


def _strip_inline_comment(line: str) -> str:
    """Remove trailing inline comments introduced with #."""

    if not line:
        return ""
    return _COMMENT_PATTERN.sub("", line).rstrip()


def _normalize_target_path(raw: str) -> str:
    """Ensure the alias target path stays within the application."""

    value = (raw or "").strip()
    if not value:
        raise AliasDefinitionError('Alias definition must include a target path after "->".')
    if value.startswith("//"):
        raise AliasDefinitionError('Alias target path must stay within this application.')

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise AliasDefinitionError('Alias target path must stay within this application.')
    return value


def _extract_primary_line(definition: str) -> Optional[str]:
    """Return the first mapping line from the definition, if any."""

    for raw_line in definition.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "->" not in stripped:
            continue
        return stripped
    return None


def parse_alias_definition(definition: str, alias_name: Optional[str] = None) -> ParsedAliasDefinition:
    """Parse the definition text and return the primary alias configuration."""

    if definition is None:
        definition = ""

    primary_line = _extract_primary_line(definition)
    if not primary_line:
        raise AliasDefinitionError('Alias definition must include a "pattern -> target" line.')

    without_comment = _strip_inline_comment(primary_line)
    if "->" not in without_comment:
        raise AliasDefinitionError('Alias definition must include a "pattern -> target" line.')

    pattern_part, _, remainder = without_comment.partition("->")
    pattern_text = (pattern_part or "").strip()
    if not remainder:
        raise AliasDefinitionError('Alias definition must include a target path after "->".')

    target_part = remainder.strip()
    options: Iterable[str]
    option_start = target_part.find("[")
    option_end = target_part.find("]") if option_start != -1 else -1

    if option_start != -1:
        if option_end == -1 or option_end < option_start:
            raise AliasDefinitionError('Alias definition options must be closed with "]".')
        option_segment = target_part[option_start + 1 : option_end]
        target_text = target_part[:option_start].strip()
        trailing = target_part[option_end + 1 :].strip()
        if trailing:
            raise AliasDefinitionError('Unexpected text after the closing options bracket.')
        options = (opt.strip().lower() for opt in option_segment.split(",") if opt.strip())
    else:
        target_text = target_part
        options = ()

    match_type = "literal"
    ignore_case = False
    specified_match_type: Optional[str] = None

    for option in options:
        if option in _MATCH_TYPE_OPTIONS:
            if specified_match_type and option != specified_match_type:
                raise AliasDefinitionError('Alias definition may specify only one match type.')
            specified_match_type = option
        elif option in _IGNORE_CASE_OPTIONS:
            ignore_case = True
        else:
            raise AliasDefinitionError(f'Unknown alias option "{option}".')

    if specified_match_type:
        match_type = specified_match_type

    try:
        normalised_pattern = normalise_pattern(match_type, pattern_text, alias_name)
    except PatternError as exc:
        raise AliasDefinitionError(str(exc)) from exc

    target_path = _normalize_target_path(target_text)

    return ParsedAliasDefinition(
        match_type=match_type,
        match_pattern=normalised_pattern,
        target_path=target_path,
        ignore_case=ignore_case,
        pattern_text=pattern_text or (alias_name or ""),
    )


def definition_contains_mapping(definition: Optional[str]) -> bool:
    """Return True when the definition already includes a mapping line."""

    if not definition:
        return False
    return _extract_primary_line(definition) is not None


def format_primary_alias_line(
    match_type: str,
    match_pattern: Optional[str],
    target_path: str,
    ignore_case: bool = False,
    alias_name: Optional[str] = None,
) -> str:
    """Render a canonical primary definition line for the alias."""

    match_type = (match_type or "literal").lower()
    display_pattern = _display_pattern(match_type, match_pattern, alias_name)

    options: list[str] = []
    if match_type != "literal":
        options.append(match_type)
    if ignore_case:
        options.append("ignore-case")

    option_text = f" [{', '.join(options)}]" if options else ""
    return f"{display_pattern} -> {target_path}{option_text}"


def _display_pattern(match_type: str, match_pattern: Optional[str], alias_name: Optional[str]) -> str:
    if match_type == "literal":
        candidate = (alias_name or "").strip() or (match_pattern or "").lstrip("/")
        return candidate or "/"
    return (match_pattern or "").strip()


def ensure_primary_line(definition: Optional[str], primary_line: str) -> str:
    """Ensure the definition text includes the provided primary line."""

    if not definition or not definition.strip():
        return primary_line

    if definition_contains_mapping(definition):
        return definition

    cleaned = definition.strip()
    if not cleaned:
        return primary_line

    return f"{primary_line}\n\n{cleaned}"


__all__ = [
    "AliasDefinitionError",
    "ParsedAliasDefinition",
    "parse_alias_definition",
    "definition_contains_mapping",
    "format_primary_alias_line",
    "ensure_primary_line",
]
