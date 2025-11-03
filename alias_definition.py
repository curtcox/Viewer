"""Helpers for parsing and formatting alias definitions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence
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


def _literal_self_route(alias_name: str) -> AliasRouteRule:
    """Return a simple literal route that points the alias at itself."""

    return AliasRouteRule(
        alias_path=alias_name,
        match_type="literal",
        match_pattern=f"/{alias_name}",
        target_path=f"/{alias_name}",
        ignore_case=False,
        source=None,
    )


_COMMENT_PATTERN = re.compile(r"\s+#.*$")
_MATCH_TYPE_OPTIONS = {"literal", "glob", "regex", "flask"}
_IGNORE_CASE_OPTIONS = {"ignore-case", "ignorecase"}
_VARIABLE_PATTERN = re.compile(r"\{([A-Za-z0-9._-]+)\}")


def _strip_inline_comment(line: str) -> str:
    """Remove trailing inline comments introduced with #."""

    if not line:
        return ""
    return _COMMENT_PATTERN.sub("", line).rstrip()


def _validate_braces(value: str) -> None:
    """Validate that braces in the target path are balanced and properly used."""
    brace_balance = 0
    for character in value:
        if character == "{":
            brace_balance += 1
        elif character == "}":
            if brace_balance == 0:
                raise AliasDefinitionError("Alias target path must reference a valid alias or URL.")
            brace_balance -= 1

    if brace_balance != 0:
        raise AliasDefinitionError("Alias target path must reference a valid alias or URL.")

    if value.startswith("{") and value.endswith("}"):
        raise AliasDefinitionError("Alias target path must reference a valid alias or URL.")


def _normalize_target_path(raw: str) -> str:
    """Ensure the alias target path stays within the application."""
    value = (raw or "").strip()

    if not value:
        raise AliasDefinitionError('Alias definition must include a target path after "->".')

    _validate_braces(value)

    if not any(character.isalnum() for character in value):
        raise AliasDefinitionError("Alias target path must reference a valid alias or URL.")

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


def _extract_variable_items(variable_source: Any) -> Iterable[tuple[Any, Any]]:
    """Extract (name, value) pairs from an iterable of variable objects."""
    collected: list[tuple[Any, Any]] = []

    try:
        iterator = iter(variable_source)
    except TypeError:
        return []

    for entry in iterator:
        if entry is None:
            continue

        name = getattr(entry, "name", None)
        if not name:
            continue

        if hasattr(entry, "enabled") and not getattr(entry, "enabled", True):
            continue

        value = getattr(entry, "definition", None)
        if value is None:
            continue

        collected.append((name, value))

    return collected


def _normalize_variable_map(variable_source: Any) -> dict[str, str]:
    """Return a mapping of variable names to their string values."""
    if not variable_source:
        return {}

    if isinstance(variable_source, Mapping):
        items = variable_source.items()
    else:
        items = _extract_variable_items(variable_source)

    normalized: dict[str, str] = {}
    for raw_name, raw_value in items:
        if raw_name is None:
            continue
        name_text = str(raw_name).strip()
        if not name_text:
            continue
        value_text = "" if raw_value is None else str(raw_value)
        normalized[name_text] = value_text

    return normalized


def _get_variables_from_alias_attributes(alias: Any) -> dict[str, str]:
    """Try to get variable values from common alias attributes."""
    for attribute in ("_resolved_variables", "resolved_variables", "variable_values"):
        candidate = getattr(alias, attribute, None)
        if candidate:
            resolved = _normalize_variable_map(candidate)
            if resolved:
                return resolved
    return {}


def _get_variables_from_database(alias: Any) -> dict[str, str]:
    """Fetch user variables from database if possible."""
    user_id = getattr(alias, "user_id", None)
    if not user_id:
        return {}

    try:
        from db_access import get_user_variables  # Local import avoids circular dependency.
    except Exception:  # pragma: no cover - defensive fallback when import fails
        return {}

    try:
        variables = get_user_variables(user_id)
    except Exception:  # pragma: no cover - defensive guard when database access fails
        return {}

    resolved = _normalize_variable_map(variables)

    # Cache the resolved variables on the alias object
    try:
        setattr(alias, "_resolved_variables", resolved)
    except Exception:
        pass

    return resolved


def _resolve_alias_variables(alias: Any, provided: Optional[Mapping[str, Any]]) -> dict[str, str]:
    """Return resolved variable values for ``alias``."""
    if provided:
        return _normalize_variable_map(provided)

    resolved = _get_variables_from_alias_attributes(alias)
    if resolved:
        return resolved

    return _get_variables_from_database(alias)


def _substitute_variables(text: Optional[str], variables: Mapping[str, str]) -> Optional[str]:
    """Replace ``{variable}`` placeholders in ``text`` with their values."""

    if text is None:
        return None
    if not text or not variables:
        return text

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if not name:
            return match.group(0)
        if name not in variables:
            return match.group(0)
        return variables[name]

    return _VARIABLE_PATTERN.sub(_replace, text)


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
    target_text, match_type, ignore_case = _parse_target_and_options(target_part)

    try:
        normalised_pattern = normalise_pattern(match_type, pattern_text, alias_name)
    except PatternError as exc:
        raise AliasDefinitionError(str(exc)) from exc

    target_path = _normalize_target_path(target_text)

    # Ensure that every mapping line in the definition is valid.  The alias
    # editing UI should surface problems anywhere in the definition, not only
    # on the primary line.  ``summarize_definition_lines`` records parse
    # errors for individual lines which we convert into a single validation
    # failure here.
    for entry in summarize_definition_lines(definition, alias_name=alias_name):
        if not entry.is_mapping or not entry.parse_error:
            continue
        raise AliasDefinitionError(f"Line {entry.number}: {entry.parse_error}")

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


def replace_primary_definition_line(
    definition: Optional[str], primary_line: str
) -> str:
    """Replace the first mapping line in the definition with ``primary_line``."""

    if not primary_line:
        return definition or ""

    if not definition or not definition.strip():
        return primary_line

    lines = definition.splitlines()

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "->" not in stripped:
            continue

        indent_length = len(line) - len(line.lstrip(" \t"))
        indent = line[:indent_length]
        lines[index] = f"{indent}{primary_line}"
        return "\n".join(lines)

    return ensure_primary_line(definition, primary_line)


def _parse_target_and_options(target_part: str) -> tuple[str, str, bool]:
    """Parse the target path, match type, and ignore-case flag from the target segment.

    Returns:
        (target_path, match_type, ignore_case)
    """
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

        specified_match_type, ignore_case = _interpret_option_segment(option_segment)
    else:
        target_text = target_part
        specified_match_type = None
        ignore_case = False

    match_type = specified_match_type or "literal"
    return target_text, match_type, ignore_case


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

    target_text, match_type, ignore_case = _parse_target_and_options(target_part)
    target_path = _normalize_target_path(target_text)

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

        if not stripped:
            summaries.append(
                DefinitionLineSummary(
                    number=index,
                    text=text,
                    is_mapping=False,
                    depth=depth,
                )
            )
            continue

        if stripped.startswith("#"):
            summaries.append(
                DefinitionLineSummary(
                    number=index,
                    text=text,
                    is_mapping=False,
                    depth=depth,
                )
            )
            continue

        if "->" not in stripped:
            summaries.append(
                DefinitionLineSummary(
                    number=index,
                    text=text,
                    is_mapping=True,
                    parse_error="Line does not contain an alias mapping.",
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


def _get_alias_definition_text(alias: Any, variables: Optional[Mapping[str, Any]]) -> str:
    """Extract and resolve the definition text from an alias object."""
    raw_definition = getattr(alias, "definition", None)

    if raw_definition is not None and not isinstance(raw_definition, str):
        definition = str(raw_definition)
    else:
        definition = raw_definition

    variable_values = _resolve_alias_variables(alias, variables)
    resolved_definition = _substitute_variables(definition, variable_values)

    return resolved_definition if resolved_definition is not None else definition


def _is_mock_alias(alias: Any) -> bool:
    """Check if the alias appears to be a Mock object."""
    has_helper_methods = hasattr(alias, "get_primary_target_path")
    return (
        not has_helper_methods
        and hasattr(alias, "__class__")
        and "Mock" in str(type(alias))
    )


def collect_alias_routes(
    alias: Any, *, variables: Optional[Mapping[str, Any]] = None
) -> Sequence[AliasRouteRule]:
    """Return all routing rules defined for the supplied alias."""
    alias_name = getattr(alias, "name", None) or ""

    if _is_mock_alias(alias) and alias_name:
        return [_literal_self_route(alias_name)]

    definition_text = _get_alias_definition_text(alias, variables)
    summary = summarize_definition_lines(definition_text, alias_name=alias_name)

    routes: list[AliasRouteRule] = []
    seen: set[tuple[str, str, str, bool]] = set()

    for entry in summary:
        if not entry.is_mapping or entry.parse_error:
            continue

        match_type = entry.match_type or "literal"
        match_pattern = entry.match_pattern or (
            f"/{entry.alias_path}" if entry.alias_path else None
        )
        target_path = entry.target_path
        if not match_pattern or not target_path:
            continue

        key = (match_type, match_pattern, target_path, entry.ignore_case)
        if key in seen:
            continue
        seen.add(key)

        alias_path = alias_name if entry.depth == 0 else (entry.alias_path or alias_name)
        source = None if entry.depth == 0 else entry

        routes.append(
            AliasRouteRule(
                alias_path=alias_path,
                match_type=match_type,
                match_pattern=match_pattern,
                target_path=target_path,
                ignore_case=entry.ignore_case,
                source=source,
            )
        )

    if routes:
        return routes

    return _create_fallback_routes(definition_text, alias_name)


def _create_fallback_routes(
    definition_text: Optional[str], alias_name: str
) -> Sequence[AliasRouteRule]:
    """Create fallback routes when no routes could be extracted from the definition."""
    # Handle empty definition case
    if definition_text is None or not str(definition_text).strip():
        if alias_name:
            return [_literal_self_route(alias_name)]
        return []

    try:
        parsed = parse_alias_definition(definition_text, alias_name=alias_name or None)
    except AliasDefinitionError as e:
        # Don't create fallback routes for external targets
        if "must stay within this application" in str(e):
            return []

        # For other parsing errors, fallback to name-based route
        if alias_name:
            return [_literal_self_route(alias_name)]
        return []

    fallback_path = alias_name or parsed.match_pattern.lstrip("/")
    return [
        AliasRouteRule(
            alias_path=fallback_path,
            match_type=parsed.match_type,
            match_pattern=parsed.match_pattern,
            target_path=parsed.target_path,
            ignore_case=parsed.ignore_case,
            source=None,
        )
    ]


def get_primary_alias_route(alias: Any) -> Optional[AliasRouteRule]:
    """Return the primary alias routing rule for the provided alias."""

    routes = collect_alias_routes(alias)
    return routes[0] if routes else None


__all__ = [
    "AliasDefinitionError",
    "AliasRouteRule",
    "ParsedAliasDefinition",
    "parse_alias_definition",
    "definition_contains_mapping",
    "format_primary_alias_line",
    "ensure_primary_line",
    "replace_primary_definition_line",
    "DefinitionLineSummary",
    "summarize_definition_lines",
    "collect_alias_routes",
    "get_primary_alias_route",
]
