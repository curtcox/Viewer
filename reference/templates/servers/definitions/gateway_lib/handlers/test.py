"""Gateway test mode handler module.

This module handles gateway test requests where a test server is used
in place of the normal server target.
"""

import json
import logging
from html import escape
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode

logger = logging.getLogger(__name__)


class GatewayTestHandler:
    """Handles gateway test mode requests."""

    def __init__(
        self,
        apply_request_transform_fn,
        apply_response_transform_for_test_fn,
        execute_target_fn,
        create_template_resolver_fn,
        safe_preview_fn,
        extract_exception_summary_fn,
        extract_stack_trace_fn,
        format_exception_detail_fn,
        format_exception_summary_fn,
        render_error_fn,
    ):
        """Initialize test handler with dependency functions.

        Args:
            apply_request_transform_fn: Function to apply request transform
            apply_response_transform_for_test_fn: Function to apply response transform in test mode
            execute_target_fn: Function to execute target request
            create_template_resolver_fn: Function to create template resolver
            safe_preview_fn: Function to safely preview request details
            extract_exception_summary_fn: Function to extract exception summary from HTML
            extract_stack_trace_fn: Function to extract stack trace from HTML
            format_exception_detail_fn: Function to format exception detail
            format_exception_summary_fn: Function to format exception summary
            render_error_fn: Function to render error page
        """
        self.apply_request_transform = apply_request_transform_fn
        self.apply_response_transform_for_test = apply_response_transform_for_test_fn
        self.execute_target = execute_target_fn
        self.create_template_resolver = create_template_resolver_fn
        self.safe_preview = safe_preview_fn
        self.extract_exception_summary = extract_exception_summary_fn
        self.extract_stack_trace = extract_stack_trace_fn
        self.format_exception_detail = format_exception_detail_fn
        self.format_exception_summary = format_exception_summary_fn
        self.render_error = render_error_fn

    def handle(
        self,
        server_name: str,
        rest_path: str,
        test_server_path: str,
        gateways: dict,
        context: dict,
        flask_request: Any,
    ) -> dict:
        """Handle a gateway test request.

        Pattern: /gateway/test/{test-server-path}/as/{server}/{rest}

        Args:
            server_name: The gateway server name (for transforms)
            rest_path: The remaining path after the server name
            test_server_path: The test server path to use instead of the normal server
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

        # Check for CIDS archive listing request (special case)
        if self._is_cids_listing_request(test_server_path, rest_path, flask_request):
            return self._handle_cids_listing(
                test_server_path, server_name, gateways, flask_request
            )

        # Build debug context
        debug_context = {
            "gateway": server_name,
            "rest_path": rest_path,
            "test_server_path": test_server_path,
            "request_path": getattr(flask_request, "path", None),
            "request_method": getattr(flask_request, "method", None),
        }

        # Build request details
        request_details = self._build_request_details(flask_request, rest_path)

        original_rest_path = rest_path

        # Extract archive information for archive-based gateways
        gateway_archive, gateway_path = self._extract_archive_info(server_name, test_server_path)

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
            "test_mode": True,
            "test_server_path": test_server_path,
        }

        # Apply request transform
        request_cid = config.get("request_transform_cid")
        response_details = None

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
                # Check if it's an error response
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
            debug_context["request_details_after_transform"] = self.safe_preview(request_details)

            # Handle special case for CIDS archives
            cids_archive_cid = self._extract_cids_archive_cid(test_server_path)

            if cids_archive_cid:
                resolved_target, request_details = self._prepare_cids_request(
                    cids_archive_cid, request_details, rest_path
                )
            else:
                # Use test server path instead of normal server
                resolved_target = self._resolve_test_target(test_server_path, request_details)

            debug_context["resolved_target"] = resolved_target

            try:
                response = self.execute_target(resolved_target, request_details)
            except Exception as e:
                logger.error("Target request error: %s", e)
                return self.render_error(
                    "Request Failed",
                    f"Failed to connect to test target: {escape(str(e))}",
                    gateways,
                    exception_summary=f"TargetRequestError: {type(e).__name__}: {str(e)}",
                    error_detail=self.format_exception_detail(e, debug_context=debug_context),
                    gateway_archive=gateway_archive,
                    gateway_path=gateway_path,
                )

            # Check for 500 errors
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
                            "test_server_path": test_server_path,
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
            response_details = self._build_response_details(response, rest_path)

            # Special handling for CIDS listing
            if cids_archive_cid and not rest_path:
                return self._render_cids_listing_from_response(
                    response_details, cids_archive_cid, server_name
                )

        # Apply response transform
        response_cid = config.get("response_transform_cid")
        if response_cid:
            try:
                result = self.apply_response_transform_for_test(
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
                return self.render_error(
                    "Response Transform Error",
                    f"Failed to execute response transform: {escape(str(e))}",
                    gateways,
                    exception_summary=self.format_exception_summary(e),
                    gateway_archive=gateway_archive,
                    gateway_path=gateway_path,
                )

        # Return response with URL rewriting for test mode
        return self._build_final_response(response_details, test_server_path, server_name)

    def _is_cids_listing_request(
        self, test_server_path: str, rest_path: str, flask_request: Any
    ) -> bool:
        """Check if this is a CIDS archive listing request."""
        return (
            isinstance(test_server_path, str)
            and test_server_path.startswith("cids/")
            and (not isinstance(rest_path, str) or not rest_path)
            and getattr(flask_request, "method", "GET") == "GET"
        )

    def _handle_cids_listing(
        self, test_server_path: str, server_name: str, gateways: dict, flask_request: Any
    ) -> dict:
        """Handle CIDS archive listing generation."""
        parts = test_server_path.split("/", 1)
        cids_archive_cid = parts[1] if len(parts) == 2 and parts[1] else None

        if not cids_archive_cid:
            return self.render_error(
                "Invalid Request",
                "CIDS archive CID not specified",
                gateways,
            )

        # Build listing request
        listing_request = {
            "path": "",
            "query_string": urlencode([("archive", cids_archive_cid)]),
            "method": "GET",
            "headers": {k: v for k, v in flask_request.headers if k.lower() != "cookie"},
            "json": None,
            "data": None,
        }

        try:
            response = self.execute_target(
                {"mode": "internal", "url": "/cids"},
                listing_request,
            )
        except Exception as e:
            logger.error("Target request error: %s", e)
            return self.render_error(
                "Request Failed",
                f"Failed to connect to test target: {escape(str(e))}",
                gateways,
                exception_summary=f"TargetRequestError: {type(e).__name__}: {str(e)}",
                error_detail=self.format_exception_detail(
                    e,
                    debug_context={
                        "gateway": server_name,
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

        return self._render_cids_listing_html(entries, cids_archive_cid, server_name)

    def _build_request_details(self, flask_request: Any, rest_path: str) -> dict:
        """Build request details dict from Flask request."""
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

    def _extract_archive_info(self, server_name: str, test_server_path: str) -> tuple:
        """Extract archive information for archive-based gateways."""
        gateway_archive = None
        gateway_path = None

        if server_name in ("hrx", "cids"):
            parts = test_server_path.strip("/").split("/", 1)
            gateway_archive = parts[0]
            gateway_path = parts[1] if len(parts) > 1 else ""

        return gateway_archive, gateway_path

    def _extract_cids_archive_cid(self, test_server_path: str) -> Optional[str]:
        """Extract CIDS archive CID from test server path."""
        if isinstance(test_server_path, str) and test_server_path.startswith("cids/"):
            parts = test_server_path.split("/", 1)
            if len(parts) == 2 and parts[1]:
                return parts[1]
        return None

    def _prepare_cids_request(
        self, cids_archive_cid: str, request_details: dict, rest_path: str
    ) -> tuple:
        """Prepare request for CIDS archive access."""
        query_pairs = parse_qsl(request_details.get("query_string") or "", keep_blank_values=True)

        if not any(k == "archive" for k, _ in query_pairs):
            query_pairs.append(("archive", cids_archive_cid))
        if rest_path and not any(k == "path" for k, _ in query_pairs):
            query_pairs.append(("path", rest_path))

        request_details["query_string"] = urlencode(query_pairs)
        request_details["path"] = ""
        resolved_target = {"mode": "internal", "url": "/cids"}

        return resolved_target, request_details

    def _resolve_test_target(self, test_server_path: str, request_details: dict) -> dict:
        """Resolve the test target path."""
        # Ensure test server path starts with /
        if not test_server_path.startswith("/"):
            test_server_path = f"/{test_server_path}"

        return {"mode": "internal", "url": test_server_path}

    def _build_response_details(self, response: Any, rest_path: str) -> dict:
        """Build response details dict from response object."""
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
            "source": "test_server",
        }

    def _render_cids_listing_from_response(
        self, response_details: dict, cids_archive_cid: str, server_name: str
    ) -> dict:
        """Render CIDS listing HTML from response details."""
        listing_text = response_details.get("text")
        if isinstance(listing_text, str):
            entries = [line.strip() for line in listing_text.splitlines() if line.strip()]
        else:
            entries = []

        return self._render_cids_listing_html(entries, cids_archive_cid, server_name)

    def _render_cids_listing_html(
        self, entries: list, cids_archive_cid: str, server_name: str
    ) -> dict:
        """Render CIDS listing as HTML."""
        base_prefix = f"/gateway/test/cids/{cids_archive_cid}/as/{server_name}/"
        items_html = "\n".join(
            f'<li><a href="{base_prefix}{escape(entry)}">{escape(entry)}</a></li>'
            for entry in entries
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
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

    def _build_final_response(
        self, response_details: dict, test_server_path: str, server_name: str
    ) -> dict:
        """Build final response with URL rewriting for test mode."""
        # Check for stored original output (from transforms)
        if "_original_output" in response_details:
            output = response_details["_original_output"]
            content_type = response_details.get("_original_content_type", "text/plain")
            if "html" in str(content_type).lower():
                output = self._rewrite_urls_for_test_mode(output, test_server_path, server_name)
            return {
                "output": output,
                "content_type": content_type,
            }

        # Default response
        output = response_details.get("content", b"")
        content_type = response_details.get("headers", {}).get("Content-Type", "text/plain")
        if "html" in str(content_type).lower():
            output = self._rewrite_urls_for_test_mode(output, test_server_path, server_name)

        return {
            "output": output,
            "content_type": content_type,
        }

    def _rewrite_urls_for_test_mode(self, output: Any, test_server_path: str, server_name: str):
        """Rewrite URLs from gateway path to test path."""
        prefix = f"/gateway/test/{test_server_path}/as/{server_name}"
        old_prefix = f"/gateway/{server_name}"

        if isinstance(output, str):
            return output.replace(old_prefix, prefix)
        elif isinstance(output, (bytes, bytearray)):
            decoded = bytes(output).decode("utf-8", errors="replace")
            return decoded.replace(old_prefix, prefix)

        return output
