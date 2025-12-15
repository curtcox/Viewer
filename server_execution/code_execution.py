"""Core Python and Bash code execution and server invocation logic."""

# pylint: disable=too-many-lines

import json
import os
import re
import textwrap
from urllib.parse import unquote
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import logfire
from flask import Response, current_app, has_app_context, has_request_context, jsonify, request

from alias_routing import find_matching_alias
from cid_presenter import cid_path, format_cid
from cid_core import extract_literal_content, split_cid_path
from cid_utils import generate_cid
from db_access import create_cid_record, get_cid_by_path, get_secrets, get_server_by_name, get_servers, get_variables
# pylint: disable=no-name-in-module  # False positive: submodules exist but pylint doesn't recognize them
from server_execution.error_handling import _handle_execution_exception
from server_execution.function_analysis import FunctionDetails, MissingParameterError, _analyze_server_definition_for_function
from server_execution.language_detection import detect_server_language
from server_execution.invocation_tracking import request_details
from server_execution.external_call_tracking import capture_external_calls, sanitize_external_calls
from server_execution.request_parsing import (
    _build_missing_parameter_response,
    _build_multi_parameter_error_page,
    _resolve_function_parameters,
)
from server_execution.response_handling import _encode_output, _handle_successful_execution, _log_server_output
from server_execution.variable_resolution import _resolve_variable_values, _should_skip_variable_prefetch
# pylint: enable=no-name-in-module
from text_function_runner import run_text_function

AUTO_MAIN_PARAMS_NAME = "__viewer_auto_main_params__"
AUTO_MAIN_RESULT_NAME = "__viewer_auto_main_result__"
_SUPPORTED_LITERAL_EXTENSIONS = {"sh", "py", "clj", "cljs", "ts"}

# Pattern to detect positional parameters in bash scripts (e.g., $1, $2)
_BASH_POSITIONAL_PARAM_PATTERN = r'\$[1-9]'


def _bash_script_uses_positional_params(code: str) -> bool:
    """Check if a bash script uses positional parameters like $1, $2, etc.

    Args:
        code: The bash script code

    Returns:
        True if the script uses positional parameters, False otherwise
    """
    return bool(re.search(_BASH_POSITIONAL_PARAM_PATTERN, code))


def _resolve_cid_content(cid_segment: str) -> Optional[str]:
    """Resolve CID content from a path segment.

    If the segment is a valid CID, returns its contents.
    Otherwise, returns None.

    Args:
        cid_segment: A path segment that may be a CID

    Returns:
        The CID content as a string, or None if not a valid CID
    """
    # Try to extract CID components
    cid_components = split_cid_path(cid_segment) or split_cid_path(f"/{cid_segment}")
    if not cid_components:
        return None

    cid_value, _ = cid_components
    normalized_cid = format_cid(cid_value)

    # Try literal CID content first
    literal_bytes = extract_literal_content(normalized_cid)
    if literal_bytes is not None:
        try:
            return literal_bytes.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return literal_bytes.decode("utf-8", errors="replace")

    # Try database CID lookup
    cid_record_path = cid_path(normalized_cid)
    if cid_record_path:
        cid_record = get_cid_by_path(cid_record_path)
        if cid_record and getattr(cid_record, "file_data", None) is not None:
            try:
                return cid_record.file_data.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                return cid_record.file_data.decode("utf-8", errors="replace")

    return None


def _resolve_bash_path_parameters(
    server_name: str,
    code: str,
) -> tuple[Optional[str], Optional[str], list[str]]:
    """Resolve path parameters for bash scripts that use $1.

    When a bash script contains $1, this function extracts path parameters:
    - The first path segment after the server name becomes $1
    - If that segment is a valid CID, its contents are used instead
    - The remaining path segments are returned for chained input resolution

    Args:
        server_name: The name of the bash server
        code: The bash script code

    Returns:
        A tuple of (script_arg, chained_input_path, remaining_segments):
        - script_arg: The value to pass as $1 to the script (or None)
        - chained_input_path: Path to resolve for stdin input (or None)
        - remaining_segments: List of remaining path segments
    """
    if not _bash_script_uses_positional_params(code):
        return None, None, []

    remainder_segments = _remaining_path_segments(server_name)
    if not remainder_segments:
        return None, None, []

    if len(remainder_segments) == 1:
        cid_content = _resolve_cid_content(remainder_segments[0])
        script_arg = cid_content if cid_content is not None else remainder_segments[0]
        return script_arg, None, []

    # When Werkzeug/Flask decodes %2F into '/', the intended $1 argument may be
    # split across multiple path segments. We recover by finding the earliest
    # tail segment that appears to be a resolvable input source (CID, server,
    # alias, or literal). Everything before that is treated as the $1 value.
    split_index: Optional[int] = None
    for index in range(1, len(remainder_segments)):
        candidate = remainder_segments[index]
        if not candidate:
            continue

        if split_cid_path(candidate) or split_cid_path(f"/{candidate}"):
            split_index = index
            break

        if get_server_by_name(candidate) is not None:
            split_index = index
            break

        alias_match = find_matching_alias("/" + "/".join(remainder_segments[index:]))
        if alias_match and getattr(alias_match, "route", None):
            split_index = index
            break

        literal_definition, _, _ = _load_server_literal(candidate)
        if literal_definition is not None:
            split_index = index
            break

    if split_index is None:
        split_index = 1

    arg_segments = remainder_segments[:split_index]
    input_segments = remainder_segments[split_index:]

    raw_arg = "/".join(arg_segments)
    cid_content = _resolve_cid_content(raw_arg)
    script_arg = cid_content if cid_content is not None else raw_arg

    chained_input_path = "/" + "/".join(input_segments) if input_segments else None
    return script_arg, chained_input_path, input_segments


def _normalize_execution_result(result: Any) -> Tuple[Any, str]:
    if isinstance(result, dict):
        return result.get("output", ""), result.get("content_type", "text/html")
    if isinstance(result, tuple) and len(result) == 2:
        return result[0], result[1]
    return result, "text/html"


def _extract_chained_output(value: Any) -> Any:
    """Extract the chained server output from dictionaries or JSON strings.

    Args:
        value: A raw execution result that may be a dict with an ``output`` key,
            a JSON-encoded string of such a dict, or any other type.

    Returns:
        The unwrapped ``output`` value when present; otherwise the original
        input. Non-dictionary strings are returned as-is unless they contain
        escaped newlines that can be decoded. Errors during JSON parsing or
        unicode unescaping fall back to returning the original value.
    """
    if isinstance(value, dict) and "output" in value:
        return value.get("output")

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            if "\\n" in value:
                try:
                    return value.encode("utf-8").decode("unicode_escape")
                except (UnicodeDecodeError, AttributeError):
                    return value

            return value

        if isinstance(parsed, dict) and "output" in parsed:
            return parsed.get("output")

    return value


def _split_path_segments(path: Optional[str]) -> List[str]:
    if not path:
        return []
    return [segment for segment in path.split("/") if segment]


def _split_request_path_segments() -> List[str]:
    if not has_request_context():
        return []

    raw_uri = request.environ.get("RAW_URI") or request.environ.get("REQUEST_URI")
    raw_path = raw_uri.split("?", 1)[0] if isinstance(raw_uri, str) and raw_uri else request.path

    segments = _split_path_segments(raw_path)
    return [unquote(segment) for segment in segments]


def _remaining_path_segments(server_name: Optional[str]) -> List[str]:
    if not server_name or not has_request_context():
        return []

    segments = _split_request_path_segments()
    if not segments:
        return []

    try:
        server_index = segments.index(server_name)
    except ValueError:
        return []

    return segments[server_index + 1 :]


def _auto_main_accepts_additional_path(server: Any) -> bool:
    definition = getattr(server, "definition", "")
    if not isinstance(definition, str):
        return False

    details = _analyze_server_definition_for_function(definition, "main")
    if not details or details.unsupported_reasons:
        return False

    return bool(details.parameter_order)


def _language_from_extension(extension: Optional[str], definition: str) -> str:
    """Return execution language based on explicit extension or code content."""

    if extension and extension.lower() == "sh":
        return "bash"
    if extension and extension.lower() == "py":
        return "python"
    if extension and extension.lower() == "clj":
        return "clojure"
    if extension and extension.lower() == "cljs":
        return "clojurescript"
    if extension and extension.lower() == "ts":
        return "typescript"
    return detect_server_language(definition)


def _is_supported_literal_extension(extension: Optional[str]) -> bool:
    return bool(extension and extension.lower() in _SUPPORTED_LITERAL_EXTENSIONS)


def _clone_request_context_kwargs(path: str, data_override: bytes | None = None) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"path": path}
    if has_request_context():
        kwargs["method"] = request.method
        kwargs["query_string"] = request.query_string.decode("utf-8")
        headers = [(k, v) for k, v in request.headers if k.lower() != "cookie"]
        if headers:
            kwargs["headers"] = headers
        json_payload = request.get_json(silent=True)
        if json_payload is not None:
            kwargs["json"] = json_payload
        else:
            data = request.get_data()
            if data:
                kwargs["data"] = data
    else:
        kwargs["method"] = "GET"
        kwargs["query_string"] = ""

    if data_override is not None:
        kwargs["data"] = data_override
        kwargs.pop("json", None)

    return kwargs


def _resolve_chained_input_from_path(
    path: str, visited: Set[str]
) -> tuple[Optional[str], Optional[Response]]:
    segments = _split_path_segments(path)
    if len(segments) <= 1:
        return None, None

    nested_path = "/" + "/".join(segments[1:])
    nested_value = _evaluate_nested_path_to_value(nested_path, visited)
    if isinstance(nested_value, Response):
        return None, nested_value
    if nested_value is None:
        return None, None
    return str(_extract_chained_output(nested_value)), None


def _execute_python_code_to_value(
    code: str, server_name: str, path: str, *, chained_input: Optional[str]
) -> Any:
    if not has_app_context():
        return None

    input_bytes = _encode_output(chained_input) if chained_input is not None else None
    kwargs = _clone_request_context_kwargs(path, data_override=input_bytes)
    with current_app.test_request_context(**kwargs):
        args = build_request_args()
        prepared = _prepare_invocation(
            code,
            args,
            function_name="main",
            allow_fallback=True,
            server_name=server_name,
        )

        if prepared is None:
            return None

        if isinstance(prepared, tuple):
            code_to_run, args_to_use = prepared
        else:
            return prepared

        try:
            result = run_text_function(code_to_run, args_to_use)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Catch all exceptions from user code execution
            return _handle_execution_exception(exc, code_to_run, args_to_use, server_name)

        output, _ = _normalize_execution_result(result)
        output_bytes = _encode_output(output)
        try:
            return output_bytes.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            # Handle decoding errors by using replacement characters
            return output_bytes.decode("utf-8", errors="replace")


def _execute_bash_code_to_value(
    code: str,
    server_name: str,
    chained_input: Optional[str],
    *,
    script_args: Optional[List[str]] = None,
) -> Any:
    stdout, status_code, stderr = _run_bash_script(
        code, server_name, chained_input=chained_input, script_args=script_args
    )
    combined_output = stdout or b""
    if status_code >= 400 and stderr:
        combined_output = (
            combined_output + (b"" if combined_output.endswith(b"\n") or not combined_output else b"\n") + stderr
        )
    _log_server_output(
        "execute_bash_code", "", combined_output, "text/plain"
    )

    if status_code >= 400:
        return Response(combined_output, status=status_code, mimetype="text/plain")

    try:
        return combined_output.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return combined_output.decode("utf-8", errors="replace")


def _execute_clojure_code_to_value(
    code: str, server_name: str, chained_input: Optional[str]
) -> Any:
    stdout, status_code, stderr = _run_clojure_script(
        code, server_name, chained_input=chained_input
    )
    combined_output = stdout or b""
    if status_code >= 400 and stderr:
        combined_output = (
            combined_output
            + (b"" if combined_output.endswith(b"\n") or not combined_output else b"\n")
            + stderr
        )

    _log_server_output(
        "execute_clojure_code", "", combined_output, "text/plain"
    )

    if status_code >= 400:
        return Response(combined_output, status=status_code, mimetype="text/plain")

    try:
        return combined_output.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return combined_output.decode("utf-8", errors="replace")


def _execute_clojurescript_code_to_value(
    code: str, server_name: str, chained_input: Optional[str]
) -> Any:
    stdout, status_code, stderr = _run_clojurescript_script(
        code, server_name, chained_input=chained_input
    )
    combined_output = stdout or b""
    if status_code >= 400 and stderr:
        combined_output = (
            combined_output
            + (b"" if combined_output.endswith(b"\n") or not combined_output else b"\n")
            + stderr
        )

    _log_server_output(
        "execute_clojurescript_code", "", combined_output, "text/plain"
    )

    if status_code >= 400:
        return Response(combined_output, status=status_code, mimetype="text/plain")

    try:
        return combined_output.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return combined_output.decode("utf-8", errors="replace")


def _execute_typescript_code_to_value(
    code: str, server_name: str, chained_input: Optional[str]
) -> Any:
    stdout, status_code, stderr = _run_typescript_script(
        code, server_name, chained_input=chained_input
    )
    combined_output = stdout or b""
    if status_code >= 400 and stderr:
        combined_output = (
            combined_output
            + (b"" if combined_output.endswith(b"\n") or not combined_output else b"\n")
            + stderr
        )

    _log_server_output(
        "execute_typescript_code", "", combined_output, "text/plain"
    )

    if status_code >= 400:
        return Response(combined_output, status=status_code, mimetype="text/plain")

    try:
        return combined_output.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return combined_output.decode("utf-8", errors="replace")


def _execute_nested_server_to_value(
    server: Any,
    server_name: str,
    path: str,
    visited: Set[str],
    *,
    language_override: Optional[str] = None,
) -> Any:
    language = language_override or detect_server_language(getattr(server, "definition", ""))
    if language == "bash":
        script_arg, chained_input_path, _ = _resolve_bash_path_parameters(
            server_name, server.definition
        )

        if script_arg is not None:
            chained_input: Optional[str] = None
            if chained_input_path:
                segments = _split_path_segments(chained_input_path)
                if len(segments) == 1:
                    cid_content = _resolve_cid_content(segments[0])
                    if cid_content is not None:
                        chained_input = cid_content
                    else:
                        nested_value = _evaluate_nested_path_to_value(
                            chained_input_path, visited
                        )
                        if isinstance(nested_value, Response):
                            return nested_value
                        if nested_value is not None:
                            chained_input = str(_extract_chained_output(nested_value))
                else:
                    nested_value = _evaluate_nested_path_to_value(chained_input_path, visited)
                    if isinstance(nested_value, Response):
                        return nested_value
                    if nested_value is not None:
                        chained_input = str(_extract_chained_output(nested_value))

            return _execute_bash_code_to_value(
                server.definition,
                server_name,
                chained_input,
                script_args=[script_arg],
            )

        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response

        return _execute_bash_code_to_value(server.definition, server_name, chained_input)
    if language == "clojure":
        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response
        return _execute_clojure_code_to_value(
            server.definition, server_name, chained_input
        )
    if language == "clojurescript":
        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response
        return _execute_clojurescript_code_to_value(
            server.definition, server_name, chained_input
        )
    if language == "typescript":
        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response
        return _execute_typescript_code_to_value(
            server.definition, server_name, chained_input
        )

    chained_input, early_response = _resolve_chained_input_from_path(path, visited)
    if early_response:
        return early_response

    return _execute_python_code_to_value(server.definition, server_name, path, chained_input=chained_input)


def _execute_literal_definition_to_value(
    definition_text: str,
    server_name: str,
    path: str,
    visited: Set[str],
    *,
    language_override: Optional[str],
) -> Any:
    language = language_override or detect_server_language(definition_text)
    if language == "bash":
        script_arg, chained_input_path, _ = _resolve_bash_path_parameters(
            server_name, definition_text
        )

        if script_arg is not None:
            chained_input: Optional[str] = None
            if chained_input_path:
                segments = _split_path_segments(chained_input_path)
                if len(segments) == 1:
                    cid_content = _resolve_cid_content(segments[0])
                    if cid_content is not None:
                        chained_input = cid_content
                    else:
                        nested_value = _evaluate_nested_path_to_value(
                            chained_input_path, visited
                        )
                        if isinstance(nested_value, Response):
                            return nested_value
                        if nested_value is not None:
                            chained_input = str(_extract_chained_output(nested_value))
                else:
                    nested_value = _evaluate_nested_path_to_value(chained_input_path, visited)
                    if isinstance(nested_value, Response):
                        return nested_value
                    if nested_value is not None:
                        chained_input = str(_extract_chained_output(nested_value))

            return _execute_bash_code_to_value(
                definition_text,
                server_name,
                chained_input,
                script_args=[script_arg],
            )

        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response

        return _execute_bash_code_to_value(definition_text, server_name, chained_input)
    if language == "clojure":
        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response
        return _execute_clojure_code_to_value(
            definition_text, server_name, chained_input
        )
    if language == "clojurescript":
        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response
        return _execute_clojurescript_code_to_value(
            definition_text, server_name, chained_input
        )
    if language == "typescript":
        chained_input, early_response = _resolve_chained_input_from_path(path, visited)
        if early_response:
            return early_response
        return _execute_typescript_code_to_value(
            definition_text, server_name, chained_input
        )

    chained_input, early_response = _resolve_chained_input_from_path(path, visited)
    if early_response:
        return early_response

    return _execute_python_code_to_value(
        definition_text, server_name, path, chained_input=chained_input
    )


def _load_server_literal(segment: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (definition, language, normalized_cid) for CID path segments."""

    cid_components = split_cid_path(segment) or split_cid_path(f"/{segment}")
    if not cid_components:
        return None, None, None

    cid_value, extension = cid_components
    normalized_cid = format_cid(cid_value)

    literal_bytes = extract_literal_content(normalized_cid)
    if literal_bytes is not None:
        try:
            definition_text = literal_bytes.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            definition_text = literal_bytes.decode("utf-8", errors="replace")

        language_override = _language_from_extension(extension, definition_text)
        return definition_text, language_override, normalized_cid

    cid_record_path = cid_path(normalized_cid)
    if not cid_record_path:
        return None, None, None

    cid_record = get_cid_by_path(cid_record_path)
    if not cid_record or getattr(cid_record, "file_data", None) is None:
        return None, None, None

    try:
        definition_text = cid_record.file_data.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        definition_text = cid_record.file_data.decode("utf-8", errors="replace")

    language_override = _language_from_extension(extension, definition_text)
    return definition_text, language_override, normalized_cid


def _evaluate_nested_path_to_value(path: str, visited: Optional[Set[str]] = None) -> Any:
    """Recursively evaluate a path to produce a value, following servers/aliases/CIDs."""
    normalized = (path or "").strip()
    if not normalized:
        return None

    if not normalized.startswith("/"):
        normalized = f"/{normalized}"

    if visited is None:
        visited = set()

    if normalized in visited:
        return None  # Prevent infinite recursion

    visited.add(normalized)

    segments = _split_path_segments(normalized)
    if not segments:
        return None

    server_name = segments[0]
    server = get_server_by_name(server_name)
    if server and not getattr(server, "enabled", True):
        server = None
    if server:
        return _execute_nested_server_to_value(server, server_name, normalized, visited)

    if len(segments) > 1:
        literal_definition, language_override, normalized_cid = _load_server_literal(
            segments[0]
        )
        if literal_definition is not None:
            literal_name = segments[0]
            return _execute_literal_definition_to_value(
                literal_definition,
                literal_name,
                normalized,
                visited,
                language_override=language_override,
            )

    alias_match = find_matching_alias(normalized)
    if alias_match and getattr(alias_match, "route", None):
        target = getattr(alias_match.route, "target_path", None)
        if target:
            return _evaluate_nested_path_to_value(target, visited)

    if len(segments) == 1:
        cid_components = split_cid_path(segments[0]) or split_cid_path(
            f"/{segments[0]}"
        )
        normalized_cid = format_cid((cid_components or (None,))[0] or segments[0])

        literal_bytes = extract_literal_content(normalized_cid)
        if literal_bytes is not None:
            try:
                return literal_bytes.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                # Handle decoding errors by using replacement characters
                return literal_bytes.decode("utf-8", errors="replace")

        cid_record_path = cid_path(normalized_cid)
        if cid_record_path:
            cid_record = get_cid_by_path(cid_record_path)
            if cid_record and getattr(cid_record, "file_data", None) is not None:
                try:
                    return cid_record.file_data.decode("utf-8")
                except (UnicodeDecodeError, AttributeError):
                    # Handle decoding errors by using replacement characters
                    return cid_record.file_data.decode("utf-8", errors="replace")

    return None


def _inject_nested_parameter_value(
    server_name: Optional[str],
    function_name: str,
    resolved: Dict[str, Any],
    missing: List[str],
    available: Dict[str, List[str]],
) -> Any:
    if not missing:
        return {}

    if len(missing) != 1:
        return _build_multi_parameter_error_page(
            server_name,
            function_name,
            missing,
            resolved.keys(),
            available,
        )

    remainder_segments = _remaining_path_segments(server_name)
    if not remainder_segments:
        return None

    nested_path = "/" + "/".join(remainder_segments)
    nested_value = _evaluate_nested_path_to_value(nested_path)
    if isinstance(nested_value, Response):
        return nested_value
    if nested_value is None:
        return None
    return {missing[0]: _extract_chained_output(nested_value)}


def _inject_optional_parameter_from_path(
    server_name: Optional[str],
    details: FunctionDetails,
    resolved: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], Optional[Response]]:
    """Provide chained input for optional parameters when present.

    Optional parameters with defaults aren't marked as "missing" during
    resolution, but server chaining should still use any remaining path
    segment as input when no value was supplied explicitly. This helper
    mirrors the nested-path lookup used for required parameters and returns
    either a mapping for the first unresolved parameter or an early
    Response.
    """

    if not server_name or not details.parameter_order:
        return None, None

    for name in details.parameter_order:
        if name not in resolved:
            remainder_segments = _remaining_path_segments(server_name)
            if not remainder_segments:
                return None, None

            nested_path = "/" + "/".join(remainder_segments)
            nested_value = _evaluate_nested_path_to_value(nested_path)
            if isinstance(nested_value, Response):
                return None, nested_value
            if nested_value is None:
                return None, None

            return {name: _extract_chained_output(nested_value)}, None

    return None, None


def _resolve_chained_input_for_server(
    server_name: str,
) -> tuple[Optional[str], Optional[Response]]:
    remainder_segments = _remaining_path_segments(server_name)
    if not remainder_segments:
        return None, None

    nested_path = "/" + "/".join(remainder_segments)
    visited: Set[str] = set()
    first_segment = remainder_segments[0]
    cid_components = split_cid_path(first_segment) or split_cid_path(f"/{first_segment}")
    extension = (cid_components or (None, None))[1]
    executes_as_terminal_literal = (
        len(remainder_segments) == 1 and _is_supported_literal_extension(extension)
    )

    if executes_as_terminal_literal:
        literal_definition, language_override, normalized_cid = _load_server_literal(
            first_segment
        )
        if literal_definition is not None:
            literal_name = normalized_cid or first_segment
            literal_value = _execute_literal_definition_to_value(
                literal_definition,
                literal_name,
                nested_path,
                visited,
                language_override=language_override,
            )
            if isinstance(literal_value, Response):
                return None, literal_value
            if literal_value is not None:
                return str(literal_value), None

    nested_value = _evaluate_nested_path_to_value(nested_path, visited)
    if isinstance(nested_value, Response):
        return None, nested_value
    if nested_value is None:
        return None, None
    return str(_extract_chained_output(nested_value)), None


def _execute_bash_server_response(
    code: str,
    server_name: str,
    debug_prefix: str,
    *,
    chained_input: Optional[str],
    script_args: Optional[List[str]] = None,
) -> Response:
    stdout, status_code, stderr = _run_bash_script(
        code, server_name, chained_input=chained_input, script_args=script_args
    )

    output_bytes = stdout if isinstance(stdout, (bytes, bytearray)) else _encode_output(stdout)
    if status_code >= 400 and stderr:
        output_bytes = output_bytes + (
            b"" if output_bytes.endswith(b"\n") or not output_bytes else b"\n"
        ) + stderr

    _log_server_output(debug_prefix, "", output_bytes, "text/plain")

    cid_value = format_cid(generate_cid(output_bytes))
    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not existing and cid_record_path:
        create_cid_record(cid_value, output_bytes)

    if has_app_context():
        from server_execution.invocation_tracking import (  # pylint: disable=no-name-in-module
            create_server_invocation_record,
        )

        create_server_invocation_record(server_name, cid_value)

    return Response(output_bytes, status=status_code, mimetype="text/plain")


def _execute_clojure_server_response(
    code: str,
    server_name: str,
    debug_prefix: str,
    *,
    chained_input: Optional[str],
) -> Response:
    stdout, status_code, stderr = _run_clojure_script(
        code, server_name, chained_input=chained_input
    )

    output_bytes = stdout if isinstance(stdout, (bytes, bytearray)) else _encode_output(stdout)
    if status_code >= 400 and stderr:
        output_bytes = output_bytes + (
            b"" if output_bytes.endswith(b"\n") or not output_bytes else b"\n"
        ) + stderr

    _log_server_output(debug_prefix, "", output_bytes, "text/plain")

    cid_value = format_cid(generate_cid(output_bytes))
    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not existing and cid_record_path:
        create_cid_record(cid_value, output_bytes)

    if has_app_context():
        from server_execution.invocation_tracking import (  # pylint: disable=no-name-in-module
            create_server_invocation_record,
        )

        create_server_invocation_record(server_name, cid_value)

    return Response(output_bytes, status=status_code, mimetype="text/plain")


def _execute_clojurescript_server_response(
    code: str,
    server_name: str,
    debug_prefix: str,
    *,
    chained_input: Optional[str],
) -> Response:
    stdout, status_code, stderr = _run_clojurescript_script(
        code, server_name, chained_input=chained_input
    )

    output_bytes = stdout if isinstance(stdout, (bytes, bytearray)) else _encode_output(stdout)
    if status_code >= 400 and stderr:
        output_bytes = output_bytes + (
            b"" if output_bytes.endswith(b"\n") or not output_bytes else b"\n"
        ) + stderr

    _log_server_output(debug_prefix, "", output_bytes, "text/plain")

    cid_value = format_cid(generate_cid(output_bytes))
    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not existing and cid_record_path:
        create_cid_record(cid_value, output_bytes)

    if has_app_context():
        from server_execution.invocation_tracking import (  # pylint: disable=no-name-in-module
            create_server_invocation_record,
        )

        create_server_invocation_record(server_name, cid_value)

    return Response(output_bytes, status=status_code, mimetype="text/plain")


def _execute_typescript_server_response(
    code: str,
    server_name: str,
    debug_prefix: str,
    *,
    chained_input: Optional[str],
) -> Response:
    stdout, status_code, stderr = _run_typescript_script(
        code, server_name, chained_input=chained_input
    )

    output_bytes = stdout if isinstance(stdout, (bytes, bytearray)) else _encode_output(stdout)
    if status_code >= 400 and stderr:
        output_bytes = output_bytes + (
            b"" if output_bytes.endswith(b"\n") or not output_bytes else b"\n"
        ) + stderr

    _log_server_output(debug_prefix, "", output_bytes, "text/plain")

    cid_value = format_cid(generate_cid(output_bytes))
    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not existing and cid_record_path:
        create_cid_record(cid_value, output_bytes)

    if has_app_context():
        from server_execution.invocation_tracking import (  # pylint: disable=no-name-in-module
            create_server_invocation_record,
        )

        create_server_invocation_record(server_name, cid_value)

    return Response(output_bytes, status=status_code, mimetype="text/plain")


def _build_unsupported_signature_response(
    function_name: str, details: FunctionDetails
):
    payload = {
        "error": f"Unsupported {function_name}() signature for automatic request mapping",
        "reasons": details.unsupported_reasons,
        "resolution": (
            f"Use only standard positional or keyword parameters, or provide an explicit return outside {function_name}()."
        ),
    }
    response = jsonify(payload)
    response.status_code = 400
    return response


def _build_function_invocation_snippet(function_name: str, code: str) -> str:
    """Generate the code snippet that invokes a function with resolved parameters."""
    snippet = textwrap.dedent(
        f"""
        {AUTO_MAIN_RESULT_NAME} = {function_name}(**{AUTO_MAIN_PARAMS_NAME})
        return {AUTO_MAIN_RESULT_NAME}
        """
    ).strip()

    # Match the indentation of the original code
    base_indent = ""
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped:
            base_indent = line[: len(line) - len(stripped)]
            break

    if base_indent:
        snippet = textwrap.indent(snippet, base_indent)

    # Combine with original code
    combined = code.rstrip()
    if combined:
        return f"{combined}\n\n{snippet}\n"
    return f"{snippet}\n"


def _handle_missing_parameters_for_main(
    function_name: str,
    *,
    server_name: Optional[str],
    base_args: Dict[str, Any],
    details: FunctionDetails,
    resolved: Dict[str, Any],
    missing: List[str],
    available: Dict[str, List[str]],
) -> Tuple[Dict[str, Any], Dict[str, Any], List[str], Dict[str, List[str]], Optional[Response]]:
    """Try to resolve missing main() parameters via nested path evaluation.

    Returns (updated_args, resolved, missing, available, early_response) tuple.
    """
    injected = _inject_nested_parameter_value(
        server_name,
        function_name,
        resolved,
        missing,
        available,
    )

    if isinstance(injected, Response):
        return base_args, resolved, missing, available, injected

    if not injected:
        return base_args, resolved, missing, available, None

    # Re-resolve with the injected parameters
    working_args = dict(base_args)
    working_args.update(injected)
    new_resolved, new_missing, new_available = _resolve_function_parameters(
        details,
        working_args,
        allow_partial=True,
    )

    return working_args, new_resolved, new_missing, new_available, None


def _prepare_invocation(
    code: str,
    base_args: Dict[str, Any],
    *,
    function_name: Optional[str],
    allow_fallback: bool,
    server_name: Optional[str] = None,
) -> Any:
    """Prepare code and arguments for function invocation with parameter resolution."""
    if not function_name:
        return code, base_args

    details = _analyze_server_definition_for_function(code, function_name)
    if not details:
        return (code, base_args) if allow_fallback else None

    if details.unsupported_reasons:
        return _build_unsupported_signature_response(function_name, details)

    # Initial parameter resolution
    resolved, missing, available = _resolve_function_parameters(
        details, base_args, allow_partial=True
    )

    # Track working args (may be updated with injected parameters)
    working_args = dict(base_args)
    working_resolved = dict(resolved)

    # Handle missing parameters
    if missing:
        if function_name != "main":
            return _build_missing_parameter_response(
                function_name, MissingParameterError(missing, available)
            )

        # For main(), try nested path injection
        working_args, working_resolved, missing, available, early_response = _handle_missing_parameters_for_main(
            function_name,
            server_name=server_name,
            base_args=base_args,
            details=details,
            resolved=resolved,
            missing=missing,
            available=available,
        )

        if early_response:
            return early_response

        if missing:
            return _build_missing_parameter_response(
                function_name, MissingParameterError(missing, available)
            )

    if function_name == "main":
        optional_injection, early_response = _inject_optional_parameter_from_path(
            server_name,
            details,
            working_resolved,
        )

        if early_response:
            return early_response

        if optional_injection:
            working_resolved.update(optional_injection)

    # Build final code with function invocation
    new_args = dict(working_args)
    new_args[AUTO_MAIN_PARAMS_NAME] = working_resolved
    combined_code = _build_function_invocation_snippet(function_name, code)

    return combined_code, new_args


def model_as_dict(model_objects: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """Convert SQLAlchemy model objects to a name->definition mapping."""
    if not model_objects:
        return {}

    result: Dict[str, Any] = {}
    for obj in model_objects:
        if not getattr(obj, "enabled", True):
            continue
        if hasattr(obj, "name") and hasattr(obj, "definition"):
            result[obj.name] = obj.definition
        else:
            result[str(obj)] = str(obj)
    return result


def _load_user_context() -> Dict[str, Dict[str, Any]]:
    variables = model_as_dict(get_variables())
    if _should_skip_variable_prefetch():
        variables = dict(variables)
    else:
        variables = _resolve_variable_values(variables)
    secrets = model_as_dict(get_secrets())
    servers = model_as_dict(get_servers())
    return {"variables": variables, "secrets": secrets, "servers": servers}


def build_request_args() -> Dict[str, Any]:
    """Build the argument payload supplied to user-defined server code."""
    return {
        "request": request_details(),
        "context": _load_user_context(),
    }


def _map_exit_code_to_status(exit_code: int) -> int:
    if exit_code == 0:
        return 200
    if exit_code < 100 or exit_code > 599:
        return 500
    return exit_code


def _build_bash_stdin_payload(chained_input: Optional[str]) -> bytes:
    if chained_input is not None:
        return _encode_output(chained_input)

    payload: Dict[str, Any] = build_request_args()

    try:
        body_data = request.get_data()
    except RuntimeError:
        body_data = b""

    input_value: Optional[str] = None
    if body_data:
        try:
            decoded_body = body_data.decode("utf-8")
        except UnicodeDecodeError:
            decoded_body = body_data.decode("utf-8", errors="replace")
        payload["body"] = decoded_body
        input_value = decoded_body

    if input_value is not None:
        payload["input"] = input_value

    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _run_bash_script(
    code: str,
    server_name: str,
    *,
    chained_input: Optional[str] = None,
    script_args: Optional[List[str]] = None,
) -> tuple[bytes, int, bytes]:
    """Execute a bash script with optional positional arguments and stdin input.

    Args:
        code: The bash script code
        server_name: Name of the server (for logging)
        chained_input: Optional content to pass as stdin
        script_args: Optional list of positional arguments ($1, $2, etc.)

    Returns:
        Tuple of (stdout, status_code, stderr)
    """
    stdin_payload = _build_bash_stdin_payload(chained_input)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as script_file:
        script_file.write(code)
        script_path = script_file.name

    # Build the command with optional script arguments
    cmd = ["bash", script_path]
    if script_args:
        cmd.extend(script_args)

    try:
        result = subprocess.run(
            cmd,
            input=stdin_payload,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return b"Script execution timed out", 504, b""
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass

    status_code = _map_exit_code_to_status(result.returncode)
    return result.stdout or b"", status_code, result.stderr or b""


def _select_clojure_command() -> Optional[list[str]]:
    runner = shutil.which("bb")
    if runner:
        return [runner]

    runner = shutil.which("clojure")
    if runner:
        return [runner, "-M"]

    return None


def _select_clojurescript_command() -> Optional[list[str]]:
    runner = shutil.which("nbb")
    if runner:
        return [runner]

    return None


def _select_typescript_command() -> Optional[list[str]]:
    runner = shutil.which("deno")
    if runner:
        return [runner, "run", "--quiet"]

    return None


def _extract_stubbed_output(code: str, markers: tuple[str, ...]) -> Optional[bytes]:
    """Extract a stubbed output marker if present in the code block."""

    for line in code.splitlines():
        stripped = line.strip()
        for marker in markers:
            if stripped.startswith(marker):
                return stripped.split(marker, 1)[1].strip().encode("utf-8")

    return None


def _run_clojure_script(
    code: str, server_name: str, *, chained_input: Optional[str] = None
) -> tuple[bytes, int, bytes]:
    stdin_payload = _build_bash_stdin_payload(chained_input)
    runner = _select_clojure_command()
    if not runner:
        stubbed = _extract_stubbed_output(code, (";; OUTPUT:",))
        if stubbed is not None:
            return stubbed, 200, b""
        return (
            b"Clojure runtime is not available for this server",
            500,
            b"clojure executable not found",
        )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".clj") as script_file:
        script_file.write(code)
        script_path = script_file.name

    try:
        result = subprocess.run(
            [*runner, script_path],
            input=stdin_payload,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return b"Script execution timed out", 504, b""
    except FileNotFoundError:
        return (
            b"Clojure runtime is not available for this server",
            500,
            b"clojure executable not found",
        )
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass

    status_code = _map_exit_code_to_status(result.returncode)
    return result.stdout or b"", status_code, result.stderr or b""


def _run_clojurescript_script(
    code: str, server_name: str, *, chained_input: Optional[str] = None
) -> tuple[bytes, int, bytes]:
    stdin_payload = _build_bash_stdin_payload(chained_input)
    runner = _select_clojurescript_command()
    if not runner:
        stubbed = _extract_stubbed_output(code, (";; OUTPUT:",))
        if stubbed is not None:
            return stubbed, 200, b""
        return (
            b"ClojureScript runtime is not available for this server",
            500,
            b"clojurescript executable not found",
        )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".cljs") as script_file:
        script_file.write(code)
        script_path = script_file.name

    try:
        result = subprocess.run(
            [*runner, script_path],
            input=stdin_payload,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return b"Script execution timed out", 504, b""
    except FileNotFoundError:
        return (
            b"ClojureScript runtime is not available for this server",
            500,
            b"clojurescript executable not found",
        )
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass

    status_code = _map_exit_code_to_status(result.returncode)
    return result.stdout or b"", status_code, result.stderr or b""


def _run_typescript_script(
    code: str, server_name: str, *, chained_input: Optional[str] = None
) -> tuple[bytes, int, bytes]:
    stdin_payload = _build_bash_stdin_payload(chained_input)
    runner = _select_typescript_command()
    if not runner:
        stubbed = _extract_stubbed_output(code, ("// OUTPUT:", "//OUTPUT:"))
        if stubbed is not None:
            return stubbed, 200, b""
        return (
            b"Deno runtime is not available for this server",
            500,
            b"deno executable not found",
        )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".ts") as script_file:
        script_file.write(code)
        script_path = script_file.name

    try:
        result = subprocess.run(
            [*runner, script_path],
            input=stdin_payload,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return b"Script execution timed out", 504, b""
    except FileNotFoundError:
        return (
            b"Deno runtime is not available for this server",
            500,
            b"deno executable not found",
        )
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass

    status_code = _map_exit_code_to_status(result.returncode)
    return result.stdout or b"", status_code, result.stderr or b""


def _execute_server_code_common(
    code: str,
    server_name: str,
    debug_prefix: str,
    error_suffix: str,
    *,
    function_name: Optional[str] = "main",
    allow_fallback: bool = True,
    language_override: Optional[str] = None,
) -> Optional[Response]:
    language = language_override or detect_server_language(code)

    if language == "bash":
        # Check if script uses positional parameters ($1, $2, etc.)
        script_arg, chained_input_path, _ = _resolve_bash_path_parameters(server_name, code)

        if script_arg is not None:
            # Script uses $1 - use path parameter logic
            chained_input: Optional[str] = None
            early_response: Optional[Response] = None

            if chained_input_path:
                # Resolve the remaining path for stdin
                segments = _split_path_segments(chained_input_path)
                if len(segments) == 1:
                    cid_content = _resolve_cid_content(segments[0])
                    if cid_content is not None:
                        chained_input = cid_content
                    else:
                        visited: Set[str] = set()
                        nested_value = _evaluate_nested_path_to_value(chained_input_path, visited)
                        if isinstance(nested_value, Response):
                            return nested_value
                        if nested_value is not None:
                            chained_input = str(_extract_chained_output(nested_value))
                else:
                    visited: Set[str] = set()
                    nested_value = _evaluate_nested_path_to_value(chained_input_path, visited)
                    if isinstance(nested_value, Response):
                        return nested_value
                    if nested_value is not None:
                        chained_input = str(_extract_chained_output(nested_value))

            return _execute_bash_server_response(
                code,
                server_name,
                debug_prefix,
                chained_input=chained_input,
                script_args=[script_arg],
            )

        # Standard bash execution (no $1 in script)
        chained_input, early_response = _resolve_chained_input_for_server(server_name)
        if early_response:
            return early_response

        return _execute_bash_server_response(
            code,
            server_name,
            debug_prefix,
            chained_input=chained_input,
        )

    if language == "clojure":
        chained_input, early_response = _resolve_chained_input_for_server(server_name)
        if early_response:
            return early_response

        return _execute_clojure_server_response(
            code,
            server_name,
            debug_prefix,
            chained_input=chained_input,
        )

    if language == "clojurescript":
        chained_input, early_response = _resolve_chained_input_for_server(server_name)
        if early_response:
            return early_response

        return _execute_clojurescript_server_response(
            code,
            server_name,
            debug_prefix,
            chained_input=chained_input,
        )

    if language == "typescript":
        chained_input, early_response = _resolve_chained_input_for_server(server_name)
        if early_response:
            return early_response

        return _execute_typescript_server_response(
            code,
            server_name,
            debug_prefix,
            chained_input=chained_input,
        )

    args = build_request_args()
    external_calls: Optional[List[Dict[str, Any]]] = None

    prepared = _prepare_invocation(
        code,
        args,
        function_name=function_name,
        allow_fallback=allow_fallback,
        server_name=server_name,
    )
    if prepared is None:
        return None

    if isinstance(prepared, tuple):
        code_to_run, args_to_use = prepared
    else:
        return prepared

    secrets_context = args.get("context", {}).get("secrets") if isinstance(args, dict) else None

    try:
        with capture_external_calls() as call_log:
            try:
                result = run_text_function(code_to_run, args_to_use)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                external_calls = sanitize_external_calls(call_log, secrets_context)
                return _handle_execution_exception(
                    exc, code, args, server_name, external_calls=external_calls
                )

        external_calls = sanitize_external_calls(call_log, secrets_context)

        if isinstance(result, dict):
            output = result.get("output", "")
            content_type = result.get("content_type", "text/html")
        elif isinstance(result, tuple) and len(result) == 2:
            output, content_type = result
        else:
            output = result
            content_type = "text/html"
        _log_server_output(debug_prefix, error_suffix, output, content_type)
        return _handle_successful_execution(
            output, content_type, server_name, external_calls=external_calls
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Top-level exception handler for all user code execution errors
        return _handle_execution_exception(
            exc, code, args, server_name, external_calls=external_calls
        )


@logfire.instrument("server_execution.execute_server_code({server=}, {server_name=})", extract_args=True, record_return=True)
def execute_server_code(server: Any, server_name: str) -> Optional[Response]:
    """Execute server code and return a redirect to the resulting CID."""
    return _execute_server_code_common(
        server.definition,
        server_name,
        "execute_server_code",
        "",
        function_name="main",
        allow_fallback=True,
    )


@logfire.instrument("server_execution.execute_server_code_from_definition({definition_text=}, {server_name=})", extract_args=True, record_return=True)
def execute_server_code_from_definition(definition_text: str, server_name: str) -> Optional[Response]:
    """Execute server code from a supplied historical definition."""
    return _execute_server_code_common(
        definition_text,
        server_name,
        "execute_server_code_from_definition",
        "in _from_definition",
        function_name="main",
        allow_fallback=True,
    )


@logfire.instrument("server_execution.execute_server_function({server=}, {server_name=}, {function_name=})", extract_args=True, record_return=True)
def execute_server_function(server: Any, server_name: str, function_name: str) -> Optional[Response]:
    """Execute a named helper function within a server definition."""
    if detect_server_language(getattr(server, "definition", "")) != "python":
        return None

    return _execute_server_code_common(
        server.definition,
        server_name,
        "execute_server_function",
        f" for {function_name}",
        function_name=function_name,
        allow_fallback=False,
    )


@logfire.instrument("server_execution.execute_server_function_from_definition({definition_text=}, {server_name=}, {function_name=})", extract_args=True, record_return=True)
def execute_server_function_from_definition(
    definition_text: str, server_name: str, function_name: str
) -> Optional[Response]:
    """Execute a helper function from a supplied historical definition."""
    if detect_server_language(definition_text) != "python":
        return None

    return _execute_server_code_common(
        definition_text,
        server_name,
        "execute_server_function_from_definition",
        f" in _from_definition for {function_name}",
        function_name=function_name,
        allow_fallback=False,
    )
