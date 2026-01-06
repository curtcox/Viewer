"""Shared utilities for conditional execution servers (if/do/try).

This module provides path parsing, truthiness evaluation, and helper
execution functions to support the control-flow servers defined in the
reference templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterable, Optional, Sequence

from flask import Response, make_response

from server_execution import _extract_chained_output, _normalize_execution_result
from server_execution import _evaluate_nested_path_to_value as evaluate_nested
from server_execution import try_server_execution


_FALSY_STRINGS = {"", "false", "0", "null", "none"}


@dataclass
class IfPathParts:
    """Parsed path components for the if server."""

    test_path: Optional[list[str]] = None
    true_path: Optional[list[str]] = None
    false_path: Optional[list[str]] = None
    identity_path: Optional[list[str]] = None


@dataclass
class DoPathParts:
    """Parsed path components for the do server."""

    body_path: Optional[list[str]] = None
    test_path: Optional[list[str]] = None
    implicit_test: bool = False


@dataclass
class TryPathParts:
    """Parsed path components for the try server."""

    try_path: Optional[list[str]] = None
    catch_path: Optional[list[str]] = None
    identity_path: Optional[list[str]] = None


def _strip_empty(segments: Iterable[str]) -> list[str]:
    return [seg for seg in segments if seg]


def parse_if_segments(segments: Sequence[str]) -> IfPathParts:
    """Parse path segments for the if server using balanced parsing."""

    cleaned = _strip_empty(segments)
    if not cleaned:
        return IfPathParts(identity_path=[])

    depth = 0
    then_index: Optional[int] = None
    else_index: Optional[int] = None

    for idx, seg in enumerate(cleaned):
        if seg == "if":
            depth += 1
            continue

        if seg == "else" and depth > 0:
            depth -= 1
            continue

        if seg == "then" and depth == 0 and then_index is None:
            then_index = idx
            continue

        if seg == "else" and depth == 0 and then_index is not None:
            else_index = idx
            break

    if then_index is None:
        return IfPathParts(identity_path=cleaned)

    test_path = cleaned[:then_index] or None
    if else_index is None:
        true_path = cleaned[then_index + 1 :] or None
        return IfPathParts(test_path=test_path, true_path=true_path)

    true_path = cleaned[then_index + 1 : else_index] or None
    false_path = cleaned[else_index + 1 :] or None
    return IfPathParts(
        test_path=test_path, true_path=true_path, false_path=false_path
    )


def parse_do_segments(segments: Sequence[str]) -> DoPathParts:
    """Parse path segments for the do server."""

    cleaned = _strip_empty(segments)
    if not cleaned:
        return DoPathParts(body_path=[])

    while_index: Optional[int] = None
    for idx, seg in enumerate(cleaned):
        if seg == "while":
            while_index = idx
            break

    if while_index is None:
        return DoPathParts(body_path=cleaned)

    body_path = cleaned[:while_index] or None
    test_path = cleaned[while_index + 1 :] or None
    implicit = test_path is None
    return DoPathParts(body_path=body_path, test_path=test_path, implicit_test=implicit)


def parse_try_segments(segments: Sequence[str]) -> TryPathParts:
    """Parse path segments for the try server."""

    cleaned = _strip_empty(segments)
    if not cleaned:
        return TryPathParts(identity_path=[])

    catch_index: Optional[int] = None
    for idx, seg in enumerate(cleaned):
        if seg == "catch":
            catch_index = idx
            break

    if catch_index is None:
        return TryPathParts(identity_path=cleaned)

    try_path = cleaned[:catch_index] or None
    catch_path = cleaned[catch_index + 1 :] or None
    return TryPathParts(try_path=try_path, catch_path=catch_path)


def _execute_path(path_segments: Optional[Sequence[str]]) -> Any:
    if not path_segments:
        return ""

    path = "/" + "/".join(path_segments)
    nested_value = evaluate_nested(path)
    if nested_value is not None:
        if isinstance(nested_value, Response):
            return (
                nested_value.get_data(as_text=True),
                nested_value.status_code,
                nested_value.headers,
            )
        return nested_value

    response = try_server_execution(path)
    if response is not None and 300 <= response.status_code < 400:
        location = response.headers.get("Location") or ""
        if location:
            return evaluate_nested(location)
    if response is not None:
        return (
            response.get_data(as_text=True),
            response.status_code,
            response.headers,
        )

    return nested_value


def _normalize_result(result: Any) -> tuple[str, str, int]:
    if isinstance(result, Response):
        return (
            result.get_data(as_text=True),
            result.content_type or "text/html",
            result.status_code,
        )

    if isinstance(result, tuple) and len(result) == 3:
        output, status_code, headers = result
        resp = make_response(output, status_code, headers)
        return (
            resp.get_data(as_text=True),
            resp.content_type or "text/html",
            resp.status_code,
        )

    output, content_type = _normalize_execution_result(result)
    return str(_extract_chained_output(output) or ""), content_type, 200


def is_truthy(result: Any) -> bool:
    output, _, status_code = _normalize_result(result)
    if status_code >= 400:
        return False

    lowered = output.lower()
    return lowered not in _FALSY_STRINGS


def is_error(result: Any) -> tuple[bool, Optional[str], Optional[int]]:
    if isinstance(result, Exception):
        return True, str(result), None

    output, _, status_code = _normalize_result(result)
    if status_code >= 400:
        return True, output, status_code

    return False, None, None


def _cost_estimate_cents(
    input_size: int, output_size: int, execution_time_ms: float
) -> float:
    base_cost = 0.0001
    size_cost = (input_size + output_size) * 0.000001
    time_cost = execution_time_ms * 0.00001
    return base_cost + size_cost + time_cost


def run_do_loop(parts: DoPathParts) -> tuple[str, int, dict[str, str]]:
    body_path = parts.body_path or []
    test_path = parts.test_path if not parts.implicit_test else ["variable", "max_do_while"]

    accumulated_output = ""
    last_content_type = "text/html"
    start = perf_counter()
    iterations = 0
    termination: Optional[str] = None

    while True:
        iterations += 1
        if iterations > 500:
            termination = "iterations"
            break

        body_result = _execute_path(body_path)
        body_output, body_content_type, _ = _normalize_result(body_result)
        last_content_type = body_content_type or last_content_type
        accumulated_output += body_output

        elapsed = perf_counter() - start
        if elapsed >= 500:
            termination = "time"
            break

        total_execution_ms = elapsed * 1000
        size = len(body_output.encode("utf-8"))
        cost = _cost_estimate_cents(size, size, total_execution_ms)
        if cost >= 0.5:
            termination = "cost"
            break

        test_result = _execute_path(test_path)
        if not is_truthy(test_result):
            break

    headers = {"Content-Type": last_content_type}
    if termination:
        headers["X-Loop-Terminated"] = termination
    return accumulated_output, 200, headers


def execute_if(parts: IfPathParts) -> tuple[str, int, dict[str, str]]:
    if parts.identity_path is not None:
        output, content_type, status_code = _normalize_result(
            _execute_path(parts.identity_path)
        )
        return output, status_code, {"Content-Type": content_type}

    test_result = _execute_path(parts.test_path)
    if is_truthy(test_result):
        output, content_type, status_code = _normalize_result(
            _execute_path(parts.true_path)
        )
        return output, status_code, {"Content-Type": content_type}

    if parts.false_path is not None:
        output, content_type, status_code = _normalize_result(
            _execute_path(parts.false_path)
        )
        return output, status_code, {"Content-Type": content_type}

    output, content_type, status_code = _normalize_result(test_result)
    return output, status_code, {"Content-Type": content_type}


def execute_try(parts: TryPathParts) -> tuple[str, int, dict[str, str]]:
    if parts.identity_path is not None:
        output, content_type, status_code = _normalize_result(
            _execute_path(parts.identity_path)
        )
        return output, status_code, {"Content-Type": content_type}

    try:
        try_result = _execute_path(parts.try_path)
        error, message, status_code = is_error(try_result)
    except Exception as exc:  # pragma: no cover - surfaced via error handling below
        try_result = exc
        error, message, status_code = True, str(exc), None

    if not error:
        output, content_type, status_code = _normalize_result(try_result)
        return output, status_code, {"Content-Type": content_type}

    if parts.catch_path is None:
        output, content_type, status_code = _normalize_result(try_result)
        return output, status_code, {"Content-Type": content_type}

    catch_result = _execute_path(parts.catch_path)
    output, content_type, catch_status = _normalize_result(catch_result)
    headers: dict[str, str] = {"Content-Type": content_type}
    if message:
        headers["X-Error-Message"] = message
    if status_code is not None:
        headers["X-Error-Status"] = str(status_code)
    headers["X-Error-Type"] = "exception" if status_code is None else "status"
    return output, catch_status, headers


def _ensure_response(result: Any) -> Response:
    if isinstance(result, Response):
        return result

    if isinstance(result, tuple) and len(result) == 3:
        output, status_code, headers = result
        return make_response(output, status_code, headers)

    output, content_type = _normalize_execution_result(result)
    response = make_response(output)
    response.headers["Content-Type"] = content_type
    return response

