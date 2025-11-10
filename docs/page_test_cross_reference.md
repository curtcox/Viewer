# Page Test Cross Reference

This document maps site pages to the automated checks that exercise them.

## templates/alias_form.html

**Routes:**
- `routes/aliases.py::new_alias` (paths: `/aliases/new`)
- `routes/aliases.py::edit_alias` (paths: `/aliases/<alias_name>/edit`)

**Unit tests:**
- `tests/integration/test_identity_responses.py::test_alias_creation_redirects_consistently`
- `tests/test_alias_routing.py::TestAliasRouting::test_create_alias_rejects_conflicting_route`
- `tests/test_alias_routing.py::TestAliasRouting::test_create_alias_via_form`
- `tests/test_alias_routing.py::TestAliasRouting::test_create_alias_with_glob_match_type`
- `tests/test_alias_routing.py::TestAliasRouting::test_edit_alias_rejects_conflicting_route_name`
- `tests/test_alias_routing.py::TestAliasRouting::test_edit_alias_updates_record`
- `tests/test_alias_routing.py::TestAliasRouting::test_new_alias_prefills_fields_from_query_parameters`
- `tests/test_alias_routing.py::TestAliasRouting::test_new_alias_prefills_name_from_path_query`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_edit_alias_post_updates_alias`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_edit_alias_save_as_creates_new_alias`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_new_alias_form_includes_ai_controls`

**Integration tests:**
- `tests/integration/test_alias_pages.py::test_new_alias_form_includes_template_options`
- `tests/integration/test_alias_pages.py::test_new_alias_form_renders_for_authenticated_user`

**Specs:**
- alias_management.spec — Alias form responds the same for all users
- alias_management.spec — Users can create aliases through the form

## templates/alias_view.html

**Routes:**
- `routes/aliases.py::view_alias` (paths: `/aliases/<alias_name>`)

**Unit tests:**
- `tests/test_alias_routing.py::TestAliasRouting::test_view_alias_displays_nested_alias_paths`
- `tests/test_alias_routing.py::TestAliasRouting::test_view_alias_page`
- `tests/test_routes_comprehensive.py::TestAliasRoutes::test_alias_detail_displays_cid_link_for_cid_target`

**Integration tests:**
- `tests/integration/test_alias_pages.py::test_alias_detail_page_displays_alias_information`
- `tests/integration/test_content_negotiation_integration.py::test_alias_detail_endpoint_returns_record`
- `tests/integration/test_content_negotiation_integration.py::test_alias_detail_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_alias_detail_endpoint_supports_xml_extension`

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
- `tests/integration/test_alias_pages.py::test_aliases_page_includes_enabled_toggle`
- `tests/integration/test_alias_pages.py::test_aliases_page_lists_user_aliases`
- `tests/integration/test_content_negotiation_integration.py::test_aliases_endpoint_honors_plain_text_accept_header`
- `tests/integration/test_content_negotiation_integration.py::test_aliases_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_aliases_endpoint_supports_json_extension`
- `tests/integration/test_content_negotiation_integration.py::test_aliases_endpoint_supports_xml_extension`

**Specs:**
- alias_management.spec — Aliases list shows available shortcuts
- content_negotiation.spec — Accept headers request alternate representations

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
- `tests/integration/test_upload_pages.py::test_edit_cid_choices_page_prompts_for_selection`
- `tests/integration/test_upload_pages.py::test_edit_cid_page_prefills_existing_content`

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
- `tests/integration/test_upload_pages.py::test_edit_cid_choices_page_prompts_for_selection`
- `tests/integration/test_upload_pages.py::test_edit_cid_page_prefills_existing_content`

**Specs:**
- _None_

## templates/history.html

**Routes:**
- `routes/history.py::history` (paths: `/history`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestHistoryRoutes::test_history_page_displays_invocation_and_referer_details`
- `tests/test_routes_comprehensive.py::TestHistoryRoutes::test_history_pagination_second_page_empty_results`

**Integration tests:**
- `tests/integration/test_history_page.py::test_history_page_displays_recent_activity`

**Specs:**
- _None_

## templates/index.html

**Routes:**
- `routes/core.py::index` (paths: `/`)

**Unit tests:**
- `tests/test_app_startup.py::test_create_app_creates_alias_definition_column`
- `tests/test_app_startup.py::test_create_app_handles_logfire_configuration_errors`
- `tests/test_app_startup.py::test_create_app_handles_logfire_instrumentation_errors`
- `tests/test_app_startup.py::test_create_app_serves_homepage`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_alias_target_displays_cid_link_for_cid_path`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_authenticated_shows_cross_reference_dashboard`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_alias_and_server_highlight_metadata`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_alias_to_alias_highlight_metadata`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_cids_include_incoming_highlight_metadata`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_lists_entities_and_relationships`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_shortcuts_link_to_entity_lists`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_cross_reference_skips_cids_without_named_alias`
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_index_unauthenticated`
- `tests/test_routes_comprehensive.py::TestSearchApi::test_index_cross_reference_skips_cids_without_named_server`

**Integration tests:**
- `tests/integration/test_index_page.py::test_index_page_displays_cross_reference_dashboard`
- `tests/integration/test_index_page.py::test_viewer_menu_lists_user_entities`
- `tests/integration/test_route_details_page.py::test_route_details_for_builtin_index`

**Specs:**
- meta_navigation.spec — Info icon links to metadata

## templates/profile.html

**Routes:**
- `routes/core.py::profile` (paths: `/profile`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestAuthenticatedRoutes::test_navigation_includes_meta_inspector_link`
- `tests/test_routes_comprehensive.py::TestAuthenticatedRoutes::test_profile_page_returns_success_for_authenticated_user`
- `tests/test_routes_comprehensive.py::TestPageViewTracking::test_page_view_tracking_authenticated`

**Integration tests:**
- `tests/integration/test_profile_page.py::test_profile_page_links_to_workspace`

**Specs:**
- profile.spec — Default workspace profile is accessible

## templates/route_details.html

**Routes:**
- `routes/route_details.py::route_details` (paths: `/routes/`, `/routes/<path:requested_path>`)

**Unit tests:**
- _None_

**Integration tests:**
- `tests/integration/test_route_details_page.py::test_route_details_follow_alias_chain_to_cid`
- `tests/integration/test_route_details_page.py::test_route_details_follow_alias_chain_to_server`
- `tests/integration/test_route_details_page.py::test_route_details_for_alias_redirect`
- `tests/integration/test_route_details_page.py::test_route_details_for_builtin_index`
- `tests/integration/test_route_details_page.py::test_route_details_for_direct_cid`
- `tests/integration/test_route_details_page.py::test_route_details_for_server_execution`

**Specs:**
- _None_

## templates/routes_overview.html

**Routes:**
- `routes/routes_overview.py::routes_overview` (paths: `/routes`)

**Unit tests:**
- `tests/test_routes_overview.py::TestRoutesOverview::test_frontend_filtering_orders_exact_partial_and_not_found`
- `tests/test_routes_overview.py::TestRoutesOverview::test_lists_builtin_alias_and_server_routes`
- `tests/test_routes_overview.py::TestRoutesOverview::test_requires_login`

**Integration tests:**
- `tests/integration/test_routes_overview_page.py::test_routes_overview_lists_user_routes`

**Specs:**
- routes_overview.spec — Routes overview highlights available route types

## templates/search.html

**Routes:**
- `routes/search.py::search_page` (paths: `/search`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestPublicRoutes::test_search_page_renders_with_filters`

**Integration tests:**
- `tests/integration/test_search_page.py::test_search_page_displays_filters_and_status`

**Specs:**
- search.spec — Search page is accessible with filters

## templates/secret_form.html

**Routes:**
- `routes/secrets.py::new_secret` (paths: `/secrets/new`)
- `routes/secrets.py::edit_secret` (paths: `/secrets/<secret_name>/edit`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_new_secret_form_includes_ai_controls`
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_new_secret_post_persists_secret_and_flashes_success`

**Integration tests:**
- `tests/integration/test_secret_pages.py::test_edit_secret_form_displays_existing_secret`
- `tests/integration/test_secret_pages.py::test_edit_secret_updates_definition_snapshot`
- `tests/integration/test_secret_pages.py::test_new_secret_form_includes_templates`
- `tests/integration/test_secret_pages.py::test_new_secret_form_renders_for_authenticated_user`

**Specs:**
- secret_form.spec — Secret form is accessible

## templates/secret_view.html

**Routes:**
- `routes/secrets.py::view_secret` (paths: `/secrets/<secret_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_view_secret_missing_returns_404`
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_view_secret_page_displays_secret_details`

**Integration tests:**
- `tests/integration/test_content_negotiation_integration.py::test_secret_detail_endpoint_returns_record`
- `tests/integration/test_content_negotiation_integration.py::test_secret_detail_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_secret_detail_endpoint_supports_xml_extension`
- `tests/integration/test_secret_pages.py::test_secret_detail_page_displays_secret_information`

**Specs:**
- _None_

## templates/secrets.html

**Routes:**
- `routes/secrets.py::secrets` (paths: `/secrets`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_new_secret_post_persists_secret_and_flashes_success`
- `tests/test_routes_comprehensive.py::TestSecretRoutes::test_secrets_list_returns_ok_for_authenticated_user`

**Integration tests:**
- `tests/integration/test_content_negotiation_integration.py::test_secrets_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_secrets_endpoint_supports_json_extension`
- `tests/integration/test_content_negotiation_integration.py::test_secrets_endpoint_supports_xml_extension`
- `tests/integration/test_secret_pages.py::test_edit_secret_updates_definition_snapshot`
- `tests/integration/test_secret_pages.py::test_secrets_list_page_displays_user_secrets`
- `tests/integration/test_secret_pages.py::test_secrets_page_includes_enabled_toggle`

**Specs:**
- secrets.spec — Secrets list is accessible

## templates/secrets_bulk_edit.html

**Routes:**
- `routes/secrets.py::bulk_edit_secrets` (paths: `/secrets/_/edit`)

**Unit tests:**
- _None_

**Integration tests:**
- `tests/integration/test_secret_pages.py::test_bulk_secret_editor_invalid_json_displays_errors`
- `tests/integration/test_secret_pages.py::test_bulk_secret_editor_prefills_existing_secrets`
- `tests/integration/test_secret_pages.py::test_bulk_secret_editor_updates_and_deletes_secrets`

**Specs:**
- _None_

## templates/server_events.html

**Routes:**
- `routes/uploads.py::server_events` (paths: `/server_events`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_server_events_page_shows_invocations`

**Integration tests:**
- `tests/integration/test_server_events_page.py::test_server_events_page_lists_recent_invocations`

**Specs:**
- server_events.spec — Server events dashboard is accessible

## templates/server_form.html

**Routes:**
- `routes/servers.py::new_server` (paths: `/servers/new`)
- `routes/servers.py::edit_server` (paths: `/servers/<server_name>/edit`)

**Unit tests:**
- `tests/integration/test_identity_responses.py::test_server_creation_redirects_consistently`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_get_returns_populated_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_includes_test_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_post_updates_name_and_definition`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_edit_server_save_as_creates_new_server`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_duplicate_name_shows_error_and_preserves_original`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_get`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_post_creates_template_backed_server`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_prefills_name_from_path_query`

**Integration tests:**
- `tests/integration/test_server_pages.py::test_edit_server_updates_definition_snapshots`
- `tests/integration/test_server_pages.py::test_new_server_form_includes_saved_templates`
- `tests/integration/test_server_pages.py::test_new_server_form_renders_for_authenticated_user`

**Specs:**
- server_form.spec — New server form is accessible
- server_form.spec — Server form stays available without a user session

## templates/server_view.html

**Routes:**
- `routes/servers.py::view_server` (paths: `/servers/<server_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_nonexistent_server_returns_404`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_falls_back_to_query_test_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_includes_main_test_form`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_invocation_history_table`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_view_server_renders_referenced_entities_and_returns_ok`

**Integration tests:**
- `tests/integration/test_content_negotiation_integration.py::test_server_detail_endpoint_returns_record`
- `tests/integration/test_content_negotiation_integration.py::test_server_detail_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_server_detail_endpoint_supports_xml_extension`
- `tests/integration/test_server_pages.py::test_server_detail_page_displays_server_information`

**Specs:**
- _None_

## templates/servers.html

**Routes:**
- `routes/servers.py::servers` (paths: `/servers`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_new_server_post_creates_template_backed_server`
- `tests/test_routes_comprehensive.py::TestServerRoutes::test_servers_list_shows_overview_and_create_link`

**Integration tests:**
- `tests/integration/test_content_negotiation_integration.py::test_servers_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_servers_endpoint_supports_json_extension`
- `tests/integration/test_content_negotiation_integration.py::test_servers_endpoint_supports_xml_extension`
- `tests/integration/test_server_pages.py::test_edit_server_updates_definition_snapshots`
- `tests/integration/test_server_pages.py::test_servers_page_includes_enabled_toggle`
- `tests/integration/test_server_pages.py::test_servers_page_links_auto_main_context_matches`
- `tests/integration/test_server_pages.py::test_servers_page_lists_user_servers`
- `tests/integration/test_server_pages.py::test_servers_page_shows_referenced_variables_and_secrets`

**Specs:**
- _None_

## templates/settings.html

**Routes:**
- `routes/core.py::settings` (paths: `/settings`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSettingsRoutes::test_settings_page_loads_for_authenticated_user`
- `tests/test_routes_comprehensive.py::TestSettingsRoutes::test_settings_page_shows_direct_access_links`

**Integration tests:**
- `tests/integration/test_settings_page.py::test_settings_page_displays_resource_counts_and_links`

**Specs:**
- settings.spec — Settings dashboard lists resource management links

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
- `tests/integration/test_source_browser_page.py::test_source_browser_displays_file_content`
- `tests/integration/test_source_browser_page.py::test_source_browser_displays_running_commit_link`
- `tests/integration/test_source_browser_page.py::test_source_browser_links_to_instance_overview`
- `tests/integration/test_source_browser_page.py::test_source_browser_lists_directories`

**Specs:**
- source_browser.spec — Source listing renders

## templates/source_instance.html

**Routes:**
- `routes/source.py::source_instance_overview` (paths: `/source/instance`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_instance_overview_lists_database_tables`

**Integration tests:**
- `tests/integration/test_source_browser_page.py::test_source_instance_lists_tables`

**Specs:**
- _None_

## templates/source_instance_table.html

**Routes:**
- `routes/source.py::source_instance_table` (paths: `/source/instance/<string:table_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestSourceRoutes::test_source_instance_table_renders_existing_rows`

**Integration tests:**
- `tests/integration/test_source_browser_page.py::test_source_instance_table_view_displays_rows`

**Specs:**
- _None_

## templates/upload.html

**Routes:**
- `routes/uploads.py::upload` (paths: `/upload`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_duplicate_file_is_deduplicated`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_get_returns_200_with_text_ai_markup`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_post_stores_file_and_returns_success_page`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_assign_cid_creates_new_variable`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_assign_cid_updates_existing_variable`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_handles_no_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_preserves_original_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_success_includes_variable_assignment_form`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_text_gets_txt_extension`

**Integration tests:**
- `tests/integration/test_upload_pages.py::test_upload_page_allows_user_to_choose_upload_method`

**Specs:**
- _None_

## templates/upload_success.html

**Routes:**
- `routes/uploads.py::upload` (paths: `/upload`)
- `routes/uploads.py::edit_cid` (paths: `/edit/<cid_prefix>`)
- `routes/uploads.py::assign_cid_variable` (paths: `/upload/assign-variable`)

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
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_duplicate_file_is_deduplicated`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_get_returns_200_with_text_ai_markup`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_upload_post_stores_file_and_returns_success_page`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_assign_cid_creates_new_variable`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_assign_cid_updates_existing_variable`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_handles_no_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_file_preserves_original_extension`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_success_includes_variable_assignment_form`
- `tests/test_upload_extensions.py::TestUploadExtensions::test_upload_text_gets_txt_extension`

**Integration tests:**
- `tests/integration/test_upload_pages.py::test_edit_cid_choices_page_prompts_for_selection`
- `tests/integration/test_upload_pages.py::test_edit_cid_page_prefills_existing_content`
- `tests/integration/test_upload_pages.py::test_upload_page_allows_user_to_choose_upload_method`

**Specs:**
- _None_

## templates/uploads.html

**Routes:**
- `routes/uploads.py::uploads` (paths: `/uploads`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_uploads_list_displays_reference_placeholder`
- `tests/test_routes_comprehensive.py::TestFileUploadRoutes::test_uploads_list_excludes_server_events`

**Integration tests:**
- `tests/integration/test_upload_pages.py::test_uploads_page_displays_user_uploads`

**Specs:**
- _None_

## templates/variable_form.html

**Routes:**
- `routes/variables.py::new_variable` (paths: `/variables/new`)
- `routes/variables.py::edit_variable` (paths: `/variables/<variable_name>/edit`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_new_variable_form_includes_ai_controls`
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_new_variable_post_creates_template_variable`
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_variable_edit_shows_404_matching_route`

**Integration tests:**
- `tests/integration/test_variable_pages.py::test_edit_variable_form_displays_existing_variable_details`
- `tests/integration/test_variable_pages.py::test_edit_variable_updates_definition_snapshot`
- `tests/integration/test_variable_pages.py::test_new_variable_form_includes_templates`
- `tests/integration/test_variable_pages.py::test_new_variable_form_renders_for_authenticated_user`

**Specs:**
- _None_

## templates/variable_view.html

**Routes:**
- `routes/variables.py::view_variable` (paths: `/variables/<variable_name>`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_variable_view_shows_matching_route_summary`

**Integration tests:**
- `tests/integration/test_content_negotiation_integration.py::test_variable_detail_endpoint_returns_record`
- `tests/integration/test_content_negotiation_integration.py::test_variable_detail_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_variable_detail_endpoint_supports_xml_extension`
- `tests/integration/test_variable_pages.py::test_variable_detail_page_displays_variable_information`

**Specs:**
- _None_

## templates/variables.html

**Routes:**
- `routes/variables.py::variables` (paths: `/variables`)

**Unit tests:**
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_new_variable_post_creates_template_variable`
- `tests/test_routes_comprehensive.py::TestVariableRoutes::test_variables_list_shows_sorted_user_variables`

**Integration tests:**
- `tests/integration/test_content_negotiation_integration.py::test_variables_endpoint_supports_csv_extension`
- `tests/integration/test_content_negotiation_integration.py::test_variables_endpoint_supports_json_extension`
- `tests/integration/test_content_negotiation_integration.py::test_variables_endpoint_supports_xml_extension`
- `tests/integration/test_variable_pages.py::test_edit_variable_updates_definition_snapshot`
- `tests/integration/test_variable_pages.py::test_variables_page_includes_enabled_toggle`
- `tests/integration/test_variable_pages.py::test_variables_page_lists_user_variables`

**Specs:**
- _None_

## templates/variables_bulk_edit.html

**Routes:**
- `routes/variables.py::bulk_edit_variables` (paths: `/variables/_/edit`)

**Unit tests:**
- _None_

**Integration tests:**
- `tests/integration/test_variable_pages.py::test_bulk_variable_editor_invalid_json_displays_errors`
- `tests/integration/test_variable_pages.py::test_bulk_variable_editor_prefills_existing_variables`
- `tests/integration/test_variable_pages.py::test_bulk_variable_editor_updates_and_deletes_variables`

**Specs:**
- _None_
