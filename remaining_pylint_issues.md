# Plan to eliminate remaining pylint issues

- **Latest pylint snapshot (2025-11-08)**: `pylint routes scripts step_impl` now scores **9.77/10** after cleaning the `routes.source` helpers and tightening `routes.secrets`.

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
   - ✅ **Secrets UX**: `routes/secrets.py` renamed helper arguments to avoid shadowing and trimmed trailing whitespace
   - ✅ **Routes cleanup**: `routes/source.py`
     - Narrowed `_get_all_project_files` to catch `OSError`, switched breadcrumb building to `enumerate`, and used `Result.mappings()` to avoid protected member access
   - **Remaining work** (lower priority; confirmed by `pylint routes scripts step_impl` on 2025-11-08):
     - Route handlers: `routes/route_details.py` (3x), `routes/history.py`, `routes/error_handlers.py` (2x), `routes/uploads.py`, `routes/search.py`, plus integration shims in `routes/import_export/routes.py`
     - Scripts: `scripts/verify-chromium.py` (1x) and `scripts/test-browser-launch.py` (3x)
     - Test support: `step_impl/web_steps.py` (behave steps) — acceptable to defer
     - Leave test modules for last unless they block enabling the pylint gate
   - **Impact**: Most core business logic now uses specific exceptions, significantly improving error clarity and reducing false-positive error catching

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

4. Resolve remaining function-level style warnings. **IN PROGRESS**
   - Confirmed by the 2025-11-08 pylint run:
     - `routes.aliases`: `redefined-outer-name` and `too-many-positional-arguments`
     - `routes.context_processors`: `use-dict-literal`
     - `routes.search`: four `unused-argument` hits and one `broad-exception-caught`
     - `routes.uploads`: iteration style issues and shadowed loop vars
     - `routes.variables`, `routes.servers`, `routes.interactions`: stray trailing-newline cleanups
     - `routes.import_export.*`: order-of-import, logging, unused-argument, nested-block, and module import exposure nits
     - Scripts: `publish_gauge_summary.py` nested blocks, `run_radon.py` string formatting, Chromium helpers with lazy imports
     - Behave steps: `step_impl/web_steps.py` `unused-argument` and lazy imports
   - ✅ Cleared the focused warnings in `db_access.aliases`, `db_access.cids`, `db_access.profile`, `gauge_stub/python.py`, `generate_page_test_cross_reference.py`, and `generate_test_index.py`.

5. Fix repository-wide formatting nits. **IN PROGRESS**
   - Outstanding trailing-newline hits: `routes/variables.py`, `routes/servers.py`, `routes/aliases.py`, `routes/interactions.py`, `routes/import_export/__init__.py`, `scripts/publish_gauge_summary.py`, `step_impl/shared_app.py`.
   - Address dictionary/iteration idioms flagged in `routes.context_processors.py`, `routes.uploads.py`, and `routes.servers.py`.
   - Standardise string formatting (switch to f-strings where recommended) and iterate over dictionaries/sequences idiomatically to silence the remaining stylistic warnings, validating with pylint at the end.
