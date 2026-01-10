"""Gateway form handlers module.

This module handles the request and response experimentation forms
that allow interactive testing of gateway transforms.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GatewayFormsHandler:
    """Handles gateway form pages."""

    def __init__(
        self,
        load_template_fn,
        get_default_request_transform_fn,
        get_default_response_transform_fn,
        load_invocation_for_request_fn,
        preview_request_transform_fn,
        execute_gateway_request_fn,
        load_invocation_for_response_fn,
        transform_response_fn,
    ):
        """Initialize forms handler with dependency functions.

        Args:
            load_template_fn: Function to load Jinja2 template
            get_default_request_transform_fn: Function to get default request transform
            get_default_response_transform_fn: Function to get default response transform
            load_invocation_for_request_fn: Function to load invocation for request form
            preview_request_transform_fn: Function to preview request transform
            execute_gateway_request_fn: Function to execute gateway request
            load_invocation_for_response_fn: Function to load invocation for response form
            transform_response_fn: Function to transform response
        """
        self.load_template = load_template_fn
        self.get_default_request_transform = get_default_request_transform_fn
        self.get_default_response_transform = get_default_response_transform_fn
        self.load_invocation_for_request = load_invocation_for_request_fn
        self.preview_request_transform = preview_request_transform_fn
        self.execute_gateway_request = execute_gateway_request_fn
        self.load_invocation_for_response = load_invocation_for_response_fn
        self.transform_response = transform_response_fn

    def handle_request_form(self, gateways: dict, context: dict, flask_request: Any) -> dict:
        """Handle the request experimentation form.

        Args:
            gateways: Gateway configurations
            context: Request context
            flask_request: Flask request object

        Returns:
            dict with 'output' and 'content_type' keys
        """
        template = self.load_template("request_form.html")

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
            "default_transform": self.get_default_request_transform(),
        }

        # Handle actions
        if action == "load" and ctx["invocation_cid"]:
            ctx = self.load_invocation_for_request(ctx, gateways)
        elif action == "preview" and ctx["selected_server"]:
            ctx = self.preview_request_transform(ctx, gateways)
        elif action == "execute" and ctx["selected_server"]:
            ctx = self.execute_gateway_request(ctx, gateways, context)

        html = template.render(**ctx)
        return {"output": html, "content_type": "text/html"}

    def handle_response_form(self, gateways: dict, context: dict, flask_request: Any) -> dict:
        """Handle the response experimentation form.

        Args:
            gateways: Gateway configurations
            context: Request context
            flask_request: Flask request object

        Returns:
            dict with 'output' and 'content_type' keys
        """
        template = self.load_template("response_form.html")

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
            "default_transform": self.get_default_response_transform(),
        }

        # Handle actions
        if action == "load" and ctx["invocation_cid"]:
            ctx = self.load_invocation_for_response(ctx, gateways)
        elif action == "transform":
            ctx = self.transform_response(ctx, gateways, context)

        html = template.render(**ctx)
        return {"output": html, "content_type": "text/html"}
