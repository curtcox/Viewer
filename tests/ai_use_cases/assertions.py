"""Common assertion helpers for AI use case tests."""

import ast
import json
from urllib.parse import parse_qs

import pytest


def assert_ai_output_valid(output: str):
    """Verify AI output is not empty and contains no error markers."""
    assert output, "AI output is empty"
    assert len(output) > 10, f"AI output too short: {len(output)} characters"
    # Don't check for 'error' in the actual content as it might be legitimate
    # Error checking is done at the response level


def assert_valid_python(code: str):
    """Verify string is valid Python code."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(f"Invalid Python syntax: {e}\n\nCode:\n{code}")


def assert_valid_json(text: str) -> dict:
    """Verify and parse JSON, returning the parsed object."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON: {e}\n\nText:\n{text}")
        return {}  # Never reached, but satisfies pylint


def assert_original_content_preserved(result: str, original: str):
    """Verify key elements from original content appear in result.

    This is a flexible check that looks for significant words/identifiers
    from the original to ensure the AI didn't completely replace the content.
    """
    if not original:
        return

    # Extract words longer than 3 characters (likely identifiers/keywords)
    original_words = set(
        word for word in original.split() if len(word) > 3 and word.isalnum()
    )

    # Check that at least some original words are preserved
    # (allowing for transformations like CSV -> JSON where structure changes)
    if original_words:
        result_lower = result.lower()
        preserved_count = sum(
            1 for word in original_words if word.lower() in result_lower
        )

        preservation_ratio = preserved_count / len(original_words)
        assert preservation_ratio >= 0.3, (
            f"Too few original words preserved: {preserved_count}/{len(original_words)}"
        )


def assert_requested_change_applied(result: str, request: str):
    """Verify the requested change is reflected in result.

    This looks for keywords from the request in the result to ensure
    the AI actually attempted to apply the requested change.
    """
    if not request:
        return

    # Extract significant words from the request
    request_lower = request.lower()

    # Common keywords that indicate the type of change
    change_indicators = {
        "add": ["new", "added", "include"],
        "remove": ["without", "removed", "deleted"],
        "convert": ["to", "into", "as"],
        "modify": ["changed", "updated", "modified"],
        "validate": ["if", "check", "validate"],
        "log": ["logging", "log", "info", "debug"],
        "retry": ["retry", "attempt", "backoff"],
        "filter": ["filter", "where", "status"],
        "sort": ["sort", "order", "by"],
    }

    # Check if any change indicators appear
    result_lower = result.lower()
    found_indicator = False

    for action, indicators in change_indicators.items():
        if action in request_lower:
            for indicator in indicators:
                if indicator in result_lower:
                    found_indicator = True
                    break

    # If we found specific indicators, great. Otherwise, just check
    # that the result is different from what we might expect
    if not found_indicator:
        # At least verify result is reasonably longer (for add/convert operations)
        if "add" in request_lower or "convert" in request_lower:
            # Result should be longer than minimal length
            assert len(result) > 20, "Result seems too short for the requested change"


def assert_valid_query_string(qs: str):
    """Verify valid query string format."""
    # Query string might have a leading ? or not
    if "?" in qs:
        assert qs.count("?") == 1, (
            f"Invalid query string: multiple ? characters in {qs}"
        )
        qs = qs.split("?", 1)[1]

    # Try to parse it
    try:
        parsed = parse_qs(qs)
        assert len(parsed) > 0, f"No query parameters found in: {qs}"
    except Exception as e:
        pytest.fail(f"Invalid query string format: {e}\nQuery string: {qs}")


def assert_no_errors_in_response(data: dict):
    """Verify the AI response doesn't contain error fields."""
    assert "error" not in data, (
        f"Response contains error: {data.get('error')}\nMessage: {data.get('message')}"
    )
