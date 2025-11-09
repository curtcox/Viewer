# Module Decomposition Documentation

This document provides guidance for decomposing oversized modules to address pylint C0302 (too-many-lines) warnings and improve code maintainability.

## Current Status

**Completed:**
- ✅ `routes/import_export.py` - Decomposed from 2,261 lines into 14 focused modules (largest: 443 lines)
- ✅ `server_execution.py` - Decomposed from 1,413 lines into 9 focused modules (largest: 480 lines)

**Remaining Work:**
- ⏳ `routes/meta.py` - 1,005 lines (MEDIUM priority)
- ⏳ `routes/openapi.py` - 1,527 lines (MEDIUM priority)

## Lessons Learned from routes/import_export

The successful decomposition of `routes/import_export.py` established proven patterns:

### Key Success Factors
- **Clear separation of concerns**: CID operations, filesystem, import/export pipelines, history
- **Backward compatibility**: Shim file + lazy imports = zero breaking changes
- **Focused modules**: Each module under 450 lines with single responsibility
- **Test-driven validation**: All existing tests continue to pass

### Critical Testing Insight
Mock patches must target where functions are **imported and used**, not their original definition:
- ❌ `patch('db_access.get_user_aliases')` - doesn't work
- ✅ `patch('routes.import_export.export_sections.get_user_aliases')` - works

## Lessons Learned from server_execution

The decomposition of `server_execution.py` revealed additional critical insights:

### Key Success Factors
- **Functional cohesion**: Modules grouped by business logic (parsing, execution, response, error handling)
- **Single source of truth**: Centralized `current_user` access through one module prevents duplication
- **Backward compatibility**: Shim file + `__getattr__` maintains all existing imports
- **All tests passing**: 978/978 tests pass (including test isolation fixes)

### Final Structure
```
server_execution/
├── __init__.py (197 lines) - Package entry with lazy loading
├── variable_resolution.py (167 lines) - Variable prefetching and path resolution
├── function_analysis.py (182 lines) - AST analysis for function parameters
├── request_parsing.py (205 lines) - HTTP request parsing and parameter resolution
├── response_handling.py (99 lines) - Output encoding and response formatting
├── error_handling.py (114 lines) - Error capture and HTML rendering
├── code_execution.py (480 lines) - Core execution logic (largest module)
├── server_lookup.py (125 lines) - Server resolution and versioning
└── invocation_tracking.py (86 lines) - Server invocation record creation
```

### Test Results
After decomposition and all fixes:
- ✅ **978/978 tests passing** (0 failed)
- ✅ All module decomposition test patches updated
- ✅ All Flask context issues resolved
- ✅ All flake8 E731 violations fixed

### Critical Pattern: Centralizing Shared Dependencies

**Problem:** `current_user` was initially imported in 4 modules, causing test complexity.

**Solution:** Consolidate to single source of truth:
1. Only `variable_resolution.py` imports `current_user` from `identity`
2. Other modules call `_current_user_id()` helper function
3. Tests patch `variable_resolution.current_user` and `identity.current_user` only

**Why This Matters:**
- Reduces mock complexity (2 patches instead of 5+)
- Prevents Flask-Login LocalProxy issues in tests
- Makes data flow explicit and traceable

### Testing Pattern for Decomposed Modules

When functions move to submodules, mock targets must follow:

```python
# Before decomposition
patch('server_execution.get_server_by_name')
patch('server_execution.current_user')

# After decomposition
patch('server_execution.server_lookup.get_server_by_name')  # where it's used
patch('server_execution.variable_resolution.current_user')  # single source

# For functions called within same module
from server_execution import variable_resolution
monkeypatch.setattr(variable_resolution, "_fetch_variable_content", mock)
```

### Test Isolation Best Practices

After decomposing server_execution.py, we encountered and fixed 9 test failures (6 module decomposition issues + 3 Flask context issues). All 978 tests now pass. Key lessons learned:

#### 1. Always Patch at the Import Site

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

#### 2. Use Context Managers for Patches

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

#### 3. Use Flask Test Contexts for Request/App Access

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

**Critical:** Don't use `patch.dict` to mock Flask's request object - it won't work because Flask's `request` is a LocalProxy requiring an active request context.

#### 4. Avoid Direct Module Attribute Modification

Don't modify module state directly; use patch decorators or context managers:

```python
# ❌ BAD: Modifies module state
import my_module
my_module.some_function = mock_function

# ✅ GOOD: Uses patch context
with patch('my_module.some_function', mock_function):
    # test code
```

#### 5. Avoid Lambda-Assigned Mock Helpers (Flake8 E731)

```python
# ❌ BAD (flake8 E731 violation)
mock_build_request_args = lambda: {"request": {...}, "context": {...}}

# ✅ GOOD
def mock_build_request_args():
    return {"request": {...}, "context": {...}}
```

## Modules to Decompose

### 1. routes/meta.py (1,005 lines) - MEDIUM PRIORITY

**Proposed Structure:**
```
routes/meta/
├── __init__.py - Package entry
├── cid_operations.py - CID CRUD operations
├── entity_management.py - Alias/Server/Variable/Secret management
├── interaction_tracking.py - History and analytics
├── search_filtering.py - Query and filter logic
├── form_handlers.py - Form processing
├── list_views.py - List page rendering
├── detail_views.py - Detail page rendering
└── routes.py - Flask route handlers
```

**Key Complexity Issues:**
- `_resolve_versioned_server_path`: 95 lines
- `_resolve_alias_path`: 80 lines
- `_gather_metadata`: 91 lines with 3 exception paths
- `_collect_template_links`: 69 lines with deep AST analysis

### 3. routes/openapi.py (1,527 lines) - MEDIUM PRIORITY

**Proposed Structure:**
```
routes/openapi/
├── __init__.py - Package entry
├── spec_generator.py - OpenAPI spec generation
├── schema_builder.py - Schema definitions
├── endpoint_documentation.py - Endpoint metadata
├── response_examples.py - Example generation
└── routes.py - Flask route handlers
```

**Key Complexity Issues:**
- `_build_openapi_spec`: 619-line monolithic function
- Needs organization more than complexity reduction
- Split schemas by entity type
- Separate path definitions from spec assembly

## Decomposition Best Practices

### Step-by-Step Process

1. **Analyze module structure** - Identify natural boundaries and functional groupings
2. **Plan package structure** - Design focused modules with clear responsibilities
3. **Extract code** - Move code into new modules, starting with utilities
4. **Create backward compatibility shim** - Original filename re-exports main functions
5. **Update imports** - Fix all import statements in dependent code
6. **Run tests** - Verify all existing tests still pass
7. **Fix failures** - Update mock patch targets to new module locations
8. **Verify with pylint** - Confirm C0302 violations are resolved

### Module Naming Conventions

- `*_engine.py` - Orchestration and main workflow
- `*_helpers.py` - Utility functions
- `*_utils.py` - Low-level operations
- `*_sections.py` - Collection functions
- `*_integration.py` - Circular import prevention helpers
- `routes.py` - Flask route handlers

### Backward Compatibility Strategy

Maintain zero breaking changes using two mechanisms:

1. **Shim file** at original location:
   ```python
   # routes/import_export.py (shim)
   from .import_export import export_data, import_data
   ```

2. **Lazy imports** in `__init__.py`:
   ```python
   def __getattr__(name):
       # Dynamic loading for internal functions
   ```

### Common Pitfalls to Avoid

❌ **Don't**: Patch functions at their definition location
✅ **Do**: Patch functions where they're imported and used

❌ **Don't**: Create breaking changes to existing imports
✅ **Do**: Maintain all existing import paths via shims

❌ **Don't**: Skip running tests until the end
✅ **Do**: Test early and often, fixing issues incrementally

## References

- See `../remaining_pylint_issues.md` for current pylint status
- See `CLAUDE_TEST_INSTRUCTIONS.md` for testing procedures
