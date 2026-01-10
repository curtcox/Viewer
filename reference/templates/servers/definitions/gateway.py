# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Gateway server for routing requests to internal servers.

This server provides a unified interface for accessing internal servers with
customizable request and response transformations. All server-specific
configuration comes from the 'gateways' variable.

Routes:
    /gateway - Instruction page
    /gateway/request - Request experimentation form
    /gateway/response - Response experimentation form
    /gateway/meta/{server} - Server meta page with transform validation
    /gateway/{server} - Issue request to gateway server root
    /gateway/{server}/{rest} - Issue request to gateway server with path
"""

import json
import logging
import re
import traceback
from html import escape
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from flask import current_app, request as flask_request
from jinja2 import Template

from cid_presenter import render_cid_link
from gateway_lib.rendering.diagnostic import (
    format_exception_summary as _format_exception_summary,
    derive_exception_summary_from_traceback as _derive_exception_summary_from_traceback,
    extract_exception_summary_from_internal_error_html as _extract_exception_summary_from_internal_error_html,
    extract_stack_trace_list_from_internal_error_html as _extract_stack_trace_list_from_internal_error_html,
)
from gateway_lib.cid.normalizer import (
    normalize_cid_lookup as _normalize_cid_lookup,
    parse_hrx_gateway_args as _parse_hrx_gateway_args,
)
from gateway_lib.cid.resolver import CIDResolver
from gateway_lib.transforms.loader import TransformLoader
from gateway_lib.transforms.validator import TransformValidator
from gateway_lib.templates.loader import TemplateLoader
from gateway_lib.config import ConfigLoader
from gateway_lib.execution.redirects import RedirectFollower, extract_internal_target_path_from_server_args_json
from gateway_lib.execution.internal import TargetExecutor, resolve_target
from gateway_lib.handlers.request import GatewayRequestHandler
from gateway_lib.handlers.test import GatewayTestHandler
from gateway_lib.handlers.meta import GatewayMetaHandler
from gateway_lib.handlers.forms import GatewayFormsHandler
from gateway_lib.routing import create_gateway_router
from gateway_lib.middleware import MiddlewareChain

logger = logging.getLogger(__name__)

# Forward declaration of _resolve_cid_content for use in service initialization
def _resolve_cid_content(cid_value, *, as_bytes: bool = False):
    """Resolve a CID value to its content.
    
    Delegates to CIDResolver for consistent resolution logic.
    This wrapper exists for backwards compatibility with tests.
    """
    return _cid_resolver.resolve(cid_value, as_bytes=as_bytes)


# Create shared service instances (no caching - always load fresh)
_cid_resolver = CIDResolver()
_transform_loader = TransformLoader(_cid_resolver)
_transform_validator = TransformValidator(_cid_resolver)
# Use lambda to allow late binding for test monkey-patching
_template_loader = TemplateLoader(_cid_resolver, resolve_fn=lambda cid, as_bytes: _resolve_cid_content(cid, as_bytes=as_bytes))
_config_loader = ConfigLoader(_cid_resolver)
_redirect_follower = RedirectFollower(_cid_resolver)
_target_executor = TargetExecutor(_redirect_follower)
_middleware_chain = MiddlewareChain()

_DEFAULT_TEST_CIDS_ARCHIVE_CID = "AAAAAAFCaOsI7LrqJuImmWLnEexNFvITSoZvrrd612bOwJLEZXcdQY0Baid8jJIbfQ4iq79SkO8RcWr4U2__XVKfaw4P9w"


def _create_router(gateways, context):
    """Create configured gateway router with all handlers.
    
    Args:
        gateways: Gateway configuration dict
        context: Request context
    
    Returns:
        Configured GatewayRouter instance
    """
    handlers = {
        "instruction": lambda: _handle_instruction_page(gateways, context),
        "request_form": lambda: _handle_request_form(gateways, context),
        "response_form": lambda: _handle_response_form(gateways, context),
        "meta": lambda server: _handle_meta_page(server, gateways, context),
        "meta_test": lambda test_path, server: _handle_meta_page_with_test(server, test_path, gateways, context),
        "test": lambda test_path, server, rest="": _handle_gateway_test_request(server, rest, test_path, gateways, context),
        "gateway_request": lambda server, rest="": _handle_gateway_request(server, rest, gateways, context),
    }
    return create_gateway_router(handlers)


def main(context=None):
    """Gateway server main function.

    Handles all gateway routes based on the request path.

    Parameters:
        context: Request context (automatically provided)
    """
    try:
        return _main_impl(context)
    except Exception as e:
        # Catch-all error handler with diagnostic information
        error_detail = traceback.format_exc()
        logger.error("Gateway error: %s\n%s", e, error_detail)
        return _render_error(
            "Gateway Error",
            f"An unexpected error occurred: {escape(str(e))}",
            {},  # Empty gateways since we may not have loaded them
            error_detail=error_detail,
            exception_summary=_format_exception_summary(e),
        )


def _main_impl(context=None):
    """Implementation of main gateway routing logic.
    
    Uses router for clean pattern-based routing instead of manual path parsing.
    """
    # Get the request path
    request_path = flask_request.path or "/"
    
    # Remove 'gateway' prefix if present
    path = request_path.strip("/")
    if path.startswith("gateway/"):
        path = path[8:]  # Remove "gateway/" prefix
    elif path == "gateway":
        path = ""
    
    # Load gateways configuration
    gateways = _load_gateways(context)
    
    # Apply before_request middleware
    context = _middleware_chain.execute_before_request(context or {})
    
    try:
        # Create router and route request
        router = _create_router(gateways, context)
        result = router.route(path)
        
        # Apply after_request middleware
        result = _middleware_chain.execute_after_request(result, context)
        
        return result
    except Exception as e:
        # Apply on_error middleware
        _middleware_chain.execute_on_error(e, context)
        raise


def _load_gateways(context):
    """Load gateway configurations from the gateways variable.
    
    Delegates to ConfigLoader for consistent loading logic.
    """
    return _config_loader.load_gateways(context)


def _load_template(template_name):
    """Load a Jinja2 template from the gateway templates directory.

    Tries multiple paths to find templates:
    1. Flask app root + reference/templates/servers/templates/gateway/
    2. Current working directory relative paths
    """
    template_paths = []

    # Try Flask app root path
    try:
        app_root = Path(current_app.root_path)
        template_paths.append(app_root / "reference/templates" / "servers" / "templates" / "gateway" / template_name)
    except RuntimeError:
        # No Flask app context
        pass

    # Try current working directory
    cwd = Path.cwd()
    template_paths.append(cwd / "reference/templates" / "servers" / "templates" / "gateway" / template_name)

    for template_path in template_paths:
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return Template(f.read())

    # Fallback: return a simple error template
    tried_paths = ", ".join(str(p) for p in template_paths)
    return Template(
        f"""<!DOCTYPE html><html><body>
        <h1>Template Not Found</h1>
        <p>Could not load template: {{{{ template_name }}}}</p>
        <p>Tried paths: {tried_paths}</p>
        </body></html>"""
    )


def _handle_instruction_page(gateways, context):
    """Render the main gateway instruction page."""
    template = _load_template("instruction.html")
    html = template.render(
        gateways=gateways,
        external_servers=_collect_external_service_servers(),
        mock_server_cids=_collect_mock_server_cids(),
        mock_server_cid_default=_default_mock_server_cid(),
    )
    return {"output": html, "content_type": "text/html"}


def _default_mock_server_cid() -> str:
    cid_file = Path.cwd() / "cids" / _DEFAULT_TEST_CIDS_ARCHIVE_CID
    return _DEFAULT_TEST_CIDS_ARCHIVE_CID if cid_file.exists() else ""


def _collect_mock_server_cids() -> dict[str, str]:
    files_dir_candidates: list[Path] = []

    try:
        files_dir_candidates.append(Path(current_app.root_path) / "reference" / "files")
    except RuntimeError:
        pass

    files_dir_candidates.append(Path.cwd() / "reference" / "files")

    files_dir = next(
        (candidate for candidate in files_dir_candidates if candidate.exists()),
        None,
    )
    if files_dir is None:
        return {}

    from cid_core import generate_cid

    mock_cids: dict[str, str] = {}
    for archive_path in sorted(files_dir.glob("*.cids")):
        server_name = archive_path.stem
        if not server_name:
            continue
        try:
            cid_value = generate_cid(archive_path.read_bytes())
        except Exception:
            continue
        mock_cids[server_name] = cid_value

    return mock_cids


def _collect_external_service_servers():
    archive_dir_candidates: list[Path] = []

    try:
        archive_dir_candidates.append(
            Path(current_app.root_path) / "reference" / "archive" / "cids"
        )
    except RuntimeError:
        pass

    archive_dir_candidates.append(Path.cwd() / "reference" / "archive" / "cids")

    archive_dir = next(
        (candidate for candidate in archive_dir_candidates if candidate.exists()),
        None,
    )
    if archive_dir is None:
        return []

    server_names: list[str] = []
    for entry in sorted(archive_dir.glob("*.source.cids")):
        name = entry.name.replace(".source.cids", "")
        if name and name not in server_names:
            server_names.append(name)

    result: list[dict] = []
    for server_name in server_names:
        result.append(
            {
                "name": server_name,
                "external_api": _infer_external_api_for_server(server_name),
            }
        )
    return result


def _infer_external_api_for_server(server_name: str) -> str | None:
    definition_dir_candidates: list[Path] = []

    try:
        definition_dir_candidates.append(
            Path(current_app.root_path)
            / "reference"
            / "templates"
            / "servers"
            / "definitions"
        )
    except RuntimeError:
        pass

    definition_dir_candidates.append(
        Path.cwd() / "reference" / "templates" / "servers" / "definitions"
    )

    definition_dir = next(
        (candidate for candidate in definition_dir_candidates if candidate.exists()),
        None,
    )
    if definition_dir is None:
        return None

    file_candidates = [
        definition_dir / f"{server_name}.py",
        definition_dir / f"{server_name}.sh",
    ]
    if server_name == "openai":
        file_candidates.insert(0, definition_dir / "openai_chat.py")
    if server_name == "teams":
        file_candidates.insert(0, definition_dir / "microsoft_teams.py")
    if server_name == "gemini":
        file_candidates.insert(0, definition_dir / "google_gemini.py")

    definition_path = next(
        (candidate for candidate in file_candidates if candidate.exists()),
        None,
    )
    if definition_path is None:
        return None

    try:
        source = definition_path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = re.search(r"https?://[^\s\"')]+", source)
    if not match:
        return None

    url = match.group(0).rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    return url


def _handle_request_form(gateways, context):
    """Handle the request experimentation form.
    
    This is a thin wrapper that delegates to GatewayFormsHandler.
    """
    # Create handler inline (no caching - always create fresh)
    handler = GatewayFormsHandler(
        load_template_fn=_load_template,
        get_default_request_transform_fn=_get_default_request_transform,
        get_default_response_transform_fn=_get_default_response_transform,
        load_invocation_for_request_fn=_load_invocation_for_request,
        preview_request_transform_fn=_preview_request_transform,
        execute_gateway_request_fn=_execute_gateway_request,
        load_invocation_for_response_fn=_load_invocation_for_response,
        transform_response_fn=_transform_response,
    )
    return handler.handle_request_form(gateways, context, flask_request)


def _handle_response_form(gateways, context):
    """Handle the response experimentation form.
    
    This is a thin wrapper that delegates to GatewayFormsHandler.
    """
    # Create handler inline (no caching - always create fresh)
    handler = GatewayFormsHandler(
        load_template_fn=_load_template,
        get_default_request_transform_fn=_get_default_request_transform,
        get_default_response_transform_fn=_get_default_response_transform,
        load_invocation_for_request_fn=_load_invocation_for_request,
        preview_request_transform_fn=_preview_request_transform,
        execute_gateway_request_fn=_execute_gateway_request,
        load_invocation_for_response_fn=_load_invocation_for_response,
        transform_response_fn=_transform_response,
    )
    return handler.handle_response_form(gateways, context, flask_request)


def _handle_meta_page(server_name, gateways, context):
    """Handle the gateway meta page showing transform source and validation.
    
    This is a thin wrapper that delegates to GatewayMetaHandler.
    """
    # Create handler inline (no caching - always create fresh)
    handler = GatewayMetaHandler(
        load_template_fn=_load_template,
        load_and_validate_transform_fn=_load_and_validate_transform,
        load_and_validate_template_fn=_load_and_validate_template,
        normalize_cid_fn=_normalize_cid_lookup,
        check_server_exists_fn=_check_server_exists,
        get_server_definition_info_fn=_get_server_definition_info,
        get_test_paths_fn=_get_test_paths,
        render_cid_link_fn=render_cid_link,
        render_error_fn=_render_error,
    )
    return handler.handle(server_name, gateways, context)


def _validate_direct_response(direct_response: dict) -> tuple[bool, str | None]:
    """Validate a direct response dict from request transform.
    
    Delegates to TransformValidator for consistent validation logic.
    
    Returns: (is_valid, error_message)
    """
    return _transform_validator.validate_direct_response(direct_response)


def _create_template_resolver(config: dict, context: dict):
    """Create a template resolution function for a gateway config.
    
    Delegates to TemplateLoader for consistent template resolution logic.
    
    Args:
        config: Gateway configuration dict with optional 'templates' key
        context: Server execution context
        
    Returns:
        Function that takes template name and returns Jinja2 Template
    """
    return _template_loader.create_template_resolver(config, context)


def _apply_response_transform_for_test(
    response_cid: str,
    response_details: dict,
    enhanced_context: dict,
    server_name: str,
    test_server_path: str,
    gateways: dict,
    gateway_archive: Optional[str],
    gateway_path: Optional[str],
) -> Optional[dict]:
    """Apply response transform in test mode with path rewriting.

    Args:
        response_cid: CID of the response transform function
        response_details: Response details from target server
        enhanced_context: Context with template resolver
        server_name: Gateway server name
        test_server_path: Test server path for URL rewriting
        gateways: All gateway configurations
        gateway_archive: HRX archive name if applicable
        gateway_path: HRX path if applicable

    Returns:
        Transformed result dict with 'output' key, or None if no transform or not applicable.
        Returns error response dict on failure.
    """
    transform_fn = _load_transform_function(_normalize_cid_lookup(response_cid), enhanced_context)
    if not transform_fn:
        return _render_error(
            "Response Transform Not Found",
            f"Could not load response transform: {escape(str(response_cid))}",
            gateways,
            exception_summary=f"ResponseTransformNotFoundError: Could not load response transform: {escape(str(response_cid))}",
            error_detail=json.dumps(
                {
                    "gateway": server_name,
                    "response_transform_cid": response_cid,
                    "test_mode": True,
                },
                indent=2,
            ),
            gateway_archive=gateway_archive,
            gateway_path=gateway_path,
        )

    result = transform_fn(response_details, enhanced_context)
    if not isinstance(result, dict) or "output" not in result:
        return None

    # Rewrite URLs for test mode
    content_type = str(result.get("content_type") or "")
    if "html" in content_type.lower():
        prefix = f"/gateway/test/{test_server_path}/as/{server_name}"
        old_prefix = f"/gateway/{server_name}"
        output = result.get("output")
        if isinstance(output, str):
            result["output"] = output.replace(old_prefix, prefix)
        elif isinstance(output, (bytes, bytearray)):
            decoded = bytes(output).decode("utf-8", errors="replace")
            result["output"] = decoded.replace(old_prefix, prefix)

    return result


def _build_direct_response_details(direct_response: dict, rest_path: str) -> dict:
    """Build response_details dict from a direct response returned by request transform.

    Args:
        direct_response: Direct response dict with 'output', 'status_code', 'content_type', 'headers'
        rest_path: Request path for context

    Returns:
        response_details dict suitable for response transform processing
    """
    output = direct_response.get("output", "")
    content = output.encode("utf-8") if isinstance(output, str) else output
    text = output if isinstance(output, str) else output.decode("utf-8", errors="replace")

    return {
        "status_code": direct_response.get("status_code", 200),
        "headers": direct_response.get("headers", {"Content-Type": direct_response.get("content_type", "text/html")}),
        "content": content,
        "text": text,
        "json": None,
        "request_path": rest_path,
        "source": "request_transform",
        "_original_output": output,  # Keep original output type for default return
        "_original_content_type": direct_response.get("content_type", "text/html"),
    }


def _apply_request_transform(
    request_cid: str,
    request_details: dict,
    enhanced_context: dict,
    rest_path: str,
    server_name: str,
    gateways: dict,
    debug_context: dict,
    gateway_archive: Optional[str],
    gateway_path: Optional[str],
) -> tuple[Optional[dict], Optional[dict]]:
    """Apply request transform and return updated request_details and optional response_details.

    Args:
        request_cid: CID of the request transform function
        request_details: Current request details
        enhanced_context: Context with template resolver
        rest_path: Request path
        server_name: Gateway server name
        gateways: All gateway configurations
        debug_context: Debug information
        gateway_archive: HRX archive name if applicable
        gateway_path: HRX path if applicable

    Returns:
        Tuple of (request_details, response_details). response_details is set if transform
        returns a direct response, otherwise None.

    Raises:
        Returns error response dict on failure
    """
    transform_fn = _load_transform_function(_normalize_cid_lookup(request_cid), enhanced_context)
    if not transform_fn:
        return _render_error(
            "Request Transform Not Found",
            f"Could not load request transform: {escape(str(request_cid))}",
            gateways,
            exception_summary=f"RequestTransformNotFoundError: Could not load request transform: {escape(str(request_cid))}",
            error_detail=json.dumps(
                {
                    "gateway": server_name,
                    "request_transform_cid": request_cid,
                },
                indent=2,
            ),
            gateway_archive=gateway_archive,
            gateway_path=gateway_path,
        ), None

    transformed = transform_fn(request_details, enhanced_context)
    if not isinstance(transformed, dict):
        return request_details, None

    # Check if this is a direct response
    if "response" not in transformed:
        # Normal request transformation
        return transformed, None

    direct_response = transformed["response"]
    # Validate the direct response
    is_valid, error_msg = _validate_direct_response(direct_response)
    if not is_valid:
        return _render_error(
            "Invalid Direct Response",
            f"Request transform returned invalid direct response: {error_msg}",
            gateways,
            exception_summary=f"InvalidDirectResponseError: {error_msg}",
            error_detail=json.dumps(
                {
                    "gateway": server_name,
                    "request_transform_cid": request_cid,
                    "validation_error": error_msg,
                    "direct_response": str(direct_response)[:500],
                },
                indent=2,
            ),
            gateway_archive=gateway_archive,
            gateway_path=gateway_path,
        ), None

    # Build response_details from direct response
    response_details = _build_direct_response_details(direct_response, rest_path)
    return request_details, response_details


def _handle_gateway_request(server_name, rest_path, gateways, context):
    """Handle an actual gateway request to a configured server.
    
    This is a thin wrapper that delegates to GatewayRequestHandler.
    """
    # Create handler inline (no caching - always create fresh)
    handler = GatewayRequestHandler(
        apply_request_transform_fn=_apply_request_transform,
        execute_target_fn=_execute_target_request,
        load_transform_fn=_load_transform_function,
        create_template_resolver_fn=_create_template_resolver,
        normalize_cid_fn=_normalize_cid_lookup,
        safe_preview_fn=_safe_preview_request_details,
        extract_exception_summary_fn=_extract_exception_summary_from_internal_error_html,
        extract_stack_trace_fn=_extract_stack_trace_list_from_internal_error_html,
        format_exception_detail_fn=_format_exception_detail,
        format_exception_summary_fn=_format_exception_summary,
        parse_hrx_args_fn=_parse_hrx_gateway_args,
        render_error_fn=_render_error,
    )
    return handler.handle(server_name, rest_path, gateways, context, flask_request)


def _handle_gateway_test_request(server_name, rest_path, test_server_path, gateways, context):
    """Handle a gateway test request using a test server in place of the normal server.
    
    This is a thin wrapper that delegates to GatewayTestHandler.
    
    Pattern: /gateway/test/{test-server-path}/as/{server}/{rest}
    """
    # Create handler inline (no caching - always create fresh)
    handler = GatewayTestHandler(
        apply_request_transform_fn=_apply_request_transform,
        apply_response_transform_for_test_fn=_apply_response_transform_for_test,
        execute_target_fn=_execute_target_request,
        create_template_resolver_fn=_create_template_resolver,
        safe_preview_fn=_safe_preview_request_details,
        extract_exception_summary_fn=_extract_exception_summary_from_internal_error_html,
        extract_stack_trace_fn=_extract_stack_trace_list_from_internal_error_html,
        format_exception_detail_fn=_format_exception_detail,
        format_exception_summary_fn=_format_exception_summary,
        render_error_fn=_render_error,
    )
    return handler.handle(server_name, rest_path, test_server_path, gateways, context, flask_request)


def _handle_meta_page_with_test(server_name, test_server_path, gateways, context):
    """Handle meta page with test server information.
    
    This is a thin wrapper that delegates to GatewayMetaHandler.
    """
    # Create handler inline (no caching - always create fresh)
    handler = GatewayMetaHandler(
        load_template_fn=_load_template,
        load_and_validate_transform_fn=_load_and_validate_transform,
        load_and_validate_template_fn=_load_and_validate_template,
        normalize_cid_fn=_normalize_cid_lookup,
        check_server_exists_fn=_check_server_exists,
        get_server_definition_info_fn=_get_server_definition_info,
        get_test_paths_fn=_get_test_paths,
        render_cid_link_fn=render_cid_link,
        render_error_fn=_render_error,
    )
    return handler.handle_with_test(server_name, test_server_path, gateways, context)


def _execute_target_request(target, request_details):
    """Execute a request to the target server.

    Delegates to TargetExecutor for execution logic.
    This wrapper exists for backwards compatibility.
    """
    return _target_executor.execute_target_request(target, request_details)


def _resolve_target(config: dict, server_name: str, request_details: dict) -> dict:
    """Resolve the final gateway target.

    Delegates to resolve_target utility function.
    This wrapper exists for backwards compatibility.
    """
    return resolve_target(config, server_name, request_details)


def _follow_internal_redirects(response, max_hops: int = 3):
    """Resolve internal redirect responses into final CID-backed content.
    
    Delegates to RedirectFollower for redirect logic.
    This wrapper exists for backwards compatibility with tests.
    """
    return _redirect_follower.follow_redirects(response, max_hops)


def _extract_internal_target_path_from_server_args_json(server_args_json):
    """Extract internal target path from server args JSON.
    
    Delegates to extract_internal_target_path_from_server_args_json utility.
    This wrapper exists for backwards compatibility.
    """
    return extract_internal_target_path_from_server_args_json(server_args_json)


def _safe_preview_request_details(request_details: dict) -> dict:
    if not isinstance(request_details, dict):
        return {"type": type(request_details).__name__}
    preview = {}
    for key in ("url", "path", "query_string", "method"):
        if key in request_details:
            preview[key] = request_details.get(key)
    headers = request_details.get("headers")
    if isinstance(headers, dict):
        preview["headers"] = {
            k: v
            for k, v in headers.items()
            if str(k).lower() not in ("cookie", "authorization")
        }
    return preview


def _format_exception_detail(exc: Exception, *, debug_context: dict | None = None) -> str:
    detail = {
        "exception_type": type(exc).__name__,
        "exception": str(exc),
    }
    if debug_context:
        detail["debug_context"] = debug_context

    detail["traceback"] = traceback.format_exc()
    return json.dumps(detail, indent=2, default=str)


def _load_transform_function(cid, context):
    """Load a transform function from a CID.
    
    Delegates to TransformLoader for consistent loading logic.
    """
    return _transform_loader.load_transform(cid, context)


def _compile_transform(source):
    """Compile transform source code and return the transform function.
    
    Delegates to TransformLoader for consistent compilation logic.
    """
    return _transform_loader.compile_transform(source)


def _load_and_validate_transform(cid, expected_fn_name, context):
    """Load transform source and validate it.
    
    Delegates to TransformValidator for consistent validation logic.
    
    Returns: (source, error, warnings)
    """
    return _transform_validator.load_and_validate_transform(cid, expected_fn_name, context)


def _load_and_validate_template(cid, context):
    """Load and validate a Jinja template.
    
    Delegates to TemplateLoader for consistent validation logic.
    
    Args:
        cid: Template CID to load
        context: Server execution context
        
    Returns:
        (source, error, variables) tuple where:
        - source: Template source code (str) or None if not found
        - error: Error message (str) or None if valid
        - variables: List of detected template variables (list[str])
    """
    return _template_loader.load_and_validate_template(cid, context)


def _check_server_exists(server_name, context):
    """Check if a server with the given name exists."""
    try:
        from db_access import get_server_by_name
        server = get_server_by_name(server_name)
        return server is not None
    except Exception:
        return False


def _get_server_definition_info(server_name: str) -> dict:
    """Load basic server info for diagnostics without raising."""
    info = {
        "exists": False,
        "definition_type": None,
        "definition_is_str": False,
        "definition_preview": None,
    }
    try:
        from db_access import get_server_by_name

        server = get_server_by_name(server_name)
        if not server:
            return info

        info["exists"] = True
        definition = getattr(server, "definition", None)
        info["definition_type"] = type(definition).__name__
        info["definition_is_str"] = isinstance(definition, str)
        try:
            preview = definition if isinstance(definition, str) else repr(definition)
        except Exception:
            preview = "<unavailable>"

        if isinstance(preview, str) and len(preview) > 500:
            preview = f"{preview[:500]}...<truncated>"
        info["definition_preview"] = preview
        return info
    except Exception as e:
        info["error"] = str(e)
        return info


def _build_probe_request_details(sample_path: str) -> dict:
    return {
        "path": sample_path,
        "query_string": "",
        "method": "GET",
        "headers": {"Accept": "text/plain"},
    }


def _preview_response(response) -> dict:
    preview = {
        "status_code": getattr(response, "status_code", None),
        "content_type": None,
        "body_preview": None,
    }
    try:
        headers = getattr(response, "headers", {}) or {}
        content_type = None
        if isinstance(headers, dict):
            content_type = headers.get("Content-Type") or headers.get("content-type")
        preview["content_type"] = content_type
    except Exception:
        preview["content_type"] = None

    try:
        text = getattr(response, "text", "")
        if isinstance(text, str):
            snippet = text[:500]
            preview["body_preview"] = snippet
        else:
            preview["body_preview"] = repr(text)[:500]
    except Exception:
        preview["body_preview"] = "<unavailable>"
    return preview


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
        target_url = f"/{server_name}"

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


def _render_error(
    title,
    message,
    gateways,
    *,
    error_detail=None,
    exception_summary=None,
    server_args_json=None,
    stack_trace_html=None,
    gateway_archive=None,
    gateway_path=None,
    test_mode_context=None,
):
    """Render an error page with optional diagnostic details."""
    if exception_summary:
        exception_summary = escape(str(exception_summary))

    internal_target_path = _extract_internal_target_path_from_server_args_json(server_args_json)
    if internal_target_path:
        separator = "<br><br>" if isinstance(message, str) and message else ""
        message = (
            f"{message}{separator}<strong>Internal target:</strong> {escape(internal_target_path)}"
        )

    if (
        exception_summary
        and isinstance(exception_summary, str)
        and ":" not in exception_summary
        and error_detail
    ):
        derived = _derive_exception_summary_from_traceback(error_detail)
        if derived:
            exception_summary = derived
    template = _load_template("error.html")
    html = template.render(
        error_title=title,
        error_message=message,
        error_detail=error_detail,
        exception_summary=exception_summary,
        server_args_json=server_args_json,
        stack_trace_html=stack_trace_html,
        gateway_archive=gateway_archive,
        gateway_path=gateway_path,
        available_gateways=gateways,
        test_mode_context=test_mode_context,
    )
    return {"output": html, "content_type": "text/html"}


def _get_default_request_transform():
    """Get the default request transform template."""
    return '''def transform_request(request_details: dict, context: dict) -> dict:
    """Transform incoming request for target server."""
    path = request_details.get("path", "")
    method = request_details.get("method", "GET")

    return {
        "path": path,
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
