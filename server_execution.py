"""Helper functions for executing user-defined servers."""

import ast
import json
import textwrap
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from flask import jsonify, make_response, redirect, render_template, request
from flask_login import current_user
import logfire

from cid_utils import (
    generate_cid,
    get_current_secret_definitions_cid,
    get_current_server_definitions_cid,
    get_current_variable_definitions_cid,
    get_extension_from_mime_type,
)
from db_access import (
    create_cid_record,
    create_server_invocation,
    get_cid_by_path,
    get_server_by_name,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    save_entity,
)
from text_function_runner import run_text_function

AUTO_MAIN_PARAMS_NAME = "__viewer_auto_main_params__"
AUTO_MAIN_RESULT_NAME = "__viewer_auto_main_result__"


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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pragma: no cover - exercised indirectly
        self.function_depth += 1
        try:
            if self.function_depth == 2 and node.name == self.target_name:
                self.target_node = node
            self.generic_visit(node)
        finally:
            self.function_depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Return(self, node: ast.Return) -> None:  # pragma: no cover - exercised indirectly
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
        {"name": name, "required": name in required}
        for name in details.parameter_order
    ]

    return {
        "parameters": parameters,
        "required_parameters": details.required_parameters,
        "optional_parameters": details.optional_parameters,
    }


def describe_main_function_parameters(code: str) -> Optional[Dict[str, Any]]:
    """Return a simplified description of ``main`` parameters for UI helpers."""

    return describe_function_parameters(code, "main")


def _extract_request_body_values() -> Dict[str, Any]:
    body: Dict[str, Any] = {}

    try:
        json_payload = request.get_json(silent=True)
    except Exception:  # pragma: no cover - defensive
        json_payload = None

    if isinstance(json_payload, dict):
        body.update(json_payload)

    if request.form:
        body.update(request.form.to_dict(flat=True))

    return body


def _resolve_function_parameters(
    details: FunctionDetails,
    base_args: Dict[str, Any],
) -> Dict[str, Any]:
    required = set(details.required_parameters)
    resolved: Dict[str, Any] = {}
    missing: List[str] = []

    query_values = request.args.to_dict(flat=True) if request.args else {}
    body_values = _extract_request_body_values()
    header_values = {k.lower(): v for k, v in request.headers.items()}
    available = {
        "query_string": sorted(query_values.keys()),
        "request_body": sorted(body_values.keys()),
        "headers": sorted({k for k in request.headers.keys()}),
    }

    def _lookup_header(name: str) -> Optional[Any]:
        lowered = name.lower()
        if lowered in header_values:
            return header_values[lowered]
        dashed = name.replace("_", "-").lower()
        if dashed in header_values:
            return header_values[dashed]
        return None

    for name in details.parameter_order:
        if name in query_values:
            resolved[name] = query_values[name]
            continue

        if name in body_values:
            resolved[name] = body_values[name]
            continue

        header_value = _lookup_header(name)
        if header_value is not None:
            resolved[name] = header_value
            continue

        if name in base_args:
            resolved[name] = base_args[name]
            continue

        if name in required:
            missing.append(name)

    if missing:
        raise MissingParameterError(missing, available)

    return resolved


def _build_missing_parameter_response(
    function_name: str, error: MissingParameterError
):
    payload = {
        "error": f"Missing required parameters for {function_name}()",
        "missing_parameters": [
            {
                "name": name,
                "detail": (
                    "Provide the parameter via the query string, request body, or HTTP headers."
                ),
            }
            for name in sorted(error.missing)
        ],
        "available_keys": error.available,
    }
    response = jsonify(payload)
    response.status_code = 400
    return response


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


def _prepare_invocation(
    code: str,
    base_args: Dict[str, Any],
    *,
    function_name: Optional[str],
    allow_fallback: bool,
) -> Any:
    if not function_name:
        return code, base_args

    details = _analyze_server_definition_for_function(code, function_name)
    if not details:
        return (code, base_args) if allow_fallback else None

    if details.unsupported_reasons:
        return _build_unsupported_signature_response(function_name, details)

    try:
        resolved = _resolve_function_parameters(details, base_args)
    except MissingParameterError as error:
        return _build_missing_parameter_response(function_name, error)

    new_args = dict(base_args)
    new_args[AUTO_MAIN_PARAMS_NAME] = resolved

    snippet = textwrap.dedent(
        f"""
        {AUTO_MAIN_RESULT_NAME} = {function_name}(**{AUTO_MAIN_PARAMS_NAME})
        return {AUTO_MAIN_RESULT_NAME}
        """
    ).strip()

    base_indent = ""
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped:
            base_indent = line[: len(line) - len(stripped)]
            break

    if base_indent:
        snippet = textwrap.indent(snippet, base_indent)

    combined = code.rstrip()
    if combined:
        combined = f"{combined}\n\n{snippet}\n"
    else:
        combined = f"{snippet}\n"

    return combined, new_args


def model_as_dict(model_objects: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """Convert SQLAlchemy model objects to a name->definition mapping."""
    if not model_objects:
        return {}

    result: Dict[str, Any] = {}
    for obj in model_objects:
        if hasattr(obj, "name") and hasattr(obj, "definition"):
            result[obj.name] = obj.definition
        else:
            result[str(obj)] = str(obj)
    return result


def request_details() -> Dict[str, Any]:
    """Collect request details for server execution context."""
    return {
        "path": request.path,
        "query_string": request.query_string.decode("utf-8"),
        "remote_addr": request.remote_addr,
        "user_agent": request.user_agent.string,
        "headers": {k: v for k, v in request.headers if k.lower() != "cookie"},
        "form_data": dict(request.form) if request.form else {},
        "args": dict(request.args) if request.args else {},
        "endpoint": request.endpoint,
        "scheme": request.scheme,
        "host": request.host,
        "method": request.method,
    }


def _load_user_context() -> Dict[str, Dict[str, Any]]:
    if not getattr(current_user, "is_authenticated", False):
        return {"variables": {}, "secrets": {}, "servers": {}}

    user_id = getattr(current_user, "id", None)
    if not user_id:
        return {"variables": {}, "secrets": {}, "servers": {}}

    variables = model_as_dict(get_user_variables(user_id))
    secrets = model_as_dict(get_user_secrets(user_id))
    servers = model_as_dict(get_user_servers(user_id))
    return {"variables": variables, "secrets": secrets, "servers": servers}


def build_request_args() -> Dict[str, Any]:
    """Build the argument payload supplied to user-defined server code."""
    return {
        "request": request_details(),
        "context": _load_user_context(),
    }


def create_server_invocation_record(user_id: str, server_name: str, result_cid: str):
    """Create a ServerInvocation record and persist related metadata."""
    servers_cid = get_current_server_definitions_cid(user_id)
    variables_cid = get_current_variable_definitions_cid(user_id)
    secrets_cid = get_current_secret_definitions_cid(user_id)

    try:
        req_json = json.dumps(request_details(), indent=2, sort_keys=True)
        req_bytes = req_json.encode("utf-8")
        req_cid = generate_cid(req_bytes)
        if not get_cid_by_path(f"/{req_cid}"):
            create_cid_record(req_cid, req_bytes, user_id)
    except Exception:
        req_cid = None

    invocation = create_server_invocation(
        user_id,
        server_name,
        result_cid,
        servers_cid=servers_cid,
        variables_cid=variables_cid,
        secrets_cid=secrets_cid,
        request_details_cid=req_cid,
        invocation_cid=None,
    )

    try:
        inv_payload = {
            "user_id": user_id,
            "server_name": server_name,
            "result_cid": result_cid,
            "servers_cid": servers_cid,
            "variables_cid": variables_cid,
            "secrets_cid": secrets_cid,
            "request_details_cid": req_cid,
            "invoked_at": invocation.invoked_at.isoformat() if invocation.invoked_at else None,
        }
        inv_json = json.dumps(inv_payload, indent=2, sort_keys=True)
        inv_bytes = inv_json.encode("utf-8")
        inv_cid = generate_cid(inv_bytes)
        if not get_cid_by_path(f"/{inv_cid}"):
            create_cid_record(inv_cid, inv_bytes, user_id)

        invocation.invocation_cid = inv_cid
        save_entity(invocation)
    except Exception:
        pass

    return invocation


def _encode_output(output: Any) -> bytes:
    if isinstance(output, bytes):
        return output
    if isinstance(output, str):
        return output.encode("utf-8")
    # Dicts -> JSON for human-friendly output instead of concatenated keys
    if isinstance(output, dict):
        try:
            return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        except Exception:
            return str(output).encode("utf-8")
    # If it's an iterable, try to handle common patterns gracefully
    try:
        from collections.abc import Iterable as _Iterable  # local import to avoid top changes
        if isinstance(output, _Iterable):
            items = list(output)
            # If elements look JSON-serializable (e.g., list of dicts), prefer JSON
            try:
                if items and any(isinstance(x, (dict, list, tuple)) for x in items):
                    return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            except Exception as json_err:
                print(f"[server_execution] JSON encoding attempt failed: {type(json_err).__name__}: {json_err}")
                print(f"[server_execution] Output type: {type(output).__name__}")
                print(f"[server_execution] Items types: {[type(x).__name__ for x in items[:5]]}...")
                traceback.print_exc()
                # Continue to try other encodings
            # List of ints -> bytes directly
            if all(isinstance(x, int) for x in items):
                return bytes(items)
            # List of bytes -> concatenate
            if all(isinstance(x, bytes) for x in items):
                return b"".join(items)
            # List of strings -> join then encode
            if all(isinstance(x, str) for x in items):
                return "".join(items).encode("utf-8")
    except Exception:
        # fall back below
        pass

    # Fallback: encode the string representation
    return str(output).encode("utf-8")


def _log_server_output(debug_prefix: str, error_suffix: str, output: Any, content_type: str) -> None:
    """Log execution details while tolerating logging failures."""
    try:
        sample = repr(output)
        if sample and len(sample) > 300:
            sample = sample[:300] + "…"
        print(
            f"[server_execution] {debug_prefix}: output_type={type(output).__name__}, "
            f"content_type={content_type}, sample={sample}"
        )
    except Exception as debug_err:
        suffix = f" {error_suffix}" if error_suffix else ""
        print(
            f"[server_execution] Debug output failed{suffix}: "
            f"{type(debug_err).__name__}: {debug_err}"
        )
        traceback.print_exc()


def _handle_successful_execution(output: Any, content_type: str, server_name: str):
    output_bytes = _encode_output(output)
    cid = generate_cid(output_bytes)

    existing = get_cid_by_path(f"/{cid}")
    if not existing:
        create_cid_record(cid, output_bytes, current_user.id)

    create_server_invocation_record(current_user.id, server_name, cid)

    extension = get_extension_from_mime_type(content_type)
    if extension:
        return redirect(f"/{cid}.{extension}")
    return redirect(f"/{cid}")


def _render_execution_error_html(exc: Exception, code: str, args: Dict[str, Any]) -> str:
    """Render an HTML error page for exceptions raised during server execution."""

    from routes.core import _build_stack_trace, _extract_exception

    exception = _extract_exception(exc)
    exception_type = type(exception).__name__
    raw_message = str(exception)
    message = raw_message if raw_message else "No error message available"
    stack_trace = _build_stack_trace(exc)

    return render_template(
        "500.html",
        stack_trace=stack_trace,
        exception_type=exception_type,
        exception_message=message,
    )


def _handle_execution_exception(exc: Exception, code: str, args: Dict[str, Any]):
    try:
        html_content = _render_execution_error_html(exc, code, args)
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    except Exception:
        text = (
            str(exc)
            + "\n\n"
            + traceback.format_exc()
            + "\n\n"
            + code
            + "\n\n"
            + str(args)
        )
        response = make_response(text)
        response.headers["Content-Type"] = "text/plain"

    response.status_code = 500
    return response


def _execute_server_code_common(
    code: str,
    server_name: str,
    debug_prefix: str,
    error_suffix: str,
    *,
    function_name: Optional[str] = "main",
    allow_fallback: bool = True,
):
    args = build_request_args()

    prepared = _prepare_invocation(
        code, args, function_name=function_name, allow_fallback=allow_fallback
    )
    if prepared is None:
        return None

    if isinstance(prepared, tuple):
        code_to_run, args_to_use = prepared
    else:
        return prepared

    try:
        result = run_text_function(code_to_run, args_to_use)
        if isinstance(result, dict):
            output = result.get("output", "")
            content_type = result.get("content_type", "text/html")
        elif isinstance(result, tuple) and len(result) == 2:
            output, content_type = result
        else:
            output = result
            content_type = "text/html"
        _log_server_output(debug_prefix, error_suffix, output, content_type)
        return _handle_successful_execution(output, content_type, server_name)
    except Exception as exc:
        return _handle_execution_exception(exc, code, args)


@logfire.instrument("server_execution.execute_server_code({server=}, {server_name=})", extract_args=True, record_return=True)
def execute_server_code(server, server_name: str):
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
def execute_server_code_from_definition(definition_text: str, server_name: str):
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
def execute_server_function(server, server_name: str, function_name: str):
    """Execute a named helper function within a server definition."""

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
):
    """Execute a helper function from a supplied historical definition."""

    return _execute_server_code_common(
        definition_text,
        server_name,
        "execute_server_function_from_definition",
        f" in _from_definition for {function_name}",
        function_name=function_name,
        allow_fallback=False,
    )


def is_potential_versioned_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could represent /{server}/{partial_cid}[/function]."""
    if not path or not path.startswith("/"):
        return False
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) not in {2, 3}:
        return False
    if f"/{parts[0]}" in existing_routes:
        return False
    return True


def try_server_execution_with_partial(
    path: str,
    history_fetcher: Callable[[str, str], Iterable[Dict[str, Any]]],
):
    """Execute a server version referenced by a partial CID."""
    if not getattr(current_user, "is_authenticated", False):
        return None

    parts = [segment for segment in path.split("/") if segment]
    if len(parts) not in {2, 3}:
        return None
    server_name, partial = parts[0], parts[1]
    function_name = parts[2] if len(parts) == 3 else None

    server = get_server_by_name(current_user.id, server_name)
    if not server:
        return None

    history = history_fetcher(current_user.id, server_name)
    matches = [h for h in history if h.get("definition_cid", "").startswith(partial)]

    if not matches:
        return render_template("404.html", path=path), 404

    if len(matches) > 1:
        payload = {
            "error": "Multiple matching server versions",
            "server": server_name,
            "partial": partial,
            "matches": [
                {
                    "definition_cid": m.get("definition_cid"),
                    "snapshot_cid": m.get("snapshot_cid"),
                    "created_at": m.get("created_at").isoformat() if m.get("created_at") else None,
                }
                for m in matches
            ],
        }
        return jsonify(payload), 400

    definition_text = matches[0].get("definition", "")
    if function_name:
        return execute_server_function_from_definition(
            definition_text, server_name, function_name
        )
    return execute_server_code_from_definition(definition_text, server_name)


def is_potential_server_path(path: str, existing_routes: Iterable[str]) -> bool:
    """Return True if path could map to a server name or helper function."""

    if not path or not path.startswith("/"):
        return False

    if path in existing_routes:
        return False

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return False

    if f"/{parts[0]}" in existing_routes:
        return False

    if len(parts) > 2:
        return False

    return True


def try_server_execution(path: str):
    """Execute the server whose name matches the request path."""
    if not getattr(current_user, "is_authenticated", False):
        return None

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return None

    server_name = parts[0]
    server = get_server_by_name(current_user.id, server_name)
    if not server:
        return None

    if len(parts) == 1:
        return execute_server_code(server, server_name)

    function_name = parts[1]
    return execute_server_function(server, server_name, function_name)
