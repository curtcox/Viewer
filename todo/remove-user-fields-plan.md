# Goal: Remove All `user_id` Usage

Convert Viewer into a single-user application by eliminating every `user_id`/`uploaded_by_user_id` column, parameter, session value, and behavior across the project.

## Remaining Steps

1. **Database & Models** – Keep schemas global-only (no ownership columns or per-user uniqueness) and enforce global name uniqueness.
2. **Data Access Layer** ✅ – All runtime helpers now ship global variants (`get_servers`, `get_aliases`, etc.) and every `get_user_*` shim has been removed or redirected to the global API.
3. **Identity & Session** – Strip out `current_user`, `_user_id`, and per-user initialization; ensure AI/CSS defaults run once at startup.
4. **Server Execution & Utilities** ✅ – Execution pipeline, analytics helpers, CID utilities, import/export shims, and template managers all operate without user context.
5. **Routes / Forms / Templates** – Update controllers, CRUD helpers, bulk editors, context processors, and templates so entities are globally visible and never filtered by user.
6. **Tests & Step Definitions** ✅ – Unit/integration specs no longer mock or expect `get_user_*` helpers; fixtures rely on globally unique entity names.
7. **Cleanup & Verification** – Delete user-specific files/docs/env vars and run a final checklist to ensure no `user_id` references remain and all tests pass.
