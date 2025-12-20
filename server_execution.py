"""Helper functions for executing user-defined servers.

COMPATIBILITY SHIM: This module has been decomposed into the server_execution package.
All imports are re-exported from server_execution/* for backward compatibility.
"""

# Re-export all public APIs from the package
from server_execution import (
    AUTO_MAIN_PARAMS_NAME,
    AUTO_MAIN_RESULT_NAME,
    VARIABLE_PREFETCH_SESSION_KEY,
    analyze_server_definition,
    build_request_args,
    create_server_invocation_record,
    describe_function_parameters,
    describe_main_function_parameters,
    execute_server_code,
    execute_server_code_from_definition,
    execute_server_function,
    execute_server_function_from_definition,
    is_potential_server_path,
    is_potential_versioned_server_path,
    try_server_execution,
    try_server_execution_with_partial,
)

__all__ = [
    "AUTO_MAIN_PARAMS_NAME",
    "AUTO_MAIN_RESULT_NAME",
    "VARIABLE_PREFETCH_SESSION_KEY",
    "analyze_server_definition",
    "build_request_args",
    "create_server_invocation_record",
    "describe_function_parameters",
    "describe_main_function_parameters",
    "execute_server_code",
    "execute_server_code_from_definition",
    "execute_server_function",
    "execute_server_function_from_definition",
    "is_potential_server_path",
    "is_potential_versioned_server_path",
    "try_server_execution",
    "try_server_execution_with_partial",
]


# For test compatibility - delegate attribute access to the package
def __getattr__(name: str):
    """Delegate attribute access to the server_execution package."""
    import server_execution

    return getattr(server_execution, name)
