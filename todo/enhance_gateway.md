# Gateway Enhancement Plan

## Overview

This plan describes a comprehensive enhancement to the gateway server to make it more flexible, user-friendly, and extensible. The key changes are:

1. **Variable-driven configuration**: All server-specific transformations are defined via the `gateways` variable, not in `gateway.py`
2. **New instructional routes**: `/gateway`, `/gateway/request`, `/gateway/response`, `/gateway/meta/{server}`
3. **Clean URL routing**: `/gateway/{server}` and `/gateway/{server}/{rest}` for issuing transformed requests
4. **External HTML templates**: Move all HTML from `gateway.py` into separate template files
5. **AI-assisted forms**: Add AI assist functionality to request/response experimentation forms
6. **Example implementations**: jsonplaceholder, man, tldr, and hrx gateway configurations

---

## Architecture

### URL Structure

| Route | Purpose |
|-------|---------|
| `/gateway` | Instruction page with links to `/servers/gateway` and `/variables/gateways` |
| `/gateway/request` | Form for experimenting with request transformations |
| `/gateway/response` | Form for experimenting with response transformations |
| `/gateway/meta/{server}` | Display server definition, request transform, and response transform source with validation |
| `/gateway/{server}` | Issue transformed request to server root |
| `/gateway/{server}/{rest}` | Issue transformed request to server with path |

### Gateways Variable Format

The `gateways` variable is a JSON map from server names to transform function pairs:

```json
{
  "jsonplaceholder": {
    "target_url": "https://jsonplaceholder.typicode.com",
    "request_transform_cid": "<CID of request transform function>",
    "response_transform_cid": "<CID of response transform function>",
    "description": "JSONPlaceholder fake REST API"
  },
  "man": {
    "target_url": "/servers/man",
    "request_transform_cid": "<CID>",
    "response_transform_cid": "<CID>",
    "description": "HTML man pages"
  },
  "tldr": {
    "target_url": "/servers/tldr",
    "request_transform_cid": "<CID>",
    "response_transform_cid": "<CID>",
    "description": "HTML tldr pages"
  },
  "hrx": {
    "target_url": "/servers/hrx",
    "request_transform_cid": "<CID>",
    "response_transform_cid": "<CID>",
    "description": "HRX archive web viewer"
  }
}
```

### Transform Function Interface

Transform functions execute in the full server execution context, with access to all standard server capabilities.

**Request Transform:**
```python
def transform_request(request_details: dict, context: dict) -> dict:
    """Transform incoming request for target server.

    Args:
        request_details: Dict containing:
            - path: The path after /gateway/{server}/
            - query_string: Original query string
            - method: HTTP method
            - headers: Request headers (dict, excludes cookies)
            - json: Request body parsed as JSON (None if not valid JSON or no body)
            - body: Raw request body as text (None if no body)
        context: Full server execution context (same as other servers)
            - Can invoke other servers
            - Can access secrets
            - Has all standard server capabilities

    Returns:
        Dict containing:
            - url: Target URL to request
            - method: HTTP method to use
            - headers: Headers to send
            - json: JSON body to send (if any)
            - data: Raw body to send as string (if any, alternative to json)
            - params: Query parameters dict (if any)
    """
```

**Response Transform:**
```python
def transform_response(response_details: dict, context: dict) -> dict:
    """Transform response from target server for user.

    Args:
        response_details: Dict containing:
            - status_code: HTTP status code
            - headers: Response headers (dict)
            - content: Raw response content (bytes)
            - text: Response as text (if decodable)
            - json: Parsed JSON (if applicable, None otherwise)
            - request_path: Original request path after /gateway/{server}/
        context: Full server execution context (same as other servers)
            - Can invoke other servers
            - Can access secrets
            - Has all standard server capabilities

    Returns:
        Dict containing:
            - output: Content to return to user (str or bytes)
            - content_type: Content type for response
    """
```

---

## Implementation Phases

### Phase 1: Core Infrastructure

#### 1.1 Create gateways.source.json

**File:** `reference_templates/gateways.source.json`

Parallel to `templates.source.json`, this file defines the gateway configurations with file references that get converted to CIDs during boot image generation.

#### 1.2 Update generate_boot_image.py

Add processing for `gateways.source.json` similar to how `templates.source.json` is processed:
- Read `gateways.source.json`
- Process referenced files (transform functions)
- Generate `gateways.json` with CIDs
- Add `gateways` variable to boot configuration with `GENERATED:gateways.json` marker

#### 1.3 Create External HTML Templates

**Files to create:**
- `reference_templates/servers/templates/gateway/instruction.html` - Main instruction page
- `reference_templates/servers/templates/gateway/request_form.html` - Request experimentation form
- `reference_templates/servers/templates/gateway/response_form.html` - Response experimentation form
- `reference_templates/servers/templates/gateway/meta.html` - Server meta page
- `reference_templates/servers/templates/gateway/error.html` - Error page template
- `reference_templates/servers/templates/gateway/json_response.html` - JSON response formatting

#### 1.4 Refactor gateway.py

- Remove all inline HTML
- Remove server-specific logic (examples list, etc.)
- Use NamedValueResolver to get `gateways` variable
- Load and render external HTML templates
- Implement transform function execution via CID lookup

### Phase 2: Instructional Pages

#### 2.1 Main Instruction Page (/gateway)

Display:
- Overview of gateway functionality
- Link to `/servers/gateway` (server definition)
- Link to `/variables/gateways` (gateway configurations)
- List of configured gateways with links to `/gateway/{server}`
- Links to `/gateway/request` and `/gateway/response` experimentation pages

#### 2.2 Request Experimentation Page (/gateway/request)

Features:
- Server selection dropdown (populated from gateways variable)
- Request path input
- Request method selector
- Headers editor (key-value pairs)
- Body editor (textarea)
- Preview of transformed request
- Temporary request transform function override (editable code area)
- Server invocation CID input to load previous request
- AI assist form integration
- "Execute" button to actually send the request

#### 2.3 Response Experimentation Page (/gateway/response)

Features:
- Server selection dropdown
- Response input area (simulate a response)
- Response headers editor
- Response status code selector
- Preview of transformed response
- Temporary response transform function override
- Server invocation CID input to load previous response
- AI assist form integration
- "Transform" button to see the result

#### 2.4 Meta Page (/gateway/meta/{server})

Display:
- Link to `/servers/{server}` definition
- Request transform source code (loaded from CID)
- Request transform validation status (syntax check)
- Response transform source code (loaded from CID)
- Response transform validation status (syntax check)
- Server configuration summary
- Test links

### Phase 3: Gateway Request Handling

#### 3.1 Route Parsing

For `/gateway/{server}/{rest}`:
1. Extract `server` from URL
2. Look up server in `gateways` variable
3. Extract `rest` as the remaining path
4. If server not found, return 404 with helpful message

#### 3.2 Request Transformation

1. Load request transform function from CID
2. Build request_details dict from incoming request
3. Execute transform function
4. Handle transform errors gracefully

#### 3.3 Target Server Request

1. Use transformed request details to make HTTP request
2. Handle connection errors, timeouts
3. Capture full response including headers

#### 3.4 Response Transformation

1. Load response transform function from CID
2. Build response_details dict from server response
3. Execute transform function
4. Return transformed output with content type

### Phase 4: Example Gateway Configurations

#### 4.1 JSONPlaceholder Gateway

**Server:** jsonplaceholder
**Target:** https://jsonplaceholder.typicode.com

**Request Transform:**
- Pass through path directly
- Add appropriate headers

**Response Transform:**
- Parse JSON response
- Format as colored/highlighted JSON
- Convert `userId` values to links: `/gateway/jsonplaceholder/users/{userId}`
- Add navigation breadcrumbs
- Style with dark theme (matching current gateway output)

#### 4.2 Man Page Gateway

**Server:** man
**Target:** /servers/man (internal)

**Request Transform:**
- Extract command from path
- Build request to /servers/man?command={command}

**Response Transform:**
- Parse man page output (groff/roff format or plain text)
- Convert to formatted HTML
- Detect command references (patterns like `command(1)`)
- Convert references to links: `/gateway/man/{referenced-command}`
- Add navigation and styling

#### 4.3 TLDR Gateway

**Server:** tldr
**Target:** /servers/tldr (internal)

**Request Transform:**
- Extract command from path
- Build request to /servers/tldr?command={command}

**Response Transform:**
- Parse tldr output (markdown-like format)
- Convert to styled HTML
- Detect command references
- Convert references to links: `/gateway/tldr/{referenced-command}`
- Highlight examples and descriptions

#### 4.4 HRX Archive Gateway

**Server:** hrx
**Target:** /servers/hrx (internal)

**Request Transform:**
- Parse path as `{CID}/{file_path}`
- Build request to /servers/hrx with archive CID and path

**Response Transform:**
- If HTML file: Fix relative URLs to point to `/gateway/hrx/{CID}/{relative_path}`
- If Markdown file: Render as HTML, fix relative links
- Add navigation showing archive contents
- Preserve styling and structure

### Phase 5: AI Assist Integration

#### 5.1 Update AI Assist Tests

Add test examples for:
- Gateway request form context
- Gateway response form context
- Transform function editing context

#### 5.2 Add AI Helpers to Forms

For `/gateway/request`:
- AI assist for request transform function editing
- Context: "gateway request transform", "Python function"
- Examples: "Add a custom header", "Modify the path format"

For `/gateway/response`:
- AI assist for response transform function editing
- Context: "gateway response transform", "Python function"
- Examples: "Add syntax highlighting", "Convert links to gateway links"

---

## Design Decisions (Resolved)

1. **Transform function execution environment**: Full context. Transform functions have access to the full server execution context, same as any other server.

2. **Error handling strategy**: Use general server debugging. Any debugging enhancements needed should be made to enhance debugging for all servers, not gateway-specific. Transform errors use the standard server error handling mechanisms.

3. **CID resolution for transforms**: Resolved at request time. Transform CIDs can be specified in the request (e.g., override via form), so they cannot be pre-resolved. CID resolution failures return 404 errors.

4. **Authentication forwarding**: Auth is up to the specified server, not the gateway. The gateway passes through the request; the target server or its transform functions handle authentication.

5. **Request body handling**: JSON. Request body is parsed as JSON before being passed to the transform function.

6. **Response caching**: No additional caching. Gateway does not add any caching layer.

7. **Form state persistence**: Form overrides are temporary. The form provides a mechanism for overriding the transform relative to that specific request only. Users can copy and paste the modified transform into the corresponding variable position if they want to persist changes.

8. **Server invocation CID lookup**: Full population from invocation data.
   - For `/gateway/request`: Load and populate all request data from the invocation
   - For `/gateway/response`: Load and populate all response data from the invocation
   - Error handling:
     - CID not found → Display error message
     - Referenced CIDs not found → Display error message
     - Not a server invocation CID → Display error message

9. **Validation depth**: Maximum ahead-of-time validation. The meta page should do as much validation as possible: syntax checking, type hints if available, and any static analysis that can be performed without execution.

10. **Template loading mechanism**: Jinja2. Use the existing Jinja2 template system for consistency with the rest of the application.

11. **Transform access to other servers and secrets**: Yes to both. Transform functions can invoke other servers directly (e.g., for chained transformations) and can access secrets directly. This follows from having full server execution context.

12. **Request body handling (detailed)**: Always transform the original request into a JSON object. The `request_details` dict passed to the transform function is a complete JSON representation of the request:
    - If body is valid JSON: `json` field contains parsed JSON, `body` field contains raw text
    - If body is not valid JSON: `json` field is `None`, `body` field contains raw text
    - If no body: both `json` and `body` are `None`

13. **Invocation source validation**: Allow populating forms from any server invocation. The form should indicate whether the server used in the invocation currently has a defined gateway in `/variables/gateways`. This allows users to experiment with transforms for servers that may not yet have gateway configurations.

---

## Open Questions

None - all questions have been resolved.

---

## Test Plan

### Unit Tests

#### Core Gateway Logic Tests

```
test_gateway_resolves_gateways_variable
    - Verify gateway.py uses NamedValueResolver to get gateways variable
    - Test with valid gateways JSON
    - Test with missing gateways variable (graceful fallback)
    - Test with malformed gateways JSON

test_gateway_extracts_server_from_path
    - /gateway/jsonplaceholder -> server="jsonplaceholder", rest=""
    - /gateway/jsonplaceholder/posts -> server="jsonplaceholder", rest="posts"
    - /gateway/jsonplaceholder/posts/1 -> server="jsonplaceholder", rest="posts/1"
    - /gateway -> no server (instruction page)
    - /gateway/ -> no server (instruction page)

test_gateway_validates_server_exists
    - Known server -> proceeds with request
    - Unknown server -> 404 with list of available servers
    - Empty gateways variable -> 404 with helpful message

test_gateway_loads_transform_from_cid
    - Valid CID -> returns transform function
    - Invalid CID -> graceful error
    - Missing CID -> uses identity transform
    - CID with syntax error -> reports error with line number
```

#### Request Transform Tests

```
test_request_transform_receives_correct_details
    - path is extracted correctly
    - query_string is included
    - method is captured
    - headers are passed (without cookie)
    - json field contains parsed JSON when body is valid JSON
    - json field is None when body is not valid JSON
    - json field is None when no body present
    - body field contains raw text when body present
    - body field is None when no body present
    - context parameter contains full server execution context

test_request_transform_context_capabilities
    - Transform can invoke other servers via context
    - Transform can access secrets via context
    - Transform has standard server capabilities

test_request_transform_modifies_request
    - Can change target URL
    - Can modify headers
    - Can alter body
    - Can change method
    - Can add query parameters

test_request_transform_error_handling
    - Transform raises exception -> shows error page
    - Transform returns invalid format -> shows error page
    - Transform times out -> shows timeout error
```

#### Response Transform Tests

```
test_response_transform_receives_correct_details
    - status_code is included
    - headers are passed
    - content (bytes) is included
    - text version is included
    - json is parsed if applicable
    - original request_path is included
    - context parameter contains full server execution context

test_response_transform_context_capabilities
    - Transform can invoke other servers via context
    - Transform can access secrets via context
    - Transform has standard server capabilities

test_response_transform_modifies_response
    - Can change output content
    - Can change content_type
    - Can convert JSON to HTML
    - Can add navigation/styling

test_response_transform_error_handling
    - Transform raises exception -> shows raw response with error notice
    - Transform returns invalid format -> shows error with raw response
```

### Route Tests

```
test_gateway_instruction_page
    - GET /gateway returns HTML instruction page
    - Page contains link to /servers/gateway
    - Page contains link to /variables/gateways
    - Page lists configured gateways
    - Page links to /gateway/request and /gateway/response

test_gateway_request_form
    - GET /gateway/request returns form page
    - Form has server selection dropdown
    - Form has request path input
    - Form has method selector
    - Form has headers editor
    - Form has body editor
    - Form has transform function editor
    - Form has AI assist controls
    - Form has CID input field
    - POST with CID populates form from invocation

test_gateway_response_form
    - GET /gateway/response returns form page
    - Form has server selection dropdown
    - Form has response input area
    - Form has status code selector
    - Form has headers editor
    - Form has transform function editor
    - Form has AI assist controls
    - Form has CID input field
    - POST with CID populates form from invocation

test_gateway_request_form_cid_loading
    - Valid invocation CID populates all request fields
    - CID not found -> displays error message
    - CID found but referenced request_details_cid missing -> displays error message
    - CID is not a server invocation -> displays error message
    - Invocation from non-gateway server -> populates form, shows indicator
    - Indicator shows "gateway defined" if server has gateway in /variables/gateways
    - Indicator shows "no gateway defined" if server lacks gateway configuration

test_gateway_response_form_cid_loading
    - Valid invocation CID populates all response fields
    - CID not found -> displays error message
    - CID found but referenced result_cid missing -> displays error message
    - CID is not a server invocation -> displays error message
    - Invocation from non-gateway server -> populates form, shows indicator
    - Indicator shows "gateway defined" if server has gateway in /variables/gateways
    - Indicator shows "no gateway defined" if server lacks gateway configuration

test_gateway_meta_page
    - GET /gateway/meta/jsonplaceholder returns meta page
    - Page links to /servers/jsonplaceholder (if exists)
    - Page shows request transform source
    - Page shows response transform source
    - Page indicates validation status
    - GET /gateway/meta/unknown returns 404

test_gateway_meta_page_validation
    - Valid transform -> shows "valid" status with green indicator
    - Syntax error in transform -> shows error with line number
    - Missing required function -> shows "missing transform_request/transform_response"
    - Wrong function signature -> shows signature mismatch warning
    - Type hint violations (if analyzable) -> shows type warnings
    - CID not found -> shows "transform not found" error
    - All validations shown for both request and response transforms

test_gateway_server_route
    - GET /gateway/jsonplaceholder makes request to JSONPlaceholder
    - GET /gateway/jsonplaceholder/posts makes request to /posts
    - GET /gateway/jsonplaceholder/posts/1 makes request to /posts/1
    - Response is transformed correctly
    - Error responses are handled gracefully
```

### JSONPlaceholder Integration Tests

```
test_jsonplaceholder_posts_endpoint
    - GET /gateway/jsonplaceholder/posts returns posts list
    - Response is formatted as colored JSON
    - userId values are links to /gateway/jsonplaceholder/users/{id}

test_jsonplaceholder_users_endpoint
    - GET /gateway/jsonplaceholder/users returns users list
    - GET /gateway/jsonplaceholder/users/1 returns single user
    - Response is formatted correctly

test_jsonplaceholder_comments_endpoint
    - GET /gateway/jsonplaceholder/comments returns comments
    - Response shows formatted JSON

test_jsonplaceholder_navigation
    - Links in response point to correct gateway URLs
    - Can navigate between posts and users via links
```

### Man Page Gateway Tests

```
test_man_gateway_basic
    - GET /gateway/man/ls returns formatted man page
    - HTML is properly structured
    - Page includes navigation

test_man_gateway_command_links
    - References like "see also: cat(1)" become links
    - Links point to /gateway/man/cat
    - Multiple references are all converted

test_man_gateway_unknown_command
    - GET /gateway/man/nonexistent shows error
    - Error includes helpful message

test_man_gateway_special_characters
    - Commands with special chars are handled
    - Output is properly escaped
```

### TLDR Gateway Tests

```
test_tldr_gateway_basic
    - GET /gateway/tldr/ls returns formatted tldr page
    - Examples are highlighted
    - Description is styled

test_tldr_gateway_command_links
    - Command references become links
    - Links point to /gateway/tldr/{command}

test_tldr_gateway_unknown_command
    - GET /gateway/tldr/nonexistent shows error
    - Error includes fallback suggestions
```

### HRX Gateway Tests

```
test_hrx_gateway_lists_files
    - GET /gateway/hrx/{CID} lists archive contents
    - Each file is a link to view it

test_hrx_gateway_serves_html
    - GET /gateway/hrx/{CID}/index.html returns HTML
    - Relative links are rewritten to /gateway/hrx/{CID}/...
    - CSS/JS references are fixed

test_hrx_gateway_serves_markdown
    - GET /gateway/hrx/{CID}/README.md returns rendered HTML
    - Markdown is converted to HTML
    - Relative links are fixed

test_hrx_gateway_relative_link_fixing
    - href="other.html" -> href="/gateway/hrx/{CID}/other.html"
    - src="image.png" -> src="/gateway/hrx/{CID}/image.png"
    - Absolute URLs are not modified
    - Protocol-relative URLs are not modified

test_hrx_gateway_directory_navigation
    - GET /gateway/hrx/{CID}/subdir/ shows directory contents
    - Breadcrumb navigation works
    - Parent directory links work
```

### AI Assist Integration Tests

```
test_ai_assist_request_form_context
    - AI assist receives correct context for request form
    - Context includes "gateway request transform"
    - Response modifies the transform function textarea

test_ai_assist_response_form_context
    - AI assist receives correct context for response form
    - Context includes "gateway response transform"
    - Response modifies the transform function textarea

test_ai_assist_examples_include_gateway
    - AI assist examples include gateway form examples
    - Examples are relevant and useful
```

### Boot Image Generation Tests

```
test_gateways_source_json_processing
    - gateways.source.json is read correctly
    - Transform CIDs are generated
    - gateways.json is created with CIDs

test_gateways_variable_in_boot
    - default.boot.json includes gateways variable
    - readonly.boot.json includes gateways variable
    - Variable definition is the gateways.json CID

test_gateways_cids_stored
    - All transform function CIDs are in /cids
    - gateways.json CID is in /cids
```

### Template Tests

```
test_gateway_templates_load
    - All template files exist
    - Templates are valid HTML/Jinja2
    - Templates render without errors

test_gateway_template_variables
    - Templates receive expected variables
    - Missing variables have sensible defaults
```

### Error Handling Tests

```
test_gateway_handles_network_errors
    - Connection refused -> shows error page
    - Timeout -> shows timeout error
    - DNS failure -> shows DNS error

test_gateway_handles_invalid_gateways_config
    - Missing target_url -> shows config error
    - Invalid CID -> shows CID error
    - Malformed JSON in variable -> shows parse error

test_gateway_handles_transform_errors
    - Syntax error in transform -> shows line number
    - Runtime error -> shows traceback
    - Invalid return value -> shows format error
```

### Security Tests

```
test_gateway_sanitizes_output
    - HTML output is properly escaped
    - XSS payloads are neutralized

test_gateway_validates_cids
    - Only valid CIDs are accepted
    - Path traversal attempts are blocked

test_gateway_respects_readonly_mode
    - In readonly boot, transforms cannot modify system state
    - External API calls are allowed
    - Internal server calls are allowed
```

---

## File Changes Summary

### New Files

| File | Description |
|------|-------------|
| `reference_templates/gateways.source.json` | Gateway configuration source |
| `reference_templates/gateways/transforms/jsonplaceholder_request.py` | JSONPlaceholder request transform |
| `reference_templates/gateways/transforms/jsonplaceholder_response.py` | JSONPlaceholder response transform |
| `reference_templates/gateways/transforms/man_request.py` | Man page request transform |
| `reference_templates/gateways/transforms/man_response.py` | Man page response transform |
| `reference_templates/gateways/transforms/tldr_request.py` | TLDR request transform |
| `reference_templates/gateways/transforms/tldr_response.py` | TLDR response transform |
| `reference_templates/gateways/transforms/hrx_request.py` | HRX request transform |
| `reference_templates/gateways/transforms/hrx_response.py` | HRX response transform |
| `reference_templates/servers/templates/gateway/instruction.html` | Main instruction page |
| `reference_templates/servers/templates/gateway/request_form.html` | Request form |
| `reference_templates/servers/templates/gateway/response_form.html` | Response form |
| `reference_templates/servers/templates/gateway/meta.html` | Meta page |
| `reference_templates/servers/templates/gateway/error.html` | Error page |
| `reference_templates/servers/templates/gateway/json_response.html` | JSON formatting |
| `tests/test_gateway_transforms.py` | Transform function tests |
| `tests/test_gateway_routes.py` | Route handling tests |
| `tests/test_gateway_ai_assist.py` | AI assist integration tests |
| `tests/integration/test_gateway_jsonplaceholder.py` | JSONPlaceholder integration |
| `tests/integration/test_gateway_man.py` | Man page integration |
| `tests/integration/test_gateway_tldr.py` | TLDR integration |
| `tests/integration/test_gateway_hrx.py` | HRX integration |

### Modified Files

| File | Changes |
|------|---------|
| `reference_templates/servers/definitions/gateway.py` | Complete refactor |
| `reference_templates/default.boot.source.json` | Add gateways variable |
| `reference_templates/readonly.boot.source.json` | Add gateways variable |
| `generate_boot_image.py` | Add gateways.source.json processing |
| `tests/test_ai_system_prompts.py` | Add gateway form examples |

---

## Dependencies

### Existing Systems Used

- `NamedValueResolver` - For resolving gateways variable
- `generate_boot_image.py` - For processing gateways.source.json
- `server_execution` - For executing transform functions
- `cid_core` - For CID generation and resolution
- AI assist system - For form integration
- `ServerInvocation` model - For loading previous invocations

### New Dependencies (None Expected)

All functionality should be achievable with existing codebase infrastructure.

---

## Migration Notes

1. **Backwards Compatibility**: The current gateway.py with hardcoded examples will be replaced. Users who have customized gateway.py will need to migrate their changes to the gateways variable.

2. **Boot Image Regeneration**: After implementation, boot images must be regenerated to include the gateways variable.

3. **Existing Tests**: Some existing gateway tests may need updates to reflect the new architecture, but the external behavior for `/gateway?target_server=...` should remain compatible.

---

## Success Criteria

1. All tests pass
2. `/gateway` shows instruction page with correct links
3. `/gateway/request` and `/gateway/response` forms work with AI assist
4. `/gateway/meta/{server}` shows transform source with validation
5. `/gateway/jsonplaceholder/posts` shows formatted JSON with working user links
6. `/gateway/man/ls` shows formatted HTML with working command links
7. `/gateway/tldr/ls` shows formatted HTML with working command links
8. `/gateway/hrx/{CID}/` shows archive contents with working file links
9. No server-specific code in gateway.py itself
10. All transforms defined via gateways variable with embedded CIDs
