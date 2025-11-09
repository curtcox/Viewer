# Module Decomposition Documentation

This document provides guidance for decomposing oversized modules to address pylint C0302 (too-many-lines) warnings and improve code maintainability.

## Current Status

**Completed:**
- ✅ `routes/import_export.py` - Decomposed from 2,261 lines into 14 focused modules (largest: 443 lines)

**Remaining Work:**
- ⏳ `server_execution.py` - 1,413 lines (HIGH priority)
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

## Modules to Decompose

### 1. server_execution.py (1,413 lines) - HIGH PRIORITY

**Why High Priority:** Core execution logic with security implications and multiple complex functions

**Proposed Structure:**
```
server_execution/
├── __init__.py - Package entry
├── request_parsing.py - HTTP request parsing
├── server_lookup.py - Server resolution logic
├── execution_context.py - Execution environment setup
├── code_execution.py - Core Python execution
├── response_handling.py - Response formatting
├── error_handling.py - Error capture and formatting
└── routes.py - Flask route handlers
```

**Key Complexity Issues:**
- `_encode_output`: 43 lines with 6 nesting levels
- `_render_execution_error_html`: 70 lines
- `_evaluate_nested_path_to_value`: 48 lines, recursive
- `_build_multi_parameter_error_page`: 70 lines

### 2. routes/meta.py (1,005 lines) - MEDIUM PRIORITY

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

- See `remaining_pylint_issues.md` for current pylint status
- See `CLAUDE_TEST_INSTRUCTIONS.md` for testing procedures
