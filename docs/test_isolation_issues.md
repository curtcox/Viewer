# Test Isolation Issues

This document describes test isolation problems discovered during module decomposition and provides solutions.

## Current Status

**Test Results:**
- **Before fixes**: 9 failed, 969 passed
- **After initial fixes**: 3 failed, 975 passed
- **After final fixes**: 0 failed, 978 passed ✅
- **Fixed**: All 9 test failures (6 module decomposition + 3 Flask context issues)

**All tests now pass!**

## What Was Fixed

### 1. Flake8 E731 Violations
**File:** `tests/test_server_execution_output_encoding.py` (lines 155-178, 199-221)

Replaced lambda-assigned mock helpers with regular `def` functions:
```python
# ❌ BAD (flake8 E731 violation)
mock_build_request_args = lambda: {"request": {...}, "context": {...}}
mock_make_response = lambda text: SimpleNamespace(headers={}, status_code=200, data=text)

# ✅ GOOD
def mock_build_request_args():
    return {"request": {...}, "context": {...}}

def mock_make_response(text):
    return SimpleNamespace(headers={}, status_code=200, data=text)
```

### 2. Test Patches for Decomposed Modules
After server_execution module decomposition, patches needed to be updated to reference the correct submodule paths:

**test_versioned_server_invocation.py:**
```python
# ❌ OLD (before decomposition)
@patch('server_execution.get_server_by_name')
@patch('server_execution.current_user')
def test_foo(self, mock_user, mock_get_server):
    mock_user.id = self.user_id

# ✅ NEW (after decomposition)
@patch('server_execution.server_lookup.get_server_by_name')
@patch('server_execution.server_lookup._current_user_id')
def test_foo(self, mock_user_id, mock_get_server):
    mock_user_id.return_value = self.user_id
```

**test_echo_functionality.py:**
```python
# ❌ OLD
@patch('server_execution.current_user')
@patch('server_execution.run_text_function')

# ✅ NEW
@patch('server_execution.server_lookup._current_user_id')
@patch('server_execution.code_execution.run_text_function')
```

**test_variables_secrets_issue.py:**
```python
# ❌ OLD
@patch('server_execution.get_user_variables')
@patch('server_execution.current_user')

# ✅ NEW
@patch('server_execution.code_execution.get_user_variables')
@patch('server_execution.code_execution._current_user_id')
```

## Fixed Flask/SQLAlchemy Context Problems

### Fix 1: test_variables_secrets_issue.py (2 tests)

Both `test_build_request_args_with_model_objects` and `test_build_request_args_skips_disabled_entries` were failing with "Working outside of request context" errors.

**Problem:** These tests call `build_request_args()` which internally accesses `flask.request`, but they were using `patch.dict('server_execution.__dict__', {'request': mock_request})` which doesn't work because Flask's `request` is a LocalProxy that requires an active request context.

**Solution:** Replaced the `patch.dict` approach with `app.test_request_context()`:

```python
from app import app

# ❌ OLD (doesn't work)
with patch.dict('server_execution.__dict__', {'request': mock_request}):
    args = build_request_args()

# ✅ NEW (works correctly)
with app.test_request_context('/echo1'):
    args = build_request_args()
```

### Fix 2: test_server_auto_main.py (1 test)

The test `test_auto_main_reads_cid_content_for_remaining_parameter` was failing with "no such table: alias" error.

**Problem:** The test was mocking `server_execution.find_matching_alias`, but `code_execution.py` imports it directly via `from alias_routing import find_matching_alias`. This meant the monkeypatch wasn't affecting the actual function call, causing a real database query.

**Solution:** Patch `find_matching_alias` where it's used (in `code_execution` module):

```python
# ❌ OLD (wrong patch location)
monkeypatch.setattr(server_execution, "find_matching_alias", lambda path: None)

# ✅ NEW (correct patch location)
from server_execution import code_execution
monkeypatch.setattr(code_execution, "find_matching_alias", lambda path: None)
```

## Best Practices for Test Isolation

### 1. Always Patch at the Import Site

After module decomposition, patch where functions are **used**, not defined:

```python
# After decomposition of server_execution:
# ❌ WRONG: Patches definition site
@patch('server_execution.variable_resolution._current_user_id')

# ✅ CORRECT: Patches the submodule where it's used
from server_execution import server_lookup
with patch.object(server_lookup, '_current_user_id', mock):
    ...

# OR patch at the import path
@patch('server_execution.server_lookup._current_user_id')
```

### 2. Use Context Managers for Patches

Replace setUp/tearDown patching with context managers that automatically clean up:

```python
# ❌ BAD: Manual cleanup required
def setUp(self):
    self.original_user = code_execution.current_user
    code_execution.current_user = mock_user

def tearDown(self):
    code_execution.current_user = self.original_user

# ✅ GOOD: Automatic cleanup
def test_something(self):
    from server_execution import variable_resolution
    with patch.object(variable_resolution, 'current_user', mock_user):
        # Test code here
        pass
    # Automatically cleaned up when context exits
```

### 3. Use Flask Test Contexts for Request/App Access

When tests need Flask request or application context:

```python
from app import app

# For request-dependent code
with app.test_request_context('/path', method='POST'):
    result = function_that_uses_request()

# For application-dependent code (database, etc.)
with app.app_context():
    result = function_that_uses_db()

# For both
with app.app_context():
    with app.test_request_context('/path'):
        result = function_that_uses_both()
```

### 4. Avoid Direct Module Attribute Modification

Don't modify module state directly; use patch decorators or context managers:

```python
# ❌ BAD: Modifies module state
import my_module
my_module.some_function = mock_function

# ✅ GOOD: Uses patch context
with patch('my_module.some_function', mock_function):
    # test code
```

## Testing Strategy

### During Development

Run tests frequently to catch issues early:

```bash
# Run specific test file
pytest tests/test_server_execution_output_encoding.py -v

# Run specific test
pytest tests/test_server_auto_main.py::test_auto_main_reads_cid_content_for_remaining_parameter -v

# Run multiple related tests
pytest tests/test_versioned_server_invocation.py tests/test_echo_functionality.py -v
```

### Before Commit

1. Run tests individually to verify correctness
2. Run full suite to detect isolation issues:
   ```bash
   PYTHONPATH=/home/user/Viewer python -m pytest tests/ -v
   ```
3. If failures occur in full suite but not individually, it's an isolation issue

### Debugging Test Failures

When a test fails, determine if it's an isolation issue:

```bash
# Run the failing test alone
pytest tests/test_foo.py::test_bar -v

# If it passes alone but fails in suite, it's an isolation issue
# Run it with the test that might be polluting state
pytest tests/test_polluter.py tests/test_foo.py -v
```

## Summary

**Final State:**
- ✅ Fixed 6 test failures related to module decomposition patches
- ✅ Fixed all flake8 E731 violations in test_server_execution_output_encoding.py
- ✅ Fixed 2 Flask request context issues in test_variables_secrets_issue.py
- ✅ Fixed 1 monkeypatch location issue in test_server_auto_main.py
- ✅ **All 978 tests passing!**

**Key Takeaways:**
1. Always patch at the import/use site after module decomposition
2. Use context managers for patches instead of setUp/tearDown
3. Flask-dependent tests need `app.test_request_context()` for request-dependent code
4. When patching imports, patch where the function is used, not where it's exposed
5. Test isolation failures ≠ code bugs (tests pass individually)

**Changes Made:**
1. **test_variables_secrets_issue.py**: Replaced `patch.dict` with `app.test_request_context()` for proper Flask request context
2. **test_server_auto_main.py**: Fixed monkeypatch location to patch `code_execution.find_matching_alias` instead of `server_execution.find_matching_alias`
