"""Pipeline execution engine.

This module provides the core logic for executing pipeline requests,
which involve chaining multiple servers/CIDs/aliases together.

A pipeline executes right-to-left, with each segment's output becoming
the input to the segment on its left.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple

from flask import Response

from alias_routing import find_matching_alias, resolve_alias_target
from cid_core import (
    extract_literal_content,
    is_normalized_cid,
    is_probable_cid_component,
    parse_cid_components,
    split_cid_path,
)
from cid_presenter import cid_path, format_cid
from db_access import get_cid_by_path, get_server_by_name
from routes.pipelines import get_segment_base_and_extension, parse_pipeline_path

# Import execution functions from existing module
from server_execution.code_execution import (
    _evaluate_nested_path_to_value_legacy,
    _extract_chained_output,
    _load_server_literal,
)
from server_execution.function_analysis import _analyze_server_definition_for_function
from server_execution.language_detection import detect_server_language


# Supported executable extensions
_EXECUTABLE_EXTENSIONS: Set[str] = {"sh", "py", "js", "ts", "clj", "cljs"}

# Supported data extensions (contents, not executed)
_DATA_EXTENSIONS: Set[str] = {"txt", "csv", "json", "xml", "html", "md"}

# Extension to language mapping
_EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    "sh": "bash",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "clj": "clojure",
    "cljs": "clojurescript",
}


class UnrecognizedExtensionError(Exception):
    """Raised when a file extension is not recognized."""

    def __init__(self, extension: str):
        self.extension = extension
        super().__init__(f"Unrecognized extension: {extension}")


class DataExtensionError(Exception):
    """Raised when a data extension is used where execution is expected."""

    def __init__(self, extension: str):
        self.extension = extension
        super().__init__(f"Data extension cannot be executed: {extension}")


@dataclass
class ParameterInfo:
    """Information about a server parameter."""

    name: str
    required: bool
    source: Optional[str] = None  # "path", "query", "body", "default"
    value: Optional[Any] = None


@dataclass
class PathSegmentInfo:
    """Information about a single path segment in a pipeline."""

    # Basic segment information
    segment_text: str
    segment_type: Literal["server", "parameter", "cid", "alias"]
    resolution_type: Literal["literal", "contents", "execution", "error"]

    # CID validation (only if segment could be a CID)
    is_valid_cid: bool = False
    cid_validation_error: Optional[str] = None

    # Alias resolution
    aliases_involved: List[str] = field(default_factory=list)

    # Server information (if segment is a server)
    server_name: Optional[str] = None
    server_definition_cid: Optional[str] = None
    supports_chaining: bool = True
    implementation_language: Optional[str] = None

    # Server parameters
    input_parameters: List[ParameterInfo] = field(default_factory=list)
    parameter_values: Dict[str, Any] = field(default_factory=dict)

    # Execution state
    executed: bool = False
    input_value: Optional[str] = None
    intermediate_output: Optional[Any] = None
    intermediate_content_type: Optional[str] = None

    # Invocation tracking
    server_invocation_cid: Optional[str] = None

    # Errors
    errors: List[str] = field(default_factory=list)


@dataclass
class PipelineExecutionResult:
    """Result of pipeline execution."""

    segments: List[PathSegmentInfo]
    final_output: Optional[Any] = None
    final_content_type: str = "text/html"
    success: bool = True
    error_message: Optional[str] = None


def detect_language_from_suffix(segment: str) -> Optional[str]:
    """Detect the execution language from file suffix.

    Args:
        segment: The path segment (e.g., "script.py")

    Returns:
        The language name or None if no suffix or unrecognized

    Raises:
        UnrecognizedExtensionError: If extension is not recognized
        DataExtensionError: If extension is a data format, not executable

    Example:
        >>> detect_language_from_suffix("script.py")
        'python'
        >>> detect_language_from_suffix("script.sh")
        'bash'
    """
    _, extension = get_segment_base_and_extension(segment)

    if extension is None:
        return None

    ext_lower = extension.lower()

    if ext_lower in _EXTENSION_TO_LANGUAGE:
        return _EXTENSION_TO_LANGUAGE[ext_lower]

    if ext_lower in _DATA_EXTENSIONS:
        raise DataExtensionError(extension)

    raise UnrecognizedExtensionError(extension)


def validate_cid(segment: str) -> Tuple[bool, Optional[str]]:
    """Validate if a segment is a valid CID.

    Args:
        segment: The path segment to validate (may include extension)

    Returns:
        Tuple of (is_valid, error_message if invalid)

    Example:
        >>> validate_cid("AAAAAAAA")
        (True, None)
        >>> validate_cid("invalid")
        (False, "not a valid CID format")
    """
    # Extract base CID without extension
    cid_parts = split_cid_path(f"/{segment}")
    if cid_parts:
        cid_value = cid_parts[0]
    else:
        base, _ = get_segment_base_and_extension(segment)
        cid_value = base

    # Check if it looks like a CID
    if not is_probable_cid_component(cid_value):
        return False, "not a valid CID format"

    # Try full validation
    if not is_normalized_cid(cid_value):
        try:
            parse_cid_components(cid_value)
        except ValueError as e:
            return False, str(e)
        return False, "CID format validation failed"

    return True, None


def resolve_aliases(segment: str) -> List[str]:
    """Return list of alias names involved in resolving this segment.

    Follows the alias chain until reaching a non-alias target.

    Args:
        segment: The path segment to check

    Returns:
        List of alias names in resolution order, empty if not an alias
    """
    aliases: List[str] = []
    visited: Set[str] = set()
    current_path = f"/{segment}"

    while True:
        if current_path in visited:
            break  # Cycle detection
        visited.add(current_path)

        resolution = resolve_alias_target(current_path)
        if resolution is None or resolution.match is None:
            break

        alias = resolution.match.alias
        alias_name = getattr(alias, "name", None)
        if alias_name:
            aliases.append(alias_name)

        target = resolution.target
        if not target or not resolution.is_relative:
            break

        current_path = target

    return aliases


def get_resolution_type(
    segment: str, segment_type: str
) -> Literal["literal", "contents", "execution", "error"]:
    """Determine whether the literal value, contents, or execution result will be used.

    Args:
        segment: The path segment
        segment_type: The type of segment ("server", "cid", "alias", "parameter")

    Returns:
        The resolution type

    Rules:
        - Executable suffixes (.sh, .py, .js, .ts, .clj, .cljs) -> execution
        - Data suffixes (.txt, .csv, .json) -> contents
        - Unrecognized suffixes -> error
        - No suffix with server/CID -> execution (use heuristics)
        - No suffix with parameter -> literal
    """
    _, extension = get_segment_base_and_extension(segment)

    if extension:
        ext_lower = extension.lower()
        if ext_lower in _EXECUTABLE_EXTENSIONS:
            return "execution"
        if ext_lower in _DATA_EXTENSIONS:
            return "contents"
        # Unrecognized extension
        return "error"

    # No extension - use segment type to determine
    if segment_type in ("server", "cid", "alias"):
        return "execution"

    return "literal"


def resolve_segment_type(segment: str) -> Literal["server", "parameter", "cid", "alias"]:
    """Determine if a segment is a server name, CID, alias, or parameter.

    Priority order:
    1. Named server
    2. Alias
    3. CID
    4. Parameter (fallback)

    Args:
        segment: The path segment to classify

    Returns:
        The segment type
    """
    base, _ = get_segment_base_and_extension(segment)

    # Check for named server
    server = get_server_by_name(base)
    if server and getattr(server, "enabled", True):
        return "server"

    # Check for alias
    alias_match = find_matching_alias(f"/{segment}")
    if alias_match is not None:
        return "alias"

    # Check for CID
    is_cid, _ = validate_cid(segment)
    if is_cid:
        return "cid"

    # Check if it looks like a CID even if validation fails
    if is_probable_cid_component(base):
        return "cid"

    # Fallback to parameter
    return "parameter"


def check_chaining_support(definition: str, language: str) -> bool:
    """Determine if a server supports being in a chain position.

    Python servers without main() can only be in the last segment.
    Other languages generally support chaining.

    Args:
        definition: The server definition code
        language: The implementation language

    Returns:
        True if the server supports chaining
    """
    if language != "python":
        # Bash, Clojure, TypeScript, JavaScript all support chaining
        return True

    # For Python, check if there's a main() function
    main_details = _analyze_server_definition_for_function(definition, "main")
    return main_details is not None


def get_server_info(segment: str) -> Optional[Dict[str, Any]]:
    """Get server information if the segment resolves to a server.

    Args:
        segment: The path segment

    Returns:
        Server info dict or None if not a server
    """
    base, extension = get_segment_base_and_extension(segment)

    # Check for named server
    server = get_server_by_name(base)
    if server and getattr(server, "enabled", True):
        definition = getattr(server, "definition", "")
        definition_cid = getattr(server, "definition_cid", None)
        language = detect_server_language(definition)

        # Get parameters from main function
        parameters: List[ParameterInfo] = []
        main_details = _analyze_server_definition_for_function(definition, "main")
        if main_details:
            for param_name in main_details.parameter_order:
                required = param_name in main_details.required_parameters
                parameters.append(ParameterInfo(name=param_name, required=required))

        return {
            "name": base,
            "definition_cid": definition_cid,
            "supports_chaining": check_chaining_support(definition, language),
            "language": language,
            "parameters": parameters,
        }

    # Check for CID-based server (literal)
    literal_definition, lang_override, normalized_cid = _load_server_literal(base)
    if literal_definition is not None:
        language = lang_override or detect_server_language(literal_definition)
        if extension:
            # Extension overrides detected language
            try:
                language = detect_language_from_suffix(segment)
            except (UnrecognizedExtensionError, DataExtensionError):
                pass

        parameters = []
        if language == "python":
            main_details = _analyze_server_definition_for_function(
                literal_definition, "main"
            )
            if main_details:
                for param_name in main_details.parameter_order:
                    required = param_name in main_details.required_parameters
                    parameters.append(ParameterInfo(name=param_name, required=required))

        return {
            "name": base,
            "definition_cid": normalized_cid,
            "supports_chaining": check_chaining_support(literal_definition, language),
            "language": language,
            "parameters": parameters,
        }

    return None


def analyze_segment(
    segment: str, position: int, total_segments: int
) -> PathSegmentInfo:
    """Analyze a single path segment to determine its type and properties.

    Args:
        segment: The path segment text
        position: Position in the pipeline (0 = leftmost)
        total_segments: Total number of segments

    Returns:
        PathSegmentInfo with all analysis results
    """
    info = PathSegmentInfo(segment_text=segment, segment_type="parameter", resolution_type="literal")

    # Determine segment type
    info.segment_type = resolve_segment_type(segment)

    # Determine resolution type
    info.resolution_type = get_resolution_type(segment, info.segment_type)

    # Check for unrecognized extension error
    _, extension = get_segment_base_and_extension(segment)
    if extension and info.resolution_type == "error":
        info.errors.append(f"unrecognized extension: {extension}")

    # Validate CID if applicable
    if info.segment_type == "cid":
        is_valid, error = validate_cid(segment)
        info.is_valid_cid = is_valid
        info.cid_validation_error = error
        if not is_valid and error:
            info.errors.append(f"invalid CID: {error}")

    # Resolve aliases
    if info.segment_type == "alias":
        info.aliases_involved = resolve_aliases(segment)

    # Get server info
    server_info = get_server_info(segment)
    if server_info:
        info.server_name = server_info["name"]
        info.server_definition_cid = server_info["definition_cid"]
        info.supports_chaining = server_info["supports_chaining"]
        info.implementation_language = server_info["language"]
        info.input_parameters = server_info["parameters"]

        # Check chaining support - Python without main only in last position
        if not info.supports_chaining and position < total_segments - 1:
            info.errors.append("server does not support chaining (no main function)")

    elif info.segment_type == "server":
        info.errors.append("server not found")

    return info


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

                break  # Execution handles the rest of the chain

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
