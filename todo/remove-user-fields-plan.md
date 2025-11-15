# Goal: Remove All `user_id` Usage

Convert Viewer into a single-user application by eliminating every `user_id`/`uploaded_by_user_id` column, parameter, session value, and behavior across the project.

## Progress

- ✅ Export routes now rely on the global `get_exports` helper instead of the legacy `get_user_exports`, ensuring exports are globally visible.

## Remaining Steps

1. **Database & Models** – Keep schemas global-only (no ownership columns or per-user uniqueness) and enforce global name uniqueness.
2. **Data Access Layer** – Retain only globally scoped repository helpers (`get_servers`, `get_aliases`, etc.) and remove remaining `get_user_*` APIs/parameters.
3. **Identity & Session** – Strip out `current_user`, `_user_id`, and per-user initialization; ensure AI/CSS defaults run once at startup.
4. **Server Execution & Utilities** – Confirm execution pipeline, analytics, CID utilities, content rendering, cross-reference tools, boot importers, and template managers operate without user context.
5. **Routes / Forms / Templates** – Update controllers, CRUD helpers, bulk editors, context processors, and templates so entities are globally visible and never filtered by user.
6. **Tests & Step Definitions** – Remove session hacks and `user_id` fixtures across unit/integration/BDD tests; rely on globally unique entity names.
7. **Cleanup & Verification** – Delete user-specific files/docs/env vars and run a final checklist to ensure no `user_id` references remain and all tests pass.
