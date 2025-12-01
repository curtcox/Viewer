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
from server_execution.language_detection import detect_server_language
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
    "detect_server_language",
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


# Lazy loading configuration
_LAZY_IMPORTS = {
    # External modules (backward compatibility)
    'run_text_function': ('text_function_runner', 'run_text_function'),
    'make_response': ('flask', 'make_response'),
    'redirect': ('flask', 'redirect'),
    'create_cid_record': ('db_access', 'create_cid_record'),
    'get_cid_by_path': ('db_access', 'get_cid_by_path'),
    'get_server_by_name': ('db_access', 'get_server_by_name'),
    'generate_cid': ('cid_utils', 'generate_cid'),
    'get_extension_from_mime_type': ('cid_utils', 'get_extension_from_mime_type'),
    'cid_path': ('cid_presenter', 'cid_path'),
    'format_cid': ('cid_presenter', 'format_cid'),
    'find_matching_alias': ('alias_routing', 'find_matching_alias'),

    # Variable resolution
    '_normalize_variable_path': ('server_execution.variable_resolution', '_normalize_variable_path'),
    '_should_skip_variable_prefetch': ('server_execution.variable_resolution', '_should_skip_variable_prefetch'),
    '_resolve_redirect_target': ('server_execution.variable_resolution', '_resolve_redirect_target'),
    '_fetch_variable_via_client': ('server_execution.variable_resolution', '_fetch_variable_via_client'),
    '_fetch_variable_content': ('server_execution.variable_resolution', '_fetch_variable_content'),
    '_resolve_variable_values': ('server_execution.variable_resolution', '_resolve_variable_values'),

    # Function analysis
    'FunctionDetails': ('server_execution.function_analysis', 'FunctionDetails'),
    '_FunctionAnalyzer': ('server_execution.function_analysis', '_FunctionAnalyzer'),
    'MissingParameterError': ('server_execution.function_analysis', 'MissingParameterError'),
    '_parse_function_details': ('server_execution.function_analysis', '_parse_function_details'),
    '_analyze_server_definition_for_function': ('server_execution.function_analysis', '_analyze_server_definition_for_function'),

    # Language detection
    'detect_server_language': ('server_execution.language_detection', 'detect_server_language'),

    # Request parsing
    '_extract_request_body_values': ('server_execution.request_parsing', '_extract_request_body_values'),
    '_extract_context_dicts': ('server_execution.request_parsing', '_extract_context_dicts'),
    '_collect_parameter_sources': ('server_execution.request_parsing', '_collect_parameter_sources'),
    '_lookup_header_value': ('server_execution.request_parsing', '_lookup_header_value'),
    '_resolve_single_parameter': ('server_execution.request_parsing', '_resolve_single_parameter'),
    '_resolve_function_parameters': ('server_execution.request_parsing', '_resolve_function_parameters'),
    '_build_missing_parameter_response': ('server_execution.request_parsing', '_build_missing_parameter_response'),
    '_build_multi_parameter_error_page': ('server_execution.request_parsing', '_build_multi_parameter_error_page'),

    # Response handling
    '_encode_output': ('server_execution.response_handling', '_encode_output'),
    '_log_server_output': ('server_execution.response_handling', '_log_server_output'),
    '_handle_successful_execution': ('server_execution.response_handling', '_handle_successful_execution'),

    # Error handling
    '_render_execution_error_html': ('server_execution.error_handling', '_render_execution_error_html'),
    '_handle_execution_exception': ('server_execution.error_handling', '_handle_execution_exception'),

    # Code execution
    '_normalize_execution_result': ('server_execution.code_execution', '_normalize_execution_result'),
    '_split_path_segments': ('server_execution.code_execution', '_split_path_segments'),
    '_remaining_path_segments': ('server_execution.code_execution', '_remaining_path_segments'),
    '_auto_main_accepts_additional_path': ('server_execution.code_execution', '_auto_main_accepts_additional_path'),
    '_clone_request_context_kwargs': ('server_execution.code_execution', '_clone_request_context_kwargs'),
    '_execute_nested_server_to_value': ('server_execution.code_execution', '_execute_nested_server_to_value'),
    '_evaluate_nested_path_to_value': ('server_execution.code_execution', '_evaluate_nested_path_to_value'),
    '_inject_nested_parameter_value': ('server_execution.code_execution', '_inject_nested_parameter_value'),
    '_build_unsupported_signature_response': ('server_execution.code_execution', '_build_unsupported_signature_response'),
    '_build_function_invocation_snippet': ('server_execution.code_execution', '_build_function_invocation_snippet'),
    '_handle_missing_parameters_for_main': ('server_execution.code_execution', '_handle_missing_parameters_for_main'),
    '_prepare_invocation': ('server_execution.code_execution', '_prepare_invocation'),
    'model_as_dict': ('server_execution.code_execution', 'model_as_dict'),
    '_load_user_context': ('server_execution.code_execution', '_load_user_context'),
    '_execute_server_code_common': ('server_execution.code_execution', '_execute_server_code_common'),

    # Invocation tracking
    'request_details': ('server_execution.invocation_tracking', 'request_details'),
}


# Lazy loading for internal/private functions (for testing and backward compatibility)
def __getattr__(name: str):
    """Dynamically load internal functions when accessed."""
    if name in _LAZY_IMPORTS:
        module_name, attr_name = _LAZY_IMPORTS[name]
        module = __import__(module_name, fromlist=[attr_name])
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
