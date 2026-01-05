# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""Response transform for JSON API gateway.

Transforms JSON API responses into formatted HTML with syntax highlighting and clickable links.
Supports configurable link detection strategies including:
- Full URL detection (https://...)
- ID reference detection (userId, postId, etc.)
 - Partial URL detection (path-only values starting with /)
"""

from html import escape
from fnmatch import fnmatch


def transform_response(response_details: dict, context: dict) -> dict:
    """Transform JSON API response to formatted HTML with link detection.

    Args:
        response_details: Dict containing status_code, headers, content, text, json, request_path
        context: Full server execution context with gateway configuration

    Returns:
        Dict with output (HTML) and content_type
    """
    request_path = response_details.get("request_path", "")
    status_code = response_details.get("status_code", 200)
    json_data = response_details.get("json")

    # Get template resolver from context
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError(
            "resolve_template not available - templates must be configured in gateway config"
        )

    # If not JSON, return as plain text
    if json_data is None:
        text = response_details.get("text", "")
        return {
            "output": text,
            "content_type": response_details.get("headers", {}).get(
                "Content-Type", "text/plain"
            ),
        }

    # Get gateway configuration from context
    gateway_config = _get_gateway_config(context)
    link_config = gateway_config.get("link_detection", {})

    # Format JSON with links
    breadcrumb = _build_breadcrumb(
        request_path, gateway_config.get("gateway_name", "json_api")
    )
    formatted_json = _format_json_with_links(
        json_data, link_config=link_config, request_path=request_path, indent=0
    )

    template = resolve_template("json_api_data.html")
    html = template.render(
        request_path=request_path,
        breadcrumb=breadcrumb,
        formatted_json=formatted_json,
        gateway_name=gateway_config.get("gateway_name", "json_api"),
    )

    return {
        "output": html,
        "content_type": "text/html",
    }


def _get_gateway_config(context: dict) -> dict:
    """Extract gateway configuration from context."""
    # The gateway name should be in the context
    gateway_name = context.get("gateway_name", "json_api")

    # Get the full gateways config
    variables = context.get("variables", {})
    gateways = variables.get("gateways", {})

    if isinstance(gateways, str):
        import json

        try:
            gateways = json.loads(gateways)
        except json.JSONDecodeError:
            gateways = {}

    config = gateways.get(gateway_name, {})
    config["gateway_name"] = gateway_name

    return config


def _build_breadcrumb(request_path: str, gateway_name: str) -> str:
    """Build breadcrumb navigation from path."""
    parts = [
        f'<a href="/gateway/{escape(gateway_name)}">{escape(gateway_name)}</a>'
    ]

    if request_path:
        path_parts = request_path.strip("/").split("/")
        current_path = f"/gateway/{gateway_name}"
        for part in path_parts:
            if part:
                current_path += "/" + part
                parts.append(
                    f'<a href="{escape(current_path)}">{escape(part)}</a>'
                )

    return " / ".join(parts)


def _format_json_with_links(obj, link_config: dict, request_path: str = "", indent: int = 0) -> str:
    """Format JSON with syntax highlighting and link detection.

    Args:
        obj: JSON object to format
        link_config: Link detection configuration
        request_path: Current request path for context
        indent: Current indentation level

    Returns:
        HTML-formatted JSON string with links
    """
    indent_str = "  " * indent

    if obj is None:
        return "<span class='json-null'>null</span>"

    if isinstance(obj, bool):
        return f"<span class='json-boolean'>{str(obj).lower()}</span>"

    if isinstance(obj, (int, float)):
        return f"<span class='json-number'>{obj}</span>"

    if isinstance(obj, str):
        # Check for full URL detection
        link_url = _detect_full_url_link(obj, link_config)
        if link_url:
            return (
                f'<a href="{escape(link_url)}" class="json-link">'
                f"<span class=\"json-string\">\"{escape(obj)}\"</span></a>"
            )

        return f"<span class='json-string'>\"{escape(obj)}\"</span>"

    if isinstance(obj, list):
        if not obj:
            return "[]"

        items = []
        for item in obj:
            formatted_item = _format_json_with_links(
                item, link_config, request_path, indent + 1
            )
            items.append(f"{indent_str}  {formatted_item}")

        return "[\n" + ",\n".join(items) + f"\n{indent_str}]"

    if isinstance(obj, dict):
        if not obj:
            return "{}"

        items = []
        for key, value in obj.items():
            formatted_value = _format_json_with_links(
                value, link_config, request_path, indent + 1
            )

            # Check for partial URL detection (path-only)
            partial_url = _detect_partial_url_link(key, value, link_config)
            if partial_url:
                formatted_value = (
                    f"<a href='{escape(partial_url)}' class='json-link'>{formatted_value}</a>"
                )

            # Check for ID reference detection
            link_url = _detect_id_reference_link(key, value, link_config, request_path)
            if link_url:
                formatted_value = (
                    f"<a href='{escape(link_url)}' class='json-link'>{formatted_value}</a>"
                )

            items.append(
                f"{indent_str}  <span class='json-key'>\"{escape(str(key))}\"</span>: {formatted_value}"
            )

        return "{\n" + ",\n".join(items) + f"\n{indent_str}" + "}"

    return f"<span class='json-string'>\"{escape(str(obj))}\"</span>"


def _detect_full_url_link(value: str, link_config: dict) -> str | None:
    """Detect if a string value is a full URL that should be linked.

    Args:
        value: String value to check
        link_config: Link detection configuration

    Returns:
        Gateway link URL if value is a linkable URL, None otherwise
    """
    full_url_config = link_config.get("full_url", {})
    if not full_url_config.get("enabled", False):
        return None

    if not isinstance(value, str):
        return None

    # Check if it's a full URL
    if not (value.startswith("http://") or value.startswith("https://")):
        return None

    # Strip base URL if configured
    base_url_strip = full_url_config.get("base_url_strip", "")
    gateway_prefix = full_url_config.get("gateway_prefix", "")

    if base_url_strip and value.startswith(base_url_strip):
        # Strip the base URL and prepend gateway prefix
        path = value[len(base_url_strip):]
        return f"{gateway_prefix}{path}"

    # Return the URL as-is (external link)
    return value


def _detect_partial_url_link(key: str, value, link_config: dict) -> str | None:
    """Detect if a key-value pair is a partial URL (path-only) that should be linked.

    Args:
        key: JSON key name
        value: JSON value
        link_config: Link detection configuration

    Returns:
        Gateway link URL if this is a linkable path-only URL, None otherwise
    """
    partial_url_config = link_config.get("partial_url", {})
    if not partial_url_config.get("enabled", False):
        return None

    if not isinstance(value, str):
        return None

    if not value.startswith("/"):
        return None

    key_patterns = partial_url_config.get("key_patterns", [])
    if key_patterns:
        if not any(fnmatch(key, pattern) for pattern in key_patterns):
            return None

    gateway_prefix = partial_url_config.get("gateway_prefix", "")
    return f"{gateway_prefix}{value}"


def _detect_id_reference_link(key: str, value, link_config: dict, request_path: str) -> str | None:
    """Detect if a key-value pair is an ID reference that should be linked.

    Args:
        key: JSON key name
        value: JSON value
        link_config: Link detection configuration
        request_path: Current request path for context

    Returns:
        Gateway link URL if this is a linkable ID reference, None otherwise
    """
    id_ref_config = link_config.get("id_reference", {})
    if not id_ref_config.get("enabled", False):
        return None

    patterns = id_ref_config.get("patterns", {})

    # Check if key matches any pattern
    if key in patterns:
        template = patterns[key]
        # Simple template substitution: replace {id} with value
        if isinstance(value, (int, str)):
            link_url = template.replace("{id}", str(value))
            return link_url

    return None
