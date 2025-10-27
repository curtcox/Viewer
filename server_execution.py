"""Helper functions for executing user-defined servers."""

import ast
import json
import textwrap
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlsplit

import logfire
from flask import (
    Response,
    current_app,
    has_app_context,
    has_request_context,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from cid_presenter import cid_path, format_cid
from cid_utils import (
    generate_cid,
    get_current_secret_definitions_cid,
    get_current_server_definitions_cid,
    get_current_variable_definitions_cid,
    get_extension_from_mime_type,
)
from db_access import (
    ServerInvocationInput,
    create_cid_record,
    create_server_invocation,
    get_cid_by_path,
    get_server_by_name,
    get_user_secrets,
    get_user_servers,
    get_user_variables,
    save_entity,
)
from identity import current_user
from models import ServerInvocation
from syntax_highlighting import highlight_source
from text_function_runner import run_text_function

AUTO_MAIN_PARAMS_NAME = "__viewer_auto_main_params__"
AUTO_MAIN_RESULT_NAME = "__viewer_auto_main_result__"

VARIABLE_PREFETCH_SESSION_KEY = "__viewer_variable_prefetch__"
_MAX_VARIABLE_REDIRECTS = 5


def _normalize_variable_path(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    if not trimmed.startswith("/"):
        return None

    return trimmed


def _should_skip_variable_prefetch() -> bool:
    if not has_request_context():
        return False

    try:
        return bool(session.get(VARIABLE_PREFETCH_SESSION_KEY))
    except Exception:
        return False


def _resolve_redirect_target(location: str, current_path: str) -> Optional[str]:
    if not location:
        return None

    parsed = urlsplit(location)
    if parsed.scheme or parsed.netloc:
        return None

    candidate = parsed.path or ""
    if not candidate:
        return None

    if not candidate.startswith("/"):
        candidate = urljoin(current_path, candidate)

    if parsed.query:
        candidate = f"{candidate}?{parsed.query}"

    return candidate


def _fetch_variable_content(path: str) -> Optional[str]:
    normalized = _normalize_variable_path(path)
    if not normalized:
        return None

    if not has_app_context():
        return None

    if has_request_context() and normalized == request.path:
        return None

    user_id = getattr(current_user, "id", None)
    if callable(user_id):
        try:
            user_id = user_id()
        except TypeError:
            user_id = None
    if not user_id:
        getter = getattr(current_user, "get_id", None)
        if callable(getter):
            user_id = getter()

    if not user_id:
        return None

    client = current_app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True
            sess[VARIABLE_PREFETCH_SESSION_KEY] = True

        visited: set[str] = set()
        target = normalized
        for _ in range(_MAX_VARIABLE_REDIRECTS):
            if target in visited:
                break
            visited.add(target)

            response = client.get(target, follow_redirects=False)
            status = getattr(response, "status_code", None) or 0

            if status in {301, 302, 303, 307, 308}:
                next_target = _resolve_redirect_target(
                    response.headers.get("Location", ""), target
                )
                if not next_target:
                    break
                target = next_target
                continue

            if status != 200:
                break

            try:
                return response.get_data(as_text=True)
            except Exception:
                return None
    except Exception:
        return None
    finally:
        try:
            with client.session_transaction() as sess:
                sess.pop(VARIABLE_PREFETCH_SESSION_KEY, None)
        except Exception:
            pass

    return None


def _resolve_variable_values(variable_map: Dict[str, Any]) -> Dict[str, Any]:
    if not variable_map:
        return {}

    resolved: Dict[str, Any] = {}
    for name, value in variable_map.items():
        resolved_value = value
        candidate = _normalize_variable_path(value)
        if candidate and not _should_skip_variable_prefetch():
            fetched = _fetch_variable_content(candidate)
            if fetched is not None:
                resolved_value = fetched

        resolved[name] = resolved_value

    return resolved


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
    }

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

    context = base_args.get("context") if isinstance(base_args, dict) else None
    if isinstance(context, dict):
        context_variables = context.get("variables")
        if not isinstance(context_variables, dict):
            context_variables = {}
        context_secrets = context.get("secrets")
        if not isinstance(context_secrets, dict):
            context_secrets = {}
    else:
        context_variables = {}
        context_secrets = {}

    available = {
        "query_string": sorted(query_values.keys()),
        "request_body": sorted(body_values.keys()),
        "headers": sorted({k for k in request.headers.keys()}),
        "context_variables": sorted(context_variables.keys()),
        "context_secrets": sorted(context_secrets.keys()),
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

        if name in context_variables:
            resolved[name] = context_variables[name]
            continue

        if name in context_secrets:
            resolved[name] = context_secrets[name]
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
                    "Provide the parameter via the query string, request body, HTTP headers, saved variables, or saved secrets."
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
    user_id = getattr(current_user, "id", None)
    if not user_id:
        return {"variables": {}, "secrets": {}, "servers": {}}

    variables = model_as_dict(get_user_variables(user_id))
    if _should_skip_variable_prefetch():
        variables = dict(variables)
    else:
        variables = _resolve_variable_values(variables)
    secrets = model_as_dict(get_user_secrets(user_id))
    servers = model_as_dict(get_user_servers(user_id))
    return {"variables": variables, "secrets": secrets, "servers": servers}


def build_request_args() -> Dict[str, Any]:
    """Build the argument payload supplied to user-defined server code."""
    return {
        "request": request_details(),
        "context": _load_user_context(),
    }


def create_server_invocation_record(user_id: str, server_name: str, result_cid: str) -> Optional[ServerInvocation]:
    """Create a ServerInvocation record and persist related metadata."""
    servers_cid = get_current_server_definitions_cid(user_id)
    variables_cid = get_current_variable_definitions_cid(user_id)
    secrets_cid = get_current_secret_definitions_cid(user_id)

    try:
        req_json = json.dumps(request_details(), indent=2, sort_keys=True)
        req_bytes = req_json.encode("utf-8")
        req_cid_value = format_cid(generate_cid(req_bytes))
        req_cid_path = cid_path(req_cid_value)
        if req_cid_path and not get_cid_by_path(req_cid_path):
            create_cid_record(req_cid_value, req_bytes, user_id)
        req_cid = req_cid_value if req_cid_path else None
    except Exception:
        req_cid = None

    invocation = create_server_invocation(
        user_id,
        server_name,
        result_cid,
        ServerInvocationInput(
            servers_cid=servers_cid,
            variables_cid=variables_cid,
            secrets_cid=secrets_cid,
            request_details_cid=req_cid,
        ),
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
        inv_cid_value = format_cid(generate_cid(inv_bytes))
        inv_cid_path = cid_path(inv_cid_value)
        if inv_cid_path and not get_cid_by_path(inv_cid_path):
            create_cid_record(inv_cid_value, inv_bytes, user_id)

        invocation.invocation_cid = inv_cid_value if inv_cid_path else None
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


def _handle_successful_execution(output: Any, content_type: str, server_name: str) -> Response:
    output_bytes = _encode_output(output)
    cid_value = format_cid(generate_cid(output_bytes))

    cid_record_path = cid_path(cid_value)
    existing = get_cid_by_path(cid_record_path) if cid_record_path else None
    if not existing and cid_record_path:
        create_cid_record(cid_value, output_bytes, current_user.id)

    create_server_invocation_record(current_user.id, server_name, cid_value)

    extension = get_extension_from_mime_type(content_type)
    if extension and cid_record_path:
        redirect_path = cid_path(cid_value, extension)
        if redirect_path:
            return redirect(redirect_path)
    if cid_record_path:
        return redirect(cid_record_path)
    return redirect('/')


def _render_execution_error_html(
    exc: Exception,
    code: str,
    args: Dict[str, Any],
    server_name: Optional[str],
) -> str:
    """Render an HTML error page for exceptions raised during server execution."""

    from routes.core import _build_stack_trace, _extract_exception

    exception = _extract_exception(exc)
    exception_type = type(exception).__name__
    raw_message = str(exception)
    message = raw_message if raw_message else "No error message available"
    stack_trace = _build_stack_trace(exc)

    code_text = code if isinstance(code, str) else ""
    highlighted_code = None
    syntax_css = None
    if code_text:
        highlighted_code, syntax_css = highlight_source(
            code_text,
            filename=f"{server_name or 'server'}.py",
            fallback_lexer="python",
        )

    server_definition_url: Optional[str]
    if server_name:
        try:
            server_definition_url = url_for("main.view_server", server_name=server_name)
        except Exception:
            server_definition_url = None
    else:
        server_definition_url = None

    def _stringify(value: Any) -> str:
        try:
            return str(value)
        except Exception:
            return repr(value)

    try:
        args_json = json.dumps(
            args,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=_stringify,
        )
    except Exception:
        args_json = _stringify(args)

    return render_template(
        "500.html",
        stack_trace=stack_trace,
        exception_type=exception_type,
        exception_message=message,
        highlighted_server_code=highlighted_code,
        server_definition=code_text,
        syntax_css=syntax_css,
        server_args_json=args_json,
        server_name=server_name,
        server_definition_url=server_definition_url,
    )


def _handle_execution_exception(
    exc: Exception, code: str, args: Dict[str, Any], server_name: Optional[str]
) -> Response:
    try:
        html_content = _render_execution_error_html(exc, code, args, server_name)
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
) -> Optional[Response]:
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
        return _handle_execution_exception(exc, code, args, server_name)


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
) -> Optional[Any]:
    """Execute a server version referenced by a partial CID."""
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


def try_server_execution(path: str) -> Optional[Response]:
    """Execute the server whose name matches the request path."""
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
    if not function_name.isidentifier():
        return execute_server_code(server, server_name)

    return execute_server_function(server, server_name, function_name)
