# Plan: Remove User and User ID Fields from Application

## Overview
This document outlines the detailed plan for converting the Viewer application from multi-user to single-user by removing all user and user_id references throughout the codebase.

**Scope:** Complete removal of user authentication, user_id columns, and user-scoping logic.

**Assumptions:**
- No migration scripts needed
- No backward compatibility required
- Database will be deleted and recreated
- No deployed version exists

---

## 1. Database Schema Changes

### 1.1 Remove user_id Columns from All Tables

**models.py** - Remove user_id columns and related constraints from:

#### CID Table (line 15)
- Remove: `uploaded_by_user_id = db.Column(db.String, nullable=True)`

#### PageView Table (line 23)
- Remove: `user_id = db.Column(db.String, nullable=False)`

#### Server Table (line 38)
- Remove: `user_id = db.Column(db.String, nullable=False)`
- Remove: `unique_user_server_name` unique constraint on (user_id, name)
- Add: New unique constraint on `name` only

#### Alias Table (line 54)
- Remove: `user_id = db.Column(db.String, nullable=False)`
- Remove: `unique_user_alias_name` unique constraint on (user_id, name)
- Add: New unique constraint on `name` only

#### EntityInteraction Table (line 126)
- Remove: `user_id = db.Column(db.String, nullable=False, index=True)`
- Remove: Index on user_id

#### Variable Table (line 147)
- Remove: `user_id = db.Column(db.String, nullable=False)`
- Remove: `unique_user_variable_name` unique constraint on (user_id, name)
- Add: New unique constraint on `name` only

#### Secret Table (line 162)
- Remove: `user_id = db.Column(db.String, nullable=False)`
- Remove: `unique_user_secret_name` unique constraint on (user_id, name)
- Add: New unique constraint on `name` only

#### ServerInvocation Table (line 175)
- Remove: `user_id = db.Column(db.String, nullable=False)`

#### Export Table (line 191)
- Remove: `user_id = db.Column(db.String, nullable=False, index=True)`
- Remove: Index on user_id

---

## 2. Database Access Layer Changes

### 2.1 Generic CRUD Operations (db_access/generic_crud.py)

**GenericEntityRepository class** - Refactor all methods:
- `get_all_for_user(user_id)` → `get_all()`
  - Remove user_id parameter
  - Remove `.filter_by(user_id=user_id)` from query

- `get_templates_for_user(user_id)` → `get_templates()`
  - Remove user_id parameter
  - Remove user_id filter

- `get_by_name(user_id, name)` → `get_by_name(name)`
  - Remove user_id parameter
  - Query only by name

- `get_first_name(user_id)` → `get_first_name()`
  - Remove user_id parameter
  - Remove user_id filter

- `count_for_user(user_id)` → `count()`
  - Remove user_id parameter
  - Remove user_id filter

- `exists(user_id, name)` → `exists(name)`
  - Remove user_id parameter
  - Check only by name

### 2.2 Server Repository (db_access/servers.py)

Refactor all functions:
- `get_user_servers(user_id)` → `get_servers()`
- `get_user_template_servers(user_id)` → `get_template_servers()`
- `get_server_by_name(user_id, name)` → `get_server_by_name(name)`
- `get_first_server_name(user_id)` → `get_first_server_name()`
- `count_user_servers(user_id)` → `count_servers()`

Remove user_id filters from all queries.

### 2.3 Alias Repository (db_access/aliases.py)

Refactor all functions:
- `get_user_aliases(user_id)` → `get_aliases()`
- `get_user_template_aliases(user_id)` → `get_template_aliases()`
- `get_alias_by_name(user_id, name)` → `get_alias_by_name(name)`
- `get_first_alias_name(user_id)` → `get_first_alias_name()`
- `get_alias_by_target_path(user_id, target_path)` → `get_alias_by_target_path(target_path)`
- `count_user_aliases(user_id)` → `count_aliases()`

Remove user_id filters from all queries.

### 2.4 Variable Repository (db_access/variables.py)

Refactor all functions:
- `get_user_variables(user_id)` → `get_variables()`
- `get_user_template_variables(user_id)` → `get_template_variables()`
- `get_variable_by_name(user_id, name)` → `get_variable_by_name(name)`
- `get_first_variable_name(user_id)` → `get_first_variable_name()`
- `count_user_variables(user_id)` → `count_variables()`

Remove user_id filters from all queries.

### 2.5 Secret Repository (db_access/secrets.py)

Refactor all functions:
- `get_user_secrets(user_id)` → `get_secrets()`
- `get_user_template_secrets(user_id)` → `get_template_secrets()`
- `get_secret_by_name(user_id, name)` → `get_secret_by_name(name)`
- `get_first_secret_name(user_id)` → `get_first_secret_name()`
- `count_user_secrets(user_id)` → `count_secrets()`

Remove user_id filters from all queries.

### 2.6 Server Invocation Repository (db_access/invocations.py)

Refactor all functions:
- `create_server_invocation(user_id, server_name, result_cid, ...)` → `create_server_invocation(server_name, result_cid, ...)`
  - Remove user_id parameter
  - Don't set user_id on ServerInvocation model

- `get_user_server_invocations(user_id)` → `get_server_invocations()`
- `get_user_server_invocations_by_server(user_id, server_name)` → `get_server_invocations_by_server(server_name)`
- `get_user_server_invocations_by_result_cids(user_id, result_cids)` → `get_server_invocations_by_result_cids(result_cids)`

Remove user_id from all queries.

### 2.7 Page Views Repository (db_access/page_views.py)

Refactor all functions:
- `save_page_view(page_view)` - Remove user_id from PageView object
- `count_user_page_views(user_id)` → `count_page_views()`
- `count_unique_page_view_paths(user_id)` → `count_unique_page_view_paths()`
- `get_popular_page_paths(user_id, limit)` → `get_popular_page_paths(limit)`
- `paginate_user_page_views(user_id, page, per_page)` → `paginate_page_views(page, per_page)`

Remove user_id filters from all queries.

### 2.8 Entity Interaction Repository (db_access/interactions.py)

- **EntityInteractionRequest dataclass** - Remove `user_id` field
- `record_entity_interaction(request)` - Don't set user_id on EntityInteraction model
- `get_recent_entity_interactions(user_id, entity_type, entity_name, limit)` → `get_recent_entity_interactions(entity_type, entity_name, limit)`
- `get_entity_interactions(user_id, entity_type, entity_name)` → `get_entity_interactions(entity_type, entity_name)`

Remove user_id from all queries.

### 2.9 Export Repository (db_access/exports.py)

Refactor all functions:
- `record_export(user_id, cid)` → `record_export(cid)`
  - Remove user_id parameter
  - Don't set user_id on Export model

- `get_user_exports(user_id, limit)` → `get_exports(limit)`

Remove user_id filters from all queries.

### 2.10 CID Repository (db_access/cids.py)

- `create_cid_record(cid, file_content, user_id)` → `create_cid_record(cid, file_content)`
  - Remove user_id parameter
  - Don't set uploaded_by_user_id

- `get_user_uploads(user_id)` → `get_uploads()`
  - Remove user_id parameter
  - Remove user_id filter

### 2.11 Profile Repository (db_access/profile.py)

- **DELETE ENTIRE FILE** - `get_user_profile_data(_user_id)` is a compatibility shim that's no longer needed

---

## 3. Authentication & Identity Module Changes

### 3.1 identity.py - Complete Overhaul

**Remove:**
- `ExternalUser` dataclass (lines 18-30)
- `_load_current_user()` function
- `_create_default_user()` function
- `ensure_default_user()` function
- `ensure_ai_stub_for_user(user_id)` function
- `ensure_css_alias_for_user(user_id)` function
- `current_user` LocalProxy
- All session handling for `"_user_id"`

**Replace with:**
- Simple initialization functions for AI stub and CSS alias that don't require user_id
- Remove all Flask session user management

**Alternative Approach:**
- If AI stub and CSS alias setup is still needed, call these functions once during app initialization
- Move setup to app.py or a startup module

---

## 4. Server Execution Module Changes

### 4.1 variable_resolution.py

- Remove `_current_user_id()` function (line 61)
- Update `_fetch_variable_content(path)`:
  - Remove user_id parameter
  - Call `get_variable_by_name(name)` without user_id
- Remove session handling for `session["_user_id"]` (line 129)

### 4.2 code_execution.py

Remove all user context retrieval:
- Remove `user_id = _current_user_id()` calls
- Update function calls:
  - `get_server_by_name(server_name)` (remove user_id)
  - `get_variables()` (remove user_id)
  - `get_secrets()` (remove user_id)
  - `get_servers()` (remove user_id)

### 4.3 response_handling.py

- Remove `user_id = _current_user_id()` (line 86)
- Update `create_cid_record(cid_value, output_bytes)` - remove user_id parameter
- Update `create_server_invocation_record(server_name, cid_value)` - remove user_id parameter

### 4.4 server_lookup.py

- Remove `user_id = _current_user_id()`
- Update `get_server_by_name(server_name)` - remove user_id parameter

### 4.5 invocation_tracking.py

- `create_server_invocation_record(server_name, result_cid)` (line 32)
  - Remove user_id parameter
  - Remove user_id from invocation record

---

## 5. Analytics Module Changes

### 5.1 analytics.py

**Remove or Simplify:**
- `create_page_view_record()` (line 43)
  - Remove `user_id=current_user.id`
  - Option 1: Remove user_id tracking from PageView records
  - Option 2: Remove entire PageView tracking if not needed for single-user

- `track_page_view(response)`
  - Remove user authentication check
  - If keeping page views, store without user_id

- `get_user_history_statistics(user_id)` → `get_history_statistics()`
  - Remove user_id parameter
  - Query all page views

- `get_paginated_page_views(user_id, page)` → `get_paginated_page_views(page)`
  - Remove user_id parameter
  - Query all page views

**Consider:** Whether page view analytics are still useful in single-user mode. If not, remove entire analytics module.

---

## 6. API Routes & Controllers Changes

### 6.1 routes/entities.py

**EntityTypeRegistry class methods:**
- `get_by_name(entity_class, user_id, name)` → `get_by_name(entity_class, name)`
  - Remove user_id parameter
  - Update repository calls

- `update_definitions_cid(entity_class, user_id)` → `update_definitions_cid(entity_class)`
  - Remove user_id parameter

**Helper functions:**
- `check_name_exists(model_class, name, user_id, exclude_id)` → `check_name_exists(model_class, name, exclude_id)`
  - Remove user_id parameter
  - Query only by name

- `create_entity(model_class, form, user_id, entity_type)` → `create_entity(model_class, form, entity_type)`
  - Remove user_id parameter
  - Don't set 'user_id' in entity data (line 126)

**All route handlers:**
- Remove `user_id = current_user.id` assignments
- Remove user_id from all function calls
- Remove user_id from entity creation

### 6.2 routes/aliases.py

- Remove all `user_id = current_user.id` assignments
- Remove `_alias_with_name_exists(user_id, name, exclude_id)` - update to remove user_id
- Update `Alias(...)` creation - remove `user_id=current_user.id`
- Update all repository function calls to remove user_id

### 6.3 routes/servers.py

Remove user_id from all functions:
- `get_server_definition_history(user_id, server_name)` → `get_server_definition_history(server_name)` (line 467)
- `update_server_definitions_cid(user_id)` → `update_server_definitions_cid()` (line 497)
- `_get_known_entity_names(user_id)` → `_get_known_entity_names()` (line 586)
- `_build_servers_list_context(servers_list, user_id)` → `_build_servers_list_context(servers_list)` (line 608)
- `_build_server_view_context(server, user_id)` → `_build_server_view_context(server)` (line 636)
- `get_server_invocation_history(user_id, server_name)` → `get_server_invocation_history(server_name)` (line 823)

Update all route handlers to remove user_id.

### 6.4 routes/interactions.py

- Remove `user_id=current_user.id` from EntityInteractionRequest
- Update `record_entity_interaction()` to not use user_id

### 6.5 routes/uploads.py

- Remove `user_id=current_user.id` from CID record creation
- Update `create_cid_record()` calls to remove user_id

### 6.6 routes/search.py

- Remove `_build_alias_lookup(user_id, aliases)` → `_build_alias_lookup(aliases)` (line 80)
- Remove `user_id = current_user.id` from search operations
- Update all repository calls to remove user_id

### 6.7 routes/context_processors.py

- Update `inject_viewer_navigation()`:
  - Remove `user_id = getattr(current_user, "id", None)`
  - Update function calls:
    - `get_aliases()` (remove user_id)
    - `get_servers()` (remove user_id)
    - `get_variables()` (remove user_id)
    - `get_secrets()` (remove user_id)

---

## 7. Utility & Support Module Changes

### 7.1 cid_utils.py

- `save_server_definition_as_cid(definition, user_id)` → `save_server_definition_as_cid(definition)` (line 149)
  - Remove user_id parameter
  - Update `create_cid_record()` call

### 7.2 content_rendering.py

- `render_html(source, user_id)` → `render_html(source)` (line 337)
  - Remove user_id parameter
  - Update any calls to `_store_svg()`

- `_store_svg(svg_bytes, user_id)` → `_store_svg(svg_bytes)` (line 401)
  - Remove user_id parameter
  - Update `create_cid_record()` call

### 7.3 utils/cross_reference.py

- `_collect_alias_entries(user_id, state)` → `_collect_alias_entries(state)` (line 239)
  - Remove user_id parameter
  - Update repository calls

- `_collect_server_entries(user_id, state)` → `_collect_server_entries(state)` (line 274)
  - Remove user_id parameter
  - Update repository calls

- `build_cross_reference_data(user_id)` → `build_cross_reference_data()` (line 471)
  - Remove user_id parameter
  - Update all helper function calls

### 7.4 boot_cid_importer.py

- `import_boot_cid(app, boot_cid, user_id)` → `import_boot_cid(app, boot_cid)` (line 169)
  - Remove user_id parameter
  - Update all entity creation to remove user_id

### 7.5 ai_defaults.py

- `ensure_ai_stub_for_user(user_id)` → `ensure_ai_stub()`
  - Remove user_id parameter
  - Update repository calls
  - Create single AI stub without user scoping

### 7.6 template_manager.py

- `get_templates_config(user_id)` → `get_templates_config()` (line 33)
- `get_template_status(user_id)` → `get_template_status()` (line 130)
- `get_templates_for_type(user_id, entity_type)` → `get_templates_for_type(entity_type)` (line 177)

Remove user_id from all template operations.

---

## 8. Migration Script Changes

### 8.1 migrate_add_server_cid.py

- Update `save_server_definition_as_cid(server.definition, server.user_id)` (line 68)
  - Remove user_id parameter

**Note:** Since we're not maintaining migrations, this file can be deleted or marked as deprecated.

### 8.2 migrate_remove_template_columns.py

- Remove user_id grouping logic
- Simplify to handle single user scenario
- Don't create user-specific template variables

**Note:** Since we're not maintaining migrations, this file can be deleted or marked as deprecated.

---

## 9. Template Changes

### 9.1 templates/_template_status.html

- `render_template_status(user_id, entity_type)` → `render_template_status(entity_type)` (line 1)
  - Remove user_id parameter
  - Update `get_template_link_info(entity_type)` call

### 9.2 All other templates

Search for any direct user_id references in templates and remove them.

---

## 10. Test Changes

### 10.1 BDD Step Implementations (step_impl/)

#### web_steps.py
- Remove `_set_session_user(user_id)` function (line 55)
- Remove `_perform_get_request_for_user(path, user_id)` (line 65)
- Remove `when_i_request_page_as_user(path, user_id)` (line 143)
- Update `Server(name=server_name, definition=definition, user_id=user_id)` - remove user_id
- Remove all session["_user_id"] assignments

#### alias_steps.py
- Remove `_login_default_user(client)` function
- Remove `_scenario_state["user_id"] = user_id` (line 110)
- Update `Alias.query.filter_by(user_id=user.id, ...)` - remove user_id filter

#### shared_app.py
- Remove `user_id = user.id` (line 55)
- Remove `session["_user_id"] = user_id` (line 58)

#### import_export_steps.py
- Remove `session["_user_id"] = "default-user"` (line 107)
- Update `Server(name=..., definition=..., user_id=user.id)` - remove user_id

### 10.2 Unit Tests

Update all unit tests in `tests/` directory:
- test_boot_cid_manual.py
- tests/integration/test_alias_pages.py
- tests/integration/test_server_pages.py
- tests/integration/test_variable_pages.py
- tests/integration/test_secret_pages.py
- tests/test_template_manager.py
- tests/test_cid_functionality.py
- tests/test_cid_directory_loader.py
- tests/test_db_access_uploads.py
- tests/test_analytics.py

**Changes needed:**
- Remove user_id from all test data creation
- Remove user_id from all assertions
- Remove user_id from all function calls
- Update mock objects to remove user_id
- Remove session user_id setup from test fixtures

---

## 11. Application Initialization Changes

### 11.1 app.py

**Remove:**
- Any user authentication middleware
- Session-based user loading
- User context setup for requests

**Add:**
- One-time initialization for AI stub (if needed)
- One-time initialization for CSS alias (if needed)

### 11.2 Configuration

- Remove any user-related configuration settings
- Remove authentication provider settings
- Simplify session configuration if no longer needed for user tracking

---

## 12. Cleanup Tasks

### 12.1 Delete Unnecessary Files

- `db_access/profile.py` - User profile shim
- Any user authentication modules
- Migration scripts (if not maintaining)

### 12.2 Update Documentation

- Update README to reflect single-user architecture
- Remove any multi-user usage instructions
- Update API documentation to remove user_id parameters

### 12.3 Environment Variables

- Remove user authentication environment variables
- Remove any user-related API keys or secrets

---

## 13. Implementation Order

Recommended order to minimize breaking changes:

1. **Phase 1: Database Layer**
   - Update models.py (remove columns and constraints)
   - Update all db_access/ repositories
   - Drop and recreate database

2. **Phase 2: Core Services**
   - Update identity.py (remove user authentication)
   - Update server_execution/ modules
   - Update analytics.py

3. **Phase 3: API Layer**
   - Update routes/entities.py
   - Update all specific route handlers
   - Update context_processors.py

4. **Phase 4: Utilities**
   - Update cid_utils.py
   - Update content_rendering.py
   - Update cross_reference.py
   - Update boot_cid_importer.py
   - Update template_manager.py

5. **Phase 5: Templates**
   - Update _template_status.html
   - Search and update any other templates

6. **Phase 6: Tests**
   - Update BDD step implementations
   - Update all unit tests
   - Update all integration tests

7. **Phase 7: Cleanup**
   - Delete obsolete files
   - Update documentation
   - Clean up configuration

---

## 14. Verification Checklist

After implementation, verify:

- [ ] No database columns named `user_id` or `uploaded_by_user_id`
- [ ] No unique constraints involving `user_id`
- [ ] No function parameters named `user_id`
- [ ] No session storage of `_user_id`
- [ ] No imports of `current_user` from identity module
- [ ] No `ExternalUser` dataclass references
- [ ] All tests pass
- [ ] Application starts without errors
- [ ] Basic CRUD operations work for all entity types
- [ ] Server execution works without user context
- [ ] No authentication required to access application
- [ ] Entities are globally unique by name (not per-user)

---

## 15. Risk Assessment

**Low Risk:**
- No production deployment
- Database will be recreated
- No backward compatibility needed

**Potential Issues:**
- Name conflicts if test data had duplicate names across different user_ids
- Any external integrations expecting user_id fields

**Mitigation:**
- Clean database recreate eliminates name conflicts
- Review any external API integrations for user_id dependencies

---

## Notes

- This plan covers all 200+ references to user_id identified in the codebase
- Total estimated changes: ~150 files
- Most changes are mechanical parameter removal
- Main complexity is in ensuring all call sites are updated consistently
- Test suite will help catch any missed references
