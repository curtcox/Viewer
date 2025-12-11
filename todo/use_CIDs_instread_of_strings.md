# Use CIDs instead of raw strings

This checklist tracks files where values that are semantically CIDs are currently represented and passed around as plain strings.

The goal of future work would be to tighten typing around these values (e.g., via the `CID` class or a lightweight wrapper / alias) and to reduce the surface area where arbitrary strings can appear in places that must be valid CIDs.

## Checklist of files

- [ ] `models.py` *(DB boundary)*
  - `ServerInvocation.result_cid`, `servers_cid`, `variables_cid`, `secrets_cid` are `db.String` columns that always represent CIDs.

- [x] `db_access/invocations.py` *(DB boundary)*
  - `create_server_invocation` and `get_server_invocations_by_result_cids` now accept validated `CID` objects in addition to strings, normalizing values before persistence and queries.

- [x] `db_access/cids.py` *(DB boundary)*
  - `create_cid_record` already accepts `Union[str, ValidatedCID]` and normalizes / validates CIDs before persisting.
  - `update_cid_references` now accepts both string and `ValidatedCID` inputs, normalizing them before updating text references.

- [ ] `db_access/aliases.py` *(DB boundary)*
  - `_create_new_alias(alias_name: str, cid: str)` and `_update_existing_aliases(..., old_cid: str, new_cid: str)` pass CIDs as strings.
  - `update_alias_cid_reference(old_cid: str, new_cid: str, ...)` also operates on CIDs as `str`.

- [x] `db_access/exports.py` *(DB boundary)*
  - `record_export` now accepts validated `CID` objects as well as strings, persisting the normalized CID value.

- [ ] `db_access/_exports.py` *(DB boundary)*
  - Re-exports helpers like `create_server_invocation`, `get_server_invocations_by_result_cids`, etc., which all use CID-valued strings.

- [ ] `content_serving.py` *(HTTP path / response boundary)*
  - `PathInfo.normalized_cid: str` and `PathInfo.target_cid: str` fields are CID-valued strings.
  - `_serve_qr_code(target_cid: str) -> bytes` takes a CID as a string.

- [ ] `server_execution/invocation_tracking.py` *(JSON payload / DB boundary)*
  - `create_server_invocation_record(server_name: str, result_cid: str)` records `result_cid` and related CIDs (`servers_cid`, `variables_cid`, `secrets_cid`, request/response CIDs) as strings.

- [ ] `server_execution/response_handling.py` *(HTTP response / DB boundary)*
  - `_handle_successful_execution(...)` creates `cid_value` as a string, stores it, and passes it through invocation tracking.

- [ ] `cid_core.py` *(core CID API boundary)*
  - Core helpers such as `parse_cid_components(cid: str)`, `generate_cid(file_data: bytes) -> str`, `is_literal_cid(cid: str)`, `extract_literal_content(cid: str)` all represent CIDs as raw strings at the API boundary.

- [ ] `cid_presenter.py` *(template / HTML boundary)*
  - Presenter helpers like `format_cid(value: Optional[str])`, `extract_cid_from_path(value: Optional[str])`, `format_cid_short(value: Optional[str], ...)`, and `render_cid_link(value: Optional[str])` operate on CID-like strings.

- [ ] `cid_utils.py` *(HTTP path parsing boundary)*
  - Utility functions for detecting / splitting CID paths (e.g., `split_cid_path`, `is_strict_cid_candidate`) work entirely in terms of CID-valued strings.

- [ ] `boot_cid_importer.py` *(CLI / JSON / DB boundary)*
  - Functions `load_and_validate_boot_cid(boot_cid: str)`, `verify_boot_cid_dependencies(boot_cid: str)`, and `import_boot_cid(..., boot_cid: str)` treat the boot CID as a string.

- [ ] `generate_boot_image.py` *(CLI / JSON boundary)*
  - Methods such as `generate_boot_json(self, templates_cid: str, ..., uis_cid: Optional[str] = None) -> str` use CID-valued strings for templates and UI definitions.

- [ ] `boot_image_diff.py` *(JSON / DB boundary)*
  - `DefinitionDiff.boot_cid: str | None` and `DefinitionDiff.db_cid: str | None` fields are CIDs.
  - `_definitions_match(..., boot_cid: str | None, db_cid: str | None)` compares CIDs as strings.

- [ ] `routes/history.py` *(HTTP path / DB / template boundary)*
  - `_extract_result_cid(path: str) -> str | None` parses CIDs out of request paths.
  - Uses `get_server_invocations_by_result_cids(result_cids)` and manipulates `result_cids` / `invocation.result_cid` as CID-valued strings.

- [ ] `routes/uploads.py` *(HTTP upload / DB / template boundary)*
  - `_shorten_cid(cid: str | None, ...)` is explicitly working with CID-valued strings.
  - Later code builds `invocation_by_cid` dicts keyed by attributes like `result_cid`, `invocation_cid`, `request_details_cid`, `servers_cid` (all string CIDs).

- [ ] `routes/servers.py` *(HTTP / template boundary)*
  - Uses `invocation.result_cid` to build links and labels (`cid_path(..., 'txt')`, `format_cid_short(...)`) while keeping CIDs as strings.

- [ ] `routes/meta/meta_cid.py` *(HTTP / template / DB boundary)*
  - Maintains a mapping of CID-related fields (`"result_cid"`, `"invocation_cid"`, `"request_details_cid"`, `"servers_cid"`, etc.) to labels; all these model attributes are CID-valued strings.

- [ ] `routes/import_export/import_sources.py` *(HTTP / JSON boundary)*
  - `ParsedImportPayload.expected_cid: str` indicates expected content identifier but is represented as a plain string.

- [ ] `routes/import_export/import_entities.py` *(HTTP / JSON / DB boundary)*
  - `load_server_definition_from_cid(name: str, definition_cid: str, ...)` passes `definition_cid` as a string.

- [ ] `scripts/checks/validate_cids.py` *(filesystem / CLI boundary)*
  - `ValidationFailure.computed_cid: str` is a CID-valued string used when validating on-disk contents.

- [ ] `scripts/ci/validate_cids_with_report.sh` *(CLI / CI boundary)*
  - Shell wrapper that invokes CID validation based on string-valued CIDs.

- [ ] `main.py` *(CLI / HTTP startup boundary)*
  - `handle_boot_cid_import(boot_cid: str)` wires boot CIDs through as strings.

- [ ] `routes/cid_editor.py` *(HTTP / template boundary)*
  - Route handlers operate on CID path segments and values as strings for editing.

- [ ] `cid_storage.py` *(filesystem / DB boundary)*
  - Storage helpers use CID values as strings when mapping to paths and database records.

- [ ] `cid_directory_loader.py` *(filesystem boundary)*
  - Loads and maps CIDs from the on-disk CID directory as strings.

- [ ] `cid_editor_helper.py` *(template / HTTP boundary)*
  - Helpers for the CID editor operate on CID-valued strings (e.g., normalizing, validating, and displaying CIDs).

- [ ] `server_execution/code_execution.py` *(HTTP execution / CID path boundary)*
  - `_load_server_literal(...)` returns `(definition, language, normalized_cid)` where `normalized_cid` is a CID-valued string.

- [ ] `routes/import_export/cid_utils.py` *(HTTP import/export path boundary)*
  - Import/export utilities that work with CID path strings.

- [ ] `reference_templates/*.cid` and `reference_templates/uploads/*embedded_cid*` *(static content boundary)*
  - Static template files that embed or reference CIDs as text (string form).

## Notes for future refactoring

- **Prioritize data model and DB boundaries first**
  - Consider introducing a CID-typed wrapper or alias for `ServerInvocation`-related fields and DB access helpers to reduce accidental misuse.

- **Wrap external/stringy boundaries**
  - HTTP path parsing, template rendering, and JSON import/export will always see CIDs as strings at the edge. Focus on converting to a stronger CID type as early as practical inside those flows.

- **Leverage existing `CID` class and helpers**
  - The `CID` class (`cid.py`) and helpers like `ensure_cid` / `to_cid_string` and the `cid_core` functions can underpin a more strongly typed API while still interoperating with legacy string-based code during migration.
