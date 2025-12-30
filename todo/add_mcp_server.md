# MCP Server Facility Plan

## Implementation Status: PLANNING

This document describes the plan for adding an MCP (Model Context Protocol) server facility analogous to the existing gateway facility. The MCP server will expose internal servers as MCP-compliant endpoints, allowing AI applications to interact with them using the standard MCP protocol.

---

## Overview

The MCP server facility will:

1. **Expose internal servers as MCP servers**: Any server defined at `/servers/foo` can be accessed as an MCP server at `/mcp/foo`
2. **Follow the gateway pattern**: Configuration is driven by the `/variables/mcps` variable, paralleling `/variables/gateways`
3. **Implement MCP protocol**: Support the Streamable HTTP transport with JSON-RPC 2.0 messaging
4. **Map server functions to MCP tools**: Server functions become invokable MCP tools
5. **Map server outputs to MCP resources**: Server output can be exposed as MCP resources
6. **Support MCP prompts**: Optionally expose configured prompts for servers

Reference: [MCP Protocol Documentation](https://modelcontextprotocol.io/docs/getting-started/intro)

---

## Architecture

### URL Structure

| Route | Purpose | MCP Method |
|-------|---------|------------|
| `/mcp` | Instruction page (HTML) | N/A |
| `/mcp/meta/{server}` | Server MCP metadata and diagnostics (HTML) | N/A |
| `/mcp/{server}` | MCP endpoint for the server (POST for requests, GET for listening) | All MCP methods |

### MCP Protocol Mapping

The MCP server will implement the **Streamable HTTP Transport** (MCP 2025-11-25):

**POST `/mcp/{server}`**: Send JSON-RPC requests
- Client sends one JSON-RPC message per request
- Must include `Accept: application/json, text/event-stream` header
- Server responds with either:
  - `application/json`: Single JSON-RPC response
  - `text/event-stream`: Streamed response (for long-running operations)
- Supported methods:
  - `initialize`: Establish session and exchange capabilities
  - `tools/list`: List available tools (derived from server functions)
  - `tools/call`: Execute a tool (invoke server function)
  - `resources/list`: List available resources (server outputs)
  - `resources/read`: Read a resource
  - `prompts/list`: List available prompts
  - `prompts/get`: Get a specific prompt

**GET `/mcp/{server}`**: Listen for server-initiated messages
- Opens a streaming connection for server notifications
- Server sends JSON-RPC requests/notifications as SSE events
- Used for real-time updates (optional capability)

### Session Management

- Sessions are identified by `Mcp-Session-Id` header
- Sessions track:
  - Client capabilities
  - Active subscriptions
  - Protocol version

---

## MCPs Variable Format

The `mcps` variable is a JSON map from server names to CIDs containing the MCP configuration. This follows the same pattern as the `gateways` variable.

### mcps.source.json (Source File)

```json
{
  "echo": {
    "config_cid": "reference_templates/mcps/configs/echo.json"
  },
  "markdown": {
    "config_cid": "reference_templates/mcps/configs/markdown.json"
  },
  "jq": {
    "config_cid": "reference_templates/mcps/configs/jq.json"
  },
  "date": {
    "config_cid": "reference_templates/mcps/configs/date.json"
  }
}
```

### mcps.json (Generated with CIDs)

After boot image generation, filenames are replaced with CIDs:

```json
{
  "echo": {
    "config_cid": "AAAAA..."
  },
  "markdown": {
    "config_cid": "AAAAA..."
  },
  "jq": {
    "config_cid": "AAAAA..."
  },
  "date": {
    "config_cid": "AAAAA..."
  }
}
```

### Individual Server Configuration Files

Each server's MCP configuration is stored in a separate JSON file.

**File:** `reference_templates/mcps/configs/echo.json`
```json
{
  "description": "Echo server - returns input as output",
  "tools": {
    "echo": {
      "description": "Echo the provided input",
      "inputSchema": {
        "type": "object",
        "properties": {
          "message": {
            "type": "string",
            "description": "The message to echo"
          }
        },
        "required": ["message"]
      }
    }
  },
  "resources": {
    "last-echo": {
      "uri": "echo://last",
      "name": "Last Echo",
      "description": "The last echoed message",
      "mimeType": "text/plain"
    }
  },
  "prompts": {}
}
```

**File:** `reference_templates/mcps/configs/markdown.json`
```json
{
  "description": "Markdown to HTML converter",
  "tools": {
    "convert": {
      "description": "Convert markdown to HTML",
      "inputSchema": {
        "type": "object",
        "properties": {
          "markdown": {
            "type": "string",
            "description": "The markdown content to convert"
          }
        },
        "required": ["markdown"]
      }
    }
  },
  "resources": {},
  "prompts": {}
}
```

**File:** `reference_templates/mcps/configs/jq.json`
```json
{
  "description": "JQ JSON processor",
  "auto_discover": true,
  "tools_transform_cid": "reference_templates/mcps/transforms/jq_tools.py",
  "resources_transform_cid": "reference_templates/mcps/transforms/jq_resources.py"
}
```

**File:** `reference_templates/mcps/configs/date.json`
```json
{
  "description": "Date/time utilities",
  "auto_discover": true
}
```

### Configuration Options (within config JSON files)

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable description of the MCP server |
| `tools` | object | Static tool definitions (name -> tool config) |
| `resources` | object | Static resource definitions (name -> resource config) |
| `prompts` | object | Static prompt definitions (name -> prompt config) |
| `auto_discover` | boolean | If true, auto-discover tools from server functions |
| `tools_transform_cid` | string | CID of Python function to generate tools list dynamically |
| `resources_transform_cid` | string | CID of Python function to generate resources dynamically |
| `prompts_transform_cid` | string | CID of Python function to generate prompts dynamically |
| `enabled` | boolean | Whether this MCP configuration is active (default: true) |

### Configuration Resolution

The MCP server loads configuration as follows:

1. Load `mcps` variable from context
2. For each server, resolve `config_cid` to get the configuration JSON
3. If config contains nested CID references (e.g., `tools_transform_cid`), resolve those as well
4. Cache resolved configurations for the session

### Transform Function Interface

**Tools Transform:**
```python
def generate_tools(server_name: str, context: dict) -> list:
    """Generate MCP tools list for a server.

    Args:
        server_name: Name of the underlying server
        context: Full server execution context

    Returns:
        List of tool definitions, each containing:
            - name: Tool identifier
            - description: Tool description
            - inputSchema: JSON Schema for tool input
    """
```

**Resources Transform:**
```python
def generate_resources(server_name: str, context: dict) -> list:
    """Generate MCP resources list for a server.

    Args:
        server_name: Name of the underlying server
        context: Full server execution context

    Returns:
        List of resource definitions, each containing:
            - uri: Resource URI
            - name: Resource name
            - description: Resource description
            - mimeType: Content type
    """
```

---

## Server-to-MCP Mapping

### Automatic Tool Discovery

When `auto_discover: true`, the MCP server will:

1. **Python servers**: Introspect the server module for callable functions
   - Functions with docstrings become tool descriptions
   - Function parameters become tool input schema (using type hints if available)

2. **Shell servers**: Create a single tool matching the command name
   - Input schema: `{"command_args": {"type": "string"}}`

3. **Multi-function Python servers**: Each exported function becomes a separate tool
   - Route pattern: `def function_name(context=None)` -> tool `function_name`

### Tool Invocation Flow

```text
MCP Client                      MCP Server (/mcp/{server})                    Internal Server (/servers/{server})
    |                                    |                                              |
    |-- POST tools/call --------------->|                                              |
    |   {name: "echo", args: {...}}     |                                              |
    |                                    |-- Invoke server execution ----------------->|
    |                                    |   (via try_server_execution)                |
    |                                    |                                              |
    |                                    |<-- Server result ---------------------------|
    |                                    |                                              |
    |<-- tools/call result -------------|                                              |
    |   {content: [...], isError: false}|                                              |
```

### Resource Mapping

Resources represent data that can be read by the MCP client:

1. **CID-backed resources**: Any CID can be exposed as a resource
   - URI: `cid://{cid_value}`
   - Content fetched via `get_cid_content()`

2. **Server output resources**: Server invocation results can be cached and exposed
   - URI: `server://{server_name}/{path}`
   - Content fetched by invoking the server

3. **Variable resources**: Variables can be exposed as resources
   - URI: `variable://{variable_name}`
   - Content from `get_variable_by_name()`

---

## Implementation Phases

### Phase 1: Core Infrastructure

#### 1.1 Create mcps.source.json and Config Files

**File:** `reference_templates/mcps.source.json`

Maps server names to CIDs of their MCP configuration files:

```json
{
  "echo": {
    "config_cid": "reference_templates/mcps/configs/echo.json"
  },
  "markdown": {
    "config_cid": "reference_templates/mcps/configs/markdown.json"
  },
  "jq": {
    "config_cid": "reference_templates/mcps/configs/jq.json"
  },
  "date": {
    "config_cid": "reference_templates/mcps/configs/date.json"
  }
}
```

**Directory:** `reference_templates/mcps/configs/`

Create individual configuration files for each MCP-enabled server:

- `echo.json` - Echo server config with auto_discover
- `markdown.json` - Markdown server config with auto_discover
- `jq.json` - JQ server config with transform CIDs
- `date.json` - Date server config with auto_discover

See "Individual Server Configuration Files" section above for file contents.

#### 1.2 Update generate_boot_image.py

Add processing for `mcps.source.json`:
- Read `mcps.source.json`
- Process referenced files (transform functions)
- Generate `mcps.json` with CIDs
- Add `mcps` variable to boot configuration with `GENERATED:mcps.json` marker

**Changes to `generate_boot_json`:**
- Accept new parameter: `mcps_cid: Optional[str] = None`
- Handle `GENERATED:mcps.json` marker replacement

#### 1.3 Update Boot Source Files

**Files to update:**
- `reference_templates/default.boot.source.json`: Add mcp server and mcps variable
- `reference_templates/readonly.boot.source.json`: Add mcp server and mcps variable

Add to servers array:
```json
{
  "name": "mcp",
  "definition_cid": "reference_templates/servers/definitions/mcp.py",
  "enabled": true
}
```

Add to variables array:
```json
{
  "name": "mcps",
  "definition": "GENERATED:mcps.json",
  "enabled": true
}
```

#### 1.4 Create MCP Server Definition

**File:** `reference_templates/servers/definitions/mcp.py`

Core structure:
```python
def main(context=None):
    """MCP server main function.

    Routes:
        /mcp - Instruction page
        /mcp/meta/{server} - Server MCP metadata
        /mcp/{server} - MCP endpoint (POST for JSON-RPC, GET for info)
        /mcp/{server}/sse - SSE stream
    """
    request_path = flask_request.path
    # ... routing logic
```

### Phase 2: MCP Protocol Implementation

#### 2.1 JSON-RPC Message Handling

Implement JSON-RPC 2.0 message parsing and response generation:

```python
def _handle_jsonrpc_request(request_body: dict, server_name: str, context: dict) -> dict:
    """Handle a JSON-RPC request.

    Args:
        request_body: Parsed JSON-RPC request
        server_name: Target server name
        context: Execution context

    Returns:
        JSON-RPC response dict
    """
    method = request_body.get("method")
    params = request_body.get("params", {})
    request_id = request_body.get("id")

    if method == "initialize":
        return _handle_initialize(params, request_id)
    elif method == "tools/list":
        return _handle_tools_list(server_name, params, request_id, context)
    elif method == "tools/call":
        return _handle_tools_call(server_name, params, request_id, context)
    # ... etc
```

#### 2.2 Initialize Handler

```python
def _handle_initialize(params: dict, request_id: any) -> dict:
    """Handle MCP initialize request.

    Returns server capabilities and protocol version.
    """
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2025-11-25",
            "serverInfo": {
                "name": "Viewer MCP Server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False}
            }
        }
    }
```

#### 2.3 Tools List Handler

```python
def _handle_tools_list(server_name: str, params: dict, request_id: any, context: dict) -> dict:
    """Handle tools/list request.

    Returns list of available tools for the server.
    """
    mcps_config = _load_mcps(context)
    server_config = mcps_config.get(server_name, {})

    tools = []

    # Static tools from config
    if "tools" in server_config:
        for name, tool_config in server_config["tools"].items():
            tools.append({
                "name": name,
                "description": tool_config.get("description", ""),
                "inputSchema": tool_config.get("inputSchema", {"type": "object"})
            })

    # Auto-discovered tools
    if server_config.get("auto_discover", False):
        discovered = _discover_server_tools(server_name, context)
        tools.extend(discovered)

    # Dynamic tools from transform
    if "tools_transform_cid" in server_config:
        transform_fn = _load_transform_function(server_config["tools_transform_cid"], context)
        if transform_fn:
            dynamic_tools = transform_fn(server_name, context)
            tools.extend(dynamic_tools)

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"tools": tools}
    }
```

#### 2.4 Tools Call Handler

```python
def _handle_tools_call(server_name: str, params: dict, request_id: any, context: dict) -> dict:
    """Handle tools/call request.

    Invokes the specified tool and returns the result.
    """
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})

    try:
        # Construct the internal server path
        if tool_name == server_name:
            # Simple server call
            path = f"/{server_name}"
        else:
            # Function call
            path = f"/{server_name}/{tool_name}"

        # Add arguments as query string or body
        result = _execute_tool(path, tool_args, context)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": result}],
                "isError": False
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": str(e)}],
                "isError": True
            }
        }
```

### Phase 3: HTML UI Pages

#### 3.1 Create HTML Templates

**Directory:** `reference_templates/servers/templates/mcp/`

**Files:**
- `instruction.html` - Main MCP instruction page
- `meta.html` - Server MCP metadata page
- `error.html` - Error page template

#### 3.2 Instruction Page (/mcp)

Display:
- Overview of MCP functionality
- Link to MCP protocol documentation
- Link to `/variables/mcps` (MCP configurations)
- List of configured MCP servers with links to `/mcp/{server}`
- Links to meta pages for each server

#### 3.3 Meta Page (/mcp/meta/{server})

Display:
- Server description
- List of available tools with schemas
- List of available resources
- List of available prompts
- Connection test interface
- Example client code snippets

### Phase 4: Auto-Discovery Implementation

#### 4.1 Python Server Introspection

```python
def _discover_python_server_tools(server_name: str, server_definition: str, context: dict) -> list:
    """Discover tools from a Python server definition.

    Uses AST parsing to extract function signatures and docstrings.
    """
    import ast

    tree = ast.parse(server_definition)
    tools = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Skip private functions
            if node.name.startswith("_"):
                continue

            # Extract docstring
            docstring = ast.get_docstring(node) or ""

            # Build input schema from function arguments
            input_schema = _build_input_schema_from_function(node)

            tools.append({
                "name": node.name,
                "description": docstring.split("\n")[0],  # First line
                "inputSchema": input_schema
            })

    return tools
```

#### 4.2 Shell Server Introspection

```python
def _discover_shell_server_tools(server_name: str, server_definition: str) -> list:
    """Discover tools from a shell server definition.

    Shell servers are treated as single-tool servers.
    """
    return [{
        "name": server_name,
        "description": f"Execute {server_name} command",
        "inputSchema": {
            "type": "object",
            "properties": {
                "args": {
                    "type": "string",
                    "description": "Command arguments"
                }
            }
        }
    }]
```

### Phase 5: Streamable HTTP Transport (MCP 2025-11-25)

The Streamable HTTP transport uses a single endpoint that handles both requests and server-initiated messages.

#### 5.1 Request Handler (POST)

POST requests send JSON-RPC messages. The server responds with either JSON or a stream:

```python
def _handle_post_request(server_name: str, context: dict):
    """Handle POST request per MCP 2025-11-25 Streamable HTTP spec.

    - Client sends one JSON-RPC message per request
    - Server responds with JSON or opens a stream
    - Session managed via Mcp-Session-Id header
    """
    # Validate Accept header
    accept = request.headers.get("Accept", "")
    if "application/json" not in accept and "text/event-stream" not in accept:
        return {"error": "Must accept application/json or text/event-stream"}, 406

    # Parse JSON-RPC request
    body = request.get_json()
    method = body.get("method")
    request_id = body.get("id")

    # Get or create session
    session_id = request.headers.get("Mcp-Session-Id")
    if method == "initialize":
        session_id = _create_session()

    # Handle the request
    result = _dispatch_method(server_name, method, body.get("params", {}), request_id, context)

    # Return response with session header
    response = make_response(jsonify(result))
    response.headers["Mcp-Session-Id"] = session_id
    response.headers["Content-Type"] = "application/json"
    return response
```

#### 5.2 Streaming Response (POST with SSE response)

For long-running operations, respond with a stream of JSON-RPC messages:

```python
def _handle_streaming_post(server_name: str, request_id: any, context: dict):
    """Handle POST that returns a streaming response.

    Per MCP 2025-11-25 spec:
    - Response Content-Type: text/event-stream
    - Each SSE event contains one JSON-RPC message in data field
    - Server may send notifications before the final response
    """
    session_id = request.headers.get("Mcp-Session-Id")

    def generate():
        # Optional: send progress notifications
        progress = {"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 50}}
        yield f"event: message\ndata: {json.dumps(progress)}\n\n"

        # Send final response
        result = {"jsonrpc": "2.0", "id": request_id, "result": {"content": [...]}}
        yield f"event: message\ndata: {json.dumps(result)}\n\n"

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Mcp-Session-Id"] = session_id
    return response
```

#### 5.3 Listener Endpoint (GET)

GET requests open a stream for server-initiated messages:

```python
def _handle_get_listener(server_name: str, context: dict):
    """Handle GET request to listen for server-initiated messages.

    Per MCP 2025-11-25 spec:
    - Opens SSE stream for server notifications and requests
    - Supports resumability via Last-Event-ID header
    - Server assigns event IDs for resumption
    """
    session_id = request.headers.get("Mcp-Session-Id")
    if not session_id:
        return {"error": "Mcp-Session-Id required"}, 400

    last_event_id = request.headers.get("Last-Event-ID")

    def generate():
        event_id = int(last_event_id) if last_event_id else 0

        while True:
            # Check for pending messages for this session
            pending = _get_pending_messages(session_id, after_id=event_id)
            for msg in pending:
                event_id += 1
                yield f"id: {event_id}\nevent: message\ndata: {json.dumps(msg)}\n\n"

            # Keep-alive comment (not an event)
            yield ": keepalive\n\n"
            time.sleep(15)

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["Mcp-Session-Id"] = session_id
    return response
```

#### 5.4 Session Management

```python
def _create_session() -> str:
    """Create a new MCP session."""
    import uuid
    return str(uuid.uuid4())

def _validate_session(session_id: str) -> bool:
    """Validate session exists and is active."""
    # For stateless implementation, always return True
    # For stateful, check session store
    return True

def _terminate_session(session_id: str):
    """Terminate a session (called on client disconnect or explicit close)."""
    pass
```

#### 5.5 Response Content Negotiation

```python
def _should_stream_response(request, method: str) -> bool:
    """Determine if response should be streamed.

    Per MCP 2025-11-25 spec:
    - Client indicates preference via Accept header
    - Server decides based on operation characteristics
    """
    accept = request.headers.get("Accept", "")
    if "text/event-stream" not in accept:
        return False

    # Stream for potentially long-running operations
    long_running_methods = {"tools/call", "resources/read"}
    return method in long_running_methods
```

---

## Test Plan

### Unit Tests

#### Configuration Loading Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T1.1 | Load empty mcps config | Call `_load_mcps()` with empty `mcps` variable | Returns empty dict `{}` |
| T1.2 | Load valid mcps config | Call `_load_mcps()` with valid JSON config | Returns parsed config dict |
| T1.3 | Load mcps from CID | Call `_load_mcps()` with CID-referenced mcps variable | Resolves CID and returns config |
| T1.4 | Handle invalid JSON | Call `_load_mcps()` with malformed JSON | Returns empty dict, logs warning |
| T1.5 | Handle missing server | Access config for non-existent server | Returns empty dict for that server |
| T1.6 | Resolve server config_cid | Load server with `config_cid` reference | Resolves CID to get server config JSON |
| T1.7 | Resolve nested CIDs | Config contains `tools_transform_cid` | Nested CID resolved correctly |
| T1.8 | Handle missing config_cid | Server entry has invalid `config_cid` | Returns error, server not available |
| T1.9 | Cache resolved configs | Load same config twice | Second load uses cached value |

#### JSON-RPC Message Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T2.1 | Parse valid request | Parse `{"jsonrpc":"2.0","id":1,"method":"initialize"}` | Returns parsed request dict |
| T2.2 | Reject invalid jsonrpc version | Parse `{"jsonrpc":"1.0","id":1,"method":"test"}` | Returns JSON-RPC error -32600 |
| T2.3 | Handle missing method | Parse `{"jsonrpc":"2.0","id":1}` | Returns JSON-RPC error -32600 |
| T2.4 | Handle notification (no id) | Parse `{"jsonrpc":"2.0","method":"test"}` | Process without response |
| T2.5 | Handle batch request | Parse array of requests | Returns array of responses |

#### Initialize Handler Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T3.1 | Initialize with valid params | Send initialize with client info | Returns server info and capabilities |
| T3.2 | Initialize with protocol version | Send with protocolVersion param | Returns matching or compatible version |
| T3.3 | Initialize returns capabilities | Check response structure | Contains tools, resources, prompts capabilities |
| T3.4 | Second initialize same session | Send initialize twice | Returns same session state |

#### Tools List Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T4.1 | List tools for configured server | Call tools/list for "echo" server | Returns tools defined in config |
| T4.2 | List tools with auto_discover | Call for server with auto_discover:true | Returns discovered tools |
| T4.3 | List tools for unconfigured server | Call for server not in mcps config | Returns empty tools list or error |
| T4.4 | List tools with transform | Call for server with tools_transform_cid | Returns dynamically generated tools |
| T4.5 | List tools pagination | Call with cursor param | Returns paginated results |
| T4.6 | Tool schema validation | Check returned inputSchema | Valid JSON Schema objects |

#### Tools Call Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T5.1 | Call simple tool | Call echo tool with message | Returns echoed message |
| T5.2 | Call tool with required args | Call tool missing required arg | Returns isError: true |
| T5.3 | Call tool with optional args | Call tool with only required args | Succeeds with defaults |
| T5.4 | Call non-existent tool | Call undefined tool name | Returns isError: true |
| T5.5 | Call tool that throws error | Call tool that raises exception | Returns isError: true with message |
| T5.6 | Call tool on disabled server | Call tool for disabled server | Returns appropriate error |
| T5.7 | Tool returns text content | Check content type in result | Contains type: "text" |
| T5.8 | Tool returns binary content | Server returns bytes | Content is base64 encoded |

#### Resources Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T6.1 | List resources | Call resources/list | Returns configured resources |
| T6.2 | Read text resource | Call resources/read for text resource | Returns text content |
| T6.3 | Read binary resource | Call resources/read for binary resource | Returns base64 blob |
| T6.4 | Read CID resource | Read resource backed by CID | Fetches from CID storage |
| T6.5 | Read non-existent resource | Call resources/read for missing URI | Returns error |
| T6.6 | Resource URI validation | Check URI format in responses | Valid URI per RFC 3986 |

#### Prompts Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T7.1 | List prompts | Call prompts/list | Returns configured prompts |
| T7.2 | Get prompt without args | Call prompts/get for simple prompt | Returns prompt messages |
| T7.3 | Get prompt with args | Call prompts/get with arguments | Returns templated messages |
| T7.4 | Get non-existent prompt | Call prompts/get for missing prompt | Returns error |
| T7.5 | Prompt argument validation | Call with invalid argument type | Returns validation error |

### Integration Tests

#### End-to-End MCP Flow Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T8.1 | Full MCP session | Initialize -> list tools -> call tool | Complete successful flow |
| T8.2 | Echo server via MCP | Initialize and call echo tool | Returns echoed message |
| T8.3 | Markdown server via MCP | Convert markdown via MCP | Returns HTML output |
| T8.4 | JQ server via MCP | Execute JQ query via MCP | Returns query result |
| T8.5 | Date server via MCP | Get date via MCP | Returns formatted date |

#### HTTP Transport Tests (Streamable HTTP 2025-11-25)

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T9.1 | POST to MCP endpoint | POST JSON-RPC to /mcp/{server} | Returns JSON-RPC response with Mcp-Session-Id |
| T9.2 | GET listener endpoint | GET /mcp/{server} with Mcp-Session-Id | Returns SSE stream for notifications |
| T9.3 | Accept header validation | POST with Accept: application/json, text/event-stream | Server accepts request |
| T9.4 | Streaming response | POST long-running operation | Returns text/event-stream with SSE events |
| T9.5 | JSON response | POST simple operation | Returns application/json response |
| T9.6 | Session ID on initialize | POST initialize request | Response includes new Mcp-Session-Id |
| T9.7 | Session ID required for GET | GET without Mcp-Session-Id | Returns 400 error |
| T9.8 | Last-Event-ID resumability | GET with Last-Event-ID header | Resumes from specified event |
| T9.9 | CORS headers | Check CORS headers in response | Appropriate CORS headers set |
| T9.10 | Content-Type validation | POST with wrong Content-Type | Returns 415 error |
| T9.11 | Accept header required | POST without Accept header | Returns 406 error |

#### Boot Image Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T10.1 | Generate mcps.json | Run generate_boot_image.py | mcps.json created with CIDs |
| T10.2 | Boot with mcps variable | Start with generated boot image | mcps variable accessible |
| T10.3 | MCP server in default boot | Check default.boot.json | mcp server listed |
| T10.4 | MCP server in readonly boot | Check readonly.boot.json | mcp server listed |
| T10.5 | Transform CID resolution | Load server with transform CID | Transform functions load correctly |

#### Auto-Discovery Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T11.1 | Discover Python server tools | Auto-discover for Python server | Returns function-based tools |
| T11.2 | Discover shell server tools | Auto-discover for shell server | Returns single command tool |
| T11.3 | Discover multi-function server | Auto-discover for server with routes | Returns all public functions |
| T11.4 | Skip private functions | Auto-discover excludes `_private` | No tools for private functions |
| T11.5 | Extract docstrings | Check tool descriptions | Match function docstrings |
| T11.6 | Build input schema | Check generated inputSchema | Matches function parameters |

### Error Handling Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T12.1 | Invalid JSON body | POST malformed JSON | Returns parse error -32700 |
| T12.2 | Unknown method | Call undefined MCP method | Returns method not found -32601 |
| T12.3 | Invalid params | Call with wrong param types | Returns invalid params -32602 |
| T12.4 | Internal server error | Server throws unhandled exception | Returns internal error -32603 |
| T12.5 | Server timeout | Server execution times out | Returns error with timeout message |
| T12.6 | Server not found | MCP endpoint for non-existent server | Returns 404 or appropriate error |

### Edge Case Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T13.1 | Empty tool arguments | Call tool with `{}` arguments | Handles gracefully |
| T13.2 | Large tool output | Tool returns very large output | Chunked or truncated appropriately |
| T13.3 | Unicode in arguments | Tool arguments contain unicode | Handled correctly |
| T13.4 | Concurrent requests | Multiple simultaneous MCP calls | All complete correctly |
| T13.5 | Nested JSON arguments | Complex nested object in args | Parsed and passed correctly |
| T13.6 | Array tool arguments | Tool takes array parameter | Array passed correctly |
| T13.7 | Null values in arguments | Arguments contain null values | Handled per JSON-RPC spec |
| T13.8 | Server returns redirect | Internal server returns redirect | Followed or exposed as resource |

### Security Tests

| ID | Test | Description | Expected Result |
|----|------|-------------|-----------------|
| T14.1 | Path traversal attempt | Server name with `../` | Rejected, no path traversal |
| T14.2 | Script injection in args | Arguments contain `<script>` | Sanitized in HTML responses |
| T14.3 | Unauthorized server access | Access disabled server via MCP | Rejected appropriately |
| T14.4 | Origin header validation | Request without valid Origin | Handled per CORS policy |
| T14.5 | Session hijacking attempt | Invalid session ID | Rejected or new session |

---

## Open Questions

### Protocol Questions

1. **Q: Which MCP protocol version should we target?**
   - Options: 2024-11-05 (original) or 2025-11-25 (latest with streamable HTTP)
   - Recommendation: 2025-11-25 for streamable HTTP support
   - Status: RESOLVED - Use 2025-11-25 (Streamable HTTP)

2. **Q: Should we support both stdio and HTTP transports?**
   - Consideration: stdio requires subprocess management
   - Recommendation: Streamable HTTP only for initial implementation (we're a web server)
   - Status: RESOLVED - Streamable HTTP (2025-11-25) only for initial implementation

3. **Q: How should we handle MCP session management?**
   - Option A: Stateless (re-initialize on each request)
   - Option B: Stateful with session storage
   - Recommendation: Stateless for simplicity, session ID is advisory only
   - Status: RESOLVED - Stateless with advisory session ID

### Configuration Questions

4. **Q: Should `mcps` configuration be optional for servers?**
   - If unconfigured, should the MCP endpoint still work with auto-discovery?
   - Recommendation: Yes, auto-discover by default if server not in mcps config
   - Status: RESOLVED - Auto-discover enabled by default

5. **Q: How should we handle servers that don't map well to MCP?**
   - Example: Streaming servers, websocket-based servers
   - Recommendation: Exclude from auto-discovery, require explicit config
   - Status: RESOLVED - Explicit opt-out via `mcp_enabled: false`

6. **Q: Should prompts be auto-generated or always explicit?**
   - Auto-generation is more complex than tools/resources
   - Recommendation: Prompts always explicit in config
   - Status: RESOLVED - Prompts are always explicit

### Implementation Questions

7. **Q: How should tool invocation map to server path and method?**
   - Tool name "foo" on server "bar" -> `/bar/foo` or `/bar?function=foo`?
   - Recommendation: Use path-based routing `/bar/foo` for multi-function servers
   - Status: RESOLVED - Path-based routing

8. **Q: How should we handle server functions that require POST vs GET?**
   - MCP tools/call always uses POST to MCP endpoint
   - Internal server invocation may need different methods
   - Recommendation: Use context to infer, default to POST for tools with args
   - Status: RESOLVED - Infer from arguments presence

9. **Q: Should resources be lazily evaluated or cached?**
   - Lazy: Fetch content on each resources/read
   - Cached: Pre-fetch and store
   - Recommendation: Lazy evaluation, let client cache if needed
   - Status: RESOLVED - Lazy evaluation

10. **Q: How should we expose server errors in MCP responses?**
    - Option A: Always wrap in isError: true
    - Option B: Map to JSON-RPC error codes
    - Recommendation: Use isError: true for tool errors, JSON-RPC errors for protocol issues
    - Status: RESOLVED - isError for tool errors, -32xxx for protocol errors

### Future Considerations

11. **Q: Should we support resource subscriptions in a future version?**
    - Current: `subscribe: false` in capabilities
    - Future: Enable for real-time updates
    - Status: DEFERRED - Not in initial implementation

12. **Q: Should we support tool annotations (output schemas)?**
    - MCP allows optional outputSchema for tools
    - Recommendation: Support but don't require
    - Status: DEFERRED - Support if explicitly configured

13. **Q: How should we handle large file resources?**
    - Streaming? Chunking? Size limits?
    - Recommendation: Set reasonable size limits, return error for oversized
    - Status: DEFERRED - Define limits during implementation

---

## File Manifest

### New Files to Create

| File | Purpose |
|------|---------|
| `reference_templates/servers/definitions/mcp.py` | Main MCP server implementation |
| `reference_templates/servers/templates/mcp.json` | Server template metadata |
| `reference_templates/servers/templates/mcp/instruction.html` | Instruction page |
| `reference_templates/servers/templates/mcp/meta.html` | Server meta page |
| `reference_templates/servers/templates/mcp/error.html` | Error page |
| `reference_templates/mcps.source.json` | MCP configurations source (server name -> config_cid) |
| `reference_templates/mcps/configs/echo.json` | MCP config for echo server |
| `reference_templates/mcps/configs/markdown.json` | MCP config for markdown server |
| `reference_templates/mcps/configs/jq.json` | MCP config for jq server |
| `reference_templates/mcps/configs/date.json` | MCP config for date server |
| `reference_templates/mcps/transforms/` | Directory for transform functions |

### Files to Modify

| File | Changes |
|------|---------|
| `generate_boot_image.py` | Add `generate_mcps_json()` method, update `generate_boot_json()` |
| `reference_templates/default.boot.source.json` | Add mcp server and mcps variable |
| `reference_templates/readonly.boot.source.json` | Add mcp server and mcps variable |

---

## Implementation Checklist

- [ ] Phase 1: Core Infrastructure
  - [ ] Create `mcps.source.json` (server name -> config_cid mapping)
  - [ ] Create `reference_templates/mcps/configs/` directory
  - [ ] Create individual config files (echo.json, markdown.json, jq.json, date.json)
  - [ ] Update `generate_boot_image.py`
  - [ ] Update boot source files
  - [ ] Create `mcp.py` skeleton

- [ ] Phase 2: MCP Protocol Implementation
  - [ ] JSON-RPC message handling
  - [ ] Initialize handler
  - [ ] Tools list handler
  - [ ] Tools call handler
  - [ ] Resources handlers
  - [ ] Prompts handlers

- [ ] Phase 3: HTML UI Pages
  - [ ] Create HTML templates
  - [ ] Instruction page
  - [ ] Meta page

- [ ] Phase 4: Auto-Discovery
  - [ ] Python server introspection
  - [ ] Shell server introspection
  - [ ] Input schema generation

- [ ] Phase 5: Streamable HTTP Transport (MCP 2025-11-25)
  - [ ] POST request handler with session management
  - [ ] Streaming POST response handler
  - [ ] GET listener endpoint with resumability
  - [ ] Session management (create, validate, terminate)
  - [ ] Response content negotiation

- [ ] Testing
  - [ ] Unit tests
  - [ ] Integration tests
  - [ ] Edge case tests
  - [ ] Security tests

---

## Dependencies

- Flask (existing) - HTTP routing
- JSON standard library - JSON-RPC parsing
- AST standard library - Python introspection
- Existing infrastructure:
  - `server_execution.try_server_execution()` - Server invocation
  - `NamedValueResolver` - Variable resolution
  - CID storage system - Content retrieval
  - Template loading from gateway server

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2024-12-30 | 0.1 | Initial plan document |
