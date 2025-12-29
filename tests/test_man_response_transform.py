"""Unit tests for the man gateway response transform."""

from __future__ import annotations

from reference_templates.gateways.transforms.man_response import (
    _normalize_man_terminal_formatting,
)


def test_normalize_man_terminal_formatting_collapses_backspace_overstrikes():
    raw = "N\bNA\bAM\bME\bE\n     c\bca\bat\bt\n"
    normalized = _normalize_man_terminal_formatting(raw)
    assert "\b" not in normalized
    assert "NAME" in normalized
    assert "cat" in normalized


def test_normalize_man_terminal_formatting_handles_cursor_backspace():
    raw = "abc\bX"
    normalized = _normalize_man_terminal_formatting(raw)
    assert normalized == "abX"
