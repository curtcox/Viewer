"""Gateway meta page handler module.

This module handles meta pages that show transform sources, validation status,
and diagnostic information for gateway servers.
"""

import logging
import re
from typing import Optional, Set

logger = logging.getLogger(__name__)


class GatewayMetaHandler:
    """Handles gateway meta pages."""

    def __init__(
        self,
        load_template_fn,
        load_and_validate_transform_fn,
        load_and_validate_template_fn,
        normalize_cid_fn,
        check_server_exists_fn,
        get_server_definition_info_fn,
        get_test_paths_fn,
        render_cid_link_fn,
        render_error_fn,
    ):
        """Initialize meta handler with dependency functions.

        Args:
            load_template_fn: Function to load Jinja2 template
            load_and_validate_transform_fn: Function to load and validate transform
            load_and_validate_template_fn: Function to load and validate template
            normalize_cid_fn: Function to normalize CID lookup
            check_server_exists_fn: Function to check if server exists
            get_server_definition_info_fn: Function to get server definition info
            get_test_paths_fn: Function to get test paths for server
            render_cid_link_fn: Function to render CID link HTML
            render_error_fn: Function to render error page
        """
        self.load_template = load_template_fn
        self.load_and_validate_transform = load_and_validate_transform_fn
        self.load_and_validate_template = load_and_validate_template_fn
        self.normalize_cid = normalize_cid_fn
        self.check_server_exists = check_server_exists_fn
        self.get_server_definition_info = get_server_definition_info_fn
        self.get_test_paths = get_test_paths_fn
        self.render_cid_link = render_cid_link_fn
        self.render_error = render_error_fn

    def handle(self, server_name: str, gateways: dict, context: dict) -> dict:
        """Handle meta page request.

        Args:
            server_name: The gateway server name
            gateways: Gateway configurations
            context: Request context

        Returns:
            dict with 'output' and 'content_type' keys
        """
        return self._handle_meta_page_impl(
            server_name, gateways, context, test_mode=False, test_server_path=None
        )

    def handle_with_test(
        self, server_name: str, test_server_path: str, gateways: dict, context: dict
    ) -> dict:
        """Handle meta page request with test server information.

        Args:
            server_name: The gateway server name
            test_server_path: The test server path
            gateways: Gateway configurations
            context: Request context

        Returns:
            dict with 'output' and 'content_type' keys
        """
        return self._handle_meta_page_impl(
            server_name, gateways, context, test_mode=True, test_server_path=test_server_path
        )

    def _handle_meta_page_impl(
        self,
        server_name: str,
        gateways: dict,
        context: dict,
        test_mode: bool,
        test_server_path: Optional[str],
    ) -> dict:
        """Internal implementation for both regular and test meta pages.

        Args:
            server_name: The gateway server name
            gateways: Gateway configurations
            context: Request context
            test_mode: Whether this is a test mode meta page
            test_server_path: Test server path (only used if test_mode=True)

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
        template = self.load_template("meta.html")

        # Load and validate transforms
        request_transform_info = self._load_transform_info(
            config.get("request_transform_cid"), "transform_request", context
        )
        response_transform_info = self._load_transform_info(
            config.get("response_transform_cid"), "transform_response", context
        )

        # Get server information
        server_exists = self.check_server_exists(server_name, context)
        server_definition_info = self.get_server_definition_info(server_name)
        server_definition_diagnostics_url = (
            f"/servers/{server_name}/definition-diagnostics" if server_exists else None
        )

        # Load template information
        templates_info = self._load_templates_info(
            config.get("templates", {}),
            request_transform_info["source"],
            response_transform_info["source"],
            context,
        )

        # Generate test paths
        test_paths = self.get_test_paths(server_name)

        # Render template
        template_vars = {
            "server_name": server_name,
            "config": config,
            "server_exists": server_exists,
            "server_definition_info": server_definition_info,
            "server_definition_diagnostics_url": server_definition_diagnostics_url,
            "request_cid_lookup": request_transform_info["cid_lookup"],
            "response_cid_lookup": response_transform_info["cid_lookup"],
            "request_cid_link_html": request_transform_info["cid_link_html"],
            "response_cid_link_html": response_transform_info["cid_link_html"],
            "request_transform_source": request_transform_info["source"],
            "request_transform_status": request_transform_info["status"],
            "request_transform_status_text": request_transform_info["status_text"],
            "request_transform_error": request_transform_info["error"],
            "request_transform_warnings": request_transform_info["warnings"],
            "response_transform_source": response_transform_info["source"],
            "response_transform_status": response_transform_info["status"],
            "response_transform_status_text": response_transform_info["status_text"],
            "response_transform_error": response_transform_info["error"],
            "response_transform_warnings": response_transform_info["warnings"],
            "templates_info": templates_info,
            "test_paths": test_paths,
        }

        # Add test mode specific variables if applicable
        if test_mode:
            template_vars["test_mode"] = True
            template_vars["test_server_path"] = test_server_path

        html = template.render(**template_vars)
        return {"output": html, "content_type": "text/html"}

    def _load_transform_info(
        self, transform_cid: Optional[str], expected_function: str, context: dict
    ) -> dict:
        """Load and validate a transform, returning comprehensive info dict.

        Args:
            transform_cid: CID of the transform (may be None)
            expected_function: Expected function name ("transform_request" or "transform_response")
            context: Request context

        Returns:
            dict with keys: cid_lookup, cid_link_html, source, status, status_text, error, warnings
        """
        result = {
            "cid_lookup": None,
            "cid_link_html": "",
            "source": None,
            "status": "error",
            "status_text": "Not Found",
            "error": None,
            "warnings": [],
        }

        if not transform_cid:
            return result

        # Normalize CID and generate link
        cid_lookup = self.normalize_cid(transform_cid)
        result["cid_lookup"] = cid_lookup

        if cid_lookup and cid_lookup.startswith("/"):
            result["cid_link_html"] = str(self.render_cid_link(cid_lookup))

        # Load and validate
        source, error, warnings = self.load_and_validate_transform(
            cid_lookup, expected_function, context
        )
        result["source"] = source

        if error:
            result["error"] = error
            result["status"] = "error"
            result["status_text"] = "Error"
        elif warnings:
            result["warnings"] = warnings
            result["status"] = "warning"
            result["status_text"] = "Valid with Warnings"
        else:
            result["status"] = "valid"
            result["status_text"] = "Valid"

        return result

    def _load_templates_info(
        self,
        templates_config: dict,
        request_transform_source: Optional[str],
        response_transform_source: Optional[str],
        context: dict,
    ) -> list:
        """Load and validate all templates referenced by the gateway.

        Args:
            templates_config: Templates configuration dict
            request_transform_source: Request transform source code
            response_transform_source: Response transform source code
            context: Request context

        Returns:
            List of template info dicts
        """
        # Find all referenced template names
        referenced_template_names = set(templates_config.keys())
        referenced_template_names |= self._extract_resolve_template_calls(
            request_transform_source
        )
        referenced_template_names |= self._extract_resolve_template_calls(
            response_transform_source
        )

        templates_info = []
        for template_name in sorted(referenced_template_names):
            template_info = self._load_template_info(template_name, templates_config, context)
            templates_info.append(template_info)

        return templates_info

    def _load_template_info(
        self, template_name: str, templates_config: dict, context: dict
    ) -> dict:
        """Load and validate a single template, returning info dict.

        Args:
            template_name: Name of the template
            templates_config: Templates configuration dict
            context: Request context

        Returns:
            dict with template information
        """
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
            template_info[
                "error"
            ] = "Template referenced by gateway transforms but not configured in gateway templates map"
            template_info["status"] = "error"
            template_info["status_text"] = "Missing Mapping"
            return template_info

        # Generate CID link
        template_cid_lookup = self.normalize_cid(template_cid)
        if template_cid_lookup and template_cid_lookup.startswith("/"):
            template_info["cid_link_html"] = str(self.render_cid_link(template_cid_lookup))

        # Load and validate template
        source, error, variables = self.load_and_validate_template(template_cid, context)
        template_info["source"] = source

        if error:
            template_info["error"] = error
            template_info["status"] = "error"
            template_info["status_text"] = "Error"
        else:
            template_info["status"] = "valid"
            template_info["status_text"] = "Valid"
            template_info["variables"] = variables

        return template_info

    def _extract_resolve_template_calls(self, source: Optional[str]) -> Set[str]:
        """Extract template names from resolve_template() calls in source code.

        Args:
            source: Python source code string

        Returns:
            Set of template names found in the source
        """
        if not source or not isinstance(source, str):
            return set()
        pattern = r"resolve_template\(\s*[\"\']([^\"\']+)[\"\']\s*\)"
        return set(re.findall(pattern, source))
