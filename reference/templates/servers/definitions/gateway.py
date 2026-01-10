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
from urllib.parse import urljoin
from urllib.parse import parse_qsl
from urllib.parse import urlencode
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


_DEFAULT_TEST_CIDS_ARCHIVE_CID = "AAAAAAFCaOsI7LrqJuImmWLnEexNFvITSoZvrrd612bOwJLEZXcdQY0Baid8jJIbfQ4iq79SkO8RcWr4U2__XVKfaw4P9w"


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
    """Implementation of main gateway routing logic."""
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

    if first_part == "meta":
        if len(path_parts) > 1:
            # Check for test meta pattern: /gateway/meta/test/{test-server-path}/as/{server}
            if path_parts[1] == "test" and len(path_parts) > 4 and "as" in path_parts:
                as_index = path_parts.index("as")
                if as_index > 2 and as_index + 1 < len(path_parts):
                    test_server_path = "/".join(path_parts[2:as_index])
                    server_name = path_parts[as_index + 1]
                    return _handle_meta_page_with_test(server_name, test_server_path, gateways, context)
            else:
                server_name = path_parts[1]
                return _handle_meta_page(server_name, gateways, context)

    # Check for test pattern: /gateway/test/{test-server-path}/as/{server}/{rest}
    if first_part == "test" and len(path_parts) > 2 and "as" in path_parts:
        as_index = path_parts.index("as")
        if as_index > 1 and as_index + 1 < len(path_parts):
            test_server_path = "/".join(path_parts[1:as_index])
            server_name = path_parts[as_index + 1]
            rest_path = "/".join(path_parts[as_index + 2:]) if len(path_parts) > as_index + 2 else ""
            return _handle_gateway_test_request(server_name, rest_path, test_server_path, gateways, context)

    # Otherwise, treat first part as server name
    server_name = first_part
    rest_path = "/".join(path_parts[1:]) if len(path_parts) > 1 else ""

    return _handle_gateway_request(server_name, rest_path, gateways, context)


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
        available = ", ".join(sorted(gateways.keys())) if gateways else "(none)"
        return _render_error(
            "Gateway Not Found",
            f"No gateway configured for '{server_name}'. Defined gateways: {available}",
            gateways,
        )

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

    request_cid_link_html = ""
    response_cid_link_html = ""

    # Load request transform
    request_cid = config.get("request_transform_cid")
    request_cid_lookup = _normalize_cid_lookup(request_cid)
    if request_cid_lookup and request_cid_lookup.startswith("/"):
        request_cid_link_html = str(render_cid_link(request_cid_lookup))
    if request_cid:
        source, error, warnings = _load_and_validate_transform(request_cid_lookup, "transform_request", context)
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
    response_cid_lookup = _normalize_cid_lookup(response_cid)
    if response_cid_lookup and response_cid_lookup.startswith("/"):
        response_cid_link_html = str(render_cid_link(response_cid_lookup))
    if response_cid:
        source, error, warnings = _load_and_validate_transform(response_cid_lookup, "transform_response", context)
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

    server_definition_info = _get_server_definition_info(server_name)
    server_definition_diagnostics_url = None
    if server_exists:
        server_definition_diagnostics_url = f"/servers/{server_name}/definition-diagnostics"

    # Load template information
    templates_config = config.get("templates", {})
    templates_info = []

    def _extract_resolve_template_calls(source: str | None) -> set[str]:
        if not source or not isinstance(source, str):
            return set()
        pattern = r"resolve_template\(\s*[\"\']([^\"\']+)[\"\']\s*\)"
        return set(re.findall(pattern, source))

    referenced_template_names = set(templates_config.keys())
    referenced_template_names |= _extract_resolve_template_calls(request_transform_source)
    referenced_template_names |= _extract_resolve_template_calls(response_transform_source)

    for template_name in sorted(referenced_template_names):
        template_cid = templates_config.get(template_name)
        template_info = {
            "name": template_name,
            "cid": template_cid,
            "cid_link_html": "",
            "source": None,
            "status": "error",
            "status_text": "Not Found",
            "error": None,
            "variables": [],
        }

        if not template_cid:
            template_info["error"] = "Template referenced by gateway transforms but not configured in gateway templates map"
            template_info["status"] = "error"
            template_info["status_text"] = "Missing Mapping"
            templates_info.append(template_info)
            continue

        # Generate CID link
        template_cid_lookup = _normalize_cid_lookup(template_cid)
        if template_cid_lookup and template_cid_lookup.startswith("/"):
            template_info["cid_link_html"] = str(render_cid_link(template_cid_lookup))

        # Load and validate template
        source, error, variables = _load_and_validate_template(template_cid, context)
        template_info["source"] = source
        if error:
            template_info["error"] = error
            template_info["status"] = "error"
            template_info["status_text"] = "Error"
        else:
            template_info["status"] = "valid"
            template_info["status_text"] = "Valid"
            template_info["variables"] = variables

        templates_info.append(template_info)

    # Generate test paths based on server type
    test_paths = _get_test_paths(server_name)

    html = template.render(
        server_name=server_name,
        config=config,
        server_exists=server_exists,
        server_definition_info=server_definition_info,
        server_definition_diagnostics_url=server_definition_diagnostics_url,
        request_cid_lookup=request_cid_lookup,
        response_cid_lookup=response_cid_lookup,
        request_cid_link_html=request_cid_link_html,
        response_cid_link_html=response_cid_link_html,
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
        templates_info=templates_info,
        test_paths=test_paths,
    )
    return {"output": html, "content_type": "text/html"}


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
    """Handle an actual gateway request to a configured server."""
    if server_name not in gateways:
        available = ", ".join(sorted(gateways.keys())) if gateways else "(none)"
        return _render_error(
            "Gateway Not Found",
            f"No gateway configured for '{server_name}'. Defined gateways: {available}",
            gateways,
        )

    config = gateways[server_name]

    debug_context = {
        "gateway": server_name,
        "rest_path": rest_path,
        "request_path": getattr(flask_request, "path", None),
        "request_method": getattr(flask_request, "method", None),
    }

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
        "data": raw_body,
    }

    original_rest_path = rest_path

    gateway_archive = None
    gateway_path = None
    if server_name == "hrx":
        archive, path = _parse_hrx_gateway_args(original_rest_path)
        gateway_archive = archive
        gateway_path = path

    debug_context["request_details_before_transform"] = {
        "path": request_details.get("path"),
        "query_string": request_details.get("query_string"),
        "method": request_details.get("method"),
    }

    # Create template resolver and enhance context
    template_resolver = _create_template_resolver(config, context)
    enhanced_context = {
        **(context or {}),
        "resolve_template": template_resolver,
    }

    # Load and execute request transform
    request_cid = config.get("request_transform_cid")
    response_details = None  # Will be set if request transform returns direct response

    if request_cid:
        try:
            result = _apply_request_transform(
                request_cid,
                request_details,
                enhanced_context,
                rest_path,
                server_name,
                gateways,
                debug_context,
                gateway_archive,
                gateway_path,
            )
            # Check if it's an error response (dict with specific keys)
            if isinstance(result, dict) and "output" in result:
                return result
            # Otherwise it's a tuple (request_details, response_details)
            request_details, response_details = result
        except Exception as e:
            logger.error("Request transform error: %s", e)
            return _render_error(
                "Request Transform Error",
                f"Failed to execute request transform: {escape(str(e))}",
                gateways,
                exception_summary=f"RequestTransformError: {type(e).__name__}: {str(e)}",
                error_detail=_format_exception_detail(
                    e,
                    debug_context={
                        **debug_context,
                        "request_transform_cid": request_cid,
                    },
                ),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

    # Skip server execution if we have a direct response
    if response_details is None:
        debug_context["request_details_after_transform"] = _safe_preview_request_details(
            request_details
        )

        resolved_target = _resolve_target(config, server_name, request_details)
        debug_context["resolved_target"] = resolved_target

        try:
            response = _execute_target_request(resolved_target, request_details)
        except Exception as e:
            logger.error("Target request error: %s", e)
            return _render_error(
                "Request Failed",
                f"Failed to connect to target: {escape(str(e))}",
                gateways,
                exception_summary=f"TargetRequestError: {type(e).__name__}: {str(e)}",
                error_detail=_format_exception_detail(e, debug_context=debug_context),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

        status_code = getattr(response, "status_code", 200)
        response_text = getattr(response, "text", "")
        if isinstance(status_code, int) and status_code >= 500:
            exception_summary = _extract_exception_summary_from_internal_error_html(response_text)
            stack_trace_html = _extract_stack_trace_list_from_internal_error_html(response_text)
            return _render_error(
                "Gateway Error",
                "An internal server error occurred.",
                gateways,
                exception_summary=exception_summary,
                stack_trace_html=stack_trace_html,
                server_args_json=json.dumps(
                    {
                        "target": resolved_target,
                        "request": {
                            **_safe_preview_request_details(request_details),
                            "original_rest_path": original_rest_path,
                        },
                    },
                    indent=2,
                ),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
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
            "source": "server",
        }

    # Load and execute response transform
    response_cid = config.get("response_transform_cid")
    if response_cid:
        try:
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
                        },
                        indent=2,
                    ),
                    gateway_archive=gateway_archive,
                    gateway_path=gateway_path,
                )
            if transform_fn:
                result = transform_fn(response_details, enhanced_context)
                if isinstance(result, dict) and "output" in result:
                    return result
        except Exception as e:
            logger.error("Response transform error: %s", e)
            return _render_error(
                "Response Transform Error",
                f"Failed to execute response transform: {escape(str(e))}",
                gateways,
                exception_summary=_format_exception_summary(e),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

    # Default: return raw response
    # Use _original_output if available (from direct response), otherwise use content (from server)
    if "_original_output" in response_details:
        return {
            "output": response_details["_original_output"],
            "content_type": response_details.get("_original_content_type", "text/plain"),
        }
    return {
        "output": response_details.get("content", b""),
        "content_type": response_details.get("headers", {}).get("Content-Type", "text/plain"),
    }


def _handle_gateway_test_request(server_name, rest_path, test_server_path, gateways, context):
    """Handle a gateway test request using a test server in place of the normal server.

    Pattern: /gateway/test/{test-server-path}/as/{server}/{rest}

    Args:
        server_name: The gateway server name (for transforms)
        rest_path: The remaining path after the server name
        test_server_path: The test server path to use instead of the normal server
        gateways: Gateway configurations
        context: Request context
    """
    if server_name not in gateways:
        available = ", ".join(sorted(gateways.keys())) if gateways else "(none)"
        return _render_error(
            "Gateway Not Found",
            f"No gateway configured for '{server_name}'. Defined gateways: {available}",
            gateways,
        )

    config = gateways[server_name]

    if (
        isinstance(test_server_path, str)
        and test_server_path.startswith("cids/")
        and (not isinstance(rest_path, str) or not rest_path)
        and getattr(flask_request, "method", "GET") == "GET"
    ):
        parts = test_server_path.split("/", 1)
        cids_archive_cid = parts[1] if len(parts) == 2 and parts[1] else None
        if cids_archive_cid:
            listing_request = {
                "path": "",
                "query_string": urlencode([("archive", cids_archive_cid)]),
                "method": "GET",
                "headers": {k: v for k, v in flask_request.headers if k.lower() != "cookie"},
                "json": None,
                "data": None,
            }

            try:
                response = _execute_target_request(
                    {"mode": "internal", "url": "/cids"},
                    listing_request,
                )
            except Exception as e:
                logger.error("Target request error: %s", e)
                return _render_error(
                    "Request Failed",
                    f"Failed to connect to test target: {escape(str(e))}",
                    gateways,
                    exception_summary=f"TargetRequestError: {type(e).__name__}: {str(e)}",
                    error_detail=_format_exception_detail(
                        e,
                        debug_context={
                            "gateway": server_name,
                            "rest_path": rest_path,
                            "test_server_path": test_server_path,
                            "request_path": getattr(flask_request, "path", None),
                            "request_method": getattr(flask_request, "method", None),
                        },
                    ),
                    gateway_archive=None,
                    gateway_path=None,
                )

            listing_text = getattr(response, "text", "")
            if isinstance(listing_text, str):
                entries = [line.strip() for line in listing_text.splitlines() if line.strip()]
            else:
                entries = []

            base_prefix = f"/gateway/test/cids/{cids_archive_cid}/as/{server_name}/"
            items_html = "\n".join(
                f'<li><a href="{base_prefix}{escape(entry)}">{escape(entry)}</a></li>'
                for entry in entries
            )

            html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>Gateway Test Index</title>
</head>
<body>
  <h1>Gateway Test Index</h1>
  <ul>
{items_html}
  </ul>
</body>
</html>"""

            return {
                "output": html,
                "content_type": "text/html",
            }

    debug_context = {
        "gateway": server_name,
        "rest_path": rest_path,
        "test_server_path": test_server_path,
        "request_path": getattr(flask_request, "path", None),
        "request_method": getattr(flask_request, "method", None),
    }

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
        "data": raw_body,
    }

    original_rest_path = rest_path

    gateway_archive = None
    gateway_path = None
    # Extract archive information for archive-based gateways (hrx, cids)
    # This follows the same pattern as the normal gateway request handling
    if server_name in ("hrx", "cids"):
        # For archive-based gateways, parse archive info from test_server_path
        parts = test_server_path.strip("/").split("/", 1)
        gateway_archive = parts[0]
        gateway_path = parts[1] if len(parts) > 1 else ""

    debug_context["request_details_before_transform"] = {
        "path": request_details.get("path"),
        "query_string": request_details.get("query_string"),
        "method": request_details.get("method"),
    }

    # Create template resolver and enhance context
    template_resolver = _create_template_resolver(config, context)
    enhanced_context = {
        **(context or {}),
        "resolve_template": template_resolver,
        "test_mode": True,
        "test_server_path": test_server_path,
    }

    # Load and execute request transform (same as normal gateway request)
    request_cid = config.get("request_transform_cid")
    response_details = None

    if request_cid:
        try:
            result = _apply_request_transform(
                request_cid,
                request_details,
                enhanced_context,
                rest_path,
                server_name,
                gateways,
                debug_context,
                gateway_archive,
                gateway_path,
            )
            # Check if it's an error response (dict with specific keys)
            if isinstance(result, dict) and "output" in result:
                return result
            # Otherwise it's a tuple (request_details, response_details)
            request_details, response_details = result
        except Exception as e:
            logger.error("Request transform error: %s", e)
            return _render_error(
                "Request Transform Error",
                f"Failed to execute request transform: {escape(str(e))}",
                gateways,
                exception_summary=f"RequestTransformError: {type(e).__name__}: {str(e)}",
                error_detail=_format_exception_detail(
                    e,
                    debug_context={
                        **debug_context,
                        "request_transform_cid": request_cid,
                    },
                ),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

    # Skip server execution if we have a direct response
    if response_details is None:
        debug_context["request_details_after_transform"] = _safe_preview_request_details(
            request_details
        )

        # Special-case the test server path for CIDS archives.
        # The cids server expects arguments like /cids?archive=<CID>&path=<...> rather than
        # addressing the archive CID as a URL path segment.
        cids_archive_cid = None
        if isinstance(test_server_path, str) and test_server_path.startswith("cids/"):
            parts = test_server_path.split("/", 1)
            if len(parts) == 2 and parts[1]:
                cids_archive_cid = parts[1]

        if cids_archive_cid:
            query_pairs = parse_qsl(request_details.get("query_string") or "", keep_blank_values=True)
            if not any(k == "archive" for k, _ in query_pairs):
                query_pairs.append(("archive", cids_archive_cid))
            if rest_path and not any(k == "path" for k, _ in query_pairs):
                query_pairs.append(("path", rest_path))

            request_details["query_string"] = urlencode(query_pairs)
            request_details["path"] = ""
            resolved_target = {"mode": "internal", "url": "/cids"}
        else:
            # Use test server path instead of normal server
            resolved_target = _resolve_test_target(test_server_path, request_details)
        # Use test server path instead of normal server
        debug_context["resolved_target"] = resolved_target

        try:
            response = _execute_target_request(resolved_target, request_details)
        except Exception as e:
            logger.error("Target request error: %s", e)
            return _render_error(
                "Request Failed",
                f"Failed to connect to test target: {escape(str(e))}",
                gateways,
                exception_summary=f"TargetRequestError: {type(e).__name__}: {str(e)}",
                error_detail=_format_exception_detail(e, debug_context=debug_context),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

        status_code = getattr(response, "status_code", 200)
        response_text = getattr(response, "text", "")
        if isinstance(status_code, int) and status_code >= 500:
            exception_summary = _extract_exception_summary_from_internal_error_html(response_text)
            stack_trace_html = _extract_stack_trace_list_from_internal_error_html(response_text)
            return _render_error(
                "Gateway Error",
                "An internal server error occurred.",
                gateways,
                exception_summary=exception_summary,
                stack_trace_html=stack_trace_html,
                server_args_json=json.dumps(
                    {
                        "target": resolved_target,
                        "test_server_path": test_server_path,
                        "request": {
                            **_safe_preview_request_details(request_details),
                            "original_rest_path": original_rest_path,
                        },
                    },
                    indent=2,
                ),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
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
            "source": "test_server",
        }

        if cids_archive_cid and not rest_path:
            listing_text = response_details.get("text")
            if isinstance(listing_text, str):
                entries = [line.strip() for line in listing_text.splitlines() if line.strip()]
            else:
                entries = []

            base_prefix = f"/gateway/test/cids/{cids_archive_cid}/as/{server_name}/"
            items_html = "\n".join(
                f'<li><a href="{base_prefix}{escape(entry)}">{escape(entry)}</a></li>'
                for entry in entries
            )

            html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>Gateway Test Index</title>
</head>
<body>
  <h1>Gateway Test Index</h1>
  <ul>
{items_html}
  </ul>
</body>
</html>"""

            return {
                "output": html,
                "content_type": "text/html",
            }

    # Load and execute response transform (same as normal gateway request)
    response_cid = config.get("response_transform_cid")
    if response_cid:
        try:
            result = _apply_response_transform_for_test(
                response_cid,
                response_details,
                enhanced_context,
                server_name,
                test_server_path,
                gateways,
                gateway_archive,
                gateway_path,
            )
            if result is not None:
                return result
        except Exception as e:
            logger.error("Response transform error: %s", e)
            return _render_error(
                "Response Transform Error",
                f"Failed to execute response transform: {escape(str(e))}",
                gateways,
                exception_summary=_format_exception_summary(e),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

    # Default: return raw response
    if "_original_output" in response_details:
        output = response_details["_original_output"]
        content_type = response_details.get("_original_content_type", "text/plain")
        if "html" in str(content_type).lower():
            prefix = f"/gateway/test/{test_server_path}/as/{server_name}"
            old_prefix = f"/gateway/{server_name}"
            if isinstance(output, str):
                output = output.replace(old_prefix, prefix)
            elif isinstance(output, (bytes, bytearray)):
                decoded = bytes(output).decode("utf-8", errors="replace")
                output = decoded.replace(old_prefix, prefix)
        return {
            "output": output,
            "content_type": content_type,
        }
    output = response_details.get("content", b"")
    content_type = response_details.get("headers", {}).get("Content-Type", "text/plain")
    if "html" in str(content_type).lower():
        prefix = f"/gateway/test/{test_server_path}/as/{server_name}"
        old_prefix = f"/gateway/{server_name}"
        if isinstance(output, str):
            output = output.replace(old_prefix, prefix)
        elif isinstance(output, (bytes, bytearray)):
            decoded = bytes(output).decode("utf-8", errors="replace")
            output = decoded.replace(old_prefix, prefix)
    return {
        "output": output,
        "content_type": content_type,
    }


def _resolve_test_target(test_server_path: str, request_details: dict) -> dict:
    """Resolve the test target path.

    Args:
        test_server_path: The test server path (e.g., "cids/SOME_CID")
        request_details: Request details dict (reserved for future use in path resolution)

    Returns:
        Target dict with mode and url

    Note:
        The request_details parameter is currently unused but maintained for API
        consistency and potential future enhancement where request information
        might influence test target resolution.
    """
    # Ensure test server path starts with /
    if not test_server_path.startswith("/"):
        test_server_path = f"/{test_server_path}"

    return {"mode": "internal", "url": test_server_path}


def _handle_meta_page_with_test(server_name, test_server_path, gateways, context):
    """Handle meta page with test server information.

    Shows information about both the configured server and the test server that will be used.
    """
    if server_name not in gateways:
        available = ", ".join(sorted(gateways.keys())) if gateways else "(none)"
        return _render_error(
            "Gateway Not Found",
            f"No gateway configured for '{server_name}'. Defined gateways: {available}",
            gateways,
        )

    config = gateways[server_name]
    template = _load_template("meta.html")

    # Load and validate transforms (same as regular meta page)
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

    request_cid_link_html = ""
    response_cid_link_html = ""

    # Load request transform
    request_cid = config.get("request_transform_cid")
    request_cid_lookup = _normalize_cid_lookup(request_cid)
    if request_cid_lookup and request_cid_lookup.startswith("/"):
        request_cid_link_html = str(render_cid_link(request_cid_lookup))
    if request_cid:
        source, error, warnings = _load_and_validate_transform(request_cid_lookup, "transform_request", context)
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
    response_cid_lookup = _normalize_cid_lookup(response_cid)
    if response_cid_lookup and response_cid_lookup.startswith("/"):
        response_cid_link_html = str(render_cid_link(response_cid_lookup))
    if response_cid:
        source, error, warnings = _load_and_validate_transform(response_cid_lookup, "transform_response", context)
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

    server_exists = _check_server_exists(server_name, context)

    server_definition_info = _get_server_definition_info(server_name)
    server_definition_diagnostics_url = None
    if server_exists:
        server_definition_diagnostics_url = f"/servers/{server_name}/definition-diagnostics"

    # Load template information
    templates_config = config.get("templates", {})
    templates_info = []

    def _extract_resolve_template_calls(source: str | None) -> set[str]:
        if not source or not isinstance(source, str):
            return set()
        pattern = r"resolve_template\(\s*[\"\']([^\"\']+)[\"\']\s*\)"
        return set(re.findall(pattern, source))

    referenced_template_names = set(templates_config.keys())
    referenced_template_names |= _extract_resolve_template_calls(request_transform_source)
    referenced_template_names |= _extract_resolve_template_calls(response_transform_source)

    for template_name in sorted(referenced_template_names):
        template_cid = templates_config.get(template_name)
        template_info = {
            "name": template_name,
            "cid": template_cid,
            "cid_link_html": "",
            "source": None,
            "status": "error",
            "status_text": "Not Found",
            "error": None,
            "variables": [],
        }

        if not template_cid:
            template_info["error"] = "Template referenced by gateway transforms but not configured in gateway templates map"
            template_info["status"] = "error"
            template_info["status_text"] = "Missing Mapping"
            templates_info.append(template_info)
            continue

        # Generate CID link
        template_cid_lookup = _normalize_cid_lookup(template_cid)
        if template_cid_lookup and template_cid_lookup.startswith("/"):
            template_info["cid_link_html"] = str(render_cid_link(template_cid_lookup))

        # Load and validate template
        source, error, variables = _load_and_validate_template(template_cid, context)
        template_info["source"] = source
        if error:
            template_info["error"] = error
            template_info["status"] = "error"
            template_info["status_text"] = "Error"
        else:
            template_info["status"] = "valid"
            template_info["status_text"] = "Valid"
            template_info["variables"] = variables

        templates_info.append(template_info)

    # Generate test paths based on server type
    test_paths = _get_test_paths(server_name)

    html = template.render(
        server_name=server_name,
        config=config,
        server_exists=server_exists,
        server_definition_info=server_definition_info,
        server_definition_diagnostics_url=server_definition_diagnostics_url,
        request_cid_lookup=request_cid_lookup,
        response_cid_lookup=response_cid_lookup,
        request_cid_link_html=request_cid_link_html,
        response_cid_link_html=response_cid_link_html,
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
        templates_info=templates_info,
        test_paths=test_paths,
        # Test mode specific
        test_mode=True,
        test_server_path=test_server_path,
    )
    return {"output": html, "content_type": "text/html"}


def _execute_target_request(target, request_details):
    """Execute a request to the target server.

    The gateway server is internal-only: it always executes another internal
    server and never performs outbound HTTP requests.
    """
    if isinstance(request_details, dict):
        explicit_url = request_details.get("url")
        if isinstance(explicit_url, str) and explicit_url and not explicit_url.startswith("/"):
            raise ValueError("Gateway requests must not specify an external URL")

    if isinstance(target, dict):
        mode = target.get("mode")
        if mode != "internal":
            raise ValueError(f"Unsupported target mode: {mode!r}")
        return _execute_internal_target(target, request_details)

    if isinstance(target, str):
        if not target.startswith("/"):
            raise ValueError("Gateway target must be an internal path")
        return _execute_internal_target({"mode": "internal", "url": target}, request_details)

    raise TypeError(f"Unsupported target type: {type(target).__name__}")


def _resolve_target(config: dict, server_name: str, request_details: dict) -> dict:
    """Resolve the final gateway target.

    The gateway server is internal-only and always targets an internal server.
    """
    explicit_url = request_details.get("url")
    if isinstance(explicit_url, str) and explicit_url:
        if explicit_url.startswith("/"):
            return {"mode": "internal", "url": explicit_url}
        raise ValueError("Gateway target must be an internal path")

    return {"mode": "internal", "url": f"/{server_name}"}


def _execute_internal_target(target: dict, request_details: dict):
    """Execute an internal target (server/alias/CID) without making HTTP requests."""
    internal_path = target.get("url")
    if not isinstance(internal_path, str) or not internal_path.startswith("/"):
        raise ValueError(f"Invalid internal target: {internal_path!r}")

    path = internal_path
    extra_path = request_details.get("path")
    if isinstance(extra_path, str) and extra_path:
        path = urljoin(path.rstrip("/") + "/", extra_path.lstrip("/"))

    query_string = request_details.get("query_string")
    if isinstance(query_string, str) and query_string:
        path = f"{path}?{query_string.lstrip('?')}"

    method = request_details.get("method", "GET")

    import server_execution

    # Create a nested request context so server execution that depends on
    # request.path sees the intended internal path (e.g. /man/grep).
    with current_app.test_request_context(
        path,
        method=method,
        headers=request_details.get("headers") or {},
        data=request_details.get("data"),
        json=request_details.get("json"),
    ):
        result = server_execution.try_server_execution(flask_request.path)
        if result is None:
            raise LookupError(f"No internal target handled path: {flask_request.path}")

        adapted = _as_requests_like_response(result)
        resolved = _follow_internal_redirects(adapted)
        return resolved


def _follow_internal_redirects(response, max_hops: int = 3):
    """Resolve internal redirect responses into final CID-backed content."""
    current = response
    for _ in range(max_hops):
        status = getattr(current, "status_code", 200)
        if status not in (301, 302, 303, 307, 308):
            return current

        headers = getattr(current, "headers", {}) or {}
        location = headers.get("Location") or headers.get("location")
        if not isinstance(location, str) or not location:
            return current

        cid_value, content_type = _try_resolve_location_to_content(location)
        if cid_value is None:
            return current

        class _ResolvedResponse:
            def __init__(self, *, body: bytes, content_type: str):
                self.status_code = 200
                self.headers = {"Content-Type": content_type}
                self.content = body
                self.text = body.decode("utf-8", errors="replace")

            def json(self):
                return json.loads(self.text)

        return _ResolvedResponse(body=cid_value, content_type=content_type)

    return current


def _extract_internal_target_path_from_server_args_json(server_args_json: str | None) -> str | None:
    if not isinstance(server_args_json, str) or not server_args_json.strip():
        return None

    try:
        payload = json.loads(server_args_json)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    target = payload.get("target")
    if isinstance(target, dict):
        url = target.get("url")
        if isinstance(url, str) and url:
            return url
    if isinstance(target, str) and target:
        return target
    return None


def _try_resolve_location_to_content(location: str) -> tuple[bytes | None, str]:
    """Try to resolve a redirect Location to CID content bytes and content type."""
    if not isinstance(location, str):
        return None, "text/plain"

    raw_path = location.split("?", 1)[0]
    raw_path = raw_path.lstrip("/")
    if not raw_path:
        return None, "text/plain"

    if "/" in raw_path:
        # Not a simple /{cid}[.ext] path.
        return None, "text/plain"

    if "." in raw_path:
        cid_candidate, ext = raw_path.split(".", 1)
    else:
        cid_candidate, ext = raw_path, ""

    cid_body = _resolve_cid_content(cid_candidate, as_bytes=True)
    if cid_body is None:
        return None, "text/plain"

    body = bytes(cid_body) if isinstance(cid_body, (bytes, bytearray)) else str(cid_body).encode("utf-8")

    content_type = {
        "html": "text/html",
        "txt": "text/plain",
        "json": "application/json",
        "md": "text/markdown",
    }.get(ext.lower() if isinstance(ext, str) else "", "text/html")

    return body, content_type


def _as_requests_like_response(result):
    """Convert a Flask Response or server result dict into a requests-like object."""
    if hasattr(result, "status_code") and hasattr(result, "headers"):
        class _FlaskResponseAdapter:
            def __init__(self, response):
                self._response = response
                self.status_code = getattr(response, "status_code", 200)
                self.headers = dict(getattr(response, "headers", {}) or {})
                self.content = getattr(response, "data", b"")
                try:
                    self.text = self.content.decode("utf-8", errors="replace")
                except Exception:
                    self.text = ""

            def json(self):
                return json.loads(self.text)

        return _FlaskResponseAdapter(result)

    if isinstance(result, dict) and "output" in result:
        class _DictResponseAdapter:
            def __init__(self, payload):
                self.status_code = 200
                self.headers = {
                    "Content-Type": payload.get("content_type", "text/html")
                }
                output = payload.get("output", "")
                self.content = (
                    output
                    if isinstance(output, (bytes, bytearray))
                    else str(output).encode("utf-8")
                )
                self.text = self.content.decode("utf-8", errors="replace")

            def json(self):
                return json.loads(self.text)

        return _DictResponseAdapter(result)

    raise TypeError(f"Unsupported internal execution result type: {type(result).__name__}")


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
