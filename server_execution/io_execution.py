"""IO execution engine.

This module provides the core logic for executing IO requests, which involve
bidirectional request/response piping through a chain of servers.

Unlike pipeline execution (right-to-left), IO execution:
- Flows requests left-to-right
- Flows responses right-to-left
- Invokes middle servers twice (request phase + response phase)
- Invokes tail server once (produces the initial response)

Data Flow Pattern:
    User Request -> [io] -> [S1] -> [S2] -> [S3] -> (tail returns response)
                                    |
    User Response <- [io] <- [S1] <- [S2] <- [S3]
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, Set

from flask import Response

from routes.pipelines import parse_pipeline_path

# Import shared segment analysis utilities
from server_execution.segment_analysis import (
    PathSegmentInfo,
    analyze_segment,
)


@dataclass
class IOSegmentInfo:
    """Extended segment info for IO execution with both phase tracking."""

    # Base segment info
    segment_text: str
    segment_type: Literal["server", "parameter", "cid", "alias"]
    resolution_type: Literal["literal", "contents", "execution", "error"]

    # Server information
    server_name: Optional[str] = None
    server_definition_cid: Optional[str] = None
    supports_chaining: bool = True
    implementation_language: Optional[str] = None

    # Request phase tracking
    request_phase_input: Optional[str] = None
    request_phase_output: Optional[str] = None
    request_phase_executed: bool = False
    request_phase_content_type: Optional[str] = None

    # Response phase tracking
    response_phase_request: Optional[str] = None  # Original request preserved
    response_phase_response: Optional[str] = None  # Response from right
    response_phase_output: Optional[str] = None
    response_phase_executed: bool = False
    response_phase_content_type: Optional[str] = None

    # Role in the chain
    role: Literal["head", "middle", "tail"] = "middle"

    # Errors
    errors: List[str] = field(default_factory=list)

    @classmethod
    def from_path_segment_info(cls, info: PathSegmentInfo) -> "IOSegmentInfo":
        """Create IOSegmentInfo from a PathSegmentInfo."""
        return cls(
            segment_text=info.segment_text,
            segment_type=info.segment_type,
            resolution_type=info.resolution_type,
            server_name=info.server_name,
            server_definition_cid=info.server_definition_cid,
            supports_chaining=info.supports_chaining,
            implementation_language=info.implementation_language,
            errors=info.errors.copy(),
        )


@dataclass
class IOExecutionResult:
    """Result of IO chain execution."""

    segments: List[IOSegmentInfo]
    final_output: Optional[Any] = None
    final_content_type: str = "text/html"
    success: bool = True
    error_message: Optional[str] = None


def parse_io_path(path: str) -> List[str]:
    """Parse an IO path into segments, ignoring empty segments.

    Args:
        path: The request path (e.g., "/io/s1/param/s2")

    Returns:
        List of non-empty segment strings (excluding 'io' prefix)
    """
    segments = parse_pipeline_path(path)

    # Filter out empty segments
    segments = [s for s in segments if s]

    # Remove 'io' prefix if present
    if segments and segments[0] == "io":
        segments = segments[1:]

    return segments


def group_segments_with_params(
    segments: List[str],
) -> List[Dict[str, Any]]:
    """Group segments into servers with their associated parameters.

    Parameters bind to the server on their LEFT (appear to the RIGHT of the server).

    Args:
        segments: List of path segments

    Returns:
        List of dicts with 'server' and 'params' keys

    Example:
        >>> group_segments_with_params(['s1', 'p1', 'p2', 's2', 'p3'])
        [{'segment': 's1', 'params': ['p1', 'p2']}, {'segment': 's2', 'params': ['p3']}]
    """
    if not segments:
        return []

    groups: List[Dict[str, Any]] = []
    current_group: Optional[Dict[str, Any]] = None

    for segment in segments:
        # Analyze to determine if it's a server or parameter
        info = analyze_segment(segment, 0, 1)

        if info.segment_type in ("server", "cid", "alias"):
            # Start a new group for this server
            if current_group is not None:
                groups.append(current_group)
            current_group = {"segment": segment, "params": [], "info": info}
        else:
            # It's a parameter - add to current group if exists
            if current_group is not None:
                current_group["params"].append(segment)
            else:
                # Parameter before any server - treat as a server group
                current_group = {"segment": segment, "params": [], "info": info}
                groups.append(current_group)
                current_group = None

    # Don't forget the last group
    if current_group is not None:
        groups.append(current_group)

    return groups


def execute_io_chain(
    path: str,
    debug: bool = False,
    execute_server: Optional[Callable] = None,
) -> IOExecutionResult:
    """Execute an IO chain request and return the result.

    IO chains execute with:
    - Request phase: left-to-right
    - Response phase: right-to-left

    Args:
        path: The request path (e.g., "/io/s1/param/s2")
        debug: If True, collect detailed information about each segment
        execute_server: Optional callable to execute a server

    Returns:
        IOExecutionResult with execution results
    """
    segments_text = parse_io_path(path)

    # If no segments, return landing page indicator
    if not segments_text:
        return IOExecutionResult(
            segments=[],
            final_output=None,
            success=True,
            error_message=None,
        )

    # Group segments with their parameters
    groups = group_segments_with_params(segments_text)

    if not groups:
        return IOExecutionResult(
            segments=[],
            final_output=None,
            success=True,
            error_message=None,
        )

    # Create IOSegmentInfo for each group
    io_segments: List[IOSegmentInfo] = []
    for i, group in enumerate(groups):
        info = group["info"]
        io_info = IOSegmentInfo.from_path_segment_info(info)

        # Determine role
        if i == 0 and len(groups) == 1:
            io_info.role = "tail"  # Only one server, it's the tail
        elif i == len(groups) - 1:
            io_info.role = "tail"
        else:
            io_info.role = "middle"

        # Store params for later use
        io_info.request_phase_input = (
            ",".join(group["params"]) if group["params"] else None
        )

        io_segments.append(io_info)

    # Check for analysis errors before execution
    has_errors = any(seg.errors for seg in io_segments)
    if has_errors and not debug:
        return IOExecutionResult(
            segments=io_segments,
            success=False,
            error_message="IO chain analysis had errors",
        )

    # Validate chaining support for non-tail segments
    for i, seg in enumerate(io_segments):
        if seg.role != "tail" and not seg.supports_chaining:
            seg.errors.append(
                "server does not support chaining (no main function) - can only be used as tail"
            )
            has_errors = True

    if has_errors and not debug:
        return IOExecutionResult(
            segments=io_segments,
            success=False,
            error_message="IO chain has servers that don't support chaining in middle positions",
        )

    # Execute request phase (left-to-right)
    current_request: Optional[str] = None
    for i, seg in enumerate(io_segments):
        seg.request_phase_input = current_request or seg.request_phase_input

        if execute_server:
            try:
                # Request phase: response=None
                result = execute_server(
                    segment=seg.segment_text,
                    request=seg.request_phase_input,
                    response=None,
                    is_tail=(seg.role == "tail"),
                )
                seg.request_phase_output = _extract_output(result)
                seg.request_phase_content_type = _extract_content_type(result)
                seg.request_phase_executed = True
                current_request = seg.request_phase_output
            except Exception as e:
                seg.errors.append(f"request phase error: {str(e)}")
                has_errors = True
                break
        else:
            # Without executor, just pass through
            seg.request_phase_output = seg.request_phase_input
            seg.request_phase_executed = True
            current_request = seg.request_phase_output

    # If tail reached, get the initial response
    tail_response: Optional[str] = None
    if io_segments and io_segments[-1].request_phase_executed:
        tail_response = io_segments[-1].request_phase_output
        io_segments[-1].response_phase_output = tail_response
        io_segments[-1].response_phase_executed = True

    # Execute response phase (right-to-left, skip tail)
    current_response = tail_response
    for i in range(len(io_segments) - 2, -1, -1):
        seg = io_segments[i]

        # Store what we're passing to this server
        seg.response_phase_request = seg.request_phase_input  # Original request
        seg.response_phase_response = current_response  # Response from right

        if execute_server:
            try:
                # Response phase: response is not None
                result = execute_server(
                    segment=seg.segment_text,
                    request=seg.response_phase_request,
                    response=seg.response_phase_response,
                    is_tail=False,
                )
                seg.response_phase_output = _extract_output(result)
                seg.response_phase_content_type = _extract_content_type(result)
                seg.response_phase_executed = True
                current_response = seg.response_phase_output
            except Exception as e:
                seg.errors.append(f"response phase error: {str(e)}")
                has_errors = True
                break
        else:
            # Without executor, just pass through
            seg.response_phase_output = current_response
            seg.response_phase_executed = True

    # Determine final content type (leftmost server wins)
    final_content_type = "text/html"
    for seg in io_segments:
        if seg.response_phase_content_type:
            final_content_type = seg.response_phase_content_type
            break
        if seg.request_phase_content_type:
            final_content_type = seg.request_phase_content_type
            break

    return IOExecutionResult(
        segments=io_segments,
        final_output=current_response,
        final_content_type=final_content_type,
        success=not has_errors,
        error_message="IO chain execution had errors" if has_errors else None,
    )


def _extract_output(result: Any) -> Optional[str]:
    """Extract output from a server result."""
    if result is None:
        return None

    if isinstance(result, Response):
        return result.get_data(as_text=True)

    if isinstance(result, dict):
        output = result.get("output")
        if output is not None:
            if isinstance(output, bytes):
                return output.decode("utf-8", errors="replace")
            return str(output)

    if isinstance(result, (str, bytes)):
        if isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")
        return result

    return str(result)


def _extract_content_type(result: Any) -> Optional[str]:
    """Extract content type from a server result."""
    if result is None:
        return None

    if isinstance(result, Response):
        return result.content_type

    if isinstance(result, dict):
        return result.get("content_type")

    return None


__all__ = [
    "IOExecutionResult",
    "IOSegmentInfo",
    "execute_io_chain",
    "group_segments_with_params",
    "parse_io_path",
]
