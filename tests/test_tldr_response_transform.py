"""Unit tests for the tldr gateway response transform."""

from __future__ import annotations

from reference_templates.gateways.transforms.tldr_response import (
    _format_command,
    _normalize_tldr_terminal_output,
)


def test_normalize_tldr_terminal_output_strips_ansi_sequences():
    raw = "\x1b[31mred\x1b[0m"
    assert _normalize_tldr_terminal_output(raw) == "red"


def test_normalize_tldr_terminal_output_handles_backspaces():
    raw = "abc\bX"
    assert _normalize_tldr_terminal_output(raw) == "abX"


def test_format_command_linkifies_pipeline_commands():
    cmd = 'cat path/to/file | grep [-v|--invert-match] "search_pattern"'
    formatted = _format_command(cmd)
    assert '<a href="/gateway/tldr/cat">cat</a>' in formatted
    assert '<a href="/gateway/tldr/grep">grep</a>' in formatted
