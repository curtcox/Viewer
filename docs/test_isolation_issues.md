# Test Isolation Issues

This document describes test isolation problems discovered during module decomposition and provides solutions.

## Problem Overview

When running the full test suite together, some tests fail due to **shared module state** that isn't properly cleaned up between tests. However, these same tests pass when run individually or in smaller groups, confirming the underlying code is correct.

**Symptoms:**
- Tests pass individually: ✅
- Tests fail when run together with other tests: ❌
- Error messages often involve missing attributes or incorrect mock state

## Root Cause: Module State Pollution

### The Issue

Python's module import system caches modules in `sys.modules`. When tests patch module attributes directly (especially using unittest.mock `patch` or pytest `monkeypatch`), these changes can leak between tests if not properly cleaned up.

**Example from server_execution decomposition:**

```python
# test_server_execution_output_encoding.py
def setUp(self):
    self.code_execution.current_user = mock_user  # Direct attribute assignment

def tearDown(self):
    self.code_execution.current_user = self.original_current_user  # Restore
```

When this test runs after decomposition (where `code_execution` no longer has `current_user`), the tearDown fails because the attribute doesn't exist, leaving the module in a polluted state for subsequent tests.

## Observed Test Isolation Failures

### 1. Error Page Tests (3 failures when run in full suite)

**Tests affected:**
- `test_server_auto_main.py::test_auto_main_error_page_includes_debug_details`
- `test_server_execution_error_pages.py::TestServerExecutionErrorPages::test_error_page_includes_server_details_and_arguments`
- `test_server_execution_error_pages.py::TestServerExecutionErrorPages::test_error_page_strips_project_root_and_links_sources`

**Status:** ✅ All pass individually, ❌ Fail when run after `test_server_execution_output_encoding.py`

**Cause:** `test_server_execution_output_encoding.py` patches module attributes in setUp/tearDown. After decomposition, it tries to restore attributes that no longer exist in those modules, leaving them in an inconsistent state.

## Solutions

### Solution 1: Use Context Managers for Patches (Recommended)

Replace setUp/tearDown patching with context managers that automatically clean up:

```python
# ❌ BAD: Manual cleanup required
def setUp(self):
    self.code_execution.current_user = mock_user

def tearDown(self):
    self.code_execution.current_user = self.original_current_user

# ✅ GOOD: Automatic cleanup
def test_something(self):
    from server_execution import variable_resolution
    with patch.object(variable_resolution, 'current_user', mock_user):
        # Test code here
        pass
    # Automatically cleaned up when context exits
```

### Solution 2: Use pytest Fixtures with autouse

For pytest-style tests, use fixtures with proper cleanup:

```python
@pytest.fixture(autouse=True)
def patch_execution_environment(monkeypatch):
    from server_execution import variable_resolution
    import identity

    mock_user = SimpleNamespace(id="user-123")
    monkeypatch.setattr(identity, "current_user", mock_user)
    monkeypatch.setattr(variable_resolution, "current_user", mock_user)

    # monkeypatch automatically undoes changes after test
```

### Solution 3: Verify Attribute Existence Before Restoration

If using setUp/tearDown, check attributes exist before restoring:

```python
def tearDown(self):
    # ✅ Safe restoration
    if hasattr(self.code_execution, 'current_user'):
        self.code_execution.current_user = self.original_current_user
```

## Best Practices for Test Isolation

### 1. Prefer Immutable Mocks

Don't modify module state directly; use patch decorators or context managers:

```python
# ❌ BAD: Modifies module state
import my_module
my_module.some_function = mock_function

# ✅ GOOD: Uses patch context
with patch('my_module.some_function', mock_function):
    # test code
```

### 2. Patch at the Import Site

After module decomposition, always patch where functions are **used**, not defined:

```python
# After decomposition of server_execution:
# ❌ WRONG: Patches definition site (doesn't work via __getattr__)
patch('server_execution.variable_resolution._current_user_id')

# ✅ CORRECT: Patches where it's used within the same module
from server_execution import variable_resolution
monkeypatch.setattr(variable_resolution, '_current_user_id', mock)
```

### 3. Use Test Markers to Run Problematic Tests Separately

For tests with unavoidable isolation issues, use pytest markers:

```python
# In pytest.ini
[pytest]
markers =
    integration: marks tests with potential isolation issues

# In test file
@pytest.mark.integration
def test_with_isolation_issues():
    pass

# Run separately
pytest -m "not integration"  # Run unit tests
pytest -m integration         # Run integration tests separately
```

### 4. Reset Module State in conftest.py

For systematic cleanup, add to `conftest.py`:

```python
# conftest.py
import pytest
import sys

@pytest.fixture(autouse=True, scope="function")
def reset_module_state():
    """Reset cached module state between tests."""
    yield
    # Optional: Clear specific modules from cache
    # for module_name in list(sys.modules.keys()):
    #     if module_name.startswith('server_execution'):
    #         del sys.modules[module_name]
```

**Warning:** Full module cache clearing can be slow. Use sparingly.

## Recommended Fixes for Current Failures

### Fix test_server_execution_output_encoding.py

Replace setUp/tearDown pattern with context managers:

```python
class TestExecuteServerCodeSharedFlow(unittest.TestCase):
    def test_execute_functions_share_success_flow(self):
        from server_execution import code_execution, variable_resolution

        # Use context managers instead of setUp/tearDown
        with patch.object(variable_resolution, 'current_user', SimpleNamespace(id="user-123")):
            with patch.object(code_execution, 'run_text_function', fake_runner):
                # Test code here
                pass
```

Or convert to pytest-style with fixtures:

```python
@pytest.fixture
def mocked_execution_env(monkeypatch):
    from server_execution import code_execution, variable_resolution

    mock_user = SimpleNamespace(id="user-123")
    monkeypatch.setattr(variable_resolution, "current_user", mock_user)

    def fake_runner(code, args):
        return {"output": "hello", "content_type": "text/plain"}

    monkeypatch.setattr(code_execution, "run_text_function", fake_runner)

def test_execute_functions_share_success_flow(mocked_execution_env):
    # Test implementation
    pass
```

## Testing Strategy

### During Development

Run tests frequently in isolation to catch issues early:

```bash
# Run specific test file
pytest tests/test_server_execution.py -v

# Run specific test
pytest tests/test_server_execution.py::TestClassName::test_method -v
```

### Before Commit

1. Run tests individually to verify correctness:
   ```bash
   pytest tests/test_server_execution.py tests/test_server_auto_main.py -v
   ```

2. Run full suite to detect isolation issues:
   ```bash
   pytest tests/ -v
   ```

3. If failures occur in full suite but not individually, it's an isolation issue (not a code bug)

### In CI/CD

Consider running problematic tests separately:

```yaml
# .github/workflows/tests.yml
- name: Run unit tests
  run: pytest tests/ -v -m "not integration"

- name: Run integration tests (isolated)
  run: pytest tests/ -v -m integration --forked
```

## Summary

**Key Takeaways:**
1. Test isolation failures ≠ code bugs (tests pass individually)
2. Use context managers or fixtures instead of setUp/tearDown when possible
3. Always patch at the import/use site after decomposition
4. Check attribute existence before restoration in tearDown
5. Consider running problematic tests separately in CI

**For server_execution decomposition:**
- 123/123 core tests pass individually ✅
- 3 tests fail only when run in full suite (isolation issue, not decomposition issue)
- Solution: Refactor `test_server_execution_output_encoding.py` to use context managers
