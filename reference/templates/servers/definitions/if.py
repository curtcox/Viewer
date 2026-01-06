# ruff: noqa: F821
"""Conditional branching server (if/then/else)."""

from server_execution import _remaining_path_segments
from server_execution.conditional_execution import execute_if, parse_if_segments


def main(context=None):
    segments = _remaining_path_segments("if")
    parts = parse_if_segments(segments)
    return execute_if(parts)

