"""Gateway request handler module.

This module handles normal gateway requests (not test mode).
Orchestrates the flow: request transform → target execution → response transform.
"""

import json
import logging
from typing import Any

from markupsafe import escape

logger = logging.getLogger(__name__)


class GatewayRequestHandler:
    """Handles normal gateway requests."""

    def __init__(
        self,
        apply_request_transform_fn,
        execute_target_fn,
        load_transform_fn,
        create_template_resolver_fn,
        normalize_cid_fn,
        safe_preview_fn,
        extract_exception_summary_fn,
        extract_stack_trace_fn,
        format_exception_detail_fn,
        format_exception_summary_fn,
        parse_hrx_args_fn,
        render_error_fn,
    ):
        """Initialize handler with dependency functions.

        Args:
            apply_request_transform_fn: Function to apply request transform
            execute_target_fn: Function to execute target request
            load_transform_fn: Function to load transform function
            create_template_resolver_fn: Function to create template resolver
            normalize_cid_fn: Function to normalize CID lookup
            safe_preview_fn: Function to safely preview request details
            extract_exception_summary_fn: Function to extract exception summary from HTML
            extract_stack_trace_fn: Function to extract stack trace from HTML
            format_exception_detail_fn: Function to format exception detail
            format_exception_summary_fn: Function to format exception summary
            parse_hrx_args_fn: Function to parse HRX gateway args
            render_error_fn: Function to render error page
        """
        self.apply_request_transform = apply_request_transform_fn
        self.execute_target = execute_target_fn
        self.load_transform = load_transform_fn
        self.create_template_resolver = create_template_resolver_fn
        self.normalize_cid = normalize_cid_fn
        self.safe_preview = safe_preview_fn
        self.extract_exception_summary = extract_exception_summary_fn
        self.extract_stack_trace = extract_stack_trace_fn
        self.format_exception_detail = format_exception_detail_fn
        self.format_exception_summary = format_exception_summary_fn
        self.parse_hrx_args = parse_hrx_args_fn
        self.render_error = render_error_fn

    def handle(
        self, server_name: str, rest_path: str, gateways: dict, context: dict, flask_request: Any
    ) -> dict:
        """Handle a gateway request.

        Args:
            server_name: The gateway server name
            rest_path: The remaining path after the server name
            gateways: Gateway configurations
            context: Request context
            flask_request: Flask request object

        Returns:
            dict with 'output' and 'content_type' keys
        """
        # Validate gateway exists
        if server_name not in gateways:
            available = ", ".join(sorted(gateways.keys())) if gateways else "(none)"
            return self.render_error(
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

        # Build request details from Flask request
        request_details = self._build_request_details(flask_request, rest_path)
        original_rest_path = rest_path

        # Extract archive information for archive-based gateways
        gateway_archive = None
        gateway_path = None
        if server_name == "hrx":
            gateway_archive, gateway_path = self.parse_hrx_args(original_rest_path)

        debug_context["request_details_before_transform"] = {
            "path": request_details.get("path"),
            "query_string": request_details.get("query_string"),
            "method": request_details.get("method"),
        }

        # Create template resolver and enhance context
        template_resolver = self.create_template_resolver(config, context)
        enhanced_context = {
            **(context or {}),
            "resolve_template": template_resolver,
        }

        # Apply request transform (may return direct response)
        response_details = None
        request_cid = config.get("request_transform_cid")

        if request_cid:
            try:
                result = self.apply_request_transform(
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
                return self.render_error(
                    "Request Transform Error",
                    f"Failed to execute request transform: {escape(str(e))}",
                    gateways,
                    exception_summary=f"RequestTransformError: {type(e).__name__}: {str(e)}",
                    error_detail=self.format_exception_detail(
                        e,
                        debug_context={
                            **debug_context,
                            "request_transform_cid": request_cid,
                        },
                    ),
                    gateway_archive=gateway_archive,
                    gateway_path=gateway_path,
                )

        # Execute target if no direct response
        if response_details is None:
            response_details = self._execute_target_and_build_response(
                config,
                server_name,
                rest_path,
                original_rest_path,
                request_details,
                debug_context,
                gateways,
                gateway_archive,
                gateway_path,
            )
            if isinstance(response_details, dict) and "output" in response_details:
                # Error was returned
                return response_details

        # Apply response transform
        response_cid = config.get("response_transform_cid")
        if response_cid:
            try:
                transform_fn = self.load_transform(
                    self.normalize_cid(response_cid), enhanced_context
                )
                if not transform_fn:
                    return self.render_error(
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
                return self.render_error(
                    "Response Transform Error",
                    f"Failed to execute response transform: {escape(str(e))}",
                    gateways,
                    exception_summary=self.format_exception_summary(e),
                    gateway_archive=gateway_archive,
                    gateway_path=gateway_path,
                )

        # Return raw response
        if "_original_output" in response_details:
            return {
                "output": response_details["_original_output"],
                "content_type": response_details.get("_original_content_type", "text/plain"),
            }
        return {
            "output": response_details.get("content", b""),
            "content_type": response_details.get("headers", {}).get("Content-Type", "text/plain"),
        }

    def _build_request_details(self, flask_request: Any, rest_path: str) -> dict:
        """Build request details dict from Flask request.

        Args:
            flask_request: Flask request object
            rest_path: The path after server name

        Returns:
            dict with request details
        """
        try:
            json_body = flask_request.get_json(silent=True)
        except Exception:
            json_body = None

        try:
            raw_body = flask_request.get_data(as_text=True)
        except Exception:
            raw_body = None

        return {
            "path": rest_path,
            "query_string": flask_request.query_string.decode("utf-8"),
            "method": flask_request.method,
            "headers": {k: v for k, v in flask_request.headers if k.lower() != "cookie"},
            "json": json_body,
            "data": raw_body,
        }

    def _execute_target_and_build_response(
        self,
        config: dict,
        server_name: str,
        rest_path: str,
        original_rest_path: str,
        request_details: dict,
        debug_context: dict,
        gateways: dict,
        gateway_archive: str | None,
        gateway_path: str | None,
    ) -> dict:
        """Execute target request and build response details.

        Args:
            config: Gateway configuration
            server_name: Gateway server name
            rest_path: Current rest path
            original_rest_path: Original rest path
            request_details: Request details dict
            debug_context: Debug context dict
            gateways: Gateway configurations
            gateway_archive: Archive name (if applicable)
            gateway_path: Path within archive (if applicable)

        Returns:
            Response details dict or error dict
        """
        debug_context["request_details_after_transform"] = self.safe_preview(request_details)

        # Import here to avoid circular dependency
        from ..execution.internal import resolve_target

        resolved_target = resolve_target(config, server_name, request_details)
        debug_context["resolved_target"] = resolved_target

        try:
            response = self.execute_target(resolved_target, request_details)
        except Exception as e:
            logger.error("Target request error: %s", e)
            return self.render_error(
                "Request Failed",
                f"Failed to connect to target: {escape(str(e))}",
                gateways,
                exception_summary=f"TargetRequestError: {type(e).__name__}: {str(e)}",
                error_detail=self.format_exception_detail(e, debug_context=debug_context),
                gateway_archive=gateway_archive,
                gateway_path=gateway_path,
            )

        # Check for internal server error
        status_code = getattr(response, "status_code", 200)
        response_text = getattr(response, "text", "")
        if isinstance(status_code, int) and status_code >= 500:
            exception_summary = self.extract_exception_summary(response_text)
            stack_trace_html = self.extract_stack_trace(response_text)
            return self.render_error(
                "Gateway Error",
                "An internal server error occurred.",
                gateways,
                exception_summary=exception_summary,
                stack_trace_html=stack_trace_html,
                server_args_json=json.dumps(
                    {
                        "target": resolved_target,
                        "request": {
                            **self.safe_preview(request_details),
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
            response_json = (
                response.json()
                if "application/json" in response.headers.get("Content-Type", "")
                else None
            )
        except Exception:
            response_json = None

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.content,
            "text": response.text,
            "json": response_json,
            "request_path": rest_path,
            "source": "server",
        }
