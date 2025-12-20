"""Function analysis and parameter inspection for server definitions."""

import ast
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FunctionDetails:
    """Extracted metadata about an auto-invoked function."""

    parameter_order: List[str]
    required_parameters: List[str]
    optional_parameters: List[str]
    unsupported_reasons: List[str]


class _FunctionAnalyzer(ast.NodeVisitor):
    """Inspect a wrapped server definition for function compatibility."""

    def __init__(self, target_name: str):
        self.function_depth = 0
        self.target_name = target_name
        self.target_node: Optional[ast.FunctionDef] = None
        self.has_outer_return = False

    def visit_FunctionDef(
        self, node: ast.FunctionDef
    ) -> None:  # pragma: no cover - exercised indirectly
        self.function_depth += 1
        try:
            if self.function_depth == 2 and node.name == self.target_name:
                self.target_node = node
            self.generic_visit(node)
        finally:
            self.function_depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Return(
        self, node: ast.Return
    ) -> None:  # pragma: no cover - exercised indirectly
        if self.function_depth == 1:
            self.has_outer_return = True
        self.generic_visit(node)


class MissingParameterError(Exception):
    """Raised when a required parameter cannot be resolved from the request."""

    def __init__(self, missing: List[str], available: Dict[str, List[str]]):
        message = ", ".join(sorted(missing))
        super().__init__(f"Missing required parameters: {message}")
        self.missing = missing
        self.available = available


def _parse_function_details(node: ast.FunctionDef) -> FunctionDetails:
    positional = [arg.arg for arg in node.args.args]
    defaults = list(node.args.defaults) if node.args.defaults else []
    num_required = len(positional) - len(defaults)
    required_params = positional[:num_required]
    optional_params = positional[num_required:]

    kwonly_args = [arg.arg for arg in node.args.kwonlyargs]
    kw_defaults = node.args.kw_defaults or []
    for index, arg in enumerate(kwonly_args):
        default_value = kw_defaults[index] if index < len(kw_defaults) else None
        if default_value is None:
            required_params.append(arg)
        else:
            optional_params.append(arg)

    parameter_order = positional + kwonly_args

    unsupported: List[str] = []
    if getattr(node.args, "posonlyargs", []):
        unsupported.append("positional-only parameters are not supported")
    if node.args.vararg is not None:
        unsupported.append("var positional parameters (*args) are not supported")
    if node.args.kwarg is not None:
        unsupported.append("arbitrary keyword parameters (**kwargs) are not supported")

    return FunctionDetails(
        parameter_order=parameter_order,
        required_parameters=required_params,
        optional_parameters=optional_params,
        unsupported_reasons=unsupported,
    )


def _analyze_server_definition_for_function(
    code: str, function_name: str
) -> Optional[FunctionDetails]:
    wrapper_src = "def __viewer_wrapper__():\n" + textwrap.indent(code, "    ")
    try:
        tree = ast.parse(wrapper_src)
    except SyntaxError:
        return None

    wrapper_fn = tree.body[0]
    if not isinstance(wrapper_fn, ast.FunctionDef):  # pragma: no cover - defensive
        return None

    analyzer = _FunctionAnalyzer(function_name)
    analyzer.visit(wrapper_fn)

    if analyzer.target_node is None or analyzer.has_outer_return:
        return None

    return _parse_function_details(analyzer.target_node)


def describe_function_parameters(
    code: str, function_name: str
) -> Optional[Dict[str, Any]]:
    """Return a simplified description of function parameters for UI helpers."""

    details = _analyze_server_definition_for_function(code or "", function_name)
    if not details or details.unsupported_reasons:
        return None

    required = set(details.required_parameters)
    parameters = [
        {"name": name, "required": name in required} for name in details.parameter_order
    ]

    return {
        "parameters": parameters,
        "required_parameters": details.required_parameters,
        "optional_parameters": details.optional_parameters,
    }


def describe_main_function_parameters(code: str) -> Optional[Dict[str, Any]]:
    """Return a simplified description of ``main`` parameters for UI helpers."""

    return describe_function_parameters(code, "main")


def analyze_server_definition(code: str) -> Dict[str, Any]:
    """Inspect a server definition and summarise auto main compatibility."""

    result: Dict[str, Any] = {
        "is_valid": True,
        "errors": [],
        "auto_main": False,
        "auto_main_errors": [],
        "parameters": [],
        "has_main": False,
        "mode": "query",
        "language": "python",
    }

    from server_execution.language_detection import (
        detect_server_language,
    )  # Local import to avoid cycles

    result["language"] = detect_server_language(code)

    try:
        ast.parse(code or "", mode="exec")
    except SyntaxError as exc:
        result["is_valid"] = False
        message = exc.msg or "Invalid syntax"
        error_info = {
            "message": message,
            "line": exc.lineno,
            "column": exc.offset,
        }
        if isinstance(exc.text, str):
            error_info["text"] = exc.text.strip()
        result["errors"].append(error_info)
        return result

    details = _analyze_server_definition_for_function(code or "", "main")
    if details is None:
        return result

    result["has_main"] = True
    if details.unsupported_reasons:
        result["auto_main_errors"] = list(details.unsupported_reasons)
        return result

    result["auto_main"] = True
    result["parameters"] = [
        {"name": name, "required": name in set(details.required_parameters)}
        for name in details.parameter_order
    ]
    result["mode"] = "main"
    return result
