# Use CIDs instead of raw strings
 
This checklist tracks files where values that are semantically CIDs are currently represented and passed around as plain strings.
 
Status: In progress. Most runtime boundaries now accept/normalize `CID`/`ValidatedCID` values, but some DB model fields and static template content still represent CIDs as plain strings.
 
The goal of future work would be to tighten typing around these values (e.g., via the `CID` class or a lightweight wrapper / alias) and to reduce the surface area where arbitrary strings can appear in places that must be valid CIDs.
 
## Checklist of files

- [ ] `models.py` *(DB boundary)*
  - `ServerInvocation.result_cid`, `servers_cid`, `variables_cid`, `secrets_cid` are `db.String` columns that always represent CIDs.

- [x] `db_access/invocations.py` *(DB boundary)*
  - `create_server_invocation` and `get_server_invocations_by_result_cids` now accept validated `CID` objects in addition to strings, normalizing values before persistence and queries.

- [x] `db_access/cids.py` *(DB boundary)*
  - `create_cid_record` already accepts `Union[str, ValidatedCID]` and normalizes / validates CIDs before persisting.
  - `update_cid_references` now accepts both string and `ValidatedCID` inputs, normalizing them before updating text references.

- [x] `db_access/aliases.py` *(DB boundary)*
  - `_create_new_alias` and `_update_existing_aliases` still operate on normalized CID strings internally.
  - `update_alias_cid_reference` now accepts both string and `ValidatedCID` inputs, normalizing them before updating alias definitions.

- [x] `db_access/exports.py` *(DB boundary)*
  - `record_export` now accepts validated `CID` objects as well as strings, persisting the normalized CID value.

- [x] `db_access/_exports.py` *(DB boundary)*
  - Re-exports CID helpers (`create_server_invocation`, `update_cid_references`, `update_alias_cid_reference`, etc.) which now accept `ValidatedCID` values as well as strings via their underlying modules.

- [x] `content_serving.py` *(HTTP path / response boundary)*
  - `PathInfo.normalized_cid` and `PathInfo.target_cid` remain CID-valued strings derived from request paths and stored CID records.
  - `_serve_qr_code(target_cid: str) -> bytes` continues to accept CID-valued strings and delegates to `cid_path` for link generation.

- [x] `server_execution/invocation_tracking.py` *(JSON payload / DB boundary)*
  - `create_server_invocation_record` now accepts `result_cid` as either a string or `ValidatedCID`, normalizing to strings only at the JSON payload boundary.

- [x] `server_execution/response_handling.py` *(HTTP response / DB boundary)*
  - `_handle_successful_execution(...)` creates `cid_value` as a string, stores it, and passes it through invocation tracking, avoiding strict CID validation to support mocked CIDs in tests.

- [x] `cid_core.py` *(core CID API boundary)*
  - Core helpers such as `generate_cid`, `parse_cid_components`, `is_literal_cid`, and `extract_literal_content` intentionally expose CIDs as normalized strings, forming the string-based foundation used by higher-level CID wrappers.

- [x] `cid_presenter.py` *(template / HTML boundary)*
  - Presenter helpers such as `format_cid`, `format_cid_short`, `cid_path`, `cid_full_url`, and `render_cid_link` now accept both plain strings and `CID` objects, normalizing to strings for display and link generation while keeping string-based outputs for templates.

- [x] `cid_utils.py` *(HTTP path parsing boundary / compatibility shim)*
  - Deprecated shim that re-exports CID/path helpers from `cid_core`, `cid_storage`, `content_rendering`, and `mime_utils`, all of which currently expose CID values as strings at their public boundaries.

- [x] `boot_cid_importer.py` *(CLI / JSON / DB boundary)*
  - Boot import functions treat boot CIDs as strings, normalizing them with `format_cid` / `cid_path` and validating with `is_normalized_cid`, while using string CID paths for DB lookups and references.

- [x] `generate_boot_image.py` *(CLI / JSON boundary)*
  - Boot image generation methods work with CID-valued strings (e.g., `templates_cid`, `uis_cid`, `boot_cid`), generating CIDs from content bytes and writing them to files/json while keeping the public API string-based.

- [x] `boot_image_diff.py` *(JSON / DB boundary)*
  - Boot image diff metadata tracks `boot_cid` and `db_cid` as strings and `_definitions_match` compares definitions using these string CIDs when both are present, falling back to raw definition text when not.

- [x] `routes/history.py` *(HTTP path / DB / template boundary)*
  - History routes parse CID-like segments from paths and use string CIDs to look up invocations and build template link helpers, delegating CID normalization/formatting to `cid_presenter` and `cid_utils`.

- [x] `routes/uploads.py` *(HTTP upload / DB / template boundary)*
  - Upload routes generate and store CIDs from bytes, use string CIDs for paths, variable assignments, and creation-source links, and rely on `cid_presenter` / helpers for normalization and display.

- [x] `routes/servers.py` *(HTTP / template boundary)*
  - Server routes work with string CIDs for invocation history, definition snapshots, and server-definitions CIDs, using `cid_path`/`format_cid`/`format_cid_short` to generate links and labels.

- [x] `routes/meta/meta_cid.py` *(HTTP / template / DB boundary)*
  - Meta CID routes work with string CID values and CID-related model fields, using `format_cid`/`cid_path` to normalize and link them in metadata views.

- [x] `routes/import_export/import_sources.py` *(HTTP / JSON boundary)*
  - Import source helpers treat `expected_cid` and computed CIDs as strings, validating local files by comparing string CIDs derived from their content.

- [x] `routes/import_export/import_entities.py` *(HTTP / JSON / DB boundary)*
  - Import entity helpers treat `definition_cid` fields as strings, normalizing them and resolving content via CID maps, then storing resulting definition CIDs as string values in the database.

- [x] `scripts/checks/validate_cids.py` *(filesystem / CLI boundary)*
  - Validation logic loads CID files from disk, recomputes CID strings with `generate_cid`, and reports mismatches using string CIDs in JSON/text reports.

- [x] `scripts/ci/validate_cids_with_report.sh` *(CLI / CI boundary)*
  - CI shell wrapper runs the Python CID validator script and passes CID directories as paths, operating entirely on string CIDs and filenames.

- [x] `main.py` *(CLI / HTTP startup boundary)*
  - CLI/startup logic treats boot CIDs and positional CID arguments as strings, passing them into `boot_cid_importer` and CLI helpers for validation/import while keeping the public interface string-based.

- [x] `routes/cid_editor.py` *(HTTP / template boundary)*
  - Route handlers intentionally operate on CID path segments and values as strings for request/response JSON and HTML, delegating CID validation and storage to helper modules.

- [x] `cid_storage.py` *(filesystem / DB boundary)*
  - `ensure_cid_exists` already accepts `Union[str, CID]` and normalizes via `to_cid_string`, while higher-level helpers generate and return CID strings for storage/DB paths.

- [x] `cid_directory_loader.py` *(filesystem boundary)*
  - Validates CID filenames and generated CIDs as normalized strings and uses them for filesystem checks and DB lookups, keeping this layer purely string-based.

- [x] `cid_editor_helper.py` *(template / HTTP boundary)*
  - CID editor helpers operate on user-entered text and CID-valued strings at the HTTP/UI boundary, leaving CID generation and validation to `cid_core` / `cid_storage` while returning plain-string CIDs for the frontend.

- [x] `server_execution/code_execution.py` *(HTTP execution / CID path boundary)*
  - `_load_server_literal(...)` returns `(definition, language, normalized_cid)` where `normalized_cid` remains a CID-valued string derived from CID paths and records.

- [x] `routes/import_export/cid_utils.py` *(HTTP import/export path boundary)*
  - Import/export helpers normalize CID values as strings, generate CIDs from bytes, and use string CIDs for paths, maps, and payloads while delegating storage to lower-level helpers.

- [ ] `reference/templates/*.cid` and `reference/templates/uploads/*embedded_cid*` *(static content boundary)*
  - Static template files that embed or reference CIDs as text (string form).

## Notes for future refactoring

- **Prioritize data model and DB boundaries first**
  - Consider introducing a CID-typed wrapper or alias for `ServerInvocation`-related fields and DB access helpers to reduce accidental misuse.

- **Wrap external/stringy boundaries**
  - HTTP path parsing, template rendering, and JSON import/export will always see CIDs as strings at the edge. Focus on converting to a stronger CID type as early as practical inside those flows.

- **Leverage existing `CID` class and helpers**
  - The `CID` class (`cid.py`) and helpers like `ensure_cid` / `to_cid_string` and the `cid_core` functions can underpin a more strongly typed API while still interoperating with legacy string-based code during migration.
