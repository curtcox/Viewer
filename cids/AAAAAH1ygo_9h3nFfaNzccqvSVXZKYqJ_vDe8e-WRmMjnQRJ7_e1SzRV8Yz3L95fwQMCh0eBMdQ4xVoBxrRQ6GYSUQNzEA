# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""MCP (Model Context Protocol) server for exposing internal servers as MCP-compliant endpoints.

This server implements the MCP 2025-11-25 Streamable HTTP transport specification,
allowing AI applications to interact with internal servers using standard MCP protocol.

Routes:
    /mcp - Instruction page
    /mcp/meta/{server} - Server MCP metadata page
    /mcp/{server} - MCP endpoint (POST for JSON-RPC, GET for SSE listener)
"""

import ast
import json
import logging
import time
import traceback
import uuid
from html import escape
from typing import Any, Dict, List, Optional

from flask import Response, make_response, request as flask_request, stream_with_context


logger = logging.getLogger(__name__)


def main(context=None):
    """MCP server main function.

    Handles all MCP routes based on the request path.

    Parameters:
        context: Request context (automatically provided)
    """
    try:
        return _main_impl(context)
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"MCP error: {e}\n{error_detail}")
        return _render_error(
            "MCP Error",
            f"An unexpected error occurred: {escape(str(e))}",
            {},
            error_detail=error_detail,
        )


def _main_impl(context=None):
    """Implementation of main MCP routing logic."""
    request_path = flask_request.path or "/"
    path_parts = request_path.strip("/").split("/")

    # Remove 'mcp' prefix if present
    if path_parts and path_parts[0] == "mcp":
        path_parts = path_parts[1:]

    # Load mcps configuration
    mcps = _load_mcps(context)

    # Route to appropriate handler
    if not path_parts or path_parts[0] == "":
        return _handle_instruction_page(mcps, context)

    first_part = path_parts[0]

    if first_part == "meta" and len(path_parts) > 1:
        server_name = path_parts[1]
        return _handle_meta_page(server_name, mcps, context)

    # Otherwise, it's a server endpoint
    server_name = first_part
    if server_name in mcps:
        return _handle_mcp_endpoint(server_name, mcps, context)

    # Server not found
    return _render_error(
        "Server Not Found",
        f"MCP server '{escape(server_name)}' is not configured.",
        mcps,
    )


# ============================================================================
# Configuration Loading
# ============================================================================


def _load_mcps(context: Optional[Dict] = None) -> Dict[str, Any]:
    """Load MCP configurations from the mcps variable.

    Args:
        context: Execution context containing variables

    Returns:
        Dictionary mapping server names to their MCP configurations
    """
    if context is None:
        return {}

    variables = context.get("variables", {})
    mcps_value = variables.get("mcps")

    if not mcps_value:
        return {}

    # If it's already a dict, use it directly
    if isinstance(mcps_value, dict):
        mcps_data = mcps_value
    elif isinstance(mcps_value, str):
        # Try to parse as JSON first
        try:
            mcps_data = json.loads(mcps_value)
        except json.JSONDecodeError:
            # Value might be a CID - try to resolve it
            if mcps_value.startswith("AAAAA"):
                cid_content = _get_cid_content(mcps_value, context)
                if cid_content:
                    try:
                        mcps_data = json.loads(cid_content)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse mcps CID content: {e}")
                        return {}
                else:
                    logger.warning(f"Failed to resolve mcps CID: {mcps_value}")
                    return {}
            else:
                logger.warning(f"mcps value is not valid JSON or CID: {mcps_value[:50]}")
                return {}
    else:
        return {}

    try:
        # Resolve config_cid references to actual configs
        resolved_mcps = {}
        for server_name, server_entry in mcps_data.items():
            config_cid = server_entry.get("config_cid")
            if config_cid:
                # Resolve the CID to get the actual config
                config_content = _get_cid_content(config_cid, context)
                if config_content:
                    try:
                        config = json.loads(config_content) if isinstance(config_content, str) else config_content
                        resolved_mcps[server_name] = config
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse config for MCP server '{server_name}'")
                else:
                    logger.warning(f"Config CID not found for MCP server '{server_name}': {config_cid}")
            else:
                # Use the entry directly if no config_cid
                resolved_mcps[server_name] = server_entry

        return resolved_mcps
    except (AttributeError, TypeError) as e:
        logger.warning(f"Failed to process mcps configuration: {e}")
        return {}


def _get_cid_content(cid_path: str, context: Optional[Dict] = None) -> Optional[str]:
    """Get content from a CID or file path.

    Args:
        cid_path: CID or file path
        context: Execution context

    Returns:
        Content as string, or None if not found
    """
    # If it's a file path, try to read it
    if cid_path.startswith("reference/templates/"):
        try:
            from pathlib import Path
            file_path = Path(cid_path)
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read file {cid_path}: {e}")
            return None

    # Otherwise, try to resolve as CID
    try:
        from cid_storage import get_cid_content

        # Try database first - CID paths are stored with leading slash
        cid_value = cid_path if cid_path.startswith("/") else f"/{cid_path}"
        content = get_cid_content(cid_value)

        if content:
            if hasattr(content, "file_data"):
                data = content.file_data
                return data.decode("utf-8") if isinstance(data, bytes) else data
            if hasattr(content, "data"):
                data = content.data
                return data.decode("utf-8") if isinstance(data, bytes) else data
            return content.decode("utf-8") if isinstance(content, bytes) else content
    except Exception as e:
        logger.warning(f"Failed to get CID content for {cid_path}: {e}")

    return None


# ============================================================================
# MCP Protocol - JSON-RPC Handlers
# ============================================================================


def _handle_mcp_endpoint(server_name: str, mcps: Dict[str, Any], context: Optional[Dict] = None):
    """Handle MCP endpoint requests (both POST and GET).

    Args:
        server_name: Name of the MCP server
        mcps: MCP configurations
        context: Execution context

    Returns:
        Flask response
    """
    method = flask_request.method

    if method == "POST":
        return _handle_post_request(server_name, mcps, context)
    elif method == "GET":
        return _handle_get_listener(server_name, mcps, context)
    else:
        return {"error": "Method not allowed"}, 405


def _handle_post_request(server_name: str, mcps: Dict[str, Any], context: Optional[Dict] = None):
    """Handle POST request per MCP 2025-11-25 Streamable HTTP spec.

    Args:
        server_name: Name of the MCP server
        mcps: MCP configurations
        context: Execution context

    Returns:
        Flask response with JSON or SSE stream
    """
    # Validate Accept header
    accept = flask_request.headers.get("Accept", "")
    if "application/json" not in accept and "text/event-stream" not in accept:
        return {"error": "Must accept application/json or text/event-stream"}, 406

    # Parse JSON-RPC request
    try:
        body = flask_request.get_json()
        if not body:
            return _jsonrpc_error(-32700, "Parse error", None)
    except Exception:
        return _jsonrpc_error(-32700, "Parse error", None)

    # Get or create session
    session_id = flask_request.headers.get("Mcp-Session-Id")
    jsonrpc_method = body.get("method")

    if jsonrpc_method == "initialize":
        session_id = _create_session()

    # Dispatch to appropriate handler
    result = _dispatch_jsonrpc(server_name, body, mcps, context)

    # Return response with session header
    response = make_response(result)
    if session_id:
        response.headers["Mcp-Session-Id"] = session_id
    response.headers["Content-Type"] = "application/json"
    return response


def _handle_get_listener(server_name: str, mcps: Dict[str, Any], context: Optional[Dict] = None):
    """Handle GET request to listen for server-initiated messages.

    Args:
        server_name: Name of the MCP server
        mcps: MCP configurations
        context: Execution context

    Returns:
        Flask response with SSE stream
    """
    session_id = flask_request.headers.get("Mcp-Session-Id")
    if not session_id:
        return {"error": "Mcp-Session-Id required"}, 400

    def generate():
        """Generate SSE events."""
        # Send keep-alive comments periodically
        yield ": keepalive\n\n"
        time.sleep(15)

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["Mcp-Session-Id"] = session_id
    return response


def _dispatch_jsonrpc(
    server_name: str, request_body: Dict, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Dispatch JSON-RPC request to appropriate handler.

    Args:
        server_name: Name of the MCP server
        request_body: JSON-RPC request body
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response dict
    """
    method = request_body.get("method")
    params = request_body.get("params", {})
    request_id = request_body.get("id")

    # Validate JSON-RPC version
    if request_body.get("jsonrpc") != "2.0":
        return _jsonrpc_error(-32600, "Invalid Request", request_id)

    # Dispatch to method handler
    if method == "initialize":
        return _handle_initialize(params, request_id)
    elif method == "tools/list":
        return _handle_tools_list(server_name, params, request_id, mcps, context)
    elif method == "tools/call":
        return _handle_tools_call(server_name, params, request_id, mcps, context)
    elif method == "resources/list":
        return _handle_resources_list(server_name, params, request_id, mcps, context)
    elif method == "resources/read":
        return _handle_resources_read(server_name, params, request_id, mcps, context)
    elif method == "prompts/list":
        return _handle_prompts_list(server_name, params, request_id, mcps, context)
    elif method == "prompts/get":
        return _handle_prompts_get(server_name, params, request_id, mcps, context)
    else:
        return _jsonrpc_error(-32601, "Method not found", request_id)


def _jsonrpc_error(code: int, message: str, request_id: Any) -> Dict:
    """Create a JSON-RPC error response.

    Args:
        code: Error code
        message: Error message
        request_id: Request ID

    Returns:
        JSON-RPC error response dict
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _jsonrpc_success(result: Any, request_id: Any) -> Dict:
    """Create a JSON-RPC success response.

    Args:
        result: Result data
        request_id: Request ID

    Returns:
        JSON-RPC success response dict
    """
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


# ============================================================================
# MCP Method Handlers
# ============================================================================


def _handle_initialize(params: Dict, request_id: Any) -> Dict:
    """Handle MCP initialize request.

    Args:
        params: Request parameters
        request_id: Request ID

    Returns:
        JSON-RPC response with server capabilities
    """
    return _jsonrpc_success(
        {
            "protocolVersion": "2025-11-25",
            "serverInfo": {"name": "Viewer MCP Server", "version": "1.0.0"},
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
        },
        request_id,
    )


def _handle_tools_list(
    server_name: str, params: Dict, request_id: Any, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Handle tools/list request.

    Args:
        server_name: Name of the MCP server
        params: Request parameters
        request_id: Request ID
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response with tools list
    """
    server_config = mcps.get(server_name, {})
    tools = []

    # Static tools from config
    static_tools = server_config.get("tools", {})
    for tool_name, tool_config in static_tools.items():
        tools.append(
            {
                "name": tool_name,
                "description": tool_config.get("description", ""),
                "inputSchema": tool_config.get("inputSchema", {"type": "object"}),
            }
        )

    # Auto-discovered tools
    if server_config.get("auto_discover", False):
        discovered = _discover_server_tools(server_name, context)
        tools.extend(discovered)

    return _jsonrpc_success({"tools": tools}, request_id)


def _handle_tools_call(
    server_name: str, params: Dict, request_id: Any, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Handle tools/call request.

    Args:
        server_name: Name of the MCP server
        params: Request parameters containing tool name and arguments
        request_id: Request ID
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response with tool result
    """
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})

    try:
        # Execute the tool by invoking the corresponding server
        result = _execute_tool(server_name, tool_name, tool_args, context)

        return _jsonrpc_success(
            {"content": [{"type": "text", "text": str(result)}], "isError": False}, request_id
        )
    except Exception as e:
        logger.error(f"Tool execution error: {e}\n{traceback.format_exc()}")
        return _jsonrpc_success(
            {"content": [{"type": "text", "text": str(e)}], "isError": True}, request_id
        )


def _handle_resources_list(
    server_name: str, params: Dict, request_id: Any, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Handle resources/list request.

    Args:
        server_name: Name of the MCP server
        params: Request parameters
        request_id: Request ID
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response with resources list
    """
    server_config = mcps.get(server_name, {})
    resources = []

    # Static resources from config
    static_resources = server_config.get("resources", {})
    for resource_name, resource_config in static_resources.items():
        resources.append(
            {
                "uri": resource_config.get("uri", f"server://{server_name}/{resource_name}"),
                "name": resource_config.get("name", resource_name),
                "description": resource_config.get("description", ""),
                "mimeType": resource_config.get("mimeType", "text/plain"),
            }
        )

    return _jsonrpc_success({"resources": resources}, request_id)


def _handle_resources_read(
    server_name: str, params: Dict, request_id: Any, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Handle resources/read request.

    Args:
        server_name: Name of the MCP server
        params: Request parameters containing resource URI
        request_id: Request ID
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response with resource content
    """
    uri = params.get("uri")
    if not uri:
        return _jsonrpc_error(-32602, "Invalid params: uri required", request_id)

    try:
        # Parse URI and fetch content
        content = _read_resource(uri, context)
        return _jsonrpc_success(
            {"contents": [{"uri": uri, "mimeType": "text/plain", "text": content}]}, request_id
        )
    except Exception as e:
        return _jsonrpc_error(-32603, f"Failed to read resource: {str(e)}", request_id)


def _handle_prompts_list(
    server_name: str, params: Dict, request_id: Any, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Handle prompts/list request.

    Args:
        server_name: Name of the MCP server
        params: Request parameters
        request_id: Request ID
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response with prompts list
    """
    server_config = mcps.get(server_name, {})
    prompts_config = server_config.get("prompts", {})
    prompts = []

    for prompt_name, prompt_config in prompts_config.items():
        prompts.append(
            {
                "name": prompt_name,
                "description": prompt_config.get("description", ""),
                "arguments": prompt_config.get("arguments", []),
            }
        )

    return _jsonrpc_success({"prompts": prompts}, request_id)


def _handle_prompts_get(
    server_name: str, params: Dict, request_id: Any, mcps: Dict[str, Any], context: Optional[Dict] = None
) -> Dict:
    """Handle prompts/get request.

    Args:
        server_name: Name of the MCP server
        params: Request parameters containing prompt name
        request_id: Request ID
        mcps: MCP configurations
        context: Execution context

    Returns:
        JSON-RPC response with prompt messages
    """
    prompt_name = params.get("name")
    if not prompt_name:
        return _jsonrpc_error(-32602, "Invalid params: name required", request_id)

    server_config = mcps.get(server_name, {})
    prompts_config = server_config.get("prompts", {})
    prompt_config = prompts_config.get(prompt_name)

    if not prompt_config:
        return _jsonrpc_error(-32602, f"Prompt '{prompt_name}' not found", request_id)

    messages = prompt_config.get("messages", [])
    return _jsonrpc_success({"messages": messages}, request_id)


# ============================================================================
# Auto-Discovery
# ============================================================================


def _discover_server_tools(server_name: str, context: Optional[Dict] = None) -> List[Dict]:
    """Discover tools from a server definition.

    Args:
        server_name: Name of the server
        context: Execution context

    Returns:
        List of tool definitions
    """
    # Get server definition
    if not context:
        return []

    servers = context.get("servers", {})
    server_def = servers.get(server_name)
    if not server_def:
        return []

    # server_def might be a string (the definition itself) or a dict with definition_cid
    if isinstance(server_def, str):
        server_code = server_def
    elif isinstance(server_def, dict):
        definition_cid = server_def.get("definition_cid")
        if not definition_cid:
            return []
        # Get the server code
        server_code = _get_cid_content(definition_cid, context)
        if not server_code:
            return []
    else:
        return []

    # Check if it's a Python or shell server
    if "def main(" in server_code:
        return _discover_python_tools(server_name, server_code)
    elif "@bash_command" in server_code:
        return _discover_shell_tools(server_name, server_code)

    return []


def _discover_python_tools(server_name: str, server_code: str) -> List[Dict]:
    """Discover tools from a Python server.

    Args:
        server_name: Name of the server
        server_code: Python source code

    Returns:
        List of tool definitions
    """
    tools = []

    try:
        tree = ast.parse(server_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions
                if node.name.startswith("_"):
                    continue

                # Extract docstring
                docstring = ast.get_docstring(node) or ""
                description = docstring.split("\n")[0] if docstring else f"{node.name} function"

                # Build input schema from function arguments
                input_schema = _build_input_schema(node)

                tools.append(
                    {"name": node.name, "description": description, "inputSchema": input_schema}
                )
    except SyntaxError:
        logger.warning(f"Failed to parse Python server {server_name}")

    return tools


def _discover_shell_tools(server_name: str, server_code: str) -> List[Dict]:
    """Discover tools from a shell server.

    Args:
        server_name: Name of the server
        server_code: Shell script source

    Returns:
        List of tool definitions
    """
    # Shell servers are treated as single-tool servers
    return [
        {
            "name": server_name,
            "description": f"Execute {server_name} command",
            "inputSchema": {
                "type": "object",
                "properties": {"args": {"type": "string", "description": "Command arguments"}},
            },
        }
    ]


def _build_input_schema(func_node: ast.FunctionDef) -> Dict:
    """Build JSON Schema from function arguments.

    Args:
        func_node: AST FunctionDef node

    Returns:
        JSON Schema dict
    """
    schema = {"type": "object", "properties": {}, "required": []}

    for arg in func_node.args.args:
        arg_name = arg.arg

        # Skip context and self
        if arg_name in ("context", "self"):
            continue

        # Default to string type
        schema["properties"][arg_name] = {"type": "string", "description": f"{arg_name} parameter"}

        # Add to required if no default value
        defaults_start = len(func_node.args.args) - len(func_node.args.defaults)
        arg_index = func_node.args.args.index(arg)
        if arg_index < defaults_start:
            schema["required"].append(arg_name)

    return schema


# ============================================================================
# Tool Execution
# ============================================================================


def _execute_tool(server_name: str, tool_name: str, args: Dict, context: Optional[Dict] = None) -> str:
    """Execute a tool by invoking the corresponding server.

    Args:
        server_name: Name of the server
        tool_name: Name of the tool
        args: Tool arguments
        context: Execution context

    Returns:
        Tool execution result as string
    """
    from server_execution import try_server_execution

    # Construct the path
    if tool_name == server_name:
        path = f"/servers/{server_name}"
    else:
        path = f"/servers/{server_name}/{tool_name}"

    # Convert args to query string
    query_params = "&".join([f"{k}={v}" for k, v in args.items()])
    if query_params:
        path = f"{path}?{query_params}"

    # Execute the server
    result = try_server_execution(path)

    if result and "output" in result:
        return result["output"]
    elif result and "error" in result:
        raise Exception(result["error"])
    else:
        return str(result)


def _read_resource(uri: str, context: Optional[Dict] = None) -> str:
    """Read a resource by URI.

    Args:
        uri: Resource URI
        context: Execution context

    Returns:
        Resource content as string
    """
    # For now, just return a placeholder
    return f"Resource content for {uri}"


# ============================================================================
# Session Management
# ============================================================================


def _create_session() -> str:
    """Create a new MCP session.

    Returns:
        Session ID
    """
    return str(uuid.uuid4())


# ============================================================================
# HTML Pages
# ============================================================================


def _handle_instruction_page(mcps: Dict[str, Any], context: Optional[Dict] = None):
    """Handle the instruction page at /mcp.

    Args:
        mcps: MCP configurations
        context: Execution context

    Returns:
        HTML response
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 30px; }
        .server-list { list-style: none; padding: 0; }
        .server-item { margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }
        .server-name { font-weight: bold; font-size: 1.1em; color: #0066cc; }
        .server-desc { color: #666; margin-top: 5px; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>MCP Server</h1>
    <p>This server implements the Model Context Protocol (MCP) 2025-11-25 Streamable HTTP transport.</p>

    <h2>What is MCP?</h2>
    <p>MCP is an open protocol that enables AI applications to securely connect to data sources and tools.
    It provides a standard way to expose tools, resources, and prompts to AI models.</p>
    <p>Learn more at <a href="https://modelcontextprotocol.io/" target="_blank">modelcontextprotocol.io</a></p>

    <h2>Available MCP Servers</h2>
"""

    if not mcps:
        html += "<p>No MCP servers are currently configured.</p>"
    else:
        html += '<ul class="server-list">'
        for server_name, config in mcps.items():
            description = config.get("description", "No description available")
            html += f"""
            <li class="server-item">
                <div class="server-name">
                    <a href="/mcp/{escape(server_name)}">{escape(server_name)}</a>
                </div>
                <div class="server-desc">{escape(description)}</div>
                <div style="margin-top: 8px; font-size: 0.9em;">
                    <a href="/mcp/meta/{escape(server_name)}">View metadata</a> |
                    <a href="/servers/{escape(server_name)}">Direct access</a>
                </div>
            </li>
"""
        html += "</ul>"

    html += """
    <h2>Protocol Information</h2>
    <p>This server implements MCP 2025-11-25 with Streamable HTTP transport:</p>
    <ul>
        <li><strong>POST /mcp/{server}</strong> - Send JSON-RPC requests</li>
        <li><strong>GET /mcp/{server}</strong> - Listen for server-initiated messages (SSE)</li>
    </ul>
    <p>See <a href="/variables/mcps">MCP configurations</a> for detailed settings.</p>
</body>
</html>
"""

    return {"output": html, "content_type": "text/html"}


def _handle_meta_page(server_name: str, mcps: Dict[str, Any], context: Optional[Dict] = None):
    """Handle the meta page at /mcp/meta/{server}.

    Args:
        server_name: Name of the MCP server
        mcps: MCP configurations
        context: Execution context

    Returns:
        HTML response
    """
    server_config = mcps.get(server_name)
    if not server_config:
        return _render_error("Server Not Found", f"MCP server '{escape(server_name)}' is not configured.", mcps)

    description = server_config.get("description", "No description available")

    # Get tools
    tools = []
    static_tools = server_config.get("tools", {})
    for tool_name, tool_config in static_tools.items():
        tools.append(
            {
                "name": tool_name,
                "description": tool_config.get("description", ""),
                "schema": tool_config.get("inputSchema", {}),
            }
        )

    if server_config.get("auto_discover", False):
        discovered = _discover_server_tools(server_name, context)
        tools.extend([{"name": t["name"], "description": t["description"], "schema": t["inputSchema"]} for t in discovered])

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server: {escape(server_name)}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .tool {{ margin: 15px 0; padding: 15px; border: 1px solid #ddd; border-radius: 4px; }}
        .tool-name {{ font-weight: bold; font-size: 1.1em; }}
        .tool-desc {{ color: #666; margin: 5px 0; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>MCP Server: {escape(server_name)}</h1>
    <p>{escape(description)}</p>
    <p><a href="/mcp">← Back to MCP servers</a> | <a href="/servers/{escape(server_name)}">Direct access</a></p>

    <h2>Available Tools</h2>
"""

    if not tools:
        html += "<p>No tools available.</p>"
    else:
        for tool in tools:
            html += f"""
    <div class="tool">
        <div class="tool-name">{escape(tool['name'])}</div>
        <div class="tool-desc">{escape(tool['description'])}</div>
        <div style="margin-top: 10px;">
            <strong>Input Schema:</strong>
            <pre>{escape(json.dumps(tool['schema'], indent=2))}</pre>
        </div>
    </div>
"""

    html += """
    <h2>Connection Example</h2>
    <p>Connect to this MCP server using the following endpoint:</p>
    <pre>POST /mcp/{server}</pre>
    <p>Send JSON-RPC 2.0 messages with method calls like:</p>
    <pre>{{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {{}}
}}</pre>
</body>
</html>
""".format(
        server=escape(server_name)
    )

    return {"output": html, "content_type": "text/html"}


def _render_error(title: str, message: str, mcps: Dict[str, Any], error_detail: str = "") -> Dict:
    """Render an error page.

    Args:
        title: Error title
        message: Error message
        mcps: MCP configurations (for navigation)
        error_detail: Detailed error information (optional)

    Returns:
        HTML response dict
    """
    detail_html = ""
    if error_detail:
        detail_html = f"""
        <h2>Details</h2>
        <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">{escape(error_detail)}</pre>
"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{escape(title)}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #d32f2f; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>{escape(title)}</h1>
    <p>{message}</p>
    {detail_html}
    <p><a href="/mcp">← Back to MCP servers</a></p>
</body>
</html>
"""

    return {"output": html, "content_type": "text/html"}
