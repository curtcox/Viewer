# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Gateway server for proxying requests to external and internal APIs.

This server provides a unified interface for accessing APIs with customizable
request and response transformations. All server-specific configuration comes
from the 'gateways' variable.

Routes:
    /gateway - Instruction page
    /gateway/request - Request experimentation form
    /gateway/response - Response experimentation form
    /gateway/meta/{server} - Server meta page with transform validation
    /gateway/{server} - Issue request to gateway server root
    /gateway/{server}/{rest} - Issue request to gateway server with path
"""

import ast
import inspect
import json
import logging
from html import escape
from pathlib import Path
from urllib.parse import urljoin

import requests
from flask import request as flask_request
from jinja2 import Template

logger = logging.getLogger(__name__)


def main(context=None):
    """Gateway server main function.

    Handles all gateway routes based on the request path.

    Parameters:
        context: Request context (automatically provided)
    """
    # Get the request path
    request_path = flask_request.path or "/"

    # Parse the path to determine the route
    path_parts = request_path.strip("/").split("/")

    # Remove 'gateway' prefix if present
    if path_parts and path_parts[0] == "gateway":
        path_parts = path_parts[1:]

    # Load gateways configuration
    gateways = _load_gateways(context)

    # Route to appropriate handler
    if not path_parts or path_parts[0] == "":
        return _handle_instruction_page(gateways, context)

    first_part = path_parts[0]

    if first_part == "request":
        return _handle_request_form(gateways, context)

    if first_part == "response":
        return _handle_response_form(gateways, context)

    if first_part == "meta" and len(path_parts) > 1:
        server_name = path_parts[1]
        return _handle_meta_page(server_name, gateways, context)

    # Otherwise, treat first part as server name
    server_name = first_part
    rest_path = "/".join(path_parts[1:]) if len(path_parts) > 1 else ""

    return _handle_gateway_request(server_name, rest_path, gateways, context)


def _load_gateways(context):
    """Load gateway configurations from the gateways variable."""
    try:
        # Try to get gateways from context variables
        if context and hasattr(context, "variables"):
            gateways_value = context.variables.get("gateways")
            if gateways_value:
                if isinstance(gateways_value, str):
                    return json.loads(gateways_value)
                return gateways_value

        # Try to resolve from named value resolver
        from server_execution.request_parsing import resolve_named_value

        found, value = resolve_named_value("gateways")
        if found and value:
            if isinstance(value, str):
                return json.loads(value)
            return value

    except Exception as e:
        logger.warning(f"Failed to load gateways: {e}")

    return {}


def _load_template(template_name):
    """Load a Jinja2 template from the gateway templates directory."""
    template_dir = Path(__file__).parent.parent / "templates" / "gateway"
    template_path = template_dir / template_name

    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as f:
            return Template(f.read())

    # Fallback: return a simple error template
    return Template(
        """<!DOCTYPE html><html><body>
        <h1>Template Not Found</h1>
        <p>Could not load template: {{ template_name }}</p>
        </body></html>"""
    )


def _handle_instruction_page(gateways, context):
    """Render the main gateway instruction page."""
    template = _load_template("instruction.html")
    html = template.render(gateways=gateways)
    return {"output": html, "content_type": "text/html"}


def _handle_request_form(gateways, context):
    """Handle the request experimentation form."""
    template = _load_template("request_form.html")

    # Get form data
    form_data = dict(flask_request.form) if flask_request.form else {}
    action = form_data.get("action", "")

    # Initialize context
    ctx = {
        "gateways": gateways,
        "selected_server": form_data.get("server", ""),
        "method": form_data.get("method", "GET"),
        "path": form_data.get("path", ""),
        "query_string": form_data.get("query_string", ""),
        "headers": form_data.get("headers", "{}"),
        "body": form_data.get("body", ""),
        "transform_override": form_data.get("transform_override", ""),
        "invocation_cid": form_data.get("invocation_cid", ""),
        "error": None,
        "success": None,
        "preview": None,
        "response": None,
        "gateway_defined": False,
        "invocation_server": None,
        "default_transform": _get_default_request_transform(),
    }

    # Handle actions
    if action == "load" and ctx["invocation_cid"]:
        ctx = _load_invocation_for_request(ctx, gateways)
    elif action == "preview" and ctx["selected_server"]:
        ctx = _preview_request_transform(ctx, gateways)
    elif action == "execute" and ctx["selected_server"]:
        ctx = _execute_gateway_request(ctx, gateways, context)

    html = template.render(**ctx)
    return {"output": html, "content_type": "text/html"}


def _handle_response_form(gateways, context):
    """Handle the response experimentation form."""
    template = _load_template("response_form.html")

    # Get form data
    form_data = dict(flask_request.form) if flask_request.form else {}
    action = form_data.get("action", "")

    # Initialize context
    ctx = {
        "gateways": gateways,
        "selected_server": form_data.get("server", ""),
        "status_code": int(form_data.get("status_code", 200)),
        "request_path": form_data.get("request_path", ""),
        "response_headers": form_data.get("response_headers", '{"Content-Type": "application/json"}'),
        "response_body": form_data.get("response_body", ""),
        "transform_override": form_data.get("transform_override", ""),
        "invocation_cid": form_data.get("invocation_cid", ""),
        "error": None,
        "success": None,
        "preview": None,
        "preview_html": None,
        "gateway_defined": False,
        "invocation_server": None,
        "default_transform": _get_default_response_transform(),
    }

    # Handle actions
    if action == "load" and ctx["invocation_cid"]:
        ctx = _load_invocation_for_response(ctx, gateways)
    elif action == "transform":
        ctx = _transform_response(ctx, gateways, context)

    html = template.render(**ctx)
    return {"output": html, "content_type": "text/html"}


def _handle_meta_page(server_name, gateways, context):
    """Handle the gateway meta page showing transform source and validation."""
    if server_name not in gateways:
        return _render_error("Gateway Not Found", f"No gateway configured for '{server_name}'", gateways)

    config = gateways[server_name]
    template = _load_template("meta.html")

    # Load and validate transforms
    request_transform_source = None
    request_transform_status = "error"
    request_transform_status_text = "Not Found"
    request_transform_error = None
    request_transform_warnings = []

    response_transform_source = None
    response_transform_status = "error"
    response_transform_status_text = "Not Found"
    response_transform_error = None
    response_transform_warnings = []

    # Load request transform
    request_cid = config.get("request_transform_cid")
    if request_cid:
        source, error, warnings = _load_and_validate_transform(request_cid, "transform_request", context)
        request_transform_source = source
        if error:
            request_transform_error = error
            request_transform_status = "error"
            request_transform_status_text = "Error"
        elif warnings:
            request_transform_warnings = warnings
            request_transform_status = "warning"
            request_transform_status_text = "Valid with Warnings"
        else:
            request_transform_status = "valid"
            request_transform_status_text = "Valid"

    # Load response transform
    response_cid = config.get("response_transform_cid")
    if response_cid:
        source, error, warnings = _load_and_validate_transform(response_cid, "transform_response", context)
        response_transform_source = source
        if error:
            response_transform_error = error
            response_transform_status = "error"
            response_transform_status_text = "Error"
        elif warnings:
            response_transform_warnings = warnings
            response_transform_status = "warning"
            response_transform_status_text = "Valid with Warnings"
        else:
            response_transform_status = "valid"
            response_transform_status_text = "Valid"

    # Check if server exists
    server_exists = _check_server_exists(server_name, context)

    # Generate test paths based on server type
    test_paths = _get_test_paths(server_name)

    html = template.render(
        server_name=server_name,
        config=config,
        server_exists=server_exists,
        request_transform_source=request_transform_source,
        request_transform_status=request_transform_status,
        request_transform_status_text=request_transform_status_text,
        request_transform_error=request_transform_error,
        request_transform_warnings=request_transform_warnings,
        response_transform_source=response_transform_source,
        response_transform_status=response_transform_status,
        response_transform_status_text=response_transform_status_text,
        response_transform_error=response_transform_error,
        response_transform_warnings=response_transform_warnings,
        test_paths=test_paths,
    )
    return {"output": html, "content_type": "text/html"}


def _handle_gateway_request(server_name, rest_path, gateways, context):
    """Handle an actual gateway request to a configured server."""
    if server_name not in gateways:
        return _render_error(
            "Gateway Not Found",
            f"No gateway configured for '{server_name}'",
            gateways,
        )

    config = gateways[server_name]

    # Build request details
    try:
        json_body = flask_request.get_json(silent=True)
    except Exception:
        json_body = None

    try:
        raw_body = flask_request.get_data(as_text=True)
    except Exception:
        raw_body = None

    request_details = {
        "path": rest_path,
        "query_string": flask_request.query_string.decode("utf-8"),
        "method": flask_request.method,
        "headers": {k: v for k, v in flask_request.headers if k.lower() != "cookie"},
        "json": json_body,
        "body": raw_body,
    }

    # Load and execute request transform
    request_cid = config.get("request_transform_cid")
    if request_cid:
        try:
            transform_fn = _load_transform_function(request_cid, context)
            if transform_fn:
                transformed = transform_fn(request_details, context)
                if isinstance(transformed, dict):
                    request_details = transformed
        except Exception as e:
            logger.error(f"Request transform error: {e}")
            return _render_error(
                "Request Transform Error",
                f"Failed to execute request transform: {escape(str(e))}",
                gateways,
            )

    # Make the request to the target
    target_url = config.get("target_url", "")
    try:
        response = _execute_target_request(target_url, request_details)
    except Exception as e:
        logger.error(f"Target request error: {e}")
        return _render_error(
            "Request Failed",
            f"Failed to connect to target: {escape(str(e))}",
            gateways,
        )

    # Build response details
    try:
        response_json = response.json() if "application/json" in response.headers.get("Content-Type", "") else None
    except Exception:
        response_json = None

    response_details = {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "content": response.content,
        "text": response.text,
        "json": response_json,
        "request_path": rest_path,
    }

    # Load and execute response transform
    response_cid = config.get("response_transform_cid")
    if response_cid:
        try:
            transform_fn = _load_transform_function(response_cid, context)
            if transform_fn:
                result = transform_fn(response_details, context)
                if isinstance(result, dict) and "output" in result:
                    return result
        except Exception as e:
            logger.error(f"Response transform error: {e}")
            return _render_error(
                "Response Transform Error",
                f"Failed to execute response transform: {escape(str(e))}",
                gateways,
            )

    # Default: return raw response
    return {
        "output": response.content,
        "content_type": response.headers.get("Content-Type", "text/plain"),
    }


def _execute_target_request(target_url, request_details):
    """Execute a request to the target server."""
    # Build the full URL
    if target_url.startswith("/"):
        # Internal server request
        base_url = flask_request.host_url.rstrip("/")
        url = urljoin(base_url, target_url)
    else:
        url = request_details.get("url", target_url)

    # Add path if not already in URL
    if "url" not in request_details:
        path = request_details.get("path", "")
        if path:
            url = urljoin(url.rstrip("/") + "/", path.lstrip("/"))

    method = request_details.get("method", "GET")
    headers = request_details.get("headers", {})
    params = request_details.get("params")
    json_body = request_details.get("json")
    data = request_details.get("data")

    # Filter headers
    filtered_headers = {}
    for key, value in headers.items():
        if key.lower() not in ("host", "content-length", "transfer-encoding"):
            filtered_headers[key] = value

    return requests.request(
        method,
        url,
        headers=filtered_headers,
        params=params,
        json=json_body if json_body else None,
        data=data if data and not json_body else None,
        timeout=30,
        allow_redirects=True,
    )


def _load_transform_function(cid, context):
    """Load a transform function from a CID."""
    try:
        # Try to load from CID store
        from db_access import get_cid_by_path

        cid_record = get_cid_by_path(cid)
        if cid_record and cid_record.file_data:
            source = cid_record.file_data.decode("utf-8")
            return _compile_transform(source)

        # Try direct file path (for development)
        from pathlib import Path
        if Path(cid).exists():
            with open(cid, "r", encoding="utf-8") as f:
                source = f.read()
            return _compile_transform(source)

    except Exception as e:
        logger.error(f"Failed to load transform from CID {cid}: {e}")

    return None


def _compile_transform(source):
    """Compile transform source code and return the transform function."""
    # Create a namespace for execution
    namespace = {"__builtins__": __builtins__}

    # Execute the source
    exec(source, namespace)

    # Look for transform functions
    for name in ("transform_request", "transform_response"):
        if name in namespace and callable(namespace[name]):
            return namespace[name]

    return None


def _load_and_validate_transform(cid, expected_fn_name, context):
    """Load transform source and validate it.

    Returns: (source, error, warnings)
    """
    source = None
    error = None
    warnings = []

    try:
        # Try to load source
        from db_access import get_cid_by_path

        cid_record = get_cid_by_path(cid)
        if cid_record and cid_record.file_data:
            source = cid_record.file_data.decode("utf-8")
        else:
            # Try file path
            from pathlib import Path
            if Path(cid).exists():
                with open(cid, "r", encoding="utf-8") as f:
                    source = f.read()

        if not source:
            return None, f"Transform not found at CID: {cid}", []

        # Syntax validation
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return source, f"Syntax error at line {e.lineno}: {e.msg}", []

        # Check for expected function
        function_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == expected_fn_name:
                function_found = True
                # Check signature
                args = node.args
                if len(args.args) < 2:
                    warnings.append(f"Function {expected_fn_name} should have at least 2 parameters (request_details, context)")
                break

        if not function_found:
            return source, f"Missing required function: {expected_fn_name}", []

        return source, None, warnings

    except Exception as e:
        return source, f"Validation error: {str(e)}", []


def _check_server_exists(server_name, context):
    """Check if a server with the given name exists."""
    try:
        from db_access import get_server_by_name
        server = get_server_by_name(server_name)
        return server is not None
    except Exception:
        return False


def _get_test_paths(server_name):
    """Get suggested test paths for a gateway."""
    test_paths = {
        "jsonplaceholder": ["posts", "users", "comments", "albums"],
        "man": ["ls", "cat", "grep"],
        "tldr": ["ls", "cat", "git"],
        "hrx": [],
    }
    return test_paths.get(server_name, [])


def _load_invocation_for_request(ctx, gateways):
    """Load invocation data for the request form."""
    try:
        from db_access import get_cid_by_path

        # Load the invocation JSON
        cid = ctx["invocation_cid"]
        cid_record = get_cid_by_path(cid)
        if not cid_record:
            ctx["error"] = f"CID not found: {cid}"
            return ctx

        invocation_data = json.loads(cid_record.file_data.decode("utf-8"))

        # Check if this is a server invocation
        if "server_name" not in invocation_data:
            ctx["error"] = "CID does not reference a server invocation"
            return ctx

        ctx["invocation_server"] = invocation_data.get("server_name", "")
        ctx["gateway_defined"] = ctx["invocation_server"] in gateways

        # Load request details
        request_cid = invocation_data.get("request_details_cid")
        if request_cid:
            request_record = get_cid_by_path(request_cid)
            if request_record:
                request_data = json.loads(request_record.file_data.decode("utf-8"))
                ctx["path"] = request_data.get("path", "")
                ctx["method"] = request_data.get("method", "GET")
                ctx["query_string"] = request_data.get("query_string", "")
                ctx["headers"] = json.dumps(request_data.get("headers", {}), indent=2)
                ctx["body"] = request_data.get("body", "")
            else:
                ctx["error"] = f"Request details CID not found: {request_cid}"

        ctx["success"] = f"Loaded invocation from {ctx['invocation_server']}"

    except Exception as e:
        ctx["error"] = f"Failed to load invocation: {str(e)}"

    return ctx


def _load_invocation_for_response(ctx, gateways):
    """Load invocation data for the response form."""
    try:
        from db_access import get_cid_by_path

        # Load the invocation JSON
        cid = ctx["invocation_cid"]
        cid_record = get_cid_by_path(cid)
        if not cid_record:
            ctx["error"] = f"CID not found: {cid}"
            return ctx

        invocation_data = json.loads(cid_record.file_data.decode("utf-8"))

        # Check if this is a server invocation
        if "server_name" not in invocation_data:
            ctx["error"] = "CID does not reference a server invocation"
            return ctx

        ctx["invocation_server"] = invocation_data.get("server_name", "")
        ctx["gateway_defined"] = ctx["invocation_server"] in gateways

        # Load result
        result_cid = invocation_data.get("result_cid")
        if result_cid:
            result_record = get_cid_by_path(result_cid)
            if result_record:
                ctx["response_body"] = result_record.file_data.decode("utf-8", errors="replace")
            else:
                ctx["error"] = f"Result CID not found: {result_cid}"

        ctx["success"] = f"Loaded invocation from {ctx['invocation_server']}"

    except Exception as e:
        ctx["error"] = f"Failed to load invocation: {str(e)}"

    return ctx


def _preview_request_transform(ctx, gateways):
    """Preview the transformed request without executing it."""
    try:
        server_name = ctx["selected_server"]
        if server_name not in gateways:
            ctx["error"] = f"Gateway not found: {server_name}"
            return ctx

        config = gateways[server_name]

        # Build request details
        request_details = {
            "path": ctx["path"],
            "query_string": ctx["query_string"],
            "method": ctx["method"],
            "headers": json.loads(ctx["headers"]) if ctx["headers"] else {},
            "json": json.loads(ctx["body"]) if ctx["body"] else None,
            "body": ctx["body"],
        }

        # Get transform source
        transform_source = ctx["transform_override"] if ctx["transform_override"] else None
        if not transform_source:
            # Load default from CID
            request_cid = config.get("request_transform_cid")
            if request_cid:
                transform_fn = _load_transform_function(request_cid, None)
                if transform_fn:
                    result = transform_fn(request_details, {})
                    ctx["preview"] = json.dumps(result, indent=2)
                    return ctx

        # Use override
        if transform_source:
            transform_fn = _compile_transform(transform_source)
            if transform_fn:
                result = transform_fn(request_details, {})
                ctx["preview"] = json.dumps(result, indent=2)
            else:
                ctx["error"] = "Could not compile transform function"
        else:
            ctx["preview"] = json.dumps(request_details, indent=2)

    except Exception as e:
        ctx["error"] = f"Preview failed: {str(e)}"

    return ctx


def _execute_gateway_request(ctx, gateways, context):
    """Execute the gateway request and show the result."""
    ctx = _preview_request_transform(ctx, gateways)

    if ctx.get("error"):
        return ctx

    try:
        # Parse the preview to get the transformed request
        transformed = json.loads(ctx.get("preview", "{}"))

        server_name = ctx["selected_server"]
        config = gateways[server_name]
        target_url = config.get("target_url", "")

        # Execute the request
        response = _execute_target_request(target_url, transformed)

        # Format the response
        response_info = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body_preview": response.text[:1000] if response.text else "",
        }
        ctx["response"] = json.dumps(response_info, indent=2)

    except Exception as e:
        ctx["error"] = f"Request failed: {str(e)}"

    return ctx


def _transform_response(ctx, gateways, context):
    """Transform a response using the specified transform."""
    try:
        server_name = ctx["selected_server"]
        config = gateways.get(server_name, {})

        # Build response details
        response_details = {
            "status_code": ctx["status_code"],
            "headers": json.loads(ctx["response_headers"]) if ctx["response_headers"] else {},
            "text": ctx["response_body"],
            "json": None,
            "content": ctx["response_body"].encode("utf-8"),
            "request_path": ctx["request_path"],
        }

        # Try to parse as JSON
        try:
            response_details["json"] = json.loads(ctx["response_body"])
        except Exception:
            pass

        # Get transform source
        transform_source = ctx["transform_override"] if ctx["transform_override"] else None
        if not transform_source:
            # Load default from CID
            response_cid = config.get("response_transform_cid")
            if response_cid:
                transform_fn = _load_transform_function(response_cid, None)
                if transform_fn:
                    result = transform_fn(response_details, context or {})
                    if isinstance(result, dict) and "output" in result:
                        ctx["preview"] = result.get("output", "")
                        ctx["preview_html"] = result.get("output", "")
                    return ctx

        # Use override
        if transform_source:
            transform_fn = _compile_transform(transform_source)
            if transform_fn:
                result = transform_fn(response_details, context or {})
                if isinstance(result, dict) and "output" in result:
                    ctx["preview"] = result.get("output", "")
                    ctx["preview_html"] = result.get("output", "")
            else:
                ctx["error"] = "Could not compile transform function"
        else:
            ctx["preview"] = ctx["response_body"]
            ctx["preview_html"] = escape(ctx["response_body"])

    except Exception as e:
        ctx["error"] = f"Transform failed: {str(e)}"

    return ctx


def _render_error(title, message, gateways):
    """Render an error page."""
    template = _load_template("error.html")
    html = template.render(
        error_title=title,
        error_message=message,
        available_gateways=gateways,
    )
    return {"output": html, "content_type": "text/html"}


def _get_default_request_transform():
    """Get the default request transform template."""
    return '''def transform_request(request_details: dict, context: dict) -> dict:
    """Transform incoming request for target server."""
    path = request_details.get("path", "")
    method = request_details.get("method", "GET")

    return {
        "url": f"https://example.com/{path}",
        "method": method,
        "headers": request_details.get("headers", {}),
        "json": request_details.get("json"),
    }
'''


def _get_default_response_transform():
    """Get the default response transform template."""
    return '''def transform_response(response_details: dict, context: dict) -> dict:
    """Transform response from target server."""
    from html import escape

    text = response_details.get("text", "")

    return {
        "output": f"<pre>{escape(text)}</pre>",
        "content_type": "text/html",
    }
'''
