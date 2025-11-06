# Plan to eliminate remaining pylint issues

1. Normalise import order and positioning in operational scripts and entry points.
   - Update modules such as `inspect_db.py`, `migrate_add_server_cid.py`, `tests/test_ai_stub_server.py`, and `routes/__init__.py` to follow standard import grouping so the `C0411`/`C0413` warnings go away without reintroducing cyclic dependencies.
   - Document any necessary lazy imports with targeted `# pylint: disable` comments and justification when restructuring is impossible, and verify with pylint afterwards.

2. Replace broad `except Exception` handlers with precise error management.
   - Catalogue each `W0718` site across core logic (`alias_matching.py`, `alias_routing.py`, `analytics.py`, `content_rendering.py`, `server_execution.py`, etc.), route handlers, scripts, and tests.
   - For each block, determine the specific exceptions that should be caught or restructure the code to avoid blanket suppression; only retain broad handlers with explicit justification comments and `# pylint: disable=broad-exception-caught` markers.
   - Add regression tests where behaviour changes so the narrower exception handling is covered.

3. Decompose oversized and high-complexity route and execution modules.
   - Split `server_execution.py`, `routes/import_export.py`, `routes/meta.py`, and `routes/openapi.py` into cohesive submodules to drop below the `C0302` module-length threshold and expose clearer public APIs.
   - While extracting code, address the nested block (`R1702`), redefined name (`W0621`), and too-many-positional-arguments (`R0917`) warnings in the affected functions, and expand or add tests to cover the new module boundaries.

4. Resolve remaining function-level style warnings.
   - Tackle outstanding `unused-argument`, `redefined-outer-name`, `attribute-defined-outside-init`, logging format (`W1203`), and dictionary/iteration style warnings across modules like `routes.aliases`, `routes.search`, `generate_page_test_cross_reference.py`, `routes.context_processors.py`, `routes.uploads.py`, `scripts/run_radon.py`, and `step_impl/web_steps.py`.
   - Adjust function signatures or usage patterns (for example, by renaming unused parameters to `_` or extracting helpers) and confirm pylint accepts the updated code.

5. Fix repository-wide formatting nits.
   - Remove trailing newline violations from all flagged modules (including `db_access` subpackages, route modules, scripts, and tests) and ensure editors or formatting hooks prevent reintroduction.
   - Standardise string formatting (switch to f-strings where recommended) and iterate over dictionaries/sequences idiomatically to silence the remaining stylistic warnings, validating with pylint at the end.
