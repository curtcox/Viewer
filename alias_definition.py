"""Helpers for parsing and formatting alias definitions."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Optional, Sequence
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


@dataclass(frozen=True)
class DefinitionLineSummary:
    """Metadata describing a single line within an alias definition."""

    number: int
    text: str
    is_mapping: bool
    match_type: Optional[str] = None
    match_pattern: Optional[str] = None
    ignore_case: bool = False
    target_path: Optional[str] = None
    parse_error: Optional[str] = None
    alias_path: Optional[str] = None
    depth: int = 0


@dataclass(frozen=True)
class AliasRouteRule:
    """Concrete routing details derived from an alias definition."""

    alias_path: str
    match_type: str
    match_pattern: str
    target_path: str
    ignore_case: bool
    source: Optional[DefinitionLineSummary] = None


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


def _interpret_option_segment(option_segment: str) -> tuple[Optional[str], bool]:
    """Return the selected match type and ignore-case flag for a line."""

    specified_match_type: Optional[str] = None
    ignore_case = False

    for raw_option in option_segment.split(","):
        option = raw_option.strip().lower()
        if not option:
            continue
        if option in _MATCH_TYPE_OPTIONS:
            if specified_match_type and option != specified_match_type:
                raise AliasDefinitionError('Alias definition may specify only one match type.')
            specified_match_type = option
        elif option in _IGNORE_CASE_OPTIONS:
            ignore_case = True
        else:
            raise AliasDefinitionError(f'Unknown alias option "{option}".')

    return specified_match_type, ignore_case


def _parse_line_metadata(
    line: str, alias_name: Optional[str]
) -> tuple[str, str, bool, str]:
    """Return the match configuration for a potential mapping line."""

    stripped = (line or "").strip()
    if not stripped or stripped.startswith("#"):
        raise AliasDefinitionError("Line does not contain an alias mapping.")
    if "->" not in stripped:
        raise AliasDefinitionError("Line does not contain an alias mapping.")

    without_comment = _strip_inline_comment(stripped)
    if "->" not in without_comment:
        raise AliasDefinitionError("Line does not contain an alias mapping.")

    pattern_part, _, remainder = without_comment.partition("->")
    pattern_text = (pattern_part or "").strip()
    target_part = remainder.strip()
    if not target_part:
        raise AliasDefinitionError('Alias definition must include a target path after "->".')

    option_segment = ""
    target_text = target_part
    option_start = target_part.find("[")
    option_end = target_part.find("]") if option_start != -1 else -1

    if option_start != -1:
        if option_end == -1 or option_end < option_start:
            raise AliasDefinitionError('Alias definition options must be closed with "]".')
        option_segment = target_part[option_start + 1 : option_end]
        trailing = target_part[option_end + 1 :].strip()
        if trailing:
            raise AliasDefinitionError('Unexpected text after the closing options bracket.')
        target_text = target_part[:option_start].rstrip()

    target_path = _normalize_target_path(target_text)

    specified_match_type, ignore_case = _interpret_option_segment(option_segment)
    match_type = specified_match_type or "literal"

    try:
        normalised_pattern = normalise_pattern(match_type, pattern_text, alias_name)
    except PatternError as exc:
        raise AliasDefinitionError(str(exc)) from exc

    return match_type, normalised_pattern, ignore_case, target_path


def summarize_definition_lines(
    definition: Optional[str], alias_name: Optional[str] = None
) -> Sequence[DefinitionLineSummary]:
    """Return a summary of each line in the alias definition."""

    if definition is None:
        definition = ""

    lines = definition.splitlines()
    if not lines:
        return []

    summaries: list[DefinitionLineSummary] = []
    base_segments = [segment for segment in (alias_name or "").split("/") if segment]
    segment_stack: list[list[str]] = []

    for index, raw_line in enumerate(lines, start=1):
        text = raw_line.rstrip("\r")
        expanded = text.expandtabs(2)
        indent_length = len(expanded) - len(expanded.lstrip(" "))
        depth = indent_length // 2 if indent_length > 0 else 0
        stripped = text.strip()

        if not stripped or stripped.startswith("#") or "->" not in stripped:
            summaries.append(
                DefinitionLineSummary(
                    number=index,
                    text=text,
                    is_mapping=False,
                    depth=depth,
                )
            )
            continue

        try:
            match_type, match_pattern, ignore_case, target_path = _parse_line_metadata(
                text, alias_name
            )
        except AliasDefinitionError as exc:
            summaries.append(
                DefinitionLineSummary(
                    number=index,
                    text=text,
                    is_mapping=True,
                    parse_error=str(exc),
                    depth=depth,
                )
            )
            continue

        alias_path = None
        resolved_pattern = match_pattern

        parent_segments: list[str] = []
        if depth > 0:
            parent_index = min(depth - 1, len(segment_stack) - 1)
            if parent_index >= 0:
                parent_segments = segment_stack[parent_index]
            if not parent_segments and base_segments:
                parent_segments = base_segments

        if match_type == "literal":
            line_segments = [segment for segment in match_pattern.lstrip("/").split("/") if segment]
            if not line_segments and alias_name:
                line_segments = [alias_name]

            alias_segments = [*parent_segments, *line_segments]
            alias_segments = [segment for segment in alias_segments if segment]
            if alias_segments:
                alias_path = "/".join(alias_segments)
                resolved_pattern = f"/{alias_path}"
            else:
                alias_path = None
                resolved_pattern = match_pattern or "/"

            if len(segment_stack) <= depth:
                segment_stack.extend([[]] * (depth + 1 - len(segment_stack)))
            segment_stack[depth] = alias_segments
            if len(segment_stack) > depth + 1:
                segment_stack[depth + 1 :] = []
        else:
            alias_path = match_pattern.lstrip("/") if match_pattern else None
            if len(segment_stack) > depth:
                segment_stack[depth] = parent_segments
            if len(segment_stack) > depth + 1:
                segment_stack[depth + 1 :] = []

        summaries.append(
            DefinitionLineSummary(
                number=index,
                text=text,
                is_mapping=True,
                match_type=match_type,
                match_pattern=resolved_pattern,
                ignore_case=ignore_case,
                target_path=target_path,
                alias_path=alias_path,
                depth=depth,
            )
        )

    return summaries


def collect_alias_routes(alias) -> Sequence[AliasRouteRule]:
    """Return all routing rules defined for the supplied alias.

    All routes are extracted from the alias definition field. The definition
    must contain at least one valid mapping line (pattern -> target) for routes
    to be generated.
    """

    alias_name = getattr(alias, "name", None) or ""
    definition = getattr(alias, "definition", None)

    summary = summarize_definition_lines(definition, alias_name=alias_name)

    routes: list[AliasRouteRule] = []
    seen: set[tuple[str, str, str, bool]] = set()

    def _register(
        alias_path: Optional[str],
        route_match_type: str,
        route_pattern: Optional[str],
        route_target: Optional[str],
        route_ignore_case: bool,
        source: Optional[DefinitionLineSummary] = None,
    ) -> None:
        if not route_pattern or not route_target:
            return

        key = (route_match_type, route_pattern, route_target, route_ignore_case)
        if key in seen:
            return

        seen.add(key)
        effective_alias_path = alias_path or route_pattern.lstrip("/") or alias_name
        routes.append(
            AliasRouteRule(
                alias_path=effective_alias_path,
                match_type=route_match_type,
                match_pattern=route_pattern,
                target_path=route_target,
                ignore_case=route_ignore_case,
                source=source,
            )
        )

    for entry in summary:
        if not entry.is_mapping or entry.parse_error:
            continue

        route_match_type = entry.match_type or "literal"
        route_pattern = entry.match_pattern or (
            f"/{entry.alias_path}" if entry.alias_path else None
        )
        route_target = entry.target_path
        route_ignore_case = entry.ignore_case
        _register(entry.alias_path, route_match_type, route_pattern, route_target, route_ignore_case, entry)

    return routes


__all__ = [
    "AliasDefinitionError",
    "AliasRouteRule",
    "ParsedAliasDefinition",
    "parse_alias_definition",
    "definition_contains_mapping",
    "format_primary_alias_line",
    "ensure_primary_line",
    "DefinitionLineSummary",
    "summarize_definition_lines",
    "collect_alias_routes",
]
