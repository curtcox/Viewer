# Plan to eliminate remaining pylint issues

- **Latest pylint snapshot (2025-11-08)**: `pylint routes scripts step_impl` now scores **9.84/10** (up from 9.79/10) after fixing style issues, exception handling, and import organization.

1. ~~Normalise import order and positioning in operational scripts and entry points.~~ **COMPLETED**
   - ✅ Updated `inspect_db.py`, `migrate_add_server_cid.py`, `tests/test_ai_stub_server.py`, and `routes/__init__.py` with proper `# pylint: disable=wrong-import-position` comments
   - ✅ All C0411/C0413 warnings resolved - pylint rating improved from 8.86/10 to 10.00/10
   - ✅ Documented justifications for necessary lazy imports:
     - `inspect_db.py` and `migrate_add_server_cid.py`: sys.path manipulation required for standalone scripts
     - `tests/test_ai_stub_server.py`: Environment variables must be set before app initialization
     - `routes/__init__.py`: Blueprint must be created before importing route modules

2. ~~Replace broad `except Exception` handlers with precise error management.~~ **MOSTLY COMPLETED**
   - ✅ **Core modules completed**: `alias_matching.py`, `alias_routing.py`, `analytics.py`, `content_rendering.py`, `encryption.py`
     - Replaced broad exceptions with specific types: `ValueError`, `TypeError`, `RuntimeError`, `AttributeError`
   - ✅ **Server execution completed**: `server_execution.py`
     - Added specific exceptions where appropriate: `UnicodeDecodeError`, `ValueError`, `TypeError`, `SQLAlchemyError`, `OSError`
     - Added `# pylint: disable=broad-exception-caught` with justifications for legitimate cases (user code execution, error handling fallbacks)
   - ✅ **Utility modules completed**: `utils/cross_reference.py`, `utils/stack_trace.py`, `syntax_highlighting.py`, `text_function_runner.py`
   - ✅ **Database access**: `routes/aliases.py` - Added SQLAlchemyError handling
   - ✅ **Secrets UX**: `routes/secrets.py` renamed helper arguments to avoid shadowing and trimmed trailing whitespace
   - ✅ **Routes cleanup**: `routes/source.py`
     - Narrowed `_get_all_project_files` to catch `OSError`, switched breadcrumb building to `enumerate`, and used `Result.mappings()` to avoid protected member access
   - ✅ **Route handlers completed**: `routes/route_details.py`, `routes/history.py`, `routes/error_handlers.py`, `routes/uploads.py`
     - `routes/history.py`: Narrowed to `(UnicodeDecodeError, json.JSONDecodeError)`
     - `routes/route_details.py`: Fixed to use `ImportError`, `(AttributeError, UnicodeDecodeError)`, added justification for routing fallback
     - `routes/error_handlers.py`: Added justification for broad exception catching in error recovery paths
     - `routes/uploads.py`: Narrowed to `(AttributeError, UnicodeDecodeError)`
   - **Remaining work** (lower priority; acceptable in test/diagnostic code):
     - Scripts: `scripts/verify-chromium.py` (1x) and `scripts/test-browser-launch.py` (3x) - diagnostic scripts
     - Test support: `step_impl/artifacts.py` (6x) - screenshot capture fallbacks in behave tests
   - **Impact**: All core business logic now uses specific exceptions or has justified broad exception handling for error recovery paths

3. Decompose oversized and high-complexity route and execution modules. **IN PROGRESS**
   - ✅ **COMPLETED**: `routes/import_export.py` (2,261 lines) → 14 focused modules (17-443 lines each)
     - Created `routes/import_export/` package with clear separation of concerns
     - Modules: cid_utils, filesystem_collection, dependency_analyzer, export_engine, export_sections, export_preview, export_helpers, import_engine, import_sources, import_entities, change_history, routes_integration, routes, __init__
     - All modules well under C0302 threshold (largest: 443 lines)
     - Backward compatibility maintained via shim at `routes/import_export.py`
     - Addressed complexity in `_build_export_preview` (150 lines), `_impl_import_secrets` (54 lines), etc.
   - ⏳ **REMAINING**: `server_execution.py` (1,413 lines) - needs 7 modules (variable_resolution, definition_analyzer, parameter_resolution, invocation_builder, execution_engine, response_handling, routing)
   - ⏳ **REMAINING**: `routes/meta.py` (1,004 lines) - needs 8 modules (still tripping `C0302` per 2025-11-08 pylint run)
   - ⏳ **REMAINING**: `routes/openapi.py` (1,526 lines) - needs 5 modules (still tripping `C0302` per 2025-11-08 pylint run)
   - See `DECOMPOSITION_SUMMARY.md` for detailed breakdown and implementation plan

4. Resolve remaining function-level style warnings. **MAJOR PROGRESS**
   - ✅ **Routes fixed**:
     - `routes.aliases`: Fixed `redefined-outer-name` (renamed `new_alias` → `alias_copy`), added pylint disable for `too-many-positional-arguments` in helper functions
     - `routes.uploads`: Fixed iteration style and shadowed loop vars (renamed `upload` → `upload_record`)
     - `routes.source`: Fixed `inconsistent-return-statements` by adding explicit returns
     - `routes.openapi`: Fixed dictionary iteration (removed redundant `.keys()`)
     - `routes.history`: Narrowed exception handling from `Exception` to `(UnicodeDecodeError, json.JSONDecodeError)`
     - `routes.route_details`: Fixed exception handling (ImportError, AttributeError) and added justification for broad exception in routing fallback
     - `routes.error_handlers`: Added justification for broad exception catching in error handlers (legitimate fallback), added unused-argument disable
     - `routes/import_export.py` (shim): Fixed import order, added pylint disable for import-self
     - `routes/import_export/routes.py`: Fixed import order (moved flask before first-party imports)
   - ✅ **Scripts fixed**:
     - `run_radon.py`: Converted string formatting to f-strings
   - ✅ **Test files fixed**:
     - `step_impl/web_steps.py`: Converted string formatting to f-strings, added pylint disable for unused-argument
   - **Remaining work** (lower priority):
     - `routes/import_export/*`: Import order and lazy import warnings (intentional design for circular dependency management)
     - `routes/meta.py`: One iteration style issue (C0208)
     - Scripts: `verify-chromium.py` and `test-browser-launch.py` broad exceptions (test/diagnostic scripts)
     - Scripts: `publish_gauge_summary.py` nested blocks, `build-report-site.py` too many lines
     - Behave test infrastructure: `step_impl/artifacts.py` broad exceptions in screenshot capture

5. Fix repository-wide formatting nits. **COMPLETED**
   - ✅ Fixed final newlines in 5 files: `routes/import_export/__init__.py`, `scripts/publish_gauge_summary.py`, `step_impl/shared_app.py`, `step_impl/alias_steps.py`, `step_impl/artifacts.py`
   - ✅ Fixed dictionary/iteration idioms in `routes.openapi.py` and `routes.uploads.py`
   - ✅ Standardized string formatting (f-strings) in `step_impl/web_steps.py` and `scripts/run_radon.py`

## Summary of Improvements (2025-11-08 session)

### Score Progress
- **Starting score**: 9.79/10
- **Ending score**: 9.84/10
- **Improvement**: +0.05 points

### Issues Fixed
1. ✅ Fixed 5 trailing newline issues
2. ✅ Fixed 3 import order issues (routes/import_export.py, routes/import_export/routes.py)
3. ✅ Fixed 2 dictionary iteration style issues
4. ✅ Fixed 3 redefined-outer-name issues (renamed shadowing variables)
5. ✅ Fixed 1 inconsistent-return-statements issue
6. ✅ Fixed 2 too-many-positional-arguments issues (added justified pylint disables)
7. ✅ Fixed 2 unused-argument issues (added justified pylint disables)
8. ✅ Fixed 2 string formatting issues (converted to f-strings)
9. ✅ Fixed 8 broad-exception-caught issues in route files:
   - 1 in routes/history.py (narrowed to specific exceptions)
   - 3 in routes/route_details.py (narrowed or justified)
   - 2 in routes/error_handlers.py (justified as error recovery)
   - 1 in routes/uploads.py (narrowed to specific exceptions)

### Remaining Low-Priority Issues
- Import-outside-toplevel warnings (C0415): Intentional lazy imports to avoid circular dependencies
- Broad exceptions in test/diagnostic scripts: Acceptable for test infrastructure
- Module size issues (C0302): Require decomposition work (tracked separately)
- Nested block complexity (R1702): Requires refactoring
- Cyclic imports (R0401): Architectural issue requiring larger refactoring effort

### Next Steps
To reach 9.90/10 or higher, focus on:
1. Fixing remaining import order issues in `routes/import_export/*` modules
2. Addressing the iteration style issue in `routes/meta.py`
3. Decomposing `routes/meta.py`, `routes/openapi.py`, and `scripts/build-report-site.py`
