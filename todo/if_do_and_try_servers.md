# Conditional Execution Servers: if, do, and try

## Overview

Create three new servers that implement conditional execution with URL-based control flow:

1. **if** - Conditional branching (if/then/else)
2. **do** - Looping (while-style iteration)
3. **try** - Exception handling (try/catch)

These servers enable declarative control flow within the URL path structure, allowing complex conditional logic to be expressed as URLs.

## Design Principles

1. **URL-based Control Flow**: All conditions, paths, and logic are expressed in the URL
2. **Composable**: These servers can be chained with other servers in pipelines
3. **Read-Only Safe**: Included in both default and readonly boot images
4. **Consistent Semantics**: Without a second keyword, all three servers simply execute and return the path that follows

## Server Specifications

### 1. The `if` Server

#### Routes

| Pattern | Description |
|---------|-------------|
| `/if/{test}/then/{true-path}/else/{false-path}` | Execute `/{true-path}` if `{test}` is truthy, else execute `/{false-path}` |
| `/if/{test}/then/{true-path}` | Execute `/{true-path}` if `{test}` is truthy, else return `/{test}` result |
| `/if/{path}` | Simply execute and return `/{path}` (identity) |

#### Path Segment Parsing (Balanced Parsing)

Segments are parsed using **balanced parsing** that tracks nesting level for nested if statements:
- Track depth by counting `if` keywords (increment) and matching `else` keywords (decrement at same level)
- `{test}`: All segments between `/if/` and the matching `/then/` at the same nesting level
- `{true-path}`: All segments between `/then/` and the matching `/else/` at the same nesting level (or end if no else)
- `{false-path}`: All segments after the matching `/else/`

**Example**:
- `/if/a/then/b/else/c` → test=a, true=b, false=c
- `/if/x/then/if/y/then/z/else/w/else/v` → test=x, true=if/y/then/z/else/w, false=v (nested if is preserved in true-path)

#### Truthiness Definition

A value is considered **truthy** if:
- It is not empty string `""`
- It is not `"false"` (case-insensitive)
- It is not `"0"`
- It is not `"null"` (case-insensitive)
- It is not `"none"` (case-insensitive)
- The HTTP status code is less than 400

A value is considered **falsy** if:
- It is empty string `""`
- It is `"false"` (case-insensitive)
- It is `"0"`
- It is `"null"` (case-insensitive)
- It is `"none"` (case-insensitive)
- The HTTP status code is >= 400

---

### 2. The `do` Server

#### Routes

| Pattern | Description |
|---------|-------------|
| `/do/{path}/while/{test}` | Execute `/{path}` repeatedly while `/{test}` is truthy |
| `/do/{path}/while` | Execute `/{path}` repeatedly while `/variable/max_do_while` is truthy |
| `/do/{path}` | Simply execute and return `/{path}` (identity) |

#### Path Segment Parsing

Segments are parsed by looking for the keyword `while`:
- `{path}`: All segments between `/do/` and `/while/` (or end if no while)
- `{test}`: All segments after `/while/` (if present)

#### Loop Behavior

- Each iteration executes `/{path}` and collects the output
- After each iteration, `/{test}` is evaluated for truthiness
- Loop continues while test is truthy
- Returns the accumulated output from all iterations (string concatenation)
- Loop terminates when ANY of these limits is reached (whichever comes first):
  - **Cost limit**: 0.5 cents of execution cost
  - **Time limit**: 500 seconds of execution time
  - **Iteration limit**: 500 iterations

#### Default While Variable

When using `/do/{path}/while` (no test path):
- The variable `max_do_while` is fetched via `/variable/max_do_while` and evaluated for truthiness
- The variable contents are NOT modified by the do server - only read and evaluated
- The loop body `/{path}` should modify `max_do_while` (or other state) to eventually terminate the loop
- Truthiness evaluation follows the same rules as other conditions (empty, "false", "0", "null", "none" are falsy)

---

### 3. The `try` Server

#### Routes

| Pattern | Description |
|---------|-------------|
| `/try/{try-path}/catch/{catch-path}` | Execute `/{try-path}`, if exception or status >= 400, execute `/{catch-path}` |
| `/try/{path}` | Simply execute and return `/{path}` (identity) |

#### Path Segment Parsing

Segments are parsed by looking for the keyword `catch`:
- `{try-path}`: All segments between `/try/` and `/catch/` (or end if no catch)
- `{catch-path}`: All segments after `/catch/`

#### Error Detection

An error is detected if:
- An exception is thrown during `/{try-path}` execution
- The HTTP status code returned by `/{try-path}` is >= 400

#### Error Context

When `/{catch-path}` is executed, error information is passed via HTTP headers:
- `X-Error-Message`: The exception message or error description
- `X-Error-Status`: The HTTP status code from `/{try-path}` (e.g., "404", "500")
- `X-Error-Type`: The type of error ("exception" or "status")

The catch path is executed normally with these headers added to the request context.

---

## Common Behavior: Identity Execution

All three servers share the same identity behavior when invoked without their control flow keywords:

```
/if/{path}   ≡  /{path}
/do/{path}   ≡  /{path}
/try/{path}  ≡  /{path}
```

This allows these servers to act as simple pass-through wrappers when no conditional logic is needed.

---

## Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Create Shared Conditional Execution Module

**File**: `server_execution/conditional_execution.py`

```python
# Functions to create:
- parse_if_path(path_segments) -> IfPathComponents
- parse_do_path(path_segments) -> DoPathComponents
- parse_try_path(path_segments) -> TryPathComponents
- is_truthy(result) -> bool
- is_error_response(result) -> bool
- execute_path(path, context) -> ExecutionResult
- get_variable_value(name, context) -> str | None

# Data structures:
@dataclass
class IfPathComponents:
    test_path: list[str]
    true_path: list[str] | None
    false_path: list[str] | None

@dataclass
class DoPathComponents:
    body_path: list[str]
    test_path: list[str] | None
    has_implicit_while: bool  # /do/path/while (no test)

@dataclass
class TryPathComponents:
    try_path: list[str]
    catch_path: list[str] | None

@dataclass
class ExecutionResult:
    output: str | bytes
    content_type: str
    status_code: int
    exception: Exception | None
    success: bool
```

### Phase 2: Server Implementations

#### 2.1 Create `if` Server

**File**: `reference/templates/servers/definitions/if.py`

```python
def main(*path_segments, context=None):
    """
    Conditional execution server.

    Routes:
        /if/{test}/then/{true-path}/else/{false-path}
        /if/{test}/then/{true-path}
        /if/{path}
    """
```

#### 2.2 Create `do` Server

**File**: `reference/templates/servers/definitions/do.py`

```python
def main(*path_segments, context=None):
    """
    Loop execution server.

    Routes:
        /do/{path}/while/{test}
        /do/{path}/while
        /do/{path}
    """
```

#### 2.3 Create `try` Server

**File**: `reference/templates/servers/definitions/try.py`

```python
def main(*path_segments, context=None):
    """
    Exception handling server.

    Routes:
        /try/{try-path}/catch/{catch-path}
        /try/{path}
    """
```

### Phase 3: Boot Image Configuration

#### 3.1 Update Default Boot Image

**File**: `reference/templates/boot.source.json`

Add entries:
```json
{"name": "if", "definition_cid": "reference/templates/servers/definitions/if.py", "enabled": true},
{"name": "do", "definition_cid": "reference/templates/servers/definitions/do.py", "enabled": true},
{"name": "try", "definition_cid": "reference/templates/servers/definitions/try.py", "enabled": true}
```

#### 3.2 Update Read-Only Boot Image

**File**: `reference/templates/readonly.boot.source.json`

Add same entries as default.

### Phase 4: Testing

#### 4.1 Unit Tests

**File**: `tests/test_conditional_execution.py`

#### 4.2 Integration Tests

**File**: `tests/test_conditional_servers_integration.py`

---

## Test Plan

### Unit Tests: Path Parsing

#### If Path Parsing

| Test ID | Test Name | Input | Expected Result |
|---------|-----------|-------|-----------------|
| IP-01 | `test_if_then_else_parsing` | `/if/test/then/a/else/b` | test=["test"], true=["a"], false=["b"] |
| IP-02 | `test_if_then_only_parsing` | `/if/test/then/a` | test=["test"], true=["a"], false=None |
| IP-03 | `test_if_path_only_parsing` | `/if/path` | test=None, true=None, false=None, path=["path"] |
| IP-04 | `test_if_multi_segment_test` | `/if/a/b/c/then/d` | test=["a","b","c"], true=["d"] |
| IP-05 | `test_if_multi_segment_true_path` | `/if/t/then/a/b/c/else/d` | test=["t"], true=["a","b","c"], false=["d"] |
| IP-06 | `test_if_multi_segment_false_path` | `/if/t/then/a/else/x/y/z` | test=["t"], true=["a"], false=["x","y","z"] |
| IP-07 | `test_if_empty_segments_filtered` | `/if//test//then//a/` | test=["test"], true=["a"] |
| IP-08 | `test_if_case_sensitive_keywords` | `/if/Then/then/ELSE/else/x` | test=["Then"], true=["ELSE"], false=["x"] |
| IP-09 | `test_if_nested_in_true_path` | `/if/a/then/if/b/then/c/else/d/else/e` | test=["a"], true=["if","b","then","c","else","d"], false=["e"] |
| IP-10 | `test_if_nested_in_false_path` | `/if/a/then/b/else/if/c/then/d/else/e` | test=["a"], true=["b"], false=["if","c","then","d","else","e"] |
| IP-11 | `test_if_double_nested` | `/if/a/then/if/b/then/if/c/then/d/else/e` | Correctly balanced at each level |
| IP-12 | `test_if_nested_in_test` | `/if/if/a/then/b/else/c/then/d/else/e` | test=["if","a","then","b","else","c"], true=["d"], false=["e"] |

#### Do Path Parsing

| Test ID | Test Name | Input | Expected Result |
|---------|-----------|-------|-----------------|
| DP-01 | `test_do_while_test_parsing` | `/do/a/while/test` | body=["a"], test=["test"], implicit=False |
| DP-02 | `test_do_while_no_test_parsing` | `/do/a/while` | body=["a"], test=None, implicit=True |
| DP-03 | `test_do_path_only_parsing` | `/do/path` | body=["path"], test=None, implicit=False |
| DP-04 | `test_do_multi_segment_body` | `/do/a/b/c/while/t` | body=["a","b","c"], test=["t"] |
| DP-05 | `test_do_multi_segment_test` | `/do/a/while/x/y/z` | body=["a"], test=["x","y","z"] |
| DP-06 | `test_do_empty_segments_filtered` | `/do//a//while//t/` | body=["a"], test=["t"] |

#### Try Path Parsing

| Test ID | Test Name | Input | Expected Result |
|---------|-----------|-------|-----------------|
| TP-01 | `test_try_catch_parsing` | `/try/a/catch/b` | try=["a"], catch=["b"] |
| TP-02 | `test_try_only_parsing` | `/try/path` | try=["path"], catch=None |
| TP-03 | `test_try_multi_segment_try` | `/try/a/b/c/catch/d` | try=["a","b","c"], catch=["d"] |
| TP-04 | `test_try_multi_segment_catch` | `/try/a/catch/x/y/z` | try=["a"], catch=["x","y","z"] |
| TP-05 | `test_try_empty_segments_filtered` | `/try//a//catch//b/` | try=["a"], catch=["b"] |

### Unit Tests: Truthiness Evaluation

| Test ID | Test Name | Input | Expected Result |
|---------|-----------|-------|-----------------|
| TR-01 | `test_empty_string_is_falsy` | `""` | False |
| TR-02 | `test_false_string_is_falsy` | `"false"` | False |
| TR-03 | `test_FALSE_string_is_falsy` | `"FALSE"` | False |
| TR-04 | `test_False_string_is_falsy` | `"False"` | False |
| TR-05 | `test_zero_string_is_falsy` | `"0"` | False |
| TR-06 | `test_null_string_is_falsy` | `"null"` | False |
| TR-07 | `test_NULL_string_is_falsy` | `"NULL"` | False |
| TR-08 | `test_none_string_is_falsy` | `"none"` | False |
| TR-09 | `test_NONE_string_is_falsy` | `"NONE"` | False |
| TR-10 | `test_non_empty_string_is_truthy` | `"hello"` | True |
| TR-11 | `test_true_string_is_truthy` | `"true"` | True |
| TR-12 | `test_one_string_is_truthy` | `"1"` | True |
| TR-13 | `test_whitespace_is_truthy` | `" "` | True |
| TR-14 | `test_status_200_is_truthy` | status_code=200 | True |
| TR-15 | `test_status_400_is_falsy` | status_code=400 | False |
| TR-16 | `test_status_404_is_falsy` | status_code=404 | False |
| TR-17 | `test_status_500_is_falsy` | status_code=500 | False |
| TR-18 | `test_status_399_is_truthy` | status_code=399 | True |

### Unit Tests: Error Detection (try server)

| Test ID | Test Name | Input | Expected Result |
|---------|-----------|-------|-----------------|
| ED-01 | `test_exception_is_error` | Exception raised | True |
| ED-02 | `test_status_400_is_error` | status_code=400 | True |
| ED-03 | `test_status_404_is_error` | status_code=404 | True |
| ED-04 | `test_status_500_is_error` | status_code=500 | True |
| ED-05 | `test_status_200_is_not_error` | status_code=200 | False |
| ED-06 | `test_status_301_is_not_error` | status_code=301 | False |
| ED-07 | `test_status_399_is_not_error` | status_code=399 | False |

### Integration Tests: If Server

| Test ID | Test Name | URL | Expected Behavior |
|---------|-----------|-----|-------------------|
| IF-01 | `test_if_true_then_else` | `/if/echo/true/then/echo/yes/else/echo/no` | Returns "yes" |
| IF-02 | `test_if_false_then_else` | `/if/echo/false/then/echo/yes/else/echo/no` | Returns "no" |
| IF-03 | `test_if_empty_then_else` | `/if/echo//then/echo/yes/else/echo/no` | Returns "no" (empty is falsy) |
| IF-04 | `test_if_true_then_only` | `/if/echo/1/then/echo/success` | Returns "success" |
| IF-05 | `test_if_false_then_only` | `/if/echo/0/then/echo/success` | Returns "0" (test result) |
| IF-06 | `test_if_identity` | `/if/echo/hello` | Returns "hello" |
| IF-07 | `test_if_nested` | `/if/echo/true/then/if/echo/1/then/echo/inner/else/echo/outer` | Returns "inner" |
| IF-08 | `test_if_server_chain_in_test` | `/if/upper/echo/true/then/echo/yes/else/echo/no` | Executes upper(echo(true)) for test |
| IF-09 | `test_if_server_chain_in_true` | `/if/echo/1/then/upper/echo/hello/else/echo/no` | Returns "HELLO" |
| IF-10 | `test_if_server_chain_in_false` | `/if/echo/0/then/echo/yes/else/upper/echo/world` | Returns "WORLD" |
| IF-11 | `test_if_with_query_params` | `/if/echo/true/then/echo/yes?format=json` | Query params passed through |
| IF-12 | `test_if_error_status_is_falsy` | `/if/nonexistent/then/echo/yes/else/echo/error` | Returns "error" (404 is falsy) |
| IF-13 | `test_if_null_string_falsy` | `/if/echo/null/then/echo/yes/else/echo/no` | Returns "no" |
| IF-14 | `test_if_whitespace_truthy` | `/if/echo/%20/then/echo/yes/else/echo/no` | Returns "yes" (space is truthy) |

### Integration Tests: Do Server

| Test ID | Test Name | URL | Expected Behavior |
|---------|-----------|-----|-------------------|
| DO-01 | `test_do_while_false_immediate` | `/do/echo/x/while/echo/false` | Returns "x" (one iteration) |
| DO-02 | `test_do_identity` | `/do/echo/hello` | Returns "hello" |
| DO-03 | `test_do_while_variable` | `/do/echo/x/while` | Loops based on max_do_while variable |
| DO-04 | `test_do_max_iterations_limit` | `/do/echo/x/while/echo/true` | Stops at 500 iterations |
| DO-05 | `test_do_accumulates_output` | `/do/echo/x/while/...` | Output is concatenated from all iterations |
| DO-06 | `test_do_server_chain_in_body` | `/do/upper/echo/hi/while/echo/false` | Returns "HI" |
| DO-07 | `test_do_server_chain_in_test` | `/do/echo/x/while/upper/echo/false` | Test evaluates upper(echo(false)) |
| DO-08 | `test_do_nested` | `/do/do/echo/y/while/echo/false/while/echo/false` | Nested loops work |
| DO-09 | `test_do_with_query_params` | `/do/echo/x/while/echo/false?debug=true` | Query params passed through |
| DO-10 | `test_do_body_can_modify_variable` | (variable-based test) | Body execution can change loop variable |
| DO-11 | `test_do_time_limit` | Long-running loop | Stops at 500 seconds |
| DO-12 | `test_do_cost_limit` | Expensive loop | Stops at 0.5 cents |
| DO-13 | `test_do_termination_header` | Loop hits limit | `X-Loop-Terminated` header present |

### Integration Tests: Try Server

| Test ID | Test Name | URL | Expected Behavior |
|---------|-----------|-----|-------------------|
| TRY-01 | `test_try_success_no_catch` | `/try/echo/hello` | Returns "hello" |
| TRY-02 | `test_try_success_with_catch` | `/try/echo/hello/catch/echo/error` | Returns "hello" |
| TRY-03 | `test_try_404_triggers_catch` | `/try/nonexistent/catch/echo/caught` | Returns "caught" |
| TRY-04 | `test_try_500_triggers_catch` | `/try/error-server/catch/echo/caught` | Returns "caught" |
| TRY-05 | `test_try_exception_triggers_catch` | `/try/throw/catch/echo/caught` | Returns "caught" |
| TRY-06 | `test_try_identity` | `/try/echo/hello` | Returns "hello" |
| TRY-07 | `test_try_server_chain_in_try` | `/try/upper/echo/hello/catch/echo/error` | Returns "HELLO" |
| TRY-08 | `test_try_server_chain_in_catch` | `/try/nonexistent/catch/upper/echo/caught` | Returns "CAUGHT" |
| TRY-09 | `test_try_nested` | `/try/try/nonexistent/catch/echo/inner/catch/echo/outer` | Returns "inner" |
| TRY-10 | `test_try_catch_receives_error_context` | (context test) | Catch path has access to error info |
| TRY-11 | `test_try_with_query_params` | `/try/echo/x/catch/echo/y?param=val` | Query params passed through |
| TRY-12 | `test_try_status_399_not_error` | `/try/status399/catch/echo/caught` | Returns status399 result (not caught) |
| TRY-13 | `test_try_status_400_is_error` | `/try/status400/catch/echo/caught` | Returns "caught" |

### Integration Tests: Identity Equivalence

| Test ID | Test Name | URLs | Expected Behavior |
|---------|-----------|------|-------------------|
| ID-01 | `test_if_identity_equivalence` | `/if/echo/hello` ≡ `/echo/hello` | Same output |
| ID-02 | `test_do_identity_equivalence` | `/do/echo/hello` ≡ `/echo/hello` | Same output |
| ID-03 | `test_try_identity_equivalence` | `/try/echo/hello` ≡ `/echo/hello` | Same output |
| ID-04 | `test_all_three_identity_same` | `/if/p`, `/do/p`, `/try/p` | All return same as `/p` |

### Integration Tests: Cross-Server Combinations

| Test ID | Test Name | URL | Expected Behavior |
|---------|-----------|-----|-------------------|
| CS-01 | `test_if_inside_try` | `/try/if/echo/false/then/throw/else/echo/ok/catch/echo/caught` | Returns "ok" |
| CS-02 | `test_try_inside_if` | `/if/echo/true/then/try/throw/catch/echo/caught/else/echo/no` | Returns "caught" |
| CS-03 | `test_do_inside_if` | `/if/echo/1/then/do/echo/x/while/echo/false/else/echo/no` | Returns "x" |
| CS-04 | `test_if_inside_do` | `/do/if/echo/1/then/echo/y/while/echo/false` | Returns "y" |
| CS-05 | `test_try_inside_do` | `/do/try/echo/ok/catch/echo/err/while/echo/false` | Returns "ok" |
| CS-06 | `test_all_three_nested` | `/try/if/echo/1/then/do/echo/x/while/echo/false/catch/echo/err` | Returns "x" |

### Integration Tests: Cost Estimate Server

| Test ID | Test Name | URL | Expected Behavior |
|---------|-----------|-----|-------------------|
| CE-01 | `test_cost_estimate_basic` | `/cost_estimate/echo` | Returns numeric cost string |
| CE-02 | `test_cost_estimate_with_input_size` | `/cost_estimate/echo?input_size=1000` | Higher cost than CE-01 |
| CE-03 | `test_cost_estimate_with_output_size` | `/cost_estimate/echo?output_size=1000` | Higher cost than CE-01 |
| CE-04 | `test_cost_estimate_with_execution_time` | `/cost_estimate/echo?execution_time=100` | Higher cost than CE-01 |
| CE-05 | `test_cost_estimate_combined` | `/cost_estimate/echo?input_size=500&output_size=500&execution_time=50` | Cumulative cost |
| CE-06 | `test_cost_estimate_returns_text` | `/cost_estimate/echo` | content_type is text/plain |
| CE-07 | `test_cost_estimate_parseable_float` | `/cost_estimate/echo` | Output parses as float |

### Integration Tests: Boot Image Verification

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| BI-01 | `test_if_in_default_boot` | Parse default.boot.source.json | if server present |
| BI-02 | `test_do_in_default_boot` | Parse default.boot.source.json | do server present |
| BI-03 | `test_try_in_default_boot` | Parse default.boot.source.json | try server present |
| BI-04 | `test_if_in_readonly_boot` | Parse readonly.boot.source.json | if server present |
| BI-05 | `test_do_in_readonly_boot` | Parse readonly.boot.source.json | do server present |
| BI-06 | `test_try_in_readonly_boot` | Parse readonly.boot.source.json | try server present |
| BI-07 | `test_cost_estimate_in_default_boot` | Parse default.boot.source.json | cost_estimate server present |
| BI-08 | `test_cost_estimate_in_readonly_boot` | Parse readonly.boot.source.json | cost_estimate server present |
| BI-09 | `test_servers_enabled` | All four enabled | `enabled == true` |
| BI-10 | `test_definitions_exist` | Definition files exist | All 4 files found |

### Edge Case Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EC-01 | `test_if_empty_test_path` | `/if//then/a/else/b` | Error or empty is falsy |
| EC-02 | `test_if_empty_true_path` | `/if/test/then//else/b` | Returns empty or error |
| EC-03 | `test_do_zero_iterations` | Test immediately false | Returns empty or single iteration |
| EC-04 | `test_do_exceeds_max_iterations` | Infinite loop attempt | Stops at 500 iterations, returns accumulated |
| EC-05 | `test_try_catch_also_throws` | `/try/throw/catch/throw` | Error bubbles up |
| EC-06 | `test_url_encoded_keywords` | `/if/%74%68%65%6e/then/a` | Keywords not decoded from URL |
| EC-07 | `test_literal_then_in_path` | `/if/test/then/echo/then` | `then` after first is part of path |
| EC-08 | `test_literal_else_in_path` | `/if/t/then/a/else/echo/else` | `else` after first is part of path |
| EC-09 | `test_literal_while_in_path` | `/do/echo/while/while/test` | Second `while` is test path |
| EC-10 | `test_literal_catch_in_path` | `/try/echo/catch/catch/handler` | Second `catch` is catch path |
| EC-11 | `test_very_long_path` | 100+ segments | Handled correctly |
| EC-12 | `test_special_chars_in_segments` | `/if/echo/hello%20world/then/...` | URL decoded correctly |
| EC-13 | `test_binary_output` | Binary data through conditionals | Bytes preserved |
| EC-14 | `test_unicode_output` | Unicode through conditionals | Encoding preserved |
| EC-15 | `test_content_type_preserved` | Server sets content-type | Content-type preserved |

---

## Resolved Design Decisions

### D1: Keyword Parsing Strategy

**Decision**: Balanced parsing - Track nesting level for nested if statements

The parser tracks nesting depth by counting control flow keywords:
- When `if` is encountered, increment depth
- When the matching `then`/`else` at the current depth is found, that's the boundary
- This allows nested conditionals to be properly parsed without ambiguity

**Example**:
```
/if/x/then/if/y/then/z/else/w/else/v
         ^depth 1 then     ^depth 1 else

Parses as: test=x, true=if/y/then/z/else/w, false=v
```

**Rationale**: Enables arbitrarily nested conditionals without requiring escape mechanisms.

---

### D2: Implicit While Condition

**Decision**: Use `/variable/max_do_while` as the test, evaluated for truthiness (not modified)

When `/do/{path}/while` is used (no explicit test path):
- The value of the `max_do_while` variable is fetched and evaluated for truthiness
- The do server does NOT modify this variable
- The loop body is responsible for updating `max_do_while` to terminate the loop
- Evaluation uses the same truthiness rules as explicit tests

**Rationale**: Consistent with the pattern of evaluating conditions without side effects. The loop body has full control over termination.

---

### D3: Loop Output Accumulation

**Decision**: String concatenation

Output from each iteration is concatenated directly:
```python
accumulated_output = ""
for iteration in range(max_iterations):
    result = execute(body_path)
    accumulated_output += result.output
    if not is_truthy(evaluate(test_path)):
        break
return accumulated_output
```

**Rationale**: Simple and predictable. Users can format output (newlines, JSON, etc.) within the loop body if needed.

---

### D4: Error Context for Catch Path

**Decision**: Error message in headers

When the catch path is executed, error information is passed via HTTP headers:
- `X-Error-Message`: The exception message or error description
- `X-Error-Status`: The HTTP status code from the try path (e.g., "404", "500")
- `X-Error-Type`: The type of error ("exception" or "status")

**Rationale**: Headers are accessible to all server types without changing function signatures. Clean separation of error context from request body.

---

### D5: Keyword Case Sensitivity

**Decision**: Case-sensitive lowercase only

Keywords must be exactly: `then`, `else`, `while`, `catch`

- `THEN`, `Then`, `WHILE`, `Catch` are NOT recognized as keywords
- They are treated as regular path segments (server names or parameters)

**Rationale**: Explicit and unambiguous. Consistent with URL path conventions which are typically case-sensitive.

---

### D6: Keyword vs Server Name Conflicts

**Decision**: Keywords take precedence within their respective servers only

- In `/if/...` paths: `then` and `else` are always keywords
- In `/do/...` paths: `while` is always a keyword
- In `/try/...` paths: `catch` is always a keyword
- **Other servers are NOT affected**: A server named `then` works normally in `/pipeline/then/data`

If a user has a server named `then`:
- It cannot be used in `/if/...` paths (keyword takes precedence)
- It works normally everywhere else (regular server execution)

**Rationale**: Minimal impact on existing functionality. Keywords are scoped to their control flow servers only.

---

### D7: Loop Termination Limits

**Decision**: Triple limit - whichever is reached first terminates the loop

Loop terminates when ANY of these limits is reached:
1. **Cost limit**: 0.5 cents of execution cost
2. **Time limit**: 500 seconds of elapsed time
3. **Iteration limit**: 500 iterations

When a limit is reached:
- The loop stops immediately
- Accumulated output up to that point is returned
- A warning header may be added: `X-Loop-Terminated: cost|time|iterations`

**Rationale**: Defense in depth against runaway loops. Cost-based limiting prevents expensive infinite loops even with short iterations.

---

### D8: No-Else Case Return Value

**Decision**: Return test result

For `/if/{test}/then/{true-path}` when test is falsy:
- Return the result of executing `/{test}` (output, content-type, status code)
- The true-path is not executed

**Example**:
```
/if/echo/0/then/echo/success
→ Returns "0" (the test result, since 0 is falsy)

/if/echo/hello/then/echo/success
→ Returns "success" (test was truthy, true-path executed)
```

**Rationale**: Preserves test result information. Useful for debugging and for pipelines that consume the test output.

---

### D9: Path Execution Method

**Decision**: Internal execution

Use `server_execution.try_server_execution()` directly for all path execution:
- No HTTP requests to self
- Shared context and state
- Lower overhead
- Consistent with pipeline execution

**Rationale**: Internal execution is simpler, faster, and maintains context properly. HTTP would add unnecessary complexity and latency.

---

### D10: Content-Type Handling

**Decision**: From executed branch

The content-type from whichever branch was actually executed is used:
- For if: content-type from true-path or false-path (whichever ran)
- For do: content-type from the final iteration (or last accumulated)
- For try: content-type from try-path if successful, or catch-path if triggered

**Rationale**: Predictable and transparent. The executed code determines its own content-type.

---

### D11: Cost Tracking Mechanism

**Decision**: Create a `/cost_estimate` server with placeholder estimation function

A new `cost_estimate` server will be added to the boot images:

**Route**: `/cost_estimate/{path}?input_size={}&output_size={}&execution_time={}`

**Parameters**:
- `path`: The server/path being estimated
- `input_size`: Size of input data in bytes (optional)
- `output_size`: Size of output data in bytes (optional)
- `execution_time`: Execution time in milliseconds (optional)

**Initial Implementation**:
```python
def main(path="", input_size=0, output_size=0, execution_time=0, *, context=None):
    """
    Placeholder cost estimation server.
    Returns estimated cost in cents for executing the given path.

    Initial implementation uses simple heuristics:
    - Base cost per invocation
    - Additional cost based on data size
    - Additional cost based on execution time

    This is a placeholder for future refinement with actual cost data.
    """
    # Placeholder estimation - to be refined
    base_cost = 0.0001  # 0.01 cents per invocation
    size_cost = (input_size + output_size) * 0.000001  # per byte
    time_cost = execution_time * 0.00001  # per millisecond

    total_cents = base_cost + size_cost + time_cost
    return {"output": str(total_cents), "content_type": "text/plain"}
```

**Usage by do server**:
- After each iteration, call `/cost_estimate` with accumulated metrics
- Compare returned value against 0.5 cent limit
- Terminate loop if limit exceeded

**Rationale**: Provides a pluggable cost estimation system that can be refined over time. The placeholder implementation ensures the infrastructure exists while allowing future improvements without changing the control flow servers.

---

### D12: Cross-Server Keyword Handling

**Decision**: Each server only handles its own keywords and delegates paths to other servers

Each control flow server:
- Only recognizes and parses its own keywords
- Treats other control flow keywords as regular path segments
- Delegates execution of nested paths to the appropriate servers

**Keyword ownership**:
- `if` server: `then`, `else`
- `do` server: `while`
- `try` server: `catch`

**Example**: `/if/a/then/do/b/while/c/else/d`

Parsing by `if` server:
1. Scan for `then` and `else` (ignoring `while` - not our keyword)
2. test = `["a"]`
3. true-path = `["do", "b", "while", "c"]` (entire path including `while`)
4. false-path = `["d"]`

When true-path is executed:
- The `if` server calls `/do/b/while/c`
- The `do` server then parses its own `while` keyword

**Example**: `/if/a/then/try/b/catch/if/c/then/d/else/e/else/f`

Parsing by outer `if` server:
1. Scan for `then` and `else` (its keywords only)
2. test = `["a"]`
3. true-path = `["try", "b", "catch", "if", "c", "then", "d", "else", "e"]`
4. false-path = `["f"]`

The inner `if` keywords (`then`, `else`) are part of the true-path and will be parsed when that nested `if` executes.

**Rationale**: Clean separation of concerns. Each server is responsible only for its own control flow. This avoids complex cross-server parsing logic and makes behavior predictable.

---

## Dependencies

- `server_execution/code_execution.py` - Server execution primitives
- `server_execution/pipeline_execution.py` - Pipeline execution (for internal path execution)
- `routes/servers.py` - Server routing
- `db_access/servers.py` - Server lookup
- `db_access/variables.py` - Variable access (for max_do_while, max_do_iterations)

## Files to Create

1. `server_execution/conditional_execution.py` - Shared conditional execution utilities
2. `reference/templates/servers/definitions/if.py` - If server definition
3. `reference/templates/servers/definitions/do.py` - Do server definition
4. `reference/templates/servers/definitions/try.py` - Try server definition
5. `reference/templates/servers/definitions/cost_estimate.py` - Cost estimation server
6. `tests/test_conditional_execution.py` - Unit tests
7. `tests/test_conditional_servers_integration.py` - Integration tests
8. `tests/test_cost_estimate_server.py` - Cost estimation tests

## Files to Modify

1. `reference/templates/boot.source.json` - Add if, do, try, cost_estimate servers
2. `reference/templates/readonly.boot.source.json` - Add if, do, try, cost_estimate servers

## Implementation Order

1. [x] Create shared conditional execution module with path parsing
2. [x] Implement truthiness evaluation and error detection
3. [x] Create cost_estimate server with placeholder implementation
4. [x] Create if server with identity behavior
5. [x] Add if/then/else logic with balanced parsing
6. [x] Create do server with identity behavior
7. [x] Add do/while logic with triple limits (cost, time, iterations)
8. [x] Create try server with identity behavior
9. [x] Add try/catch logic with error headers
10. [x] Add all servers to boot images
11. [x] Write unit tests (ongoing)
12. [x] Write integration tests

---

## Estimated Scope

| Component | Effort |
|-----------|--------|
| Path parsing utilities | Medium |
| Truthiness evaluation | Low |
| Cost estimate server | Low |
| If server implementation | Medium |
| Do server implementation | Medium-High |
| Try server implementation | Medium |
| Boot image updates | Low |
| Unit tests | High |
| Integration tests | High |
