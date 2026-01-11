# Vulture dead code analysis

* Found 68 potential dead code issue(s) across 31 file(s).
* Minimum confidence threshold: 80%

## Summary by type

| Type | Count |
| --- | ---: |
| import | 18 |
| unknown | 2 |
| variable | 48 |

## Dead code findings

| File | Line | Confidence | Type | Message |
| --- | ---: | ---: | --- | --- |
| cid_utils.py | 21 | 80% | import | unused import '_base64url_decode' (90% confidence, 27 lines) |
| cid_utils.py | 21 | 80% | import | unused import '_normalize_component' (90% confidence, 27 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_convert_github_relative_links' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_count_bullet_lines' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_decode_text_safely' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_extract_markdown_title' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_GITHUB_RELATIVE_LINK_PATH_SANITIZER' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_GITHUB_RELATIVE_LINK_PATTERN' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_INLINE_BOLD_PATTERN' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_INLINE_CODE_PATTERN' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_INLINE_ITALIC_PATTERN' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_MARKDOWN_EXTENSIONS' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_MARKDOWN_INDICATOR_PATTERNS' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_normalize_github_relative_link_target_v2' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_replace_formdown_fences' (90% confidence, 22 lines) |
| cid_utils.py | 59 | 80% | import | unused import '_replace_mermaid_fences' (90% confidence, 22 lines) |
| cid_utils.py | 110 | 80% | import | unused import '_generate_qr_data_url' (90% confidence, 4 lines) |
| reference/templates/servers/definitions/amplitude.py | 47 | 80% | variable | unused variable 'AMPLITUDE_SECRET_KEY' (100% confidence, 1 line) |
| reference/templates/servers/definitions/coda.py | 53 | 80% | variable | unused variable 'column_id' (100% confidence, 1 line) |
| reference/templates/servers/definitions/gateway.py | 187 | 80% | unknown | unreachable code after 'return' (100% confidence, 30 lines) |
| reference/templates/servers/definitions/paypal.py | 98 | 80% | variable | unused variable 'payment_id' (100% confidence, 1 line) |
| reference/templates/servers/definitions/segment.py | 51 | 80% | variable | unused variable 'request_context' (100% confidence, 1 line) |
| reference/templates/servers/definitions/whatsapp.py | 80 | 80% | variable | unused variable 'media_url' (100% confidence, 1 line) |
| server_execution/variable_resolution.py | 121 | 80% | unknown | unreachable code after 'try' (100% confidence, 1 line) |
| step_impl/page_request_steps.py | 94 | 80% | variable | unused variable 'arg1' (100% confidence, 1 line) |
| step_impl/page_request_steps.py | 124 | 80% | variable | unused variable 'arg1' (100% confidence, 1 line) |
| tests/ai_use_cases/test_00_diagnostics.py | 15 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_00_diagnostics.py | 206 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_alias_editor.py | 14 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_cid_editor.py | 14 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_import_form.py | 14 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_secret_form.py | 14 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_server_definition_editor.py | 16 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_server_definition_editor.py | 73 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_server_test_card.py | 14 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_upload_form.py | 13 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/ai_use_cases/test_variable_form.py | 14 | 80% | variable | unused variable 'requires_openrouter_api_key' (100% confidence, 1 line) |
| tests/integration/test_gateway_server.py | 413 | 80% | variable | unused variable 'gateways_variable_with_transforms' (100% confidence, 1 line) |
| tests/integration/test_gateway_table_links.py | 221 | 80% | variable | unused variable 'mock_cid_record' (100% confidence, 1 line) |
| tests/integration/test_gateway_table_links.py | 271 | 80% | variable | unused variable 'service_mock_cid_records' (100% confidence, 1 line) |
| tests/integration/test_gateway_table_links.py | 312 | 80% | variable | unused variable 'service_mock_cid_records' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 101 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 124 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 145 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 173 | 80% | variable | unused variable 'local_jsonplaceholder_alias' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 187 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 188 | 80% | variable | unused variable 'local_jsonplaceholder_alias' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 208 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 225 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 242 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_gateway_test_server.py | 262 | 80% | variable | unused variable 'gateways_variable_with_jsonplaceholder' (100% confidence, 1 line) |
| tests/integration/test_json_api_gateway.py | 183 | 80% | variable | unused variable 'json_api_gateway_config' (100% confidence, 1 line) |
| tests/integration/test_json_api_gateway.py | 183 | 80% | variable | unused variable 'json_api_gateway_server' (100% confidence, 1 line) |
| tests/integration/test_json_api_gateway.py | 184 | 80% | variable | unused variable 'mock_jsonplaceholder_server' (100% confidence, 1 line) |
| tests/integration/test_json_api_gateway.py | 200 | 80% | variable | unused variable 'json_api_gateway_config' (100% confidence, 1 line) |
| tests/integration/test_json_api_gateway.py | 200 | 80% | variable | unused variable 'json_api_gateway_server' (100% confidence, 1 line) |
| tests/test_ai_editor.py | 33 | 80% | variable | unused variable 'silent' (100% confidence, 1 line) |
| tests/test_crud_factory.py | 256 | 80% | variable | unused variable 'mock_wants' (100% confidence, 1 line) |
| tests/test_crud_factory.py | 296 | 80% | variable | unused variable 'mock_extract' (100% confidence, 1 line) |
| tests/test_gateway_server.py | 152 | 80% | variable | unused variable 'cache' (100% confidence, 1 line) |
| tests/test_gateway_server.py | 183 | 80% | variable | unused variable 'cache' (100% confidence, 1 line) |
| tests/test_markdown.py | 99 | 80% | variable | unused variable 'patched_server_execution' (100% confidence, 1 line) |
| tests/test_meta_route.py | 437 | 80% | variable | unused variable 'return_rule' (100% confidence, 1 line) |
| tests/test_server_execution.py | 763 | 80% | variable | unused variable 'capture_output' (100% confidence, 1 line) |
| tests/test_server_execution_output_encoding.py | 36 | 80% | variable | unused variable 'kw' (100% confidence, 1 line) |
| tests/test_shell.py | 60 | 80% | variable | unused variable 'patched_server_execution' (100% confidence, 1 line) |
| tests/test_urleditor.py | 182 | 80% | variable | unused variable 'tz' (100% confidence, 1 line) |
