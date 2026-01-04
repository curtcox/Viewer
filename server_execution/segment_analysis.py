"""Shared segment analysis utilities for pipeline and io execution.

This module provides functions for analyzing URL path segments to determine
their type (server, alias, CID, parameter), resolution type (execution,
contents, literal), and other properties.

These utilities are shared between the pipeline execution engine (right-to-left)
and the io execution engine (left-to-right request, right-to-left response).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from alias_routing import find_matching_alias, resolve_alias_target
from cid_core import (
    is_normalized_cid,
    is_probable_cid_component,
    parse_cid_components,
    split_cid_path,
)
from db_access import get_server_by_name
from routes.pipelines import get_segment_base_and_extension

from server_execution.code_execution import _load_server_literal
from server_execution.function_analysis import _analyze_server_definition_for_function
from server_execution.language_detection import detect_server_language


# Supported executable extensions
EXECUTABLE_EXTENSIONS: Set[str] = {"sh", "py", "js", "ts", "clj", "cljs"}

# Supported data extensions (contents, not executed)
DATA_EXTENSIONS: Set[str] = {"txt", "csv", "json", "xml", "html", "md"}

# Extension to language mapping
EXTENSION_TO_LANGUAGE: Dict[str, str] = {
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
    """Information about a single path segment in a pipeline or io chain."""

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

    if ext_lower in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[ext_lower]

    if ext_lower in DATA_EXTENSIONS:
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
        if ext_lower in EXECUTABLE_EXTENSIONS:
            return "execution"
        if ext_lower in DATA_EXTENSIONS:
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
    info = PathSegmentInfo(
        segment_text=segment, segment_type="parameter", resolution_type="literal"
    )

    # Determine segment type
    info.segment_type = resolve_segment_type(segment)
    if info.segment_type == "parameter" and total_segments > 1 and position == 0:
        info.segment_type = "server"

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


__all__ = [
    "DATA_EXTENSIONS",
    "DataExtensionError",
    "EXECUTABLE_EXTENSIONS",
    "EXTENSION_TO_LANGUAGE",
    "ParameterInfo",
    "PathSegmentInfo",
    "UnrecognizedExtensionError",
    "analyze_segment",
    "check_chaining_support",
    "detect_language_from_suffix",
    "get_resolution_type",
    "get_server_info",
    "resolve_aliases",
    "resolve_segment_type",
    "validate_cid",
]
