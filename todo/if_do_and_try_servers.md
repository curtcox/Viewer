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

#### Path Segment Parsing

Segments are parsed by looking for the keywords `then` and `else`:
- `{test}`: All segments between `/if/` and `/then/`
- `{true-path}`: All segments between `/then/` and `/else/` (or end if no else)
- `{false-path}`: All segments after `/else/`

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
- Returns the accumulated output from all iterations (concatenated)
- Maximum iteration limit enforced via `/variable/max_do_iterations` (default: 100)

#### Default While Variable

When using `/do/{path}/while` (no test path):
- The variable `max_do_while` controls the loop
- This variable should be decremented or set to falsy by `/{path}` to terminate the loop

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

When `/{catch-path}` is executed, the following context is available:
- The original exception message (if any)
- The status code from `/{try-path}`
- The error output from `/{try-path}`

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
| DO-04 | `test_do_max_iterations_limit` | `/do/echo/x/while/echo/true` | Stops at max_do_iterations (100) |
| DO-05 | `test_do_accumulates_output` | `/do/echo/x/while/...` | Output is concatenated from all iterations |
| DO-06 | `test_do_server_chain_in_body` | `/do/upper/echo/hi/while/echo/false` | Returns "HI" |
| DO-07 | `test_do_server_chain_in_test` | `/do/echo/x/while/upper/echo/false` | Test evaluates upper(echo(false)) |
| DO-08 | `test_do_nested` | `/do/do/echo/y/while/echo/false/while/echo/false` | Nested loops work |
| DO-09 | `test_do_with_query_params` | `/do/echo/x/while/echo/false?debug=true` | Query params passed through |
| DO-10 | `test_do_body_can_modify_variable` | (variable-based test) | Body execution can change loop variable |

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

### Integration Tests: Boot Image Verification

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| BI-01 | `test_if_in_default_boot` | Parse default.boot.source.json | if server present |
| BI-02 | `test_do_in_default_boot` | Parse default.boot.source.json | do server present |
| BI-03 | `test_try_in_default_boot` | Parse default.boot.source.json | try server present |
| BI-04 | `test_if_in_readonly_boot` | Parse readonly.boot.source.json | if server present |
| BI-05 | `test_do_in_readonly_boot` | Parse readonly.boot.source.json | do server present |
| BI-06 | `test_try_in_readonly_boot` | Parse readonly.boot.source.json | try server present |
| BI-07 | `test_servers_enabled` | All three enabled | `enabled == true` |
| BI-08 | `test_definitions_exist` | Definition files exist | Files found |

### Edge Case Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| EC-01 | `test_if_empty_test_path` | `/if//then/a/else/b` | Error or empty is falsy |
| EC-02 | `test_if_empty_true_path` | `/if/test/then//else/b` | Returns empty or error |
| EC-03 | `test_do_zero_iterations` | Test immediately false | Returns empty or single iteration |
| EC-04 | `test_do_exceeds_max_iterations` | Infinite loop attempt | Stops at max, returns accumulated |
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

## Open Questions

### Q1: How should the `then` and `else` keywords be parsed?

**Options**:
1. **First occurrence** - Parse left-to-right, first `then` splits test from true-path
2. **Greedy test** - Longest possible test path (last `then` before first `else`)
3. **Balanced parsing** - Track nesting level for nested if statements

**Current Assumption**: First occurrence (Option 1). The first `then` encountered after `/if/` marks the end of the test path. Nested `if` statements would need the outer `then` to come first.

**Example**:
- `/if/a/then/b/else/c` → test=a, true=b, false=c (clear)
- `/if/a/b/then/c/then/d/else/e` → test=a/b, true=c/then/d, false=e
- For nested: `/if/x/then/if/y/then/z/else/w/else/v` → test=x, true=if/y/then/z/else/w, false=v

**Question**: Is first-occurrence parsing correct, or do we need more sophisticated parsing for deeply nested conditionals?

---

### Q2: What should `/do/{path}/while` (implicit while) use as its condition?

**Current Assumption**: Uses the variable `max_do_while` from context.

**Options**:
1. **Named variable**: Use `/variable/max_do_while` as the test
2. **Counter variable**: Auto-decrementing counter variable
3. **Remove implicit while**: Require explicit test path always

**Question**: Is the `max_do_while` variable approach correct? How should it be initialized and modified?

---

### Q3: How should the do server accumulate output from multiple iterations?

**Options**:
1. **String concatenation**: `output += iteration_result`
2. **Newline-separated**: `output += iteration_result + "\n"`
3. **JSON array**: `[result1, result2, ...]`
4. **Last iteration only**: Only return final iteration's output

**Question**: Which accumulation strategy is most useful?

---

### Q4: What information should be passed to the catch path?

**Options**:
1. **Nothing extra**: Just execute catch path normally
2. **Error message in header**: `X-Error-Message` header
3. **Error as input**: Exception/error message as body input to catch path
4. **Context variables**: Set error variables (error_message, error_code, etc.)

**Question**: How should error context be communicated to the catch handler?

---

### Q5: Should keywords be case-sensitive?

**Current Assumption**: Yes, keywords (`then`, `else`, `while`, `catch`) are case-sensitive and must be lowercase.

**Options**:
1. **Case-sensitive lowercase only**: `then`, `else`, `while`, `catch`
2. **Case-insensitive**: `THEN`, `Then`, `then` all work
3. **Case-insensitive with canonical form**: Accept any case, normalize internally

**Question**: Should we accept `THEN`, `Else`, `WHILE`, `Catch`?

---

### Q6: How should keyword conflicts with server names be handled?

What if a server is named `then`, `else`, `while`, or `catch`?

**Options**:
1. **Keywords take precedence**: `then` is always a keyword in if paths
2. **Escape mechanism**: `\then` or `%then` to use as path segment
3. **Context-aware**: Only treat as keyword if in correct position
4. **Prohibit conflicting names**: Don't allow servers with these names

**Current Assumption**: Keywords take precedence. If you have a server named `then`, it cannot be used in if paths.

**Question**: Is keyword precedence acceptable, or do we need an escape mechanism?

---

### Q7: What is the maximum iteration limit for do loops?

**Current Assumption**: 100 iterations, configurable via `/variable/max_do_iterations`.

**Options**:
1. **Fixed limit**: Hard-coded maximum (e.g., 100)
2. **Configurable via variable**: Use `max_do_iterations` variable
3. **No limit**: Trust the user (risky)
4. **Timeout-based**: Time limit instead of iteration count

**Question**: What should the default and maximum limits be?

---

### Q8: How should the test path result be used in `/if/{test}/then/{true-path}`?

When there's no else clause and the test is falsy, what should be returned?

**Current Assumption**: Return the result of executing `/{test}`.

**Options**:
1. **Return test result**: Return whatever the test path returned
2. **Return empty**: Return empty string/response
3. **Return error**: Return 404 or similar error status
4. **Return literal test path**: Return the path string itself

**Question**: Which behavior is most useful for the no-else case?

---

### Q9: Should path execution be internal or use HTTP?

**Options**:
1. **Internal execution**: Use `server_execution.try_server_execution()` directly
2. **HTTP request**: Make HTTP request to own server (self-referential)
3. **Hybrid**: Internal when possible, HTTP as fallback

**Current Assumption**: Internal execution using existing server execution infrastructure.

**Question**: Is internal execution sufficient, or are there cases where HTTP is needed?

---

### Q10: How should content-type be handled through conditionals?

When different branches return different content types, which should be used?

**Options**:
1. **From executed branch**: Use content-type from whichever path was executed
2. **Force specific type**: Always return text/html or application/json
3. **Inherit from outer context**: Use content-type from the overall request

**Current Assumption**: Use content-type from the executed branch (option 1).

**Question**: Is pass-through of content-type correct?

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
5. `tests/test_conditional_execution.py` - Unit tests
6. `tests/test_conditional_servers_integration.py` - Integration tests

## Files to Modify

1. `reference/templates/boot.source.json` - Add if, do, try servers
2. `reference/templates/readonly.boot.source.json` - Add if, do, try servers

## Implementation Order

1. Create shared conditional execution module with path parsing
2. Implement truthiness evaluation and error detection
3. Create if server with identity behavior
4. Add if/then/else logic
5. Create do server with identity behavior
6. Add do/while logic with iteration limits
7. Create try server with identity behavior
8. Add try/catch logic
9. Add to boot images
10. Write unit tests (ongoing)
11. Write integration tests
12. Resolve open questions through iteration

---

## Estimated Scope

| Component | Effort |
|-----------|--------|
| Path parsing utilities | Medium |
| Truthiness evaluation | Low |
| If server implementation | Medium |
| Do server implementation | Medium-High |
| Try server implementation | Medium |
| Boot image updates | Low |
| Unit tests | High |
| Integration tests | High |
