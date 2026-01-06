# ruff: noqa: F821
"""Exception handling server (try/catch)."""

from server_execution import _remaining_path_segments
from server_execution.conditional_execution import execute_try, parse_try_segments


def main(context=None):
    segments = _remaining_path_segments("try")
    parts = parse_try_segments(segments)
    return execute_try(parts)

