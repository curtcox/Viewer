"""Helper functions for executing user-defined servers.

This package provides the core server execution functionality for Viewer,
including code analysis, parameter resolution, and execution handling.
"""

# Import public API from submodules
from server_execution.code_execution import (
    AUTO_MAIN_PARAMS_NAME,
    AUTO_MAIN_RESULT_NAME,
    build_request_args,
    execute_server_code,
    execute_server_code_from_definition,
    execute_server_function,
    execute_server_function_from_definition,
)
from server_execution.function_analysis import (
    analyze_server_definition,
    describe_function_parameters,
    describe_main_function_parameters,
)
from server_execution.invocation_tracking import create_server_invocation_record
from server_execution.server_lookup import (
    is_potential_server_path,
    is_potential_versioned_server_path,
    try_server_execution,
    try_server_execution_with_partial,
)
from server_execution.variable_resolution import VARIABLE_PREFETCH_SESSION_KEY

# Public API
__all__ = [
    # Constants
    "AUTO_MAIN_PARAMS_NAME",
    "AUTO_MAIN_RESULT_NAME",
    "VARIABLE_PREFETCH_SESSION_KEY",
    # Function analysis
    "analyze_server_definition",
    "describe_function_parameters",
    "describe_main_function_parameters",
    # Execution
    "build_request_args",
    "execute_server_code",
    "execute_server_code_from_definition",
    "execute_server_function",
    "execute_server_function_from_definition",
    # Invocation tracking
    "create_server_invocation_record",
    # Server lookup
    "is_potential_server_path",
    "is_potential_versioned_server_path",
    "try_server_execution",
    "try_server_execution_with_partial",
]


# Lazy loading for internal/private functions (for testing and backward compatibility)
def __getattr__(name: str):
    """Dynamically load internal functions when accessed."""
    # External module re-exports for backward compatibility with tests
    if name == "run_text_function":
        from text_function_runner import run_text_function
        return run_text_function
    if name == "current_user":
        from identity import current_user
        return current_user
    if name == "make_response":
        from flask import make_response
        return make_response
    if name == "redirect":
        from flask import redirect
        return redirect
    if name == "create_cid_record":
        from db_access import create_cid_record
        return create_cid_record
    if name == "get_cid_by_path":
        from db_access import get_cid_by_path
        return get_cid_by_path
    if name == "get_server_by_name":
        from db_access import get_server_by_name
        return get_server_by_name
    if name == "generate_cid":
        from cid_utils import generate_cid
        return generate_cid
    if name == "get_extension_from_mime_type":
        from cid_utils import get_extension_from_mime_type
        return get_extension_from_mime_type
    if name == "cid_path":
        from cid_presenter import cid_path
        return cid_path
    if name == "format_cid":
        from cid_presenter import format_cid
        return format_cid
    if name == "find_matching_alias":
        from alias_routing import find_matching_alias
        return find_matching_alias

    # Variable resolution
    if name == "_normalize_variable_path":
        from server_execution.variable_resolution import _normalize_variable_path
        return _normalize_variable_path
    if name == "_should_skip_variable_prefetch":
        from server_execution.variable_resolution import _should_skip_variable_prefetch
        return _should_skip_variable_prefetch
    if name == "_resolve_redirect_target":
        from server_execution.variable_resolution import _resolve_redirect_target
        return _resolve_redirect_target
    if name == "_current_user_id":
        from server_execution.variable_resolution import _current_user_id
        return _current_user_id
    if name == "_fetch_variable_via_client":
        from server_execution.variable_resolution import _fetch_variable_via_client
        return _fetch_variable_via_client
    if name == "_fetch_variable_content":
        from server_execution.variable_resolution import _fetch_variable_content
        return _fetch_variable_content
    if name == "_resolve_variable_values":
        from server_execution.variable_resolution import _resolve_variable_values
        return _resolve_variable_values

    # Function analysis
    if name == "FunctionDetails":
        from server_execution.function_analysis import FunctionDetails
        return FunctionDetails
    if name == "_FunctionAnalyzer":
        from server_execution.function_analysis import _FunctionAnalyzer
        return _FunctionAnalyzer
    if name == "MissingParameterError":
        from server_execution.function_analysis import MissingParameterError
        return MissingParameterError
    if name == "_parse_function_details":
        from server_execution.function_analysis import _parse_function_details
        return _parse_function_details
    if name == "_analyze_server_definition_for_function":
        from server_execution.function_analysis import _analyze_server_definition_for_function
        return _analyze_server_definition_for_function

    # Request parsing
    if name == "_extract_request_body_values":
        from server_execution.request_parsing import _extract_request_body_values
        return _extract_request_body_values
    if name == "_extract_context_dicts":
        from server_execution.request_parsing import _extract_context_dicts
        return _extract_context_dicts
    if name == "_collect_parameter_sources":
        from server_execution.request_parsing import _collect_parameter_sources
        return _collect_parameter_sources
    if name == "_lookup_header_value":
        from server_execution.request_parsing import _lookup_header_value
        return _lookup_header_value
    if name == "_resolve_single_parameter":
        from server_execution.request_parsing import _resolve_single_parameter
        return _resolve_single_parameter
    if name == "_resolve_function_parameters":
        from server_execution.request_parsing import _resolve_function_parameters
        return _resolve_function_parameters
    if name == "_build_missing_parameter_response":
        from server_execution.request_parsing import _build_missing_parameter_response
        return _build_missing_parameter_response
    if name == "_build_multi_parameter_error_page":
        from server_execution.request_parsing import _build_multi_parameter_error_page
        return _build_multi_parameter_error_page

    # Response handling
    if name == "_encode_output":
        from server_execution.response_handling import _encode_output
        return _encode_output
    if name == "_log_server_output":
        from server_execution.response_handling import _log_server_output
        return _log_server_output
    if name == "_handle_successful_execution":
        from server_execution.response_handling import _handle_successful_execution
        return _handle_successful_execution

    # Error handling
    if name == "_render_execution_error_html":
        from server_execution.error_handling import _render_execution_error_html
        return _render_execution_error_html
    if name == "_handle_execution_exception":
        from server_execution.error_handling import _handle_execution_exception
        return _handle_execution_exception

    # Code execution
    if name == "_normalize_execution_result":
        from server_execution.code_execution import _normalize_execution_result
        return _normalize_execution_result
    if name == "_split_path_segments":
        from server_execution.code_execution import _split_path_segments
        return _split_path_segments
    if name == "_remaining_path_segments":
        from server_execution.code_execution import _remaining_path_segments
        return _remaining_path_segments
    if name == "_auto_main_accepts_additional_path":
        from server_execution.code_execution import _auto_main_accepts_additional_path
        return _auto_main_accepts_additional_path
    if name == "_clone_request_context_kwargs":
        from server_execution.code_execution import _clone_request_context_kwargs
        return _clone_request_context_kwargs
    if name == "_execute_nested_server_to_value":
        from server_execution.code_execution import _execute_nested_server_to_value
        return _execute_nested_server_to_value
    if name == "_evaluate_nested_path_to_value":
        from server_execution.code_execution import _evaluate_nested_path_to_value
        return _evaluate_nested_path_to_value
    if name == "_inject_nested_parameter_value":
        from server_execution.code_execution import _inject_nested_parameter_value
        return _inject_nested_parameter_value
    if name == "_build_unsupported_signature_response":
        from server_execution.code_execution import _build_unsupported_signature_response
        return _build_unsupported_signature_response
    if name == "_build_function_invocation_snippet":
        from server_execution.code_execution import _build_function_invocation_snippet
        return _build_function_invocation_snippet
    if name == "_handle_missing_parameters_for_main":
        from server_execution.code_execution import _handle_missing_parameters_for_main
        return _handle_missing_parameters_for_main
    if name == "_prepare_invocation":
        from server_execution.code_execution import _prepare_invocation
        return _prepare_invocation
    if name == "model_as_dict":
        from server_execution.code_execution import model_as_dict
        return model_as_dict
    if name == "_load_user_context":
        from server_execution.code_execution import _load_user_context
        return _load_user_context
    if name == "_execute_server_code_common":
        from server_execution.code_execution import _execute_server_code_common
        return _execute_server_code_common

    # Invocation tracking
    if name == "request_details":
        from server_execution.invocation_tracking import request_details
        return request_details

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
