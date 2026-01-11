# Radon summary

* Analysed 8036 code blocks across 734 files.
* Worst cyclomatic complexity rank: E (fails if worse than E).
* Lowest maintainability index: 0.00 (C).

## Cyclomatic complexity distribution

| Rank | Blocks |
| --- | ---: |
| A | 7307 |
| B | 461 |
| C | 202 |
| D | 53 |
| E | 13 |
| F | 0 |

## Maintainability index distribution

| Rank | Files |
| --- | ---: |
| A | 747 |
| B | 11 |
| C | 8 |
| D | 0 |
| E | 0 |
| F | 0 |

## Most complex code blocks

| Rank | Complexity | Location | Block |
| --- | ---: | --- | --- |
| E | 31.00 | reference/templates/servers/definitions/insightly.py:61 | main |
| E | 31.00 | reference/templates/servers/definitions/segment.py:38 | main |
| E | 31.00 | reference/templates/servers/definitions/wix.py:47 | main |
| E | 34.00 | reference/templates/servers/definitions/microsoft_outlook.py:63 | main |
| E | 35.00 | reference/templates/servers/definitions/azure_blob.py:83 | main |
| E | 36.00 | reference/templates/servers/definitions/google_calendar.py:64 | main |
| E | 37.00 | app.py:125 | create_app |
| E | 38.00 | reference/templates/servers/definitions/microsoft_excel.py:64 | main |
| E | 38.00 | reference/templates/servers/definitions/cloudconvert.py:22 | main |
| E | 38.00 | reference/templates/servers/definitions/gcs.py:69 | main |
| E | 38.00 | reference/templates/servers/definitions/shopify.py:88 | main |
| E | 39.00 | reference/templates/servers/definitions/miro.py:68 | main |
| E | 39.00 | routes/import_export/github_pr.py:84 | prepare_boot_image_update |
| D | 21.00 | reference/templates/servers/definitions/mixpanel.py:39 | main |
| D | 21.00 | reference/templates/servers/definitions/postgresql.py:34 | main |
| D | 21.00 | reference/templates/servers/definitions/pymongo_pool.py:32 | main |
| D | 21.00 | routes/uploads.py:423 | edit_cid |
| D | 22.00 | scripts/generate_gauge_failure_report.py:39 | parse_gauge_log_failures |
| D | 22.00 | reference/templates/servers/definitions/whatsapp.py:71 | main |
| D | 22.00 | reference/templates/servers/definitions/gmail.py:63 | main |
| D | 22.00 | reference/templates/servers/definitions/gateway_lib/routing.py:88 | _match_with_greedy |
| D | 22.00 | routes/servers.py:408 | upload_server_test_page |
| D | 22.00 | routes/search.py:185 | _alias_results |
| D | 23.00 | reference/templates/servers/definitions/bigquery.py:36 | main |
| D | 23.00 | reference/templates/servers/definitions/ai_assist.py:414 | main |

## Lowest maintainability files

| Rank | MI | File |
| --- | ---: | --- |
| C | 0.00 | server_execution/code_execution.py |
| C | 0.00 | tests/test_routes_comprehensive.py |
| C | 0.00 | tests/test_server_execution.py |
| C | 3.55 | tests/test_import_export.py |
| C | 3.60 | step_impl/chaining_steps.py |
| C | 4.46 | scripts/build-report-site.py |
| C | 7.75 | alias_definition.py |
| C | 8.88 | formdown_renderer.py |
| B | 10.14 | tests/integration/test_content_negotiation_integration.py |
| B | 11.37 | step_impl/content_verification_steps.py |
| B | 12.27 | tests/integration/test_server_execution_auto_main.py |
| B | 15.91 | routes/route_details.py |
| B | 16.03 | tests/test_server_auto_main.py |
| B | 16.88 | tests/test_generate_boot_image.py |
| B | 16.90 | tests/integration/test_one_shot_equivalence.py |
| B | 17.98 | routes/import_export/import_entities.py |
| B | 18.30 | scripts/run_radon.py |
| B | 18.50 | step_impl/import_export_steps.py |
| B | 18.80 | response_formats.py |
| A | 19.57 | step_impl/pipeline_debug_steps.py |
| A | 20.09 | tests/test_markdown_rendering.py |
| A | 20.35 | routes/servers.py |
| A | 20.62 | tests/integration/test_server_pages.py |
| A | 20.95 | tests/test_limit_validator.py |
| A | 21.40 | step_impl/urleditor_steps.py |

## Exclusions

- .git
- .github
- docs
- env
- gauge
- gauge_stub
- node_modules
- static
- step_impl
- templates
- test
- test-gauge
- test-unit
- tests

## Ignored patterns

- **/__init__.py
