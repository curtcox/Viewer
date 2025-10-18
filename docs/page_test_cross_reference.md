# Page Test Cross Reference

This document maps site pages to the automated checks that exercise them.

## templates/alias_form.html

**Routes:**
- `routes/aliases.py::new_alias` (paths: `/aliases/new`)
- `routes/aliases.py::edit_alias` (paths: `/aliases/<alias_name>/edit`)

**Unit tests:**
- `tests/test_alias_routing.py::TestAliasRouting::test_create_alias_rejects_conflicting_route`
- `tests/test_alias_routing.py::TestAliasRouting::test_create_alias_via_form`
- `tests/test_alias_routing.py::TestAliasRouting::test_create_alias_with_glob_match_type`
- `tests/test_alias_routing.py::TestAliasRouting::test_edit_alias_rejects_conflicting_route_name`
- `tests/test_alias_routing.py::TestAliasRouting::test_edit_alias_updates_record`
- `tests/test_alias_routing.py::TestAliasRouting::test_new_alias_prefills_name_from_path_query`
- `tests/test_alias_routing.py::TestAliasRouting::test_test_pattern_button_displays_results_without_saving`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_new_alias_form_includes_ai_controls`

**Integration tests:**
- `tests/integration/test_alias_pages.py::test_new_alias_form_renders_for_authenticated_user`

**Specs:**
- _None_

## templates/alias_view.html

**Routes:**
- `routes/aliases.py::view_alias` (paths: `/aliases/<alias_name>`)

**Unit tests:**
- `tests/test_alias_routing.py::TestAliasRouting::test_view_alias_page`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_alias_detail_displays_cid_link_for_cid_target`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/aliases.html

**Routes:**
- `routes/aliases.py::aliases` (paths: `/aliases`)

**Unit tests:**
- `tests/test_alias_routing.py::TestAliasRouting::test_aliases_route_lists_aliases`
- `tests/test_alias_routing.py::TestAliasRouting::test_aliases_route_lists_aliases_for_default_user`
- `tests/test_error_page_source_links.py::TestErrorPageSourceLinks::test_aliases_error_shows_source_links_in_stack_trace`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_alias_list_displays_cid_link_for_cid_target`

**Integration tests:**
- `tests/integration/test_alias_pages.py::test_aliases_page_lists_user_aliases`

**Specs:**
- _None_

## templates/edit_cid.html

**Routes:**
- `routes/uploads.py::edit_cid` (paths: `/edit/<cid_prefix>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_alias_name_conflict_shows_error`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_full_match_preferred_over_prefix`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_full_match`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_unique_prefix`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_with_existing_alias_updates_button_text`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_without_alias_shows_alias_field`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_multiple_matches`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_not_found`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_allows_creating_new_alias`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_creates_new_record`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_existing_content`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_updates_existing_alias_target`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_requires_login`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/edit_cid_choices.html

**Routes:**
- `routes/uploads.py::edit_cid` (paths: `/edit/<cid_prefix>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_alias_name_conflict_shows_error`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_full_match_preferred_over_prefix`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_full_match`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_unique_prefix`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_with_existing_alias_updates_button_text`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_without_alias_shows_alias_field`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_multiple_matches`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_not_found`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_allows_creating_new_alias`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_creates_new_record`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_existing_content`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_updates_existing_alias_target`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_requires_login`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/export.html

**Routes:**
- `routes/import_export.py::export_data` (paths: `/export`)

**Unit tests:**
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_allows_runtime_only`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_excludes_unreferenced_cids_by_default`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_excludes_virtualenv_python_files`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_app_source_cids`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_runtime_section`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_selected_collections`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_unreferenced_cids_when_requested`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_without_cid_map_excludes_section`

**Integration tests:**
- `tests/integration/test_import_export_flow.py::test_user_can_transport_server_between_sites`

**Specs:**
- _None_

## templates/export_result.html

**Routes:**
- `routes/import_export.py::export_data` (paths: `/export`)

**Unit tests:**
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_allows_runtime_only`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_excludes_unreferenced_cids_by_default`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_excludes_virtualenv_python_files`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_app_source_cids`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_runtime_section`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_selected_collections`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_includes_unreferenced_cids_when_requested`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_export_without_cid_map_excludes_section`

**Integration tests:**
- `tests/integration/test_import_export_flow.py::test_user_can_transport_server_between_sites`

**Specs:**
- _None_

## templates/history.html

**Routes:**
- `routes/history.py::history` (paths: `/history`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestHistoryRoutes::test_history_page`
- `tests/test_routes_comprehensive.py::TestHistoryRoutes::test_history_pagination`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/import.html

**Routes:**
- `routes/import_export.py::import_data` (paths: `/import`)

**Unit tests:**
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_change_history_creates_events`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_rejects_invalid_secret_key`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_rejects_mismatched_cid_map_entry`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_reports_mismatched_app_source`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_reports_missing_cid_content`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_reports_missing_selected_content`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_import_verifies_app_source_matches`
- `tests/test_import_export.py::ImportExportRoutesTestCase::test_successful_import_creates_entries`
- `tests/test_routes_comprehensive.py::TestSettingsRoutes::test_import_form_includes_ai_controls`

**Integration tests:**
- `tests/integration/test_import_export_flow.py::test_user_can_transport_server_between_sites`

**Specs:**
- _None_

## templates/index.html

**Routes:**
- `routes/core.py::index` (paths: `/`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_alias_target_displays_cid_link_for_cid_path`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_authenticated_shows_cross_reference_dashboard`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_cids_include_incoming_highlight_metadata`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_lists_entities_and_relationships`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_shortcuts_link_to_entity_lists`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_skips_cids_without_named_alias`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_skips_cids_without_named_server`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_unauthenticated`

**Integration tests:**
- _None_

**Specs:**
- meta_navigation.spec — Info icon links to metadata

## templates/profile.html

**Routes:**
- `routes/core.py::profile` (paths: `/profile`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestAuthenticatedRoutes::test_navigation_includes_meta_inspector_link`
- `tests/test_routes_comprehensive.py::TestAuthenticatedRoutes::test_profile_page`
- `tests/test_routes_comprehensive.py::TestPageViewTracking::test_page_view_tracking_authenticated`

**Integration tests:**
- `tests/integration/test_profile_page.py::test_profile_page_links_to_workspace`

**Specs:**
- _None_

## templates/routes_overview.html

**Routes:**
- `routes/routes_overview.py::routes_overview` (paths: `/routes`)

**Unit tests:**
- `tests/test_routes_overview.py::RoutesOverviewTestCase::test_frontend_filtering_orders_exact_partial_and_not_found`
- `tests/test_routes_overview.py::RoutesOverviewTestCase::test_lists_builtin_alias_and_server_routes`
- `tests/test_routes_overview.py::RoutesOverviewTestCase::test_requires_login`

**Integration tests:**
- `tests/integration/test_routes_overview_page.py::test_routes_overview_lists_user_routes`

**Specs:**
- _None_

## templates/secret_form.html

**Routes:**
- `routes/secrets.py::new_secret` (paths: `/secrets/new`)
- `routes/secrets.py::edit_secret` (paths: `/secrets/<secret_name>/edit`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_new_secret_form_includes_ai_controls`
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_new_secret_post`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/secret_view.html

**Routes:**
- `routes/secrets.py::view_secret` (paths: `/secrets/<secret_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_view_secret_missing_returns_404`
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_view_secret_page_displays_secret_details`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/secrets.html

**Routes:**
- `routes/secrets.py::secrets` (paths: `/secrets`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_new_secret_post`
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_secrets_list`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/server_events.html

**Routes:**
- `routes/uploads.py::server_events` (paths: `/server_events`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_server_events_page_shows_invocations`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/server_form.html

**Routes:**
- `routes/servers.py::new_server` (paths: `/servers/new`)
- `routes/servers.py::edit_server` (paths: `/servers/<server_name>/edit`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_get`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_includes_test_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_post`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_duplicate_name`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_get`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_post`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_prefills_name_from_path_query`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/server_view.html

**Routes:**
- `routes/servers.py::view_server` (paths: `/servers/<server_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_nonexistent_server`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_falls_back_to_query_test_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_includes_main_test_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_invocation_history_table`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/servers.html

**Routes:**
- `routes/servers.py::servers` (paths: `/servers`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_post`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_servers_list`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/settings.html

**Routes:**
- `routes/core.py::settings` (paths: `/settings`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSettingsRoutes::test_settings_page`
- `tests/test_routes_comprehensive.py::TestSettingsRoutes::test_settings_page_shows_direct_access_links`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/source_browser.html

**Routes:**
- `routes/source.py::source_browser` (paths: `/source`, `/source/<path:requested_path>`)

**Unit tests:**
- `tests/test_enhanced_error_pages.py::TestEnhancedErrorPageIntegration::test_source_browser_serves_comprehensive_files`
- `tests/test_error_pages.py::TestEnhancedSourceBrowser::test_enhanced_source_browser_serves_untracked_files`
- `tests/test_error_pages_e2e.py::TestErrorPagesEndToEnd::test_source_browser_accessibility_from_error_links`
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_htmlcov_serves_raw_content`
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_index_lists_tracked_files`
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_rejects_files_outside_project`
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_rejects_path_traversal`
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_serves_file_content`
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_serves_untracked_project_files`
- `tests/test_source_spec_report.py::test_source_serves_gauge_report`

**Integration tests:**
- _None_

**Specs:**
- source_browser.spec — Source listing renders

## templates/upload.html

**Routes:**
- `routes/uploads.py::upload` (paths: `/upload`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_duplicate_file`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_get`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_post_success`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_handles_no_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_preserves_original_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_text_gets_txt_extension`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/upload_success.html

**Routes:**
- `routes/uploads.py::upload` (paths: `/upload`)
- `routes/uploads.py::edit_cid` (paths: `/edit/<cid_prefix>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_alias_name_conflict_shows_error`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_full_match_preferred_over_prefix`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_full_match`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_unique_prefix`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_with_existing_alias_updates_button_text`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_get_without_alias_shows_alias_field`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_multiple_matches`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_not_found`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_allows_creating_new_alias`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_creates_new_record`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_existing_content`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_cid_save_updates_existing_alias_target`
- `tests/test_routes_comprehensive.py::TestCidEditingRoutes::test_edit_requires_login`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_duplicate_file`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_get`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_post_success`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_handles_no_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_preserves_original_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_text_gets_txt_extension`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/uploads.html

**Routes:**
- `routes/uploads.py::uploads` (paths: `/uploads`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_uploads_list`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_uploads_list_excludes_server_events`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/variable_form.html

**Routes:**
- `routes/variables.py::new_variable` (paths: `/variables/new`)
- `routes/variables.py::edit_variable` (paths: `/variables/<variable_name>/edit`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_new_variable_form_includes_ai_controls`
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_new_variable_post`
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_variable_edit_shows_404_matching_route`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/variable_view.html

**Routes:**
- `routes/variables.py::view_variable` (paths: `/variables/<variable_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_variable_view_shows_matching_route_summary`

**Integration tests:**
- _None_

**Specs:**
- _None_

## templates/variables.html

**Routes:**
- `routes/variables.py::variables` (paths: `/variables`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_new_variable_post`
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_variables_list`

**Integration tests:**
- _None_

**Specs:**
- _None_
