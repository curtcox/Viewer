"""Compatibility helpers for the pipeline execution module.

These helpers allow legacy code paths in ``code_execution`` to delegate
to the new pipeline execution engine without creating circular imports.
"""

from typing import Any, Optional, Set, Tuple

from flask import Response

from server_execution.code_execution import (
    _evaluate_nested_path_to_value_legacy,
    _extract_chained_output,
)
from server_execution.pipeline_execution import execute_pipeline


def _run_pipeline(path: str, debug: bool = False):
    """Execute the pipeline while reusing the legacy evaluator for execution."""
    return execute_pipeline(
        path,
        debug=debug,
        evaluate_path=_evaluate_nested_path_to_value_legacy,
    )


def evaluate_nested_path_to_value_v2(
    path: str, visited: Optional[Set[str]] = None
) -> Any:
    """Evaluate a nested path using the pipeline module."""
    # The visited parameter is accepted for interface compatibility.
    _ = visited
    result = _run_pipeline(path, debug=False)
    if not result.success:
        return None
    return result.final_output


def resolve_chained_input_from_path_v2(
    path: str, visited: Optional[Set[str]] = None
) -> Tuple[Optional[str], Optional[Response]]:
    """Resolve chained input using the pipeline execution engine."""
    # The visited parameter is accepted for interface compatibility.
    _ = visited
    result = _run_pipeline(path, debug=False)
    if not result.success:
        if result.error_message:
            return None, Response(result.error_message, status=500)
        return None, None

    if isinstance(result.final_output, Response):
        return None, result.final_output
    if result.final_output is None:
        return None, None

    return str(_extract_chained_output(result.final_output)), None
