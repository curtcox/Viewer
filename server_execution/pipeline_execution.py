"""Pipeline execution engine.

This module provides the core logic for executing pipeline requests,
which involve chaining multiple servers/CIDs/aliases together.

A pipeline executes right-to-left, with each segment's output becoming
the input to the segment on its left.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Set

from flask import Response

from alias_routing import resolve_alias_target
from cid_core import extract_literal_content
from cid_presenter import cid_path, format_cid
from db_access import get_cid_by_path
from routes.pipelines import get_segment_base_and_extension, parse_pipeline_path

# Import execution functions from existing module
from server_execution.code_execution import (
    _evaluate_nested_path_to_value_legacy,
    _extract_chained_output,
)

# Import shared segment analysis utilities
from server_execution.segment_analysis import (
    DATA_EXTENSIONS,
    EXECUTABLE_EXTENSIONS,
    EXTENSION_TO_LANGUAGE,
    DataExtensionError,
    ParameterInfo,
    PathSegmentInfo,
    UnrecognizedExtensionError,
    analyze_segment,
    check_chaining_support,
    detect_language_from_suffix,
    get_resolution_type,
    get_server_info,
    resolve_aliases,
    resolve_segment_type,
    validate_cid,
)


# Re-export for backward compatibility
_EXECUTABLE_EXTENSIONS = EXECUTABLE_EXTENSIONS
_DATA_EXTENSIONS = DATA_EXTENSIONS
_EXTENSION_TO_LANGUAGE = EXTENSION_TO_LANGUAGE


@dataclass
class PipelineExecutionResult:
    """Result of pipeline execution."""

    segments: List[PathSegmentInfo]
    final_output: Optional[Any] = None
    final_content_type: str = "text/html"
    success: bool = True
    error_message: Optional[str] = None


def execute_pipeline(
    path: str,
    debug: bool = False,
    evaluate_path: Optional[Callable[[str, Optional[Set[str]]], Any]] = None,
) -> PipelineExecutionResult:
    """Execute a pipeline request and return the result.

    Pipelines execute right-to-left, with each segment's output becoming
    the input to the segment on its left.

    Args:
        path: The request path (e.g., "/s2/s1/input")
        debug: If True, collect detailed information about each segment

    Returns:
        PipelineExecutionResult with execution results
    """
    segments_text = parse_pipeline_path(path)

    if not segments_text:
        return PipelineExecutionResult(
            segments=[],
            success=False,
            error_message="Empty pipeline path",
        )

    # Analyze all segments
    segment_infos: List[PathSegmentInfo] = []
    for i, seg_text in enumerate(segments_text):
        info = analyze_segment(seg_text, i, len(segments_text))
        segment_infos.append(info)

    # Check for analysis errors
    has_errors = any(info.errors for info in segment_infos)

    # Execute the pipeline right-to-left
    visited: Set[str] = set()
    current_output: Optional[Any] = None
    current_content_type = "text/html"
    path_evaluator = evaluate_path or _evaluate_nested_path_to_value_legacy

    # Start from the rightmost segment
    for i in range(len(segment_infos) - 1, -1, -1):
        info = segment_infos[i]

        # Skip if previous errors prevent execution
        if has_errors and not debug:
            info.executed = False
            continue

        # Record input value
        info.input_value = str(current_output) if current_output is not None else None

        # Execute based on resolution type
        try:
            if info.resolution_type == "error":
                info.executed = False
                continue

            if info.resolution_type == "literal":
                # Use the segment text as-is
                current_output = info.segment_text
                info.intermediate_output = current_output
                info.executed = True

            elif info.resolution_type == "contents":
                # Get the content of the CID/alias
                content = _get_segment_contents(info.segment_text, visited)
                current_output = content
                info.intermediate_output = current_output
                info.executed = True

            elif info.resolution_type == "execution":
                # Execute the segment
                nested_path = "/" + "/".join(
                    seg.segment_text for seg in segment_infos[i:]
                )
                result = path_evaluator(nested_path, visited.copy())

                if isinstance(result, Response):
                    # Handle Response object
                    info.executed = True
                    info.intermediate_output = result.get_data(as_text=True)
                    current_output = info.intermediate_output
                else:
                    info.executed = True
                    extracted = _extract_chained_output(result)
                    info.intermediate_output = extracted
                    current_output = extracted

                # For execution, we've processed remaining segments
                # Mark them as executed too
                for j in range(i + 1, len(segment_infos)):
                    segment_infos[j].executed = True

        except Exception as e:
            info.errors.append(f"execution error: {str(e)}")
            info.executed = False
            has_errors = True

        info.intermediate_content_type = current_content_type

    # Build result
    result = PipelineExecutionResult(
        segments=segment_infos,
        final_output=current_output,
        final_content_type=current_content_type,
        success=not has_errors,
        error_message=None if not has_errors else "Pipeline execution had errors",
    )

    return result


def _get_segment_contents(segment: str, visited: Set[str]) -> Optional[str]:
    """Get the contents of a segment (CID or alias target).

    Args:
        segment: The path segment
        visited: Set of already-visited paths (for cycle detection)

    Returns:
        The content as a string, or None
    """
    # Check for literal CID content
    base, _ = get_segment_base_and_extension(segment)
    normalized_cid = format_cid(base)

    literal_bytes = extract_literal_content(normalized_cid)
    if literal_bytes is not None:
        try:
            return literal_bytes.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return literal_bytes.decode("utf-8", errors="replace")

    # Try to get from database
    cid_record_path = cid_path(normalized_cid)
    if cid_record_path:
        cid_record = get_cid_by_path(cid_record_path)
        if cid_record and getattr(cid_record, "file_data", None) is not None:
            try:
                return cid_record.file_data.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                return cid_record.file_data.decode("utf-8", errors="replace")

    # Try alias resolution
    resolution = resolve_alias_target(f"/{segment}")
    if resolution and resolution.target and resolution.is_relative:
        if resolution.target not in visited:
            visited.add(resolution.target)
            return _get_segment_contents(resolution.target.lstrip("/"), visited)

    return None


__all__ = [
    "DataExtensionError",
    "ParameterInfo",
    "PathSegmentInfo",
    "PipelineExecutionResult",
    "UnrecognizedExtensionError",
    "analyze_segment",
    "check_chaining_support",
    "detect_language_from_suffix",
    "execute_pipeline",
    "get_resolution_type",
    "get_server_info",
    "resolve_aliases",
    "resolve_segment_type",
    "validate_cid",
]
