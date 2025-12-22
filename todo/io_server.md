# IO Server Implementation Plan

## Overview

Create a new server named "io" that provides bidirectional request/response piping through a chain of servers. Unlike the existing pipeline execution (which flows right-to-left), the io server flows requests left-to-right and responses right-to-left, creating a circular data flow pattern.

## Key Differences from Pipeline

| Aspect | Pipeline | IO |
|--------|----------|-----|
| Request flow | Right-to-left | Left-to-right |
| Response flow | N/A (single pass) | Right-to-left |
| Implementation | Built into app | Named server |
| Invocation count | Each segment once | Middle segments twice (request + response) |

## Architecture

### Data Flow Pattern

```
User Request → [io] → [S1] → [S2] → [S3] → (tail returns response)
                              ↓
User Response ← [io] ← [S1] ← [S2] ← [S3]
```

### Server Roles

1. **Head (io server)**: Accepts user request, orchestrates chain, returns final response
2. **Middle servers (S1, S2, ...)**: Invoked twice:
   - **Request phase**: Receives request, produces chained request for next server
   - **Response phase**: Receives original request + response from right, produces modified response
3. **Tail server (last)**: Invoked once, directly returns response (no further chaining)

## Implementation Steps

### Phase 1: Core Infrastructure

#### 1.1 Create Shared Pipeline Utilities Module

Extract reusable logic from `server_execution/pipeline_execution.py` into a shared module that both pipeline and io can use.

**File**: `server_execution/segment_analysis.py`

```python
# Functions to extract:
- resolve_segment_type()
- detect_language_from_suffix()
- get_resolution_type()
- validate_cid()
- resolve_aliases()
- get_server_info()
- check_chaining_support()
- analyze_segment()

# Data structures to extract:
- PathSegmentInfo
- ParameterInfo
- DataExtensionError
- UnrecognizedExtensionError
```

#### 1.2 Create IO Execution Engine

**File**: `server_execution/io_execution.py`

Core classes and functions:
- `IOExecutionResult` - Result dataclass for IO execution
- `IOSegmentState` - State tracking for each segment (request/response phases)
- `execute_io_chain()` - Main execution function
- `execute_request_phase()` - Left-to-right request propagation
- `execute_response_phase()` - Right-to-left response propagation

#### 1.3 Debug Mode Integration

Reuse the existing debug detection logic from `server_execution/pipeline_debug.py`:
- `should_return_debug_response()` - Check for `?debug=true|1|yes|on`
- Debug output respects final extension (`.json`, `.html`, `.txt`)

### Phase 2: IO Server Implementation

#### 2.1 Create Server Definition

**File**: `reference_templates/servers/definitions/io.py`

```python
def main(
    *path_segments,
    context=None,
    _request=None,
):
    """
    IO server - bidirectional request/response piping.

    When invoked with no additional servers:
        Returns documentation page with link to /help/io

    When invoked with servers:
        Flows requests left-to-right, responses right-to-left
    """
```

#### 2.2 Landing Page (No Servers Specified)

When `/io` is accessed directly without additional path segments:
- Display a minimal HTML page
- Include a link to io server documentation
- Follow the pattern established by `gateway.py`

### Phase 3: Boot Image Configuration

#### 3.1 Update Default Boot Image

**File**: `reference_templates/default.boot.source.json`

Add entry:
```json
{
  "name": "io",
  "definition_cid": "reference_templates/servers/definitions/io.py",
  "enabled": true
}
```

#### 3.2 Update Read-Only Boot Image

**File**: `reference_templates/readonly.boot.source.json`

Add same entry as default.

### Phase 4: Documentation

#### 4.1 Create IO Documentation

**File**: `docs/io-requests.md`

Contents:
- What is IO vs Pipeline
- Data flow diagram
- Server role explanations (head, middle, tail)
- Examples with different server types
- Debug mode usage
- Error handling
- Best practices

### Phase 5: Testing

#### 5.1 Unit Tests

**File**: `tests/test_io_execution.py`

#### 5.2 Integration Tests

**File**: `tests/test_io_server_integration.py`

---

## Test Plan

### Unit Tests: Segment Analysis (Shared Logic)

These tests verify that io reuses the same segment classification as pipeline.

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UA-01 | `test_named_server_resolution` | Verify named server is detected | `segment_type == "server"` |
| UA-02 | `test_alias_resolution` | Verify alias is detected | `segment_type == "alias"` |
| UA-03 | `test_cid_resolution` | Verify CID is detected | `segment_type == "cid"` |
| UA-04 | `test_parameter_fallback` | Non-server/alias/CID becomes parameter | `segment_type == "parameter"` |
| UA-05 | `test_disabled_server_fallback` | Disabled server falls through | Not `"server"` |

### Unit Tests: Language Detection (Shared Logic)

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UL-01 | `test_py_extension` | `.py` → Python | `language == "python"` |
| UL-02 | `test_sh_extension` | `.sh` → Bash | `language == "bash"` |
| UL-03 | `test_js_extension` | `.js` → JavaScript | `language == "javascript"` |
| UL-04 | `test_ts_extension` | `.ts` → TypeScript | `language == "typescript"` |
| UL-05 | `test_clj_extension` | `.clj` → Clojure | `language == "clojure"` |
| UL-06 | `test_cljs_extension` | `.cljs` → ClojureScript | `language == "clojurescript"` |
| UL-07 | `test_no_extension_uses_detection` | No extension uses content detection | Detected from content |
| UL-08 | `test_data_extension_error` | `.csv`, `.json`, `.txt` → Error | `DataExtensionError` raised |
| UL-09 | `test_unrecognized_extension_error` | `.xyz` → Error | `UnrecognizedExtensionError` raised |
| UL-10 | `test_case_insensitive_extension` | `.PY`, `.Sh` work | Correct language returned |

### Unit Tests: Debug Detection (Shared Logic)

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UD-01 | `test_debug_true` | `?debug=true` enables debug | `debug == True` |
| UD-02 | `test_debug_1` | `?debug=1` enables debug | `debug == True` |
| UD-03 | `test_debug_yes` | `?debug=yes` enables debug | `debug == True` |
| UD-04 | `test_debug_on` | `?debug=on` enables debug | `debug == True` |
| UD-05 | `test_debug_false` | `?debug=false` no debug | `debug == False` |
| UD-06 | `test_debug_case_insensitive` | `?debug=TRUE` works | `debug == True` |
| UD-07 | `test_no_debug_param` | No param → no debug | `debug == False` |

### Unit Tests: Debug Output Format

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| DO-01 | `test_debug_json_extension` | `/io/s1.json?debug=true` | JSON output |
| DO-02 | `test_debug_html_extension` | `/io/s1.html?debug=true` | HTML output |
| DO-03 | `test_debug_txt_extension` | `/io/s1.txt?debug=true` | Plain text output |
| DO-04 | `test_debug_no_extension` | `/io/s1?debug=true` | JSON output (default) |
| DO-05 | `test_debug_final_extension_used` | `/io/s1.json/s2.html?debug=true` | Uses `.json` (leftmost/final) |

### Unit Tests: IO Execution Flow

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UE-01 | `test_empty_chain_returns_landing` | `/io` with no servers | Landing page HTML |
| UE-02 | `test_single_server_request` | `/io/echo/hello` | Echo receives hello, returns response |
| UE-03 | `test_two_server_chain` | `/io/s1/s2` | s1→s2→response→s1→final |
| UE-04 | `test_three_server_chain` | `/io/s1/s2/s3` | Correct flow through 3 servers |
| UE-05 | `test_tail_invoked_once` | Tail server call count | Exactly 1 invocation |
| UE-06 | `test_middle_invoked_twice` | Middle server call count | Exactly 2 invocations |
| UE-07 | `test_request_phase_data` | Request phase receives correct input | Verify input at each step |
| UE-08 | `test_response_phase_data` | Response phase receives request + response | Both values available |

### Unit Tests: Path Element Resolution

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| PE-01 | `test_alias_resolved_in_chain` | `/io/my-alias/input` | Alias resolved to target |
| PE-02 | `test_named_server_in_chain` | `/io/echo/hello` | Named server executed |
| PE-03 | `test_server_literal_in_chain` | `/io/{CID}.py/hello` | CID content executed as Python |
| PE-04 | `test_parameter_passed_to_server` | `/io/grep/pattern/input` | Pattern passed to grep |
| PE-05 | `test_mixed_elements` | `/io/echo/{CID}/param` | All element types work together |
| PE-06 | `test_alias_chain_resolution` | Alias → alias → server | Full alias chain resolved |
| PE-07 | `test_cid_with_extension` | `/io/{CID}.sh/input` | Extension overrides detection |

### Unit Tests: Data Piping Between Element Types

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| DP-01 | `test_server_to_server_piping` | Server output → Server input | Data flows correctly |
| DP-02 | `test_cid_to_server_piping` | CID output → Server input | Data flows correctly |
| DP-03 | `test_alias_to_server_piping` | Alias (→server) → Server | Data flows correctly |
| DP-04 | `test_parameter_to_server_piping` | Literal param → Server | Literal value passed |
| DP-05 | `test_server_to_cid_piping` | Server output → CID server | Data flows correctly |
| DP-06 | `test_mixed_language_chain` | Python → Bash → Python | Cross-language data flow |
| DP-07 | `test_binary_data_piping` | Binary data through chain | Bytes preserved |
| DP-08 | `test_unicode_data_piping` | Unicode text through chain | Encoding preserved |

### Unit Tests: Error Handling

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EH-01 | `test_nonexistent_server_error` | `/io/nonexistent/hello` | Appropriate error response |
| EH-02 | `test_disabled_server_error` | `/io/disabled-server/hello` | Appropriate error response |
| EH-03 | `test_invalid_cid_error` | `/io/INVALID-CID/hello` | CID validation error |
| EH-04 | `test_unrecognized_extension_error` | `/io/server.xyz/hello` | Extension error |
| EH-05 | `test_chaining_not_supported_error` | Python without main() in middle | Chaining error |
| EH-06 | `test_runtime_unavailable_error` | TypeScript without Deno | Runtime error |
| EH-07 | `test_execution_timeout` | Long-running server | Timeout error |
| EH-08 | `test_request_phase_error_propagation` | Error in S1 request phase | Error returned, no response phase |
| EH-09 | `test_response_phase_error_handling` | Error in S1 response phase | Error returned to user |

### Integration Tests: Full Request/Response Cycle

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-01 | `test_io_landing_page` | GET `/io` | HTML with documentation link |
| IT-02 | `test_io_simple_echo` | `/io/echo/hello` | "hello" returned |
| IT-03 | `test_io_two_server_chain` | `/io/upper/reverse/hello` | "OLLEH" (reversed then uppercased on return) |
| IT-04 | `test_io_with_query_params` | `/io/server?param=value` | Query params accessible |
| IT-05 | `test_io_with_post_body` | POST to `/io/server` with body | Body accessible |
| IT-06 | `test_io_debug_mode` | `/io/echo/hello?debug=true` | Debug JSON output |
| IT-07 | `test_io_debug_html` | `/io/echo.html/hello?debug=true` | Debug HTML output |
| IT-08 | `test_io_preserves_content_type` | Server sets content-type | Content-type preserved |

### Integration Tests: Boot Image Verification

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| BI-01 | `test_io_in_default_boot` | Parse default.boot.source.json | io server present |
| BI-02 | `test_io_in_readonly_boot` | Parse readonly.boot.source.json | io server present |
| BI-03 | `test_io_server_enabled` | Server enabled flag | `enabled == true` |
| BI-04 | `test_io_definition_exists` | Definition file exists | File found |

### Edge Case Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EC-01 | `test_empty_response_from_tail` | Tail returns empty string | Empty response propagated |
| EC-02 | `test_null_response_from_tail` | Tail returns None | Handled gracefully |
| EC-03 | `test_very_long_chain` | 10+ servers in chain | All invoked correctly |
| EC-04 | `test_circular_alias_detection` | Alias A → Alias B → Alias A | Cycle detected, error |
| EC-05 | `test_same_server_multiple_times` | `/io/echo/echo/echo` | Each instance invoked |
| EC-06 | `test_special_characters_in_param` | `/io/echo/hello%20world` | URL decoded correctly |
| EC-07 | `test_nested_io_request` | `/io/io/echo/hello` | Nested io handled |
| EC-08 | `test_concurrent_io_requests` | Multiple simultaneous requests | No cross-contamination |

---

## Open Questions

### Q1: Middle Server Signature for Response Phase

**Question**: What signature should middle servers use to receive both the original request and the response from the right?

**Options**:
a) Separate positional parameters: `def main(request, response, *, context=None)`
b) Combined dict parameter: `def main(data, *, context=None)` where `data = {"request": ..., "response": ...}`
c) Use context: `def main(input, *, context=None)` where `context["io_response"]` contains the response
d) Named parameters: `def main(*, io_request=None, io_response=None, context=None)`

**Implications**:
- Option (a) requires all io-compatible servers to follow specific signature
- Option (b) requires servers to unpack dict, but flexible
- Option (c) keeps signature simple but uses context magic
- Option (d) uses kwargs for flexibility

### Q2: Request Phase vs Response Phase Detection

**Question**: How does a middle server know if it's in the request phase or response phase?

**Options**:
a) Separate function names: `main_request()` and `main_response()`
b) Phase parameter: `def main(data, *, phase="request", context=None)`
c) Presence of response: Check if response parameter is None/present
d) Context flag: `context["io_phase"]` = "request" or "response"

### Q3: Chaining Semantics for Parameters

**Question**: In `/io/s1/param/s2`, how should `param` be treated?

**Options**:
a) `param` is passed as input to `s2`, result becomes input to `s1`
b) `param` is configuration for `s1`, `s2` gets empty input
c) Error - parameters can only be at the end
d) `param` is treated as a literal server that just returns its text

**Recommended**: Option (d) - consistent with pipeline behavior where parameters are literal values

### Q4: How Should io Handle Non-Chainable Servers?

**Question**: What happens if a Python server without `main()` is in a non-tail position?

**Options**:
a) Error immediately before execution
b) Execute in tail-only mode (single invocation)
c) Skip response phase for that server
d) Allow it but only invoke once

**Recommended**: Option (a) - consistent with pipeline error behavior

### Q5: Response Modification vs Replacement

**Question**: When a middle server is invoked in the response phase, should it:

**Options**:
a) Modify the response (must return modified version)
b) Optionally return nothing to pass response unchanged
c) Have access to both but only return the final response
d) Return a tuple of (modified_response, metadata)

### Q6: Debug Output Structure

**Question**: Should debug output for io be different from pipeline?

**Options**:
a) Same structure as pipeline debug
b) Extended structure showing request phase + response phase for each segment
c) Separate sections for request flow and response flow

**Recommended**: Option (b) - extend `PathSegmentInfo` with:
```python
request_phase_input: Optional[str]
request_phase_output: Optional[str]
response_phase_input: Optional[str]  # Original request + response from right
response_phase_output: Optional[str]
```

### Q7: Error Recovery in Response Phase

**Question**: If a server fails during the response phase, what happens?

**Options**:
a) Return error immediately, skip remaining servers
b) Pass original response to next server, continue chain
c) Provide error to next server in chain to handle
d) Return partial response with error information

### Q8: Content-Type Handling Through Chain

**Question**: How should content-type be managed as data flows through the chain?

**Options**:
a) Each server can set/override content-type
b) Only final (leftmost) server's content-type is used
c) io server aggregates and negotiates content-types
d) Content-type from tail propagates unless overridden

**Recommended**: Option (d) - mirrors how HTTP proxies work

---

## Dependencies

- `server_execution/pipeline_execution.py` - Source for extracted shared utilities
- `server_execution/pipeline_debug.py` - Debug formatting logic
- `server_execution/code_execution.py` - Server execution primitives
- `routes/pipelines.py` - Path parsing utilities
- `db_access/servers.py` - Server lookup

## Files to Create

1. `server_execution/segment_analysis.py` - Shared segment analysis utilities
2. `server_execution/io_execution.py` - IO execution engine
3. `reference_templates/servers/definitions/io.py` - IO server definition
4. `docs/io-requests.md` - IO documentation
5. `tests/test_io_execution.py` - Unit tests
6. `tests/test_io_server_integration.py` - Integration tests

## Files to Modify

1. `server_execution/pipeline_execution.py` - Import from shared module
2. `reference_templates/default.boot.source.json` - Add io server
3. `reference_templates/readonly.boot.source.json` - Add io server

## Estimated Scope

| Component | Effort |
|-----------|--------|
| Shared utilities extraction | Medium |
| IO execution engine | High |
| IO server definition | Low |
| Boot image updates | Low |
| Documentation | Medium |
| Unit tests | High |
| Integration tests | Medium |

---

## Implementation Order

1. Extract shared utilities (allows parallel work on tests)
2. Create IO execution engine skeleton
3. Add io server to boot images
4. Create landing page
5. Implement request phase
6. Implement response phase
7. Add debug mode support
8. Write unit tests (ongoing)
9. Write integration tests
10. Write documentation
11. Final testing and polish
