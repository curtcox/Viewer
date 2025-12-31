# Gateway Enhancement Plan

## Overview

This plan details enhancements to the gateway facility to support:
1. Request transforms that can directly return responses (bypassing the server)
2. Response transforms that know whether the response came from a request transform or the server
3. External Jinja templates resolved via a template function passed to transforms
4. Template CIDs specified in the gateways variable
5. Enhanced `/gateways/meta/{server}` to list and preview gateway templates

---

## Current Architecture Summary

### Background: Content-Addressed Storage (CIDs)

A **CID (Content Identifier)** is a content-addressed identifier used throughout this codebase. CIDs are cryptographic hashes of file contents, ensuring immutability and deduplication.

**Key characteristics:**
- CIDs start with `AAAAA` (base64-encoded hash)
- Content is stored in `cid_storage` module and accessible via `db_access.get_cid_by_path()`
- The `_resolve_cid_content()` function in `gateway.py` handles CID resolution
- If a CID is invalid or corrupted, resolution returns `None` and the gateway displays an error page

**Resolution flow:**
```
CID string → _normalize_cid_lookup() → get_cid_by_path() → file_data bytes → decode to string
```

**Existing documentation:** See `cid_storage.py` and `cid_utils.py` for implementation details.

### Key Files
- `reference_templates/servers/definitions/gateway.py` - Main gateway server (1234 lines)
- `reference_templates/gateways.json` - Gateway configuration with CIDs
- `reference_templates/gateways/transforms/*.py` - Transform implementations
- `reference_templates/servers/templates/gateway/*.html` - Gateway UI templates
- `tests/test_gateway_server.py` - Unit tests
- `tests/integration/test_gateway_server.py` - Integration tests

### Current Transform Interfaces

**Request Transform:**
```python
def transform_request(request_details: dict, context: dict) -> dict:
    """
    Args:
        request_details: {path, query_string, method, headers, json, body}
        context: Full server execution context
    Returns: {method, headers, path, json, data, params}
    """
```

**Response Transform:**
```python
def transform_response(response_details: dict, context: dict) -> dict:
    """
    Args:
        response_details: {status_code, headers, content, text, json, request_path}
        context: Full server execution context
    Returns: {output, content_type}
    """
```

### Current Gateway Config Structure
```json
{
  "man": {
    "request_transform_cid": "AAAAA...",
    "response_transform_cid": "AAAAA...",
    "description": "HTML formatted man pages with command links"
  }
}
```

---

## Enhancement 1: Request Transform Direct Response

### Description
Allow request transforms to return a response directly, bypassing the target server. This is used for:
- Producing clarifying menus when the request is ambiguous
- Returning cached responses
- Validating input and returning error pages
- Rendering help/documentation pages

### New Request Transform Interface

```python
def transform_request(request_details: dict, context: dict) -> dict:
    """
    Returns either:
    1. A transformed request dict (current behavior):
       {"method": ..., "headers": ..., "path": ..., "json": ..., "data": ..., "params": ...}

    2. A direct response dict (new behavior):
       {"response": {"output": ..., "content_type": ...}}
    """
```

### Detection Logic
The gateway will check if the return value contains a `response` key. If present, it skips server execution and proceeds directly to the response transform (if configured).

**Precedence rule:** If a dict contains both `response` and other keys (like `path`), the `response` key takes precedence and the request is treated as a direct response.

### Direct Response Validation

The gateway validates direct response dicts to prevent malformed responses:

```python
def _validate_direct_response(direct_response: dict) -> tuple[bool, str | None]:
    """Validate a direct response dict from request transform.

    Returns: (is_valid, error_message)
    """
    if not isinstance(direct_response, dict):
        return False, "Direct response must be a dict"

    # 'output' is required (can be str or bytes, but must be present)
    if "output" not in direct_response:
        return False, "Direct response must contain 'output' key"

    output = direct_response.get("output")
    if output is not None and not isinstance(output, (str, bytes)):
        return False, f"Direct response 'output' must be str or bytes, got {type(output).__name__}"

    # 'content_type' is optional but must be string if present
    content_type = direct_response.get("content_type")
    if content_type is not None and not isinstance(content_type, str):
        return False, f"Direct response 'content_type' must be str, got {type(content_type).__name__}"

    # 'status_code' is optional but must be int if present
    status_code = direct_response.get("status_code")
    if status_code is not None and not isinstance(status_code, int):
        return False, f"Direct response 'status_code' must be int, got {type(status_code).__name__}"

    return True, None
```

**Handling malformed responses:** If validation fails, the gateway returns an error page with a diagnostic message indicating what was wrong with the direct response.

### Implementation Changes

**File: `reference_templates/servers/definitions/gateway.py`**

Modify `_handle_gateway_request()`:

```python
# After executing request transform
if isinstance(transformed, dict):
    if "response" in transformed:
        # Request transform returned a direct response
        direct_response = transformed["response"]
        response_details = {
            "status_code": direct_response.get("status_code", 200),
            "headers": direct_response.get("headers", {"Content-Type": direct_response.get("content_type", "text/html")}),
            "content": direct_response.get("output", "").encode("utf-8") if isinstance(direct_response.get("output"), str) else direct_response.get("output", b""),
            "text": direct_response.get("output", "") if isinstance(direct_response.get("output"), str) else direct_response.get("output", b"").decode("utf-8", errors="replace"),
            "json": None,
            "request_path": rest_path,
            "source": "request_transform",  # NEW: indicates source
        }
        # Skip to response transform
    else:
        request_details = transformed
        # Continue with server execution...
```

### Tests for Enhancement 1

#### Unit Tests (test_gateway_server.py)

```python
# Test 1.1: Request transform returning direct response bypasses server
def test_request_transform_direct_response_bypasses_server():
    """Request transform returning response dict should bypass server execution."""
    # Setup: Create a request transform that returns {"response": {...}}
    # Verify: Server is not called, response is returned directly
    pass

# Test 1.2: Request transform direct response has correct content type
def test_request_transform_direct_response_content_type():
    """Direct response from request transform should preserve content_type."""
    pass

# Test 1.3: Request transform direct response status code
def test_request_transform_direct_response_status_code():
    """Direct response can specify custom status_code."""
    pass

# Test 1.4: Request transform returning normal dict continues to server
def test_request_transform_normal_dict_continues():
    """Request transform returning normal dict should continue to server."""
    pass

# Test 1.5: Request transform direct response with binary output
def test_request_transform_direct_response_binary_output():
    """Direct response output can be bytes."""
    pass

# Test 1.6: Request transform direct response with HTML menu
def test_request_transform_direct_response_clarifying_menu():
    """Request transform can return a clarifying menu HTML page."""
    pass

# Test 1.7: Request transform response key takes precedence
def test_request_transform_response_key_precedence():
    """If both 'response' and 'path' keys present, 'response' takes precedence."""
    pass

# Test 1.10: Direct response validation - missing output
def test_request_transform_direct_response_missing_output():
    """Direct response without 'output' key should return validation error."""
    pass

# Test 1.11: Direct response validation - invalid output type
def test_request_transform_direct_response_invalid_output_type():
    """Direct response with non-str/bytes output should return validation error."""
    pass

# Test 1.12: Direct response validation - invalid status_code type
def test_request_transform_direct_response_invalid_status_code():
    """Direct response with non-int status_code should return validation error."""
    pass
```

#### Integration Tests (tests/integration/test_gateway_server.py)

```python
# Test 1.8: End-to-end direct response from request transform
def test_gateway_request_transform_direct_response_integration():
    """Full integration test for request transform returning direct response."""
    pass

# Test 1.9: Direct response followed by response transform
def test_gateway_direct_response_then_response_transform():
    """Response transform should be called even for direct responses."""
    pass
```

---

## Enhancement 2: Response Transform Source Indicator

### Description
The response transform needs to know whether the response was generated by:
1. The request transform (direct response)
2. The target server (normal flow)

This allows the response transform to handle these cases differently.

### New Response Details Field

Add a `source` field to `response_details`:

```python
response_details = {
    "status_code": ...,
    "headers": ...,
    "content": ...,
    "text": ...,
    "json": ...,
    "request_path": ...,
    "source": "request_transform" | "server",  # NEW
}
```

### Implementation Changes

**File: `reference_templates/servers/definitions/gateway.py`**

When building `response_details` after server execution:
```python
response_details = {
    # ... existing fields ...
    "source": "server",
}
```

When building `response_details` from request transform direct response:
```python
response_details = {
    # ... existing fields ...
    "source": "request_transform",
}
```

### Tests for Enhancement 2

#### Unit Tests

```python
# Test 2.1: Response from server has source="server"
def test_response_details_source_server():
    """Response details from server should have source='server'."""
    pass

# Test 2.2: Response from request transform has source="request_transform"
def test_response_details_source_request_transform():
    """Response details from request transform should have source='request_transform'."""
    pass

# Test 2.3: Response transform receives source field
def test_response_transform_receives_source():
    """Response transform should receive the source field in response_details."""
    pass

# Test 2.4: Response transform can behave differently based on source
def test_response_transform_conditional_on_source():
    """Response transform can conditionally process based on source."""
    pass

# Test 2.5: Source field defaults to server when not set
def test_response_details_source_defaults_server():
    """Source field should default to 'server' for backwards compatibility."""
    pass
```

---

## Enhancement 3: External Jinja Templates for Transforms

### Description
Replace inline HTML templates in transforms with external Jinja template files. Transforms receive a template resolution function that loads templates by name from CIDs specified in the gateway configuration.

### New Template Resolution Function

Transforms receive a `resolve_template` function via the context:

```python
def transform_response(response_details: dict, context: dict) -> dict:
    resolve_template = context.get("resolve_template")
    if resolve_template:
        template = resolve_template("man_page.html")
        html = template.render(command=command, sections=sections)
        return {"output": html, "content_type": "text/html"}
```

### Template Resolution Flow

1. Gateway loads template CIDs from the gateway config
2. When executing a transform, gateway creates `resolve_template` function
3. `resolve_template(name)` looks up the template CID from config
4. Loads template content from CID storage
5. Returns a Jinja2 Template object

### New Gateway Config Structure

```json
{
  "man": {
    "request_transform_cid": "AAAAA...",
    "response_transform_cid": "AAAAA...",
    "description": "HTML formatted man pages with command links",
    "templates": {
      "man_page.html": "AAAAA_template_cid...",
      "man_error.html": "AAAAA_error_template_cid...",
      "man_menu.html": "AAAAA_menu_template_cid..."
    }
  }
}
```

### Implementation Changes

**File: `reference_templates/servers/definitions/gateway.py`**

Add template resolution function factory:

```python
def _create_template_resolver(config: dict, context: dict):
    """Create a template resolution function for a gateway config.

    Args:
        config: Gateway configuration dict with optional 'templates' key
        context: Server execution context

    Returns:
        Function that takes template name and returns Jinja2 Template
    """
    templates_config = config.get("templates", {})

    def resolve_template(template_name: str):
        """Resolve a template by name from the gateway's templates config.

        Args:
            template_name: Name of the template (e.g., "man_page.html")

        Returns:
            jinja2.Template object

        Raises:
            ValueError: If template not found in config
            LookupError: If template CID cannot be resolved
        """
        if template_name not in templates_config:
            raise ValueError(f"Template '{template_name}' not found in gateway config. "
                           f"Available templates: {list(templates_config.keys())}")

        template_cid = templates_config[template_name]
        content = _resolve_cid_content(template_cid)
        if content is None:
            raise LookupError(f"Could not resolve template CID: {template_cid}")

        return Template(content)

    return resolve_template
```

Modify transform execution to inject resolver:

```python
# In _handle_gateway_request:
template_resolver = _create_template_resolver(config, context)
enhanced_context = {
    **(context or {}),
    "resolve_template": template_resolver,
}

# Pass enhanced_context to transforms
result = transform_fn(request_details, enhanced_context)
```

### Tests for Enhancement 3

#### Unit Tests

```python
# Test 3.1: Template resolver created from config
def test_template_resolver_creation():
    """Template resolver should be created from gateway config."""
    pass

# Test 3.2: Template resolver returns Jinja Template
def test_template_resolver_returns_jinja_template():
    """resolve_template should return a jinja2.Template object."""
    pass

# Test 3.3: Template resolver raises ValueError for unknown template
def test_template_resolver_unknown_template():
    """resolve_template should raise ValueError for unknown template name."""
    pass

# Test 3.4: Template resolver raises LookupError for missing CID
def test_template_resolver_missing_cid():
    """resolve_template should raise LookupError if CID cannot be resolved."""
    pass

# Test 3.5: Transform receives resolve_template in context
def test_transform_receives_template_resolver():
    """Transforms should receive resolve_template function in context."""
    pass

# Test 3.6: Template can be rendered with variables
def test_template_rendering_with_variables():
    """Resolved template can be rendered with variables."""
    pass

# Test 3.7: Empty templates config handled gracefully
def test_empty_templates_config():
    """Gateway with no templates config should still work."""
    pass

# Test 3.8: Template resolver available to request transform
def test_request_transform_receives_template_resolver():
    """Request transform should receive resolve_template in context."""
    pass

# Test 3.9: Template resolver available to response transform
def test_response_transform_receives_template_resolver():
    """Response transform should receive resolve_template in context."""
    pass
```

#### Integration Tests

```python
# Test 3.10: End-to-end template resolution
def test_gateway_template_resolution_integration():
    """Full integration test for template resolution from CID."""
    pass

# Test 3.11: Response transform using external template
def test_response_transform_external_template():
    """Response transform can use external template via resolve_template."""
    pass
```

---

## Enhancement 4: Update Existing Transforms

### Description
Update the existing man, tldr, jsonplaceholder, and hrx transforms to use external Jinja templates via the `resolve_template` function.

### Man Gateway Templates

Create the following templates:

**man_page.html** - Main man page template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>man {{ command }}</title>
    <!-- styles -->
</head>
<body>
    <div class="nav">
        <a href="/gateway/man">man pages</a>
        <a href="/gateway/tldr/{{ command }}">tldr {{ command }}</a>
    </div>
    <h1>man {{ command }}</h1>
    {% if sections %}
    <div class="toc">...</div>
    {% for section_name, section_content in sections.items() %}
    <h2 id="{{ section_name | lower | replace(' ', '-') }}">{{ section_name }}</h2>
    <pre>{{ section_content }}</pre>
    {% endfor %}
    {% else %}
    <pre>{{ content }}</pre>
    {% endif %}
</body>
</html>
```

**man_error.html** - Man error page template
```html
<!DOCTYPE html>
<html>
<head>
    <title>man {{ command }} - Error</title>
</head>
<body>
    <div class="error">
        <h1>man {{ command }}</h1>
        <p>{{ message }}</p>
    </div>
</body>
</html>
```

### Transform Update Pattern

Transforms use external templates exclusively via `resolve_template`. The gateway supports inline templates for backwards compatibility, but transforms themselves should only use external templates:

```python
def transform_response(response_details: dict, context: dict) -> dict:
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured")

    # Prepare data
    command = extract_command(response_details)
    sections = parse_sections(response_details.get("text", ""))

    # Use external template (no fallback to inline)
    template = resolve_template("man_page.html")
    html = template.render(command=command, sections=sections)

    return {"output": html, "content_type": "text/html"}
```

### Tests for Enhancement 4

```python
# Test 4.1: Man transform uses external template
def test_man_transform_uses_external_template():
    """Man response transform should use external template."""
    pass

# Test 4.2: Man transform raises error when templates not configured
def test_man_transform_requires_templates():
    """Man transform should raise error if resolve_template not available."""
    pass

# Test 4.3: TLDR transform uses external template
def test_tldr_transform_uses_external_template():
    """TLDR transform should use external template."""
    pass

# Test 4.4: TLDR transform raises error when templates not configured
def test_tldr_transform_requires_templates():
    """TLDR transform should raise error if resolve_template not available."""
    pass

# Test 4.5: JSONPlaceholder transform uses external template
def test_jsonplaceholder_transform_uses_external_template():
    """JSONPlaceholder transform should use external template."""
    pass

# Test 4.6: JSONPlaceholder transform raises error when templates not configured
def test_jsonplaceholder_transform_requires_templates():
    """JSONPlaceholder transform should raise error if resolve_template not available."""
    pass

# Test 4.7: HRX transform uses external template
def test_hrx_transform_uses_external_template():
    """HRX transform should use external template."""
    pass

# Test 4.8: HRX transform raises error when templates not configured
def test_hrx_transform_requires_templates():
    """HRX transform should raise error if resolve_template not available."""
    pass

# Test 4.9: Gateway inline template support maintained for backwards compatibility
def test_gateway_inline_templates_supported():
    """Gateway should still support inline templates for backwards compatibility."""
    pass
```

---

## Enhancement 5: Update /gateways/meta/{server} for Templates

### Description
Enhance the gateway meta page to list and preview all templates associated with a gateway.

### New Meta Page Features

1. **Templates Section** - List all template names and their CIDs
2. **Template Preview** - Show template source code
3. **Template Validation** - Validate Jinja syntax
4. **Template Variables** - List expected template variables (if detectable)

### Implementation Changes

**File: `reference_templates/servers/definitions/gateway.py`**

Update `_handle_meta_page()`:

```python
def _handle_meta_page(server_name, gateways, context):
    # ... existing code ...

    # Load template information
    templates_config = config.get("templates", {})
    templates_info = []

    for template_name, template_cid in templates_config.items():
        template_info = {
            "name": template_name,
            "cid": template_cid,
            "source": None,
            "status": "error",
            "status_text": "Not Found",
            "error": None,
            "variables": [],
        }

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

    # Add to template context
    html = template.render(
        # ... existing vars ...
        templates_info=templates_info,
    )
```

Add template validation function:

```python
def _load_and_validate_template(cid, context):
    """Load and validate a Jinja template.

    Returns: (source, error, variables)
    """
    try:
        cid_lookup = _normalize_cid_lookup(cid)
        content = _resolve_cid_content(cid_lookup)
        if not content:
            return None, f"Template not found at CID: {cid}", []

        # Try to parse as Jinja template
        from jinja2 import Environment, meta
        env = Environment()
        try:
            ast = env.parse(content)
            # Extract referenced variables
            variables = list(meta.find_undeclared_variables(ast))
        except Exception as e:
            return content, f"Jinja syntax error: {e}", []

        return content, None, variables

    except Exception as e:
        return None, f"Validation error: {e}", []
```

**File: `reference_templates/servers/templates/gateway/meta.html`**

Add templates section:

```html
{% if templates_info %}
<div class="card">
    <h3>Templates</h3>
    {% for tpl in templates_info %}
    <div class="template-item">
        <h4>
            {{ tpl.name }}
            <span class="status {{ tpl.status }}">{{ tpl.status_text }}</span>
        </h4>
        <div class="info-row">
            <span class="info-label">CID:</span>
            <span class="info-value"><code>{{ tpl.cid }}</code></span>
        </div>
        {% if tpl.variables %}
        <div class="info-row">
            <span class="info-label">Variables:</span>
            <span class="info-value">
                {{ tpl.variables | join(', ') }}
                <span class="note">(auto-detected, may be incomplete)</span>
            </span>
        </div>
        {% endif %}
        {% if tpl.error %}
        <div class="error-detail">{{ tpl.error }}</div>
        {% endif %}
        {% if tpl.source %}
        <details>
            <summary>View Template Source</summary>
            <pre>{{ tpl.source }}</pre>
        </details>
        {% endif %}
    </div>
    {% endfor %}
</div>
{% else %}
<div class="card">
    <h3>Templates</h3>
    <p><em>No templates configured for this gateway.</em></p>
</div>
{% endif %}
```

### Tests for Enhancement 5

```python
# Test 5.1: Meta page shows templates section
def test_meta_page_shows_templates_section():
    """Meta page should show templates section when templates configured."""
    pass

# Test 5.2: Meta page lists all template names
def test_meta_page_lists_template_names():
    """Meta page should list all template names from config."""
    pass

# Test 5.3: Meta page shows template CIDs
def test_meta_page_shows_template_cids():
    """Meta page should show CID for each template."""
    pass

# Test 5.4: Meta page shows template source preview
def test_meta_page_shows_template_source():
    """Meta page should show template source in collapsible section."""
    pass

# Test 5.5: Meta page validates Jinja syntax
def test_meta_page_validates_jinja_syntax():
    """Meta page should show syntax validation status for templates."""
    pass

# Test 5.6: Meta page shows syntax errors
def test_meta_page_shows_template_syntax_errors():
    """Meta page should display Jinja syntax errors."""
    pass

# Test 5.7: Meta page lists template variables
def test_meta_page_lists_template_variables():
    """Meta page should list detected template variables."""
    pass

# Test 5.8: Meta page handles missing template CID
def test_meta_page_handles_missing_template_cid():
    """Meta page should handle templates with unresolvable CIDs."""
    pass

# Test 5.9: Meta page with no templates config
def test_meta_page_no_templates_configured():
    """Meta page should show message when no templates configured."""
    pass

# Test 5.10: Meta page template CID links
def test_meta_page_template_cid_links():
    """Template CIDs should be clickable links."""
    pass
```

---

## Complete Test List

### Unit Tests (tests/test_gateway_server.py)

| ID | Test Name | Description |
|----|-----------|-------------|
| 1.1 | test_request_transform_direct_response_bypasses_server | Request transform returning response dict should bypass server execution |
| 1.2 | test_request_transform_direct_response_content_type | Direct response from request transform should preserve content_type |
| 1.3 | test_request_transform_direct_response_status_code | Direct response can specify custom status_code |
| 1.4 | test_request_transform_normal_dict_continues | Request transform returning normal dict should continue to server |
| 1.5 | test_request_transform_direct_response_binary_output | Direct response output can be bytes |
| 1.6 | test_request_transform_direct_response_clarifying_menu | Request transform can return a clarifying menu HTML page |
| 1.7 | test_request_transform_response_key_precedence | If both 'response' and 'path' keys present, 'response' takes precedence |
| 1.10 | test_request_transform_direct_response_missing_output | Direct response without 'output' key should return validation error |
| 1.11 | test_request_transform_direct_response_invalid_output_type | Direct response with non-str/bytes output should return validation error |
| 1.12 | test_request_transform_direct_response_invalid_status_code | Direct response with non-int status_code should return validation error |
| 2.1 | test_response_details_source_server | Response details from server should have source='server' |
| 2.2 | test_response_details_source_request_transform | Response details from request transform should have source='request_transform' |
| 2.3 | test_response_transform_receives_source | Response transform should receive the source field in response_details |
| 2.4 | test_response_transform_conditional_on_source | Response transform can conditionally process based on source |
| 2.5 | test_response_details_source_defaults_server | Source field should default to 'server' for backwards compatibility |
| 3.1 | test_template_resolver_creation | Template resolver should be created from gateway config |
| 3.2 | test_template_resolver_returns_jinja_template | resolve_template should return a jinja2.Template object |
| 3.3 | test_template_resolver_unknown_template | resolve_template should raise ValueError for unknown template name |
| 3.4 | test_template_resolver_missing_cid | resolve_template should raise LookupError if CID cannot be resolved |
| 3.5 | test_transform_receives_template_resolver | Transforms should receive resolve_template function in context |
| 3.6 | test_template_rendering_with_variables | Resolved template can be rendered with variables |
| 3.7 | test_empty_templates_config | Gateway with no templates config should still work |
| 3.8 | test_request_transform_receives_template_resolver | Request transform should receive resolve_template in context |
| 3.9 | test_response_transform_receives_template_resolver | Response transform should receive resolve_template in context |
| 4.1 | test_man_transform_uses_external_template | Man response transform should use external template |
| 4.2 | test_man_transform_requires_templates | Man transform should raise error if resolve_template not available |
| 4.3 | test_tldr_transform_uses_external_template | TLDR transform should use external template |
| 4.4 | test_tldr_transform_requires_templates | TLDR transform should raise error if resolve_template not available |
| 4.5 | test_jsonplaceholder_transform_uses_external_template | JSONPlaceholder transform should use external template |
| 4.6 | test_jsonplaceholder_transform_requires_templates | JSONPlaceholder transform should raise error if resolve_template not available |
| 4.7 | test_hrx_transform_uses_external_template | HRX transform should use external template |
| 4.8 | test_hrx_transform_requires_templates | HRX transform should raise error if resolve_template not available |
| 4.9 | test_gateway_inline_templates_supported | Gateway should still support inline templates for backwards compatibility |
| 5.1 | test_meta_page_shows_templates_section | Meta page should show templates section when templates configured |
| 5.2 | test_meta_page_lists_template_names | Meta page should list all template names from config |
| 5.3 | test_meta_page_shows_template_cids | Meta page should show CID for each template |
| 5.4 | test_meta_page_shows_template_source | Meta page should show template source in collapsible section |
| 5.5 | test_meta_page_validates_jinja_syntax | Meta page should show syntax validation status for templates |
| 5.6 | test_meta_page_shows_template_syntax_errors | Meta page should display Jinja syntax errors |
| 5.7 | test_meta_page_lists_template_variables | Meta page should list detected template variables |
| 5.8 | test_meta_page_handles_missing_template_cid | Meta page should handle templates with unresolvable CIDs |
| 5.9 | test_meta_page_no_templates_configured | Meta page should show message when no templates configured |
| 5.10 | test_meta_page_template_cid_links | Template CIDs should be clickable links |
| 5.11 | test_meta_page_warns_transforms_without_templates | Meta page should warn when transforms exist but templates are missing |

### Integration Tests (tests/integration/test_gateway_server.py)

| ID | Test Name | Description |
|----|-----------|-------------|
| 1.8 | test_gateway_request_transform_direct_response_integration | Full integration test for request transform returning direct response |
| 1.9 | test_gateway_direct_response_then_response_transform | Response transform should be called even for direct responses |
| 3.10 | test_gateway_template_resolution_integration | Full integration test for template resolution from CID |
| 3.11 | test_response_transform_external_template | Response transform can use external template via resolve_template |

---

## Edge Cases and Error Handling

### Edge Case Tests

| ID | Test Name | Description |
|----|-----------|-------------|
| E.1 | test_request_transform_returns_none | Handle request transform returning None |
| E.2 | test_request_transform_returns_empty_dict | Handle request transform returning {} |
| E.3 | test_response_in_request_transform_with_none_output | Handle response with output=None |
| E.4 | test_template_with_undefined_variable | Template rendering with undefined variable |
| E.5 | test_template_with_circular_include | Template with circular include (if supported) |
| E.6 | test_very_large_template | Template that exceeds reasonable size limits |
| E.7 | test_template_cid_pointing_to_non_template | CID pointing to binary/non-text content |
| E.8 | test_concurrent_template_resolution | Multiple concurrent resolve_template calls |
| E.9 | test_source_field_preserved_through_transform_chain | Source field preserved if response transform re-wraps |
| E.10 | test_request_transform_response_with_headers | Direct response with custom headers dict |
| E.11 | test_transform_error_when_no_templates_configured | Transform raises clear error when templates not configured |
| E.12 | test_gateway_error_page_for_missing_templates | Gateway shows helpful error when transform fails due to missing templates |
| E.13 | test_template_with_non_ascii_content | Template containing non-ASCII characters (emoji, CJK) renders correctly |

---

## Design Decisions

The following decisions have been made:

| # | Question | Decision |
|---|----------|----------|
| 1 | **Template Caching** | No caching. Templates are resolved per-request to ensure freshness. |
| 2 | **Template Include/Extend** | Keep templates standalone for simplicity. No include/extend support initially. |
| 3 | **Template Errors at Runtime** | Let the exception propagate. The gateway error handler will display a diagnostic error page. |
| 4 | **Response Transform for Direct Responses** | Always call the response transform. It can check `source` and return early if desired. |
| 5 | **Direct Response Status Code** | Default to 200 when not explicitly specified. |
| 6 | **Template Variable Detection** | Use Jinja2's `meta.find_undeclared_variables()`. Accept that it may miss some variables. |
| 7 | **Inline Template Support** | The gateway maintains inline template support for backwards compatibility, but transforms should ONLY use external templates. No transform should use inline templates. |
| 8 | **Template Security** | No additional sandboxing. Templates are trusted content stored as CIDs. |
| 9 | **Transform Behavior Without Templates** | Raise a `RuntimeError` with a clear message indicating templates must be configured. Fail fast. |
| 10 | **Meta Page Template Validation Warning** | Show a warning when a gateway has transforms configured but no templates. Explicit validation helps users diagnose issues. |

---

## Migration Strategy: Inline to External Templates

### Overview

This section clarifies the transition path for existing transforms that currently use inline templates.

### Current State

Existing transforms (man, tldr, jsonplaceholder, hrx) currently embed HTML templates as Python string literals within the transform code. For example, `man_response.py` contains `_render_man_as_html()` with ~60 lines of inline HTML.

### Target State

All transforms will use external Jinja templates via `resolve_template()`. The inline HTML will be extracted to separate `.html` files stored as CIDs.

### Migration Path

| Phase | Action | Timeline |
|-------|--------|----------|
| 1 | Create external template files for all transforms | Phase 2 of implementation |
| 2 | Update transforms to require external templates (fail if not configured) | Phase 2 of implementation |
| 3 | Update `gateways.json` to include template CIDs | Phase 2 of implementation |
| 4 | Remove inline template code from transforms | Phase 2 of implementation |

### Developer Guidelines

**When modifying existing transforms:**
- Use `resolve_template()` to load templates
- Do NOT add inline HTML - create external template files instead
- Raise `RuntimeError` if `resolve_template` is not available

**When creating new transforms:**
- Always use external templates
- Create corresponding `.html` files in `reference_templates/gateways/templates/`
- Add template CIDs to gateway config

### Backwards Compatibility Note

The **gateway server** (`gateway.py`) maintains inline template support indefinitely for:
- Gateway UI pages (instruction.html, meta.html, etc.)
- Third-party transforms that may not have migrated

However, **first-party transforms** (man, tldr, jsonplaceholder, hrx) will exclusively use external templates after migration. There is no deprecation period for inline templates in first-party transforms.

---

## Performance Considerations

### Per-Request Template Resolution

Design Decision #1 specifies no template caching. This means each request:
1. Looks up template CID from config
2. Fetches template content from CID storage
3. Parses template with Jinja2

### Expected Latency Impact

| Operation | Typical Latency |
|-----------|-----------------|
| CID lookup (database) | ~1-5ms |
| Template parsing (Jinja2) | ~0.5-2ms |
| **Total overhead per template** | **~2-7ms** |

For requests using multiple templates, this overhead is additive.

### Why No Caching?

Template "freshness" means templates can be updated (new CID in config) and take effect immediately without server restart or cache invalidation. This is valuable for:
- Rapid iteration during development
- Hot-fixing template issues in production
- A/B testing different template versions

### Future Optimization

If performance becomes a bottleneck, consider:
1. **Request-scoped caching**: Cache templates within a single request (no cross-request caching)
2. **TTL-based caching**: Cache with short TTL (e.g., 60 seconds)
3. **Config-version caching**: Invalidate cache when gateways config changes

**Performance testing requirement:** During Phase 4, run load tests on the gateway to validate that per-request resolution meets latency requirements (<100ms p95).

---

## Template Variable Detection Limitations

### Implementation

The meta page uses Jinja2's `meta.find_undeclared_variables()` to detect template variables. This provides reasonable but incomplete detection.

### Known Limitations

| Pattern | Detected? | Example |
|---------|-----------|---------|
| Simple variables | Yes | `{{ name }}` |
| Attribute access | Partial | `{{ user.name }}` → detects `user` only |
| Subscript access | No | `{{ items[0] }}` → misses `items` |
| Loop variables | No | `{% for x in items %}` → misses `items` |
| Filter chains | Partial | `{{ name | upper }}` → detects `name` |
| Nested conditionals | Partial | Complex logic may be missed |

### UI Disclosure

The meta page template should include a disclaimer:

```html
{% if tpl.variables %}
<div class="info-row">
    <span class="info-label">Variables:</span>
    <span class="info-value">
        {{ tpl.variables | join(', ') }}
        <span class="note">(auto-detected, may be incomplete)</span>
    </span>
</div>
{% endif %}
```

---

## Test Implementation Approach

### Methodology: Test-Driven Development (TDD)

Tests should be written **before or alongside** implementation, not after.

| Phase | Test Approach |
|-------|---------------|
| Phase 1 | Write unit tests first, then implement |
| Phase 2 | Write transform tests, then update transforms |
| Phase 3 | Write meta page tests, then update templates |
| Phase 4 | Integration tests verify end-to-end behavior |

### Edge Case Test Priority

Edge case tests (Section E) should be implemented during Phase 1 alongside core functionality:
- E.1-E.3: During direct response implementation
- E.4-E.8: During template resolver implementation
- E.9-E.12: During transform update phase

### Template Encoding

All templates are assumed to be **UTF-8 encoded**. This is standard for HTML/Jinja2 templates.

**Additional encoding test:**

| ID | Test Name | Description |
|----|-----------|-------------|
| E.13 | test_template_with_non_ascii_content | Template containing non-ASCII characters (e.g., emoji, CJK) renders correctly |

Templates containing non-UTF-8 bytes will fail during CID content decoding and produce a clear error.

---

## Implementation Order

### Phase 1: Core Infrastructure
1. Implement request transform direct response detection
2. Add `source` field to response details
3. Implement template resolver function
4. Write unit tests for phases 1-3

### Phase 2: Transform Updates
5. Update gateway config schema to support templates
6. Update man_response.py to use external templates (as reference implementation)
7. Create man page template files
8. Update remaining transforms (tldr, jsonplaceholder, hrx)

### Phase 3: Meta Page Enhancement
9. Update `_handle_meta_page()` to load templates info
10. Add template validation function
11. Update meta.html template with templates section
12. Write tests for meta page changes

### Phase 4: Integration and Polish
13. Write integration tests
14. Update documentation
15. Update gateways.json with template CIDs
16. End-to-end testing

---

## Files to Modify

| File | Changes |
|------|---------|
| `reference_templates/servers/definitions/gateway.py` | Add direct response detection, source field, template resolver |
| `reference_templates/servers/templates/gateway/meta.html` | Add templates section |
| `reference_templates/gateways/transforms/man_request.py` | Add template support (optional) |
| `reference_templates/gateways/transforms/man_response.py` | Use external templates |
| `reference_templates/gateways/transforms/tldr_request.py` | Add template support (optional) |
| `reference_templates/gateways/transforms/tldr_response.py` | Use external templates |
| `reference_templates/gateways/transforms/jsonplaceholder_response.py` | Use external templates |
| `reference_templates/gateways/transforms/hrx_response.py` | Use external templates |
| `reference_templates/gateways.json` | Add templates config |
| `reference_templates/gateways.source.json` | Add templates config (source) |
| `tests/test_gateway_server.py` | Add unit tests |
| `tests/integration/test_gateway_server.py` | Add integration tests |

## New Files to Create

| File | Purpose |
|------|---------|
| `reference_templates/gateways/templates/man_page.html` | Man page main template |
| `reference_templates/gateways/templates/man_error.html` | Man page error template |
| `reference_templates/gateways/templates/tldr_page.html` | TLDR page template |
| `reference_templates/gateways/templates/tldr_error.html` | TLDR error template |
| `reference_templates/gateways/templates/jsonplaceholder_item.html` | JSONPlaceholder item template |
| `reference_templates/gateways/templates/jsonplaceholder_list.html` | JSONPlaceholder list template |
| `reference_templates/gateways/templates/hrx_viewer.html` | HRX archive viewer template |

---

## Success Criteria

1. All listed tests pass
2. Gateway server maintains backwards compatibility (inline template support)
3. All transforms use external templates exclusively (no inline templates in transform code)
4. Transforms raise clear errors when templates are not configured
5. New gateways can be configured with external templates via CIDs
6. Meta page displays template information, validation, and warnings for misconfiguration
7. Request transforms can return clarifying menus (direct responses)
8. Response transforms receive `source` field indicating origin
9. Meta page lists and previews all templates associated with each gateway
