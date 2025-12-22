# Phase 7: Refactor Existing Chaining Code

## Overview

This document provides a detailed plan for refactoring `server_execution/code_execution.py` to use the new pipeline module. The goal is to consolidate duplicated chaining logic while maintaining full backward compatibility with existing tests.

---

## Current State Analysis

### Existing Chaining Functions in `code_execution.py`

The file contains **1716 lines** with significant chaining-related functionality:

#### Path Parsing & Segment Handling
| Function | Lines | Purpose | New Module Equivalent |
|----------|-------|---------|----------------------|
| `_split_path_segments()` | 253-256 | Split path into segments | `pipelines.parse_pipeline_path()` |
| `_split_request_path_segments()` | 259-271 | Split request path with URL decoding | `pipelines.parse_pipeline_path()` |
| `_remaining_path_segments()` | 274-287 | Get segments after server name | *Keep (request-specific)* |

#### CID/Content Resolution
| Function | Lines | Purpose | New Module Equivalent |
|----------|-------|---------|----------------------|
| `_resolve_cid_content()` | 95-133 | Get CID content as string | `pipeline_execution._get_segment_contents()` |
| `_load_server_literal()` | 667-703 | Load CID-based server definition | `pipeline_execution.get_server_info()` |

#### Chained Input Resolution
| Function | Lines | Purpose | New Module Equivalent |
|----------|-------|---------|----------------------|
| `_resolve_chained_input_from_path()` | 350-363 | Resolve chained input from path | `pipeline_execution.execute_pipeline()` |
| `_resolve_chained_input_for_server()` | 861-902 | Resolve input for server with literals | `pipeline_execution.execute_pipeline()` |
| `_resolve_chained_input_for_bash_arg()` | 512-532 | Resolve bash $1 input | `pipeline_execution.execute_pipeline()` |

#### Nested Path Evaluation
| Function | Lines | Purpose | New Module Equivalent |
|----------|-------|---------|----------------------|
| `_evaluate_nested_path_to_value()` | 706-780 | Recursive path evaluation | `pipeline_execution.execute_pipeline()` |
| `_execute_nested_server_to_value()` | 535-600 | Execute server in nested context | `pipeline_execution.execute_pipeline()` |
| `_execute_literal_definition_to_value()` | 603-664 | Execute CID literal in nested context | `pipeline_execution.execute_pipeline()` |

#### Language Detection
| Function | Lines | Purpose | New Module Equivalent |
|----------|-------|---------|----------------------|
| `_language_from_extension()` | 302-315 | Detect language from extension | `pipeline_execution.detect_language_from_suffix()` |
| `_is_supported_literal_extension()` | 318-319 | Check supported extensions | `pipeline_execution._EXECUTABLE_EXTENSIONS` |

---

## Refactoring Strategy

### Principles

1. **Incremental Changes**: Refactor one function at a time
2. **Test-Driven**: Run existing tests after each change
3. **Feature Parity**: Maintain exact behavior for all existing paths
4. **No Breaking Changes**: All existing Gauge specs must pass

### Risk Mitigation

- Keep original functions as private fallbacks initially
- Add feature flag to switch between old/new implementations
- Extensive logging during transition phase

---

## Implementation Plan

### Step 1: Create Compatibility Layer

**File**: `server_execution/pipeline_compat.py`

Create a thin compatibility layer that wraps the new pipeline module functions to match existing function signatures:

```python
"""Compatibility layer between old chaining code and new pipeline module."""

from server_execution.pipeline_execution import (
    execute_pipeline,
    analyze_segment,
    detect_language_from_suffix,
    validate_cid,
)
from routes.pipelines import parse_pipeline_path

def evaluate_nested_path_to_value_v2(path: str, visited=None):
    """New implementation using pipeline module."""
    result = execute_pipeline(path, debug=False)
    if not result.success:
        return None
    return result.final_output

def resolve_chained_input_from_path_v2(path: str, visited=None):
    """New implementation using pipeline module."""
    result = execute_pipeline(path, debug=False)
    if isinstance(result.final_output, Response):
        return None, result.final_output
    return result.final_output, None
```

#### Tests for Step 1

```python
class TestCompatibilityLayer(unittest.TestCase):
    """Verify compatibility layer matches old behavior."""

    def test_evaluate_nested_path_matches_old(self):
        """New implementation produces same results as old."""
        # Test with various path patterns

    def test_resolve_chained_input_matches_old(self):
        """New implementation produces same results as old."""
```

---

### Step 2: Add Feature Flag

**File**: `server_execution/code_execution.py`

Add a feature flag to toggle between old and new implementations:

```python
# At top of file
import os

_USE_PIPELINE_MODULE = os.environ.get("VIEWER_USE_PIPELINE_MODULE", "false").lower() == "true"
```

Modify `_evaluate_nested_path_to_value()`:

```python
def _evaluate_nested_path_to_value(path: str, visited=None) -> Any:
    if _USE_PIPELINE_MODULE:
        from server_execution.pipeline_compat import evaluate_nested_path_to_value_v2
        return evaluate_nested_path_to_value_v2(path, visited)

    # ... existing implementation ...
```

#### Tests for Step 2

```python
class TestFeatureFlag(unittest.TestCase):
    """Test feature flag toggles implementation."""

    @patch.dict(os.environ, {"VIEWER_USE_PIPELINE_MODULE": "true"})
    def test_uses_new_implementation(self):
        """Feature flag enables new implementation."""

    @patch.dict(os.environ, {"VIEWER_USE_PIPELINE_MODULE": "false"})
    def test_uses_old_implementation(self):
        """Feature flag disabled uses old implementation."""
```

---

### Step 3: Migrate Path Splitting Functions

Replace internal calls to `_split_path_segments` with `parse_pipeline_path`:

**Before**:
```python
segments = _split_path_segments(path)
```

**After**:
```python
from routes.pipelines import parse_pipeline_path
segments = parse_pipeline_path(path)
```

#### Files to Modify
- `server_execution/code_execution.py`
  - Line 253-256: Replace `_split_path_segments`
  - Line 353: Replace call in `_resolve_chained_input_from_path`
  - Line 520: Replace call in `_resolve_chained_input_for_bash_arg`
  - Line 725: Replace call in `_evaluate_nested_path_to_value`

#### Tests
- Run `specs/server_command_chaining.spec` - all tests must pass

---

### Step 4: Migrate CID Resolution

Replace `_resolve_cid_content` with pipeline module's CID handling:

**Current Usage (4 locations)**:
1. `_resolve_bash_path_parameters` (line 165)
2. `_resolve_bash_path_parameters` (line 204)
3. `_resolve_chained_input_for_bash_arg` (line 522)

**Migration**:
```python
from server_execution.pipeline_execution import validate_cid
from cid_presenter import format_cid
from cid_core import extract_literal_content

def _resolve_cid_content_via_pipeline(segment: str) -> Optional[str]:
    """Resolve CID using pipeline module validation."""
    is_valid, _ = validate_cid(segment)
    if not is_valid:
        return None
    # Use existing extraction logic
    ...
```

---

### Step 5: Migrate Language Detection

Replace `_language_from_extension` with pipeline module's detection:

**Current**:
```python
language = _language_from_extension(extension, definition)
```

**New**:
```python
from server_execution.pipeline_execution import detect_language_from_suffix

try:
    language = detect_language_from_suffix(f"file.{extension}")
except (UnrecognizedExtensionError, DataExtensionError):
    language = detect_server_language(definition)
```

#### Files to Modify
- `_load_server_literal` (lines 686, 702)
- `_execute_literal_definition_to_value` (line 611)
- `_execute_nested_server_to_value` (line 543)

---

### Step 6: Migrate Nested Path Evaluation

This is the core migration - replacing `_evaluate_nested_path_to_value`:

**Current Flow**:
```
_evaluate_nested_path_to_value()
  ├── Check for server by name
  │     └── _execute_nested_server_to_value()
  ├── Check for CID literal
  │     └── _execute_literal_definition_to_value()
  ├── Check for alias
  │     └── Recursive call
  └── Return CID content
```

**New Flow**:
```
execute_pipeline(path)
  ├── parse_pipeline_path()
  ├── analyze_segment() for each segment
  └── Execute right-to-left
```

**Migration Approach**:

```python
def _evaluate_nested_path_to_value(path: str, visited=None) -> Any:
    """Recursively evaluate a path to produce a value."""
    if _USE_PIPELINE_MODULE:
        from server_execution.pipeline_execution import execute_pipeline
        result = execute_pipeline(path, debug=False)
        if not result.success:
            return None
        return result.final_output

    # ... existing implementation for backward compatibility ...
```

---

### Step 7: Migrate Chained Input Resolution

Replace `_resolve_chained_input_from_path` and `_resolve_chained_input_for_server`:

**Current**:
```python
chained_input, early_response = _resolve_chained_input_from_path(path, visited)
```

**New**:
```python
from server_execution.pipeline_execution import execute_pipeline

def _resolve_chained_input_via_pipeline(path: str) -> tuple[Optional[str], Optional[Response]]:
    result = execute_pipeline(path)
    if not result.success:
        if result.error_message:
            return None, Response(result.error_message, status=500)
        return None, None
    return str(result.final_output), None
```

---

### Step 8: Add Debug Mode Integration

Integrate the debug response formatting into the request flow:

**File**: `routes/servers.py` or appropriate route handler

```python
from routes.pipelines import should_return_debug_response, is_pipeline_request
from server_execution.pipeline_execution import execute_pipeline
from server_execution.pipeline_debug import format_debug_response

@main_bp.route("/<path:path>")
def handle_request(path):
    if is_pipeline_request(path) and should_return_debug_response(request):
        result = execute_pipeline(path, debug=True)
        extension = get_final_extension(path)
        return format_debug_response(result, extension)

    # Normal execution path...
```

---

### Step 9: Remove Deprecated Code

After all tests pass with `_USE_PIPELINE_MODULE=true`:

1. Remove feature flag checks
2. Remove old implementations:
   - `_split_path_segments` (use `parse_pipeline_path`)
   - `_language_from_extension` (use `detect_language_from_suffix`)
   - `_resolve_cid_content` (use pipeline CID handling)
3. Keep essential request-context functions:
   - `_remaining_path_segments` (request-specific)
   - `_split_request_path_segments` (request-specific)

---

## Test Plan

### Unit Tests

Each step should maintain passing tests:

```bash
# After each step
python -m pytest tests/test_pipeline_*.py tests/test_server_execution.py -v
```

### Integration Tests

All Gauge specs must pass:

```bash
# After each step
gauge run specs/server_command_chaining.spec
gauge run specs/pipeline_debug.spec
```

### Manual Testing

Test matrix for critical paths:

| Path Pattern | Expected Behavior | Verified |
|--------------|-------------------|----------|
| `/echo/input` | Server receives "input" | ☐ |
| `/s2/s1` | s2 receives s1 output | ☐ |
| `/s3/s2/s1` | Three-level chain | ☐ |
| `/server/CID` | Server receives CID content | ☐ |
| `/CID.py/input` | Execute CID as Python | ☐ |
| `/grep/pattern/CID` | Bash with $1 and CID | ☐ |
| `/alias/input` | Alias resolution | ☐ |
| `/?debug=true` | Debug response | ☐ |

---

## Rollback Plan

If issues are discovered:

1. Set `VIEWER_USE_PIPELINE_MODULE=false`
2. All requests use original implementation
3. Investigate and fix issues in pipeline module
4. Re-enable with `VIEWER_USE_PIPELINE_MODULE=true`

---

## Success Criteria

1. ✅ All existing `server_command_chaining.spec` tests pass
2. ✅ All new `pipeline_debug.spec` tests pass
3. ✅ All unit tests pass
4. ✅ No performance regression (< 5% latency increase)
5. ✅ Debug mode works for all pipeline patterns
6. ✅ Code reduction: Remove ~300 lines of duplicated logic

---

## Timeline Estimates

| Step | Estimated Effort | Dependencies |
|------|------------------|--------------|
| Step 1: Compatibility Layer | 2 hours | None |
| Step 2: Feature Flag | 1 hour | Step 1 |
| Step 3: Path Splitting | 1 hour | Step 2 |
| Step 4: CID Resolution | 2 hours | Step 3 |
| Step 5: Language Detection | 1 hour | Step 4 |
| Step 6: Nested Evaluation | 4 hours | Steps 4, 5 |
| Step 7: Chained Input | 2 hours | Step 6 |
| Step 8: Debug Integration | 2 hours | Step 7 |
| Step 9: Cleanup | 2 hours | Steps 1-8 verified |

**Total**: ~17 hours

---

## Files Modified

### Primary Changes
- `server_execution/code_execution.py` - Main refactoring target
- `server_execution/pipeline_compat.py` - New compatibility layer

### Minor Changes
- `routes/servers.py` - Debug mode integration
- `routes/core.py` - Pipeline request detection

### No Changes Required
- `server_execution/pipeline_execution.py` - Already complete
- `server_execution/pipeline_debug.py` - Already complete
- `routes/pipelines.py` - Already complete

---

## Appendix: Function Dependency Graph

```
execute_server_code()
  └── _execute_server_code_common()
        ├── _resolve_bash_path_parameters()
        │     └── _resolve_cid_content()
        ├── _resolve_chained_input_for_server()
        │     ├── _load_server_literal()
        │     ├── _execute_literal_definition_to_value()
        │     │     └── _evaluate_nested_path_to_value()
        │     └── _evaluate_nested_path_to_value()
        ├── _resolve_chained_input_for_bash_arg()
        │     └── _evaluate_nested_path_to_value()
        └── _prepare_invocation()
              └── _inject_nested_parameter_value()
                    └── _evaluate_nested_path_to_value()
```

The key entry point is `_evaluate_nested_path_to_value()` which is called from multiple locations. Replacing this function with `execute_pipeline()` will propagate changes throughout the system.
