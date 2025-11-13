# Template System Refactor Plan

## Overview

Refactor the template system from database column-based storage to a centralized JSON configuration stored in a `templates` variable. The templates variable will contain JSON (or a CID pointing to JSON) that defines all templates for aliases, servers, variables, and secrets.

## Current State

### Database Schema (models.py)
- `Server.template` (line 42): Boolean column
- `Alias.template` (line 59): Boolean column
- `Variable.template` (line 153): Boolean column
- `Secret.template` (line 169): Boolean column

### Database Access Layer
- `db_access/generic_crud.py`: `get_templates_for_user()` (lines 45-58)
- `db_access/aliases.py`: `get_user_template_aliases()` (lines 41-47)
- `db_access/servers.py`: `get_user_template_servers()` (lines 18-20)
- `db_access/variables.py`: `get_user_template_variables()` (lines 17-19)
- `db_access/secrets.py`: `get_user_template_secrets()` (lines 17-19)

### UI Components Using Templates
- List pages: `aliases.html`, `servers.html`, `variables.html`, `secrets.html` (template badge display)
- Form pages: `alias_form.html`, `server_form.html`, `variable_form.html`, `secret_form.html` (template checkbox)
- Export page: `export.html` (template filtering)

### CRUD Operations
- `routes/entities.py`:
  - `create_entity()` (line 229): Sets `entity.template` flag
  - `update_entity()` (line 229): Updates `entity.template` flag

### Import/Export
- `routes/import_export/export_helpers.py`: `should_export_entry()` filters templates
- `routes/import_export/import_entities.py`: Preserves template flags on import
- `routes/import_export/export_sections.py`: Includes template flag in JSON

## Target State

### Templates Variable Structure

The `templates` variable will contain JSON with the following structure:

```json
{
  "aliases": {
    "template-name-1": {
      "name": "Template Display Name",
      "description": "Optional description",
      "target_path_cid": "AAAABGFiY2Q",
      "metadata": {
        "created": "2025-01-01T00:00:00Z",
        "author": "username"
      }
    }
  },
  "servers": {
    "template-name-2": {
      "name": "Server Template Name",
      "description": "Optional description",
      "definition_cid": "AAAAAAAA...",
      "metadata": {
        "created": "2025-01-01T00:00:00Z",
        "author": "username"
      }
    }
  },
  "variables": {
    "template-name-3": {
      "name": "Variable Template Name",
      "description": "Optional description",
      "definition_cid": "AAAAAAAA...",
      "metadata": {
        "created": "2025-01-01T00:00:00Z",
        "author": "username"
      }
    }
  },
  "secrets": {
    "template-name-4": {
      "name": "Secret Template Name",
      "description": "Optional description",
      "value_cid": "AAAAAAAA...",
      "metadata": {
        "created": "2025-01-01T00:00:00Z",
        "author": "username"
      }
    }
  }
}
```

### CID Storage Options

The `templates` variable can store either:
1. **Direct JSON**: The JSON structure shown above as a string
2. **CID Reference**: A CID pointing to stored JSON (e.g., "AAAABGFiY2Q")

### Template Status Labels

Each page using templates should display a status label with link to `/variables/templates`:
- "11 templates" - When templates exist and are valid
- "No templates" - When templates variable is empty or doesn't exist
- "Invalid template definition" - When JSON is malformed or CID is invalid

## Implementation Plan

### Phase 1: Infrastructure and Core Logic

#### 1.1 Create Template Manager Module
**File**: `template_manager.py` (new)

**Functions**:
- `get_templates_config(user_id: str) -> Optional[Dict]`
  - Read the `templates` variable for the user
  - Check if it's a CID or direct JSON
  - Parse and validate the JSON structure
  - Return parsed dict or None on error

- `validate_templates_json(json_data: str) -> Tuple[bool, Optional[str]]`
  - Validate JSON schema
  - Check for required keys (aliases, servers, variables, secrets)
  - Verify CID references are valid
  - Return (is_valid, error_message)

- `get_template_status(user_id: str) -> Dict[str, Any]`
  - Return status info: count, validity, error message
  - Used for generating status labels

- `get_templates_for_type(user_id: str, entity_type: str) -> List[Dict]`
  - Extract templates for specific entity type
  - Resolve embedded CIDs to actual content
  - Return list of template definitions

- `get_template_by_key(user_id: str, entity_type: str, template_key: str) -> Optional[Dict]`
  - Get a specific template by its key
  - Resolve embedded CIDs
  - Return template dict or None

**Tests**:
- `tests/test_template_manager.py` (new)
  - Test JSON parsing with valid structure
  - Test CID resolution
  - Test invalid JSON handling
  - Test missing templates variable
  - Test partial CID validation
  - Test embedded CID resolution

#### 1.2 Create Template Status Helper
**File**: `template_status.py` (new)

**Functions**:
- `generate_template_status_label(user_id: str, entity_type: Optional[str] = None) -> str`
  - Generate human-readable status label
  - If entity_type provided, show count for that type only
  - Otherwise show total count across all types

- `get_template_link_info(user_id: str, entity_type: Optional[str] = None) -> Dict[str, str]`
  - Return dict with 'label', 'url', 'css_class'
  - Used by templates to render status links

**Tests**:
- `tests/test_template_status.py` (new)
  - Test label generation for various states
  - Test link info generation
  - Test per-type vs global status

#### 1.3 Update Database Access Layer
**Files**: `db_access/aliases.py`, `db_access/servers.py`, `db_access/variables.py`, `db_access/secrets.py`

**Changes**:
- Update `get_user_template_*()` functions to use `template_manager`
- Remove direct database queries on `template` column
- Fetch templates from JSON configuration instead

**Example** (`db_access/aliases.py`):
```python
def get_user_template_aliases(user_id: str) -> List[Alias]:
    """Get template aliases from templates variable configuration."""
    from template_manager import get_templates_for_type
    templates = get_templates_for_type(user_id, 'aliases')
    # Convert template dicts to Alias objects (read-only representations)
    return [create_alias_from_template(t) for t in templates]
```

**File**: `db_access/generic_crud.py`

**Changes**:
- Update `get_templates_for_user()` to use new template system
- Route to appropriate type-specific function

**Tests**:
- `tests/test_db_access_templates.py` (new)
  - Test retrieval of templates from JSON config
  - Test empty template handling
  - Test invalid configuration handling
  - Test CID resolution in db_access layer

### Phase 2: UI Updates

#### 2.1 Create Template Status Component
**File**: `templates/_template_status.html` (new)

**Content**:
- Reusable component showing template status with link
- Takes parameters: user_id, entity_type
- Displays status label with appropriate styling
- Links to `/variables/templates` (filtered by entity_type if specified)

**Example**:
```html
{% macro render_template_status(user_id, entity_type=None) %}
  {% set status_info = get_template_status_info(user_id, entity_type) %}
  <a href="{{ url_for('main.templates_config', type=entity_type) }}"
     class="template-status {{ status_info.css_class }}">
    {{ status_info.label }}
  </a>
{% endmacro %}
```

#### 2.2 Update Entity List Pages
**Files**: `templates/aliases.html`, `templates/servers.html`, `templates/variables.html`, `templates/secrets.html`

**Changes**:
- Add template status component at top of page
- Remove "Template" badge display from individual items (since templates come from variable)
- Import and use `_template_status.html` macro

**Example addition** (for `aliases.html`):
```html
{% from '_template_status.html' import render_template_status %}

<div class="template-status-container">
  {{ render_template_status(current_user.id, 'aliases') }}
</div>
```

#### 2.3 Update Entity Form Pages
**Files**: `templates/alias_form.html`, `templates/server_form.html`, `templates/variable_form.html`, `templates/secret_form.html`

**Changes**:
- Remove template checkbox field (no longer stored in entity)
- Add template status component
- Templates now managed through `/variables/templates` page

#### 2.4 Create Templates Configuration Page
**File**: `templates/templates_config.html` (new)

**Route**: `/variables/templates` (in `routes/variables.py`)

**Features**:
- Display current templates variable content
- JSON editor for templates configuration
- Validation feedback
- Preview of templates by type
- Option to use CID or direct JSON
- Filter view by entity type (query param: `?type=aliases`)

**Sections**:
1. Status overview (counts by type)
2. JSON editor with syntax highlighting
3. Validation messages
4. Template preview (expandable per type)
5. Help text explaining structure

**Tests**:
- `tests/integration/test_templates_config_page.py` (new)
  - Test page access
  - Test JSON editor rendering
  - Test validation display
  - Test save functionality
  - Test filter by type

#### 2.5 Update Export Page
**File**: `templates/export.html`

**Changes**:
- Update template display to work with new system
- Templates shown should reflect JSON config, not DB column
- Update checkboxes for including/excluding templates

### Phase 3: Routes and Forms

#### 3.1 Update Entity CRUD Routes
**File**: `routes/entities.py`

**Changes**:
- Remove `entity.template = bool(template_field.data)` from `create_entity()` (line 229)
- Remove `entity.template = bool(template_field.data)` from `update_entity()` (line 229)
- Template flag no longer part of entity creation/update

#### 3.2 Create Templates Configuration Routes
**File**: `routes/variables.py`

**New Routes**:
```python
@main_bp.route('/variables/templates', methods=['GET'])
def view_templates_config():
    """Display templates configuration page."""
    # Show current templates variable
    # Display status and validation
    pass

@main_bp.route('/variables/templates/edit', methods=['GET', 'POST'])
def edit_templates_config():
    """Edit templates configuration."""
    # JSON editor for templates
    # Validation on save
    # Update templates variable
    pass

@main_bp.route('/variables/templates/validate', methods=['POST'])
def validate_templates_json():
    """AJAX endpoint for JSON validation."""
    # Real-time validation feedback
    pass
```

**Tests**:
- `tests/test_templates_routes.py` (new)
  - Test GET templates config page
  - Test POST templates config update
  - Test validation endpoint
  - Test permission checks

#### 3.3 Update Forms
**File**: `forms.py`

**Changes**:
- Remove `template = BooleanField('Template', default=False)` from `EntityForm` (line 49)
- Create new `TemplatesConfigForm` for editing templates JSON

**New Form**:
```python
class TemplatesConfigForm(FlaskForm):
    """Form for editing templates configuration."""
    templates_json = TextAreaField(
        'Templates Configuration',
        validators=[DataRequired(), validate_templates_json]
    )
    use_cid = BooleanField('Store as CID', default=False)
    submit = SubmitField('Save Templates')
```

#### 3.4 Update Variable Routes
**File**: `routes/variables.py`

**Changes**:
- Update `new_variable()` (line 321) to get templates from new system
- Update `get_user_template_variables()` call to use new function
- Remove template-related form handling

### Phase 4: Import/Export Updates

#### 4.1 Update Export Logic
**File**: `routes/import_export/export_helpers.py`

**Changes**:
- Update `should_export_entry()` to check template status from JSON config
- Add helper to determine if entity is a template based on templates variable

**New Function**:
```python
def is_template_entity(user_id: str, entity_type: str, entity_name: str) -> bool:
    """Check if entity is defined as a template in templates variable."""
    from template_manager import get_templates_for_type
    templates = get_templates_for_type(user_id, entity_type)
    return any(t.get('name') == entity_name for t in templates)
```

#### 4.2 Update Export Sections
**File**: `routes/import_export/export_sections.py`

**Changes**:
- Remove `template` field from exported entities (lines 74, 120, 159, 204)
- Add option to export templates variable itself
- Update entity serialization to exclude template flag

#### 4.3 Update Import Logic
**File**: `routes/import_export/import_entities.py`

**Changes**:
- Remove template flag handling from imports (lines 114, 120, 181, 187, 215, 223, 275, 284, 332, 338, 346, 399, 405, 413)
- Add logic to import templates variable if present
- Update dataclasses to remove `template: bool` field

**Changes to Dataclasses**:
```python
@dataclass
class AliasImport:
    name: str
    target_path: str
    # Remove: template: bool

@dataclass
class ServerImport:
    name: str
    definition: str
    # Remove: template: bool
```

#### 4.4 Update Export Form
**File**: `forms.py`

**Changes**:
- Update `ExportForm` to handle template filtering via templates variable
- Update field help text to reference new template system

**Tests**:
- Update `tests/test_import_export.py`
  - Test export without template flag
  - Test import without template flag
  - Test templates variable export/import
  - Test backward compatibility

### Phase 5: Context Processors

#### 5.1 Add Template Context Processor
**File**: `routes/context_processors.py`

**Changes**:
- Add function to inject template status helper into all templates

**New Function**:
```python
@main_bp.app_context_processor
def inject_template_helpers():
    """Inject template management helpers into template context."""
    from template_status import get_template_link_info, generate_template_status_label
    return {
        'get_template_link_info': get_template_link_info,
        'generate_template_status_label': generate_template_status_label,
    }
```

### Phase 6: Database Migration

#### 6.1 Remove Template Columns
**File**: `models.py`

**Changes**:
- Remove `template = db.Column(db.Boolean, nullable=False, default=False)` from:
  - `Server` (line 42)
  - `Alias` (line 59)
  - `Variable` (line 153)
  - `Secret` (line 169)

#### 6.2 Create Migration Script
**File**: `migrate_remove_template_columns.py` (new)

**Purpose**:
- Remove template columns from database tables
- Migrate existing template entities to templates variable
- Create initial templates JSON from existing template=True entities

**Process**:
1. Query all entities where `template=True`
2. Build templates JSON structure
3. Store as templates variable for each user
4. Drop template columns from tables
5. Log migration results

**Example**:
```python
def migrate_templates_to_variable():
    """Migrate template flags to templates variable."""
    for user in get_all_users():
        templates = {
            'aliases': {},
            'servers': {},
            'variables': {},
            'secrets': {}
        }

        # Collect template entities
        for alias in get_user_aliases(user.id):
            if alias.template:
                templates['aliases'][alias.name] = {
                    'name': alias.name,
                    'target_path_cid': store_as_cid(alias.target_path),
                    'metadata': {
                        'created': alias.created_at.isoformat(),
                        'migrated': True
                    }
                }

        # ... similar for servers, variables, secrets ...

        # Store as templates variable
        templates_json = json.dumps(templates, indent=2)
        create_or_update_variable(
            user.id,
            'templates',
            templates_json
        )
```

**Tests**:
- `tests/test_template_migration.py` (new)
  - Test migration with various template entities
  - Test migration with no templates
  - Test migration creates valid JSON
  - Test CID storage for large content
  - Test idempotency (running migration twice)

### Phase 7: Testing Strategy

#### 7.1 Unit Tests

**New Test Files**:
1. `tests/test_template_manager.py`
   - JSON parsing and validation
   - CID resolution
   - Template retrieval by type
   - Error handling

2. `tests/test_template_status.py`
   - Status label generation
   - Link info generation
   - Edge cases (no templates, invalid JSON)

3. `tests/test_db_access_templates.py`
   - Template retrieval through db_access layer
   - Integration with template_manager
   - Empty and invalid template handling

4. `tests/test_templates_routes.py`
   - Route access and permissions
   - Template config viewing
   - Template config editing
   - Validation endpoint

5. `tests/test_template_migration.py`
   - Migration script execution
   - Data integrity after migration
   - Idempotency

**Updated Test Files**:
1. `tests/test_import_export.py`
   - Remove template flag assertions
   - Add templates variable import/export tests
   - Update test fixtures

2. `tests/test_routes_comprehensive.py`
   - Update entity CRUD tests
   - Remove template flag checks
   - Add templates config route tests

3. `tests/test_crud_factory.py`
   - Update form handling tests
   - Remove template field tests

#### 7.2 Integration Tests

**New Test Files**:
1. `tests/integration/test_templates_config_page.py`
   - Full page rendering
   - Form submission
   - Validation feedback
   - Type filtering

2. `tests/integration/test_template_ui_components.py`
   - Template status display on entity pages
   - Link behavior
   - Status label accuracy

**Updated Test Files**:
1. `tests/integration/test_alias_pages.py`
   - Remove template checkbox tests (line ~88)
   - Add template status display tests
   - Update form submission tests

2. `tests/integration/test_server_pages.py`
   - Remove template checkbox tests (line ~92)
   - Add template status display tests
   - Update form submission tests

3. `tests/integration/test_variable_pages.py`
   - Remove template checkbox tests (line ~85)
   - Add template status display tests
   - Update template selection tests

4. `tests/integration/test_secret_pages.py`
   - Remove template checkbox tests (line ~80)
   - Add template status display tests
   - Update form submission tests

#### 7.3 Spec Tests (BDD)

**New Spec Files**:
1. `specs/template_configuration.spec`
   ```
   # Template Configuration Management

   ## View templates configuration
   * Navigate to "/variables/templates"
   * Should see templates status
   * Should see JSON editor

   ## Edit templates configuration
   * Navigate to "/variables/templates/edit"
   * Enter valid JSON in editor
   * Submit form
   * Should see success message
   * Should redirect to templates page

   ## Validate templates JSON
   * Navigate to "/variables/templates/edit"
   * Enter invalid JSON
   * Should see validation error
   * Should not save configuration
   ```

2. `specs/template_status_display.spec`
   ```
   # Template Status Display

   ## Status on alias page
   * Create templates variable with aliases
   * Navigate to "/aliases"
   * Should see "2 templates" status
   * Status should link to "/variables/templates"

   ## Status with no templates
   * Delete templates variable
   * Navigate to "/servers"
   * Should see "No templates" status

   ## Status with invalid templates
   * Create templates variable with invalid JSON
   * Navigate to "/variables"
   * Should see "Invalid template definition" status
   ```

**Updated Spec Files**:
1. Update `specs/alias_management.spec` - remove template checkbox scenarios
2. Update `specs/server_management.spec` - remove template checkbox scenarios
3. Update `specs/import_export.spec` - remove template flag scenarios

**New Step Implementations**:
- `step_impl/template_steps.py` - steps for template configuration scenarios

#### 7.4 Test Coverage Requirements

**Minimum Coverage Targets**:
- `template_manager.py`: 95%
- `template_status.py`: 90%
- Updated db_access functions: 90%
- Template routes: 85%
- Migration script: 85%

**Critical Test Scenarios**:
1. Empty templates variable (no templates defined)
2. Invalid JSON in templates variable
3. CID that doesn't exist
4. Large templates (requiring CID storage)
5. Concurrent template updates
6. Migration with mixed template/non-template entities
7. Import/export round-trip without template flags
8. Backward compatibility with old exports

### Phase 8: Documentation Updates

#### 8.1 User Documentation
**File**: `docs/templates.md` (new)

**Content**:
- Overview of template system
- How to configure templates via `/variables/templates`
- JSON structure documentation
- CID vs direct JSON storage
- Examples for each entity type
- Migration guide for users

#### 8.2 Developer Documentation
**File**: `docs/templates_technical.md` (new)

**Content**:
- Architecture overview
- Template manager API
- Adding new entity types
- Testing templates
- Migration scripts

#### 8.3 Update README
**File**: `README.md`

**Changes**:
- Update template system description
- Link to new template documentation
- Note breaking changes

### Phase 9: Backward Compatibility

#### 9.1 Handle Old Exports
**File**: `routes/import_export/import_entities.py`

**Changes**:
- Support importing old exports that include `template` flag
- Silently ignore template flag if present
- Log warning about deprecated field

**Example**:
```python
def import_alias(data: dict, user_id: str):
    """Import alias, handling legacy template field."""
    if 'template' in data:
        logger.warning(f"Ignoring deprecated 'template' field in alias import")

    # Continue with import without template field
    ...
```

#### 9.2 Graceful Degradation
**File**: `template_manager.py`

**Changes**:
- If templates variable doesn't exist, return empty templates
- Don't fail on missing or invalid templates
- Provide helpful error messages in UI

### Phase 10: Rollout Plan

#### 10.1 Pre-Migration Validation
1. Run full test suite on current code
2. Create database backup
3. Document current template usage statistics
4. Identify users with templates enabled

#### 10.2 Migration Execution
1. Deploy new code with feature flag disabled
2. Run migration script on staging
3. Validate migration results
4. Enable feature flag
5. Monitor for errors
6. Deploy to production

#### 10.3 Post-Migration Validation
1. Verify all templates migrated correctly
2. Check template status displays properly
3. Validate import/export functionality
4. Monitor error logs
5. Gather user feedback

#### 10.4 Rollback Plan
1. Keep template columns in database initially (deprecated)
2. Feature flag to switch between old/new system
3. If issues found, disable feature flag
4. Fix issues and re-deploy
5. Only drop columns after stable period

## File Changes Summary

### New Files (11)
1. `template_manager.py` - Core template logic
2. `template_status.py` - Status label generation
3. `templates/_template_status.html` - UI component
4. `templates/templates_config.html` - Configuration page
5. `migrate_remove_template_columns.py` - Migration script
6. `tests/test_template_manager.py` - Unit tests
7. `tests/test_template_status.py` - Unit tests
8. `tests/test_db_access_templates.py` - Unit tests
9. `tests/test_templates_routes.py` - Unit tests
10. `tests/test_template_migration.py` - Migration tests
11. `tests/integration/test_templates_config_page.py` - Integration tests

### Modified Files (29)
1. `models.py` - Remove template columns
2. `forms.py` - Remove template field, add TemplatesConfigForm
3. `db_access/generic_crud.py` - Use new template system
4. `db_access/aliases.py` - Use new template system
5. `db_access/servers.py` - Use new template system
6. `db_access/variables.py` - Use new template system
7. `db_access/secrets.py` - Use new template system
8. `routes/entities.py` - Remove template flag handling
9. `routes/variables.py` - Add template config routes
10. `routes/context_processors.py` - Add template helpers
11. `routes/import_export/export_helpers.py` - New template checking
12. `routes/import_export/export_sections.py` - Remove template flag
13. `routes/import_export/import_entities.py` - Remove template flag, backward compatibility
14. `templates/aliases.html` - Add status component, remove badge
15. `templates/servers.html` - Add status component, remove badge
16. `templates/variables.html` - Add status component, remove badge
17. `templates/secrets.html` - Add status component, remove badge
18. `templates/alias_form.html` - Remove template checkbox, add status
19. `templates/server_form.html` - Remove template checkbox, add status
20. `templates/variable_form.html` - Remove template checkbox, add status
21. `templates/secret_form.html` - Remove template checkbox, add status
22. `templates/export.html` - Update template filtering
23. `tests/test_import_export.py` - Remove template assertions
24. `tests/test_routes_comprehensive.py` - Update CRUD tests
25. `tests/test_crud_factory.py` - Update form tests
26. `tests/integration/test_alias_pages.py` - Update UI tests
27. `tests/integration/test_server_pages.py` - Update UI tests
28. `tests/integration/test_variable_pages.py` - Update UI tests
29. `tests/integration/test_secret_pages.py` - Update UI tests

### Deleted Columns (4)
1. `Server.template` column
2. `Alias.template` column
3. `Variable.template` column
4. `Secret.template` column

## Dependencies

### Python Packages
- No new dependencies required
- Uses existing: `json`, `typing`, CID infrastructure

### Frontend
- JSON editor library for templates config page (consider: CodeMirror or Monaco)
- No other new dependencies

## Risk Assessment

### High Risk
- Database migration (column removal)
- Breaking changes for existing template users

**Mitigation**:
- Thorough testing of migration script
- Staged rollout with feature flag
- Keep columns initially (mark deprecated)
- Comprehensive backward compatibility

### Medium Risk
- Import/export compatibility
- Performance with large template configurations

**Mitigation**:
- Support old export format
- CID storage for large templates
- Load testing with large configs
- Caching of parsed templates

### Low Risk
- UI changes
- New routes

**Mitigation**:
- Integration tests for UI
- Route permission tests
- User documentation

## Success Criteria

1. ✅ All template data migrated from DB columns to templates variable
2. ✅ All entity pages show template status with link
3. ✅ Template configuration page fully functional
4. ✅ Import/export works without template flags
5. ✅ Database columns removed cleanly
6. ✅ All tests passing (unit, integration, spec)
7. ✅ Test coverage meets targets
8. ✅ No performance degradation
9. ✅ Zero data loss during migration
10. ✅ Documentation complete

## Timeline Estimate

- **Phase 1** (Infrastructure): 2-3 days
- **Phase 2** (UI Updates): 2 days
- **Phase 3** (Routes/Forms): 1-2 days
- **Phase 4** (Import/Export): 2 days
- **Phase 5** (Context): 0.5 days
- **Phase 6** (Migration): 1-2 days
- **Phase 7** (Testing): 3-4 days
- **Phase 8** (Documentation): 1 day
- **Phase 9** (Compatibility): 1 day
- **Phase 10** (Rollout): 1 day

**Total**: ~15-19 days

## Open Questions

1. Should we allow per-entity-type template variables (e.g., `templates.aliases`) or only global `templates`?
2. Should templates be versioned (tracking changes over time)?
3. Should there be a UI for managing individual templates (vs editing raw JSON)?
4. Should we support template inheritance/composition?
5. How should template permissions work in multi-user scenarios?
6. Should we maintain a template changelog?
7. Should templates support validation rules for derived entities?

## Next Steps

1. Review and approve plan
2. Create tracking issues for each phase
3. Set up feature flag
4. Begin Phase 1 implementation
5. Establish testing schedule
6. Plan staging environment validation
