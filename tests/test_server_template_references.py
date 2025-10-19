from __future__ import annotations

import re

from routes.servers import _extract_context_references
from server_templates import iter_server_templates


_SECRET_LITERAL_PATTERN = re.compile(
    r"\bsecrets\[['\"]([^'\"]+)['\"]\]|\bsecrets\.get\(\s*['\"]([^'\"]+)['\"]"
)
_VARIABLE_LITERAL_PATTERN = re.compile(
    r"\bvariables\[['\"]([^'\"]+)['\"]\]|\bvariables\.get\(\s*['\"]([^'\"]+)['\"]"
)


def _collect_literal_names(pattern: re.Pattern[str], definition: str) -> list[str]:
    names: set[str] = set()
    for match in pattern.finditer(definition):
        literal = match.group(1) or match.group(2)
        if literal:
            names.add(literal)
    return sorted(names)


def test_template_context_references_are_detected() -> None:
    """Server templates should surface their context variable and secret usage."""

    exercised = False

    for template in iter_server_templates():
        definition = template.get('definition') or ""
        expected_secrets = _collect_literal_names(_SECRET_LITERAL_PATTERN, definition)
        expected_variables = _collect_literal_names(_VARIABLE_LITERAL_PATTERN, definition)

        if not expected_secrets and not expected_variables:
            continue

        exercised = True
        references = _extract_context_references(definition)

        assert references['secrets'] == expected_secrets
        assert references['variables'] == expected_variables

    assert exercised, "Expected at least one template to include context references"
