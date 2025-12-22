"""Compatibility helpers for the pipeline execution module.

These helpers allow legacy code paths in ``code_execution`` to delegate
to the new pipeline execution engine without creating circular imports.
"""

from contextlib import contextmanager
from typing import Any, Optional, Set, Tuple

from flask import Response

from server_execution.code_execution import (
    _evaluate_nested_path_to_value_legacy,
    _extract_chained_output,
)
from server_execution.pipeline_execution import execute_pipeline


@contextmanager
def _patched_pipeline_dependencies():
    """Patch pipeline execution to reuse code_execution monkeypatches."""
    import server_execution.pipeline_execution as pipeline_execution
    import server_execution.code_execution as code_execution

    original_get_server = pipeline_execution.get_server_by_name
    pipeline_execution.get_server_by_name = code_execution.get_server_by_name
    try:
        yield
    finally:
        pipeline_execution.get_server_by_name = original_get_server


def _run_pipeline(path: str, debug: bool = False):
    """Execute the pipeline while reusing the legacy evaluator for execution."""
    with _patched_pipeline_dependencies():
        return execute_pipeline(
            path,
            debug=debug,
            evaluate_path=_evaluate_nested_path_to_value_legacy,
        )


def evaluate_nested_path_to_value_v2(
    path: str, visited: Optional[Set[str]] = None
) -> Any:
    """Evaluate a nested path using the legacy evaluator."""
    return _evaluate_nested_path_to_value_legacy(path, visited)


def resolve_chained_input_from_path_v2(
    path: str, visited: Optional[Set[str]] = None
) -> Tuple[Optional[str], Optional[Response]]:
    """Resolve chained input using the legacy evaluator."""
    if visited is None:
        visited = set()

    from routes.pipelines import parse_pipeline_path

    segments = parse_pipeline_path(path)
    if len(segments) <= 1:
        return None, None

    nested_path = "/" + "/".join(segments[1:])
    nested_value = _evaluate_nested_path_to_value_legacy(nested_path, visited)
    if isinstance(nested_value, Response):
        return None, nested_value
    if nested_value is None:
        return None, None
    return str(_extract_chained_output(nested_value)), None
