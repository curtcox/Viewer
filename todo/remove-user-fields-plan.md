# Goal: Remove All `user_id` Usage

Convert Viewer into a single-user application by eliminating every `user_id`/`uploaded_by_user_id` column, parameter, session value, and behavior across the project.

## Remaining Steps

1. **Database & Models** – Confirm every schema is global-only (no ownership columns or per-user uniqueness) and enforce global name uniqueness. Drop any lingering `user_id`/`uploaded_by_user_id` fields and associated constraints. Cross-check Alembic/migration scripts so future upgrades don’t reintroduce the columns.
2. ~~**Identity & Session** – Remove all `current_user`, `_user_id`, and login helper usage. Ensure AI/CSS defaults run exactly once at startup and audit fixtures/middleware for leftover authentication hooks. Replace `login_default_user`/`authenticate_user` helpers with no-ops that only set session freshness where absolutely required.~~ ✅
3. **Routes / Forms / Templates** – Double-check controllers, CRUD helpers, bulk editors, context processors, and templates for residual per-user wording or helpers; normalize labels to global terminology. Review Flask flashes/tooltips for “your aliases/servers” phrasing and update to single-user copy.
4. **Tests & Step Definitions** – Keep removing `get_user_*` shims, login helpers, and per-user expectations. Ensure fixtures rely on globally unique entity names and exercise single-user behaviors exclusively. Add regression tests whenever an assertion now depends on global counts (e.g., CLI list/search/category totals).
5. **Cleanup & Verification** – Run `./doctor`, `./test unit`, `./test integration`, and spot checks (CLI, search, import/export) after each batch of changes. Keep reviewing for stray helper references before final sign-off, and update documentation/README when the final sweep is complete.
   - ✅ `./doctor`
   - ✅ `./test`
