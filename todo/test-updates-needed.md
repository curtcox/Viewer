# Remaining Test Updates for Template System Refactor

## Status
**Core infrastructure complete** - All routes and import/export updated
**27 tests failing** - Tests need updates to remove `.template` attribute checks

## Failing Tests Summary

### Route Tests (tests/test_routes_comprehensive.py)
- `test_new_server_post_creates_template_backed_server` - Remove `server.template` assertion
- `test_edit_server_get_returns_populated_form` - May reference template field
- `test_new_server_duplicate_name_shows_error_and_preserves_original` - Check for template refs
- `test_new_server_get` - May have template field
- `test_new_server_prefills_name_from_path_query` - Check for template refs
- `test_edit_server_includes_test_form` - May reference template
- `test_new_variable_post_creates_template_variable` - Remove `variable.template` assertion
- `test_new_variable_form_includes_ai_controls` - Check for template refs
- `test_variable_edit_shows_404_matching_route` - Check for template refs
- `test_new_secret_form_includes_ai_controls` - Check for template refs
- `test_new_secret_post_persists_secret_and_flashes_success` - Remove `secret.template` assertion
- `test_edit_alias_save_as_creates_new_alias` - Check for template refs

### Import/Export Tests (tests/test_import_export.py)
- `test_export_and_import_preserve_enablement` - Remove template field assertions
- `test_export_includes_disabled_templates_with_template_selection` - Update for new system
- `test_export_preview_respects_disabled_and_template_filters` - Update for new system
- `test_export_requires_template_selection_for_templates` - Update for new system
- `test_import_cid_values_backward_compatibility` - Remove template checks
- `test_import_cid_values_from_utf8_strings` - Remove template checks
- `test_import_defaults_to_utf8_without_encoding` - Remove template checks
- `test_import_generates_snapshot_export` - Remove template checks
- `test_snapshot_unchecked_applies_default_settings` - Remove template checks
- `test_successful_import_creates_entries` - Remove template checks

### Alias Route Tests (tests/test_alias_routing.py)
- `test_create_alias_via_form` - May submit template field
- `test_create_alias_with_glob_match_type` - May reference template

### Boot CID Tests (tests/test_boot_cid_importer.py)
- `test_import_boot_cid_success` - Check for template refs
- `test_import_boot_cid_with_cid_values_section` - Check for template refs

### Integration Tests (tests/integration/)
- `test_identity_responses.py::test_alias_creation_redirects_consistently` - Check for template refs

## Fix Pattern

For each test, apply these changes:

1. **Remove template field from form submissions:**
   ```python
   # Before:
   data={'name': 'test', 'definition': 'value', 'template': 'y'}

   # After:
   data={'name': 'test', 'definition': 'value'}
   ```

2. **Remove template attribute assertions:**
   ```python
   # Before:
   self.assertTrue(server.template)
   self.assertFalse(alias.template)

   # After:
   # (remove these lines)
   ```

3. **Remove template from export assertions:**
   ```python
   # Before:
   self.assertIn('template', exported['aliases'][0])
   self.assertTrue(exported['aliases'][0]['template'])

   # After:
   # (remove these lines)
   ```

4. **Remove template from entity creation:**
   ```python
   # Before:
   alias = Alias(name='test', definition='value', user_id=user_id, template=True)

   # After:
   alias = Alias(name='test', definition='value', user_id=user_id)
   ```

## Commands to Run

```bash
# After fixing all tests, verify with:
./test-unit

# Should show:
# === X passed, 0 failed ===

# Then run full checks:
./full-checks
```

## Notes

- Template functionality is now managed through the `templates` variable (JSON configuration)
- Entity models (Server, Alias, Variable, Secret) no longer have a `template` attribute
- Import/export no longer includes template field in payloads
- Tests need manual review to ensure they're testing the right behavior
