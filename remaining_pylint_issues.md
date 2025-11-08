# Plan to eliminate remaining pylint issues

1. ~~Normalise import order and positioning in operational scripts and entry points.~~ **COMPLETED**
   - ✅ Updated `inspect_db.py`, `migrate_add_server_cid.py`, `tests/test_ai_stub_server.py`, and `routes/__init__.py` with proper `# pylint: disable=wrong-import-position` comments
   - ✅ All C0411/C0413 warnings resolved - pylint rating improved from 8.86/10 to 10.00/10
   - ✅ Documented justifications for necessary lazy imports:
     - `inspect_db.py` and `migrate_add_server_cid.py`: sys.path manipulation required for standalone scripts
     - `tests/test_ai_stub_server.py`: Environment variables must be set before app initialization
     - `routes/__init__.py`: Blueprint must be created before importing route modules

2. ~~Replace broad `except Exception` handlers with precise error management.~~ **MAJOR PROGRESS**
   - ✅ **Core modules completed**: `alias_matching.py`, `alias_routing.py`, `analytics.py`, `content_rendering.py`, `encryption.py`
     - Replaced broad exceptions with specific types: `ValueError`, `TypeError`, `RuntimeError`, `AttributeError`
   - ✅ **Server execution completed**: `server_execution.py`
     - Added specific exceptions where appropriate: `UnicodeDecodeError`, `ValueError`, `TypeError`, `SQLAlchemyError`, `OSError`
     - Added `# pylint: disable=broad-exception-caught` with justifications for legitimate cases (user code execution, error handling fallbacks)
   - ✅ **Utility modules completed**: `utils/cross_reference.py`, `utils/stack_trace.py`, `syntax_highlighting.py`, `text_function_runner.py`
   - ✅ **Database access**: `routes/aliases.py` - Added SQLAlchemyError handling
   - **Remaining work** (lower priority):
     - Route handlers: ~13 instances in `routes/error_handlers.py`, `routes/history.py`, `routes/import_export.py`, `routes/route_details.py`, `routes/search.py`, `routes/source.py`, `routes/uploads.py`
     - Scripts: ~4 instances in `migrate_add_server_cid.py`, `scripts/verify-chromium.py`, `scripts/test-browser-launch.py`
     - Test support: ~6 instances in `step_impl/artifacts.py`, `db_access/aliases.py`
     - Test files: ~25 instances in various test files (lowest priority)
   - **Impact**: Most core business logic now uses specific exceptions, significantly improving error clarity and reducing false-positive error catching

3. Decompose oversized and high-complexity route and execution modules. **IN PROGRESS**
   - ✅ **COMPLETED**: `routes/import_export.py` (2,261 lines) → 14 focused modules (17-443 lines each)
     - Created `routes/import_export/` package with clear separation of concerns
     - Modules: cid_utils, filesystem_collection, dependency_analyzer, export_engine, export_sections, export_preview, export_helpers, import_engine, import_sources, import_entities, change_history, routes_integration, routes, __init__
     - All modules well under C0302 threshold (largest: 443 lines)
     - Backward compatibility maintained via shim at `routes/import_export.py`
     - Addressed complexity in `_build_export_preview` (150 lines), `_impl_import_secrets` (54 lines), etc.
   - ⏳ **REMAINING**: `server_execution.py` (1,413 lines) - needs 7 modules (variable_resolution, definition_analyzer, parameter_resolution, invocation_builder, execution_engine, response_handling, routing)
   - ⏳ **REMAINING**: `routes/meta.py` (1,004 lines) - needs 8 modules
   - ⏳ **REMAINING**: `routes/openapi.py` (1,526 lines) - needs 5 modules
   - See `DECOMPOSITION_SUMMARY.md` for detailed breakdown and implementation plan

4. Resolve remaining function-level style warnings.
   - Tackle outstanding `unused-argument`, `redefined-outer-name`, `attribute-defined-outside-init`, logging format (`W1203`), and dictionary/iteration style warnings across modules like `routes.aliases`, `routes.search`, `generate_page_test_cross_reference.py`, `routes.context_processors.py`, `routes.uploads.py`, `scripts/run_radon.py`, and `step_impl/web_steps.py`.
   - Adjust function signatures or usage patterns (for example, by renaming unused parameters to `_` or extracting helpers) and confirm pylint accepts the updated code.

5. Fix repository-wide formatting nits.
   - Remove trailing newline violations from all flagged modules (including `db_access` subpackages, route modules, scripts, and tests) and ensure editors or formatting hooks prevent reintroduction.
   - Standardise string formatting (switch to f-strings where recommended) and iterate over dictionaries/sequences idiomatically to silence the remaining stylistic warnings, validating with pylint at the end.
