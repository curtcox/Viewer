# Import/Export JSON Format Documentation

## Overview

The Viewer application uses a JSON-based format for exporting and importing global configuration data across different instances. This format supports **Content-Addressed Storage (CAS)** via CID (Content Identifier) references, allowing efficient storage and transfer of large or duplicate content.

The import/export system enables operators to:
- **Export** aliases, servers, variables, secrets, change history, and application source files
- **Import** data from other Viewer instances or backup files
- **Transport** complete configurations between development, staging, and production environments
- **Backup** and restore configuration data with integrity verification

## Version History

- **Version 6** (Current): Simplified CID value format using plain UTF-8 strings
- Previous versions used dictionary format with explicit encoding fields

## Top-Level Structure

```json
{
  "version": 6,
  "runtime": "bafybeicid...",
  "project_files": "bafybeicid...",
  "aliases": "bafybeicid...",
  "servers": "bafybeicid...",
  "variables": "bafybeicid...",
  "secrets": "bafybeicid...",
  "change_history": "bafybeicid...",
  "app_source": "bafybeicid..."
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | **Yes** | Format version number (currently `6`) |
| `runtime` | string (CID) | **Yes** | CID reference to runtime environment information |
| `project_files` | string (CID) | **Yes** | CID reference to project metadata files |
| `aliases` | string (CID) | No | CID reference to aliases list (included if aliases exported) |
| `servers` | string (CID) | No | CID reference to servers list (included if servers exported) |
| `variables` | string (CID) | No | CID reference to variables list (included if variables exported) |
| `secrets` | string (CID) | No | CID reference to encrypted secrets section (included if secrets exported) |
| `change_history` | string (CID) | No | CID reference to entity change history (included if history exported) |
| `app_source` | string (CID) | No | CID reference to application source files (included if source exported) |
| `cid_values` | object | No | Map of CID keys to their content (included if CID map enabled) |

**Source**: [routes/import_export/export_engine.py:63-171](../routes/import_export/export_engine.py#L63-L171)

## CID (Content Identifier) References

Most sections in the export format are stored as **CID references** rather than inline data. This approach:

1. **Deduplicates content** - Identical content shares the same CID
2. **Enables content verification** - CID is a cryptographic hash of the content
3. **Supports external storage** - Content can be stored separately and referenced
4. **Allows optional embedding** - Content can be embedded in `cid_values` or stored externally

### CID Format

CIDs use the IPFS/Multihash format and typically look like:
```
bafybeicid123abc456def789...
```

**Normalization**: [routes/import_export/cid_utils.py:15-24](../routes/import_export/cid_utils.py#L15-L24)

### CID Values Section

The optional `cid_values` section maps CID references to their actual content:

```json
{
  "cid_values": {
    "bafybeicid1": "literal /docs -> /usr/share/doc",
    "bafybeicid2": "def main():\n    return 'Hello, World!'",
    "bafybeicid3": "{\"pyproject.toml content here\"}"
  }
}
```

**New Format** (Version 6+): CID values are **plain UTF-8 strings**

**Legacy Format** (backward compatible):
```json
{
  "cid_values": {
    "bafybeicid1": {
      "encoding": "utf-8",
      "value": "content here"
    },
    "bafybeicid2": {
      "encoding": "base64",
      "value": "YmFzZTY0IGVuY29kZWQgY29udGVudA=="
    }
  }
}
```

**Serialization**: [routes/import_export/cid_utils.py:44-51](../routes/import_export/cid_utils.py#L44-L51)
**Deserialization**: [routes/import_export/cid_utils.py:100-125](../routes/import_export/cid_utils.py#L100-L125)

### Content Resolution

When importing, CID content is resolved in this order:

1. **Embedded** - Check `cid_values` map in the import payload
2. **Database** - Look up CID in local database storage
3. **Error** - Report missing content if not found

**Resolution Logic**: [routes/import_export/cid_utils.py:156-174](../routes/import_export/cid_utils.py#L156-L174)

## Section Formats

### Runtime Section

```json
{
  "python": {
    "version": "3.11.7",
    "implementation": "CPython",
    "executable": "/usr/bin/python3"
  },
  "dependencies": {
    "flask": {
      "version": "3.0.0"
    },
    "werkzeug": {
      "version": "3.0.1"
    }
  }
}
```

Captures the runtime environment for reproducibility and compatibility checking.

**Builder**: [routes/import_export/dependency_analyzer.py](../routes/import_export/dependency_analyzer.py)

### Project Files Section

```json
{
  "pyproject.toml": {
    "cid": "bafybeicid..."
  },
  "requirements.txt": {
    "cid": "bafybeicid..."
  }
}
```

References to key project configuration files.

**Collector**: [routes/import_export/export_sections.py:16-33](../routes/import_export/export_sections.py#L16-L33)

### Aliases Section

```json
[
  {
    "name": "alias-name",
    "definition_cid": "bafybeicid...",
    "enabled": true
  },
  {
    "name": "another-alias",
    "definition_cid": "bafybeicid...",
    "enabled": false
  }
]
```

**Fields**:
- `name` (string, required): Unique alias name
- `definition_cid` (string, required): CID reference to alias definition text
- `enabled` (boolean, optional, default: `true`): Whether the alias is enabled

**Alias Definition Format**: The content referenced by `definition_cid` follows the alias definition syntax:
```
literal /home -> /home/user
```

**Exporter**: [routes/import_export/export_sections.py:35-77](../routes/import_export/export_sections.py#L35-L77)
**Importer**: [routes/import_export/import_entities.py](../routes/import_export/import_entities.py)

**Tests**: [tests/test_import_export.py:1124-1201](../tests/test_import_export.py#L1124-L1201)

### Servers Section

```json
[
  {
    "name": "server-name",
    "definition_cid": "bafybeicid...",
    "enabled": true
  },
  {
    "name": "disabled-server",
    "definition_cid": "bafybeicid...",
    "enabled": false
  }
]
```

**Fields**:
- `name` (string, required): Unique server name
- `definition_cid` (string, required): CID reference to Python server code
- `enabled` (boolean, optional, default: `true`): Whether the server is enabled

**Server Definition Format**: The content referenced by `definition_cid` is Python code:
```python
def main():
    return {"output": "Hello, World!", "content_type": "text/plain"}
```

**Exporter**: [routes/import_export/export_sections.py:79-121](../routes/import_export/export_sections.py#L79-L121)
**Importer**: [routes/import_export/import_entities.py](../routes/import_export/import_entities.py)

**Tests**: [tests/integration/test_import_export_flow.py:93-182](../tests/integration/test_import_export_flow.py#L93-L182)

### Variables Section

```json
[
  {
    "name": "variable-name",
    "definition": "variable value here",
    "enabled": true
  },
  {
    "name": "api-endpoint",
    "definition": "https://api.example.com/v1",
    "enabled": true
  }
]
```

**Fields**:
- `name` (string, required): Unique variable name
- `definition` (string, required): Variable value (stored inline, not as CID)
- `enabled` (boolean, optional, default: `true`): Whether the variable is enabled

**Note**: Unlike aliases and servers, variable values are stored **inline** rather than as CID references.

**Exporter**: [routes/import_export/export_sections.py:123-158](../routes/import_export/export_sections.py#L123-L158)
**Importer**: [routes/import_export/import_entities.py](../routes/import_export/import_entities.py)

### Secrets Section

```json
{
  "encryption": "fernet",
  "items": [
    {
      "name": "secret-name",
      "ciphertext": "gAAAAABf...",
      "enabled": true
    },
    {
      "name": "api-key",
      "ciphertext": "gAAAAABf...",
      "enabled": false
    }
  ]
}
```

**Top-Level Fields**:
- `encryption` (string, required): Encryption scheme (currently `"fernet"`)
- `items` (array, required): List of encrypted secret entries

**Item Fields**:
- `name` (string, required): Unique secret name
- `ciphertext` (string, required): Encrypted secret value
- `enabled` (boolean, optional, default: `true`): Whether the secret is enabled

**Encryption**: Secrets are encrypted using the Fernet symmetric encryption scheme. The same encryption key (passphrase) must be used for both export and import.

**Exporter**: [routes/import_export/export_sections.py:160-204](../routes/import_export/export_sections.py#L160-L204)
**Importer**: [routes/import_export/import_entities.py](../routes/import_export/import_entities.py)

**Tests**: [tests/test_import_export.py:1098-1123](../tests/test_import_export.py#L1098-L1123)

### Change History Section

```json
{
  "aliases": {
    "alias-name": [
      {
        "timestamp": "2025-01-14T10:30:00+00:00",
        "message": "Created alias",
        "action": "save"
      },
      {
        "timestamp": "2025-01-14T11:00:00+00:00",
        "message": "Updated definition",
        "action": "save"
      }
    ]
  },
  "servers": {
    "server-name": [
      {
        "timestamp": "2025-01-14T10:45:00+00:00",
        "message": "Created server",
        "action": "save"
      }
    ]
  }
}
```

**Structure**: Dictionary mapping entity types to entity names to event arrays.

**Event Fields**:
- `timestamp` (string, required): ISO 8601 timestamp
- `message` (string, required): User-provided change message
- `action` (string, required): Action type (e.g., `"save"`, `"delete"`)

**Gatherer**: [routes/import_export/change_history.py](../routes/import_export/change_history.py)
**Importer**: [routes/import_export/change_history.py](../routes/import_export/change_history.py)

**Tests**: [tests/test_import_export.py:1428-1480](../tests/test_import_export.py#L1428-L1480)

### Application Source Section

```json
{
  "python": [
    {
      "path": "app.py",
      "cid": "bafybeicid..."
    },
    {
      "path": "routes/import_export/routes.py",
      "cid": "bafybeicid..."
    }
  ],
  "templates": [
    {
      "path": "templates/export.html",
      "cid": "bafybeicid..."
    }
  ],
  "static": [
    {
      "path": "static/css/styles.css",
      "cid": "bafybeicid..."
    }
  ],
  "other": [
    {
      "path": "README.md",
      "cid": "bafybeicid..."
    }
  ]
}
```

**Categories**:
- `python`: Python source files (`.py`)
- `templates`: HTML templates
- `static`: Static assets (CSS, JS, images)
- `other`: Other source files

**Entry Fields**:
- `path` (string, required): Relative file path from application root
- `cid` (string, required): CID reference to file content

**Purpose**: Used for verification during import to detect source code drift between instances.

**Collector**: [routes/import_export/export_sections.py:206-233](../routes/import_export/export_sections.py#L206-L233)
**Verifier**: [routes/import_export/import_sources.py:162-232](../routes/import_export/import_sources.py#L162-L232)

**Tests**: [tests/test_import_export.py:1021-1070](../tests/test_import_export.py#L1021-L1070)

## Import Process

### Import Payload Parsing

**Input Sources**:
1. **File Upload**: JSON file uploaded via web form
2. **Text Input**: JSON pasted directly into textarea
3. **URL**: JSON fetched from remote URL

**Payload Loader**: [routes/import_export/import_sources.py:53-93](../routes/import_export/import_sources.py#L53-L93)

### Import Validation

1. **JSON Syntax**: Payload must be valid JSON
2. **Structure**: Root must be a JSON object (not array)
3. **CID Integrity**: CID content must match its hash
4. **Encryption Key**: Secret decryption key must be correct

**Parser**: [routes/import_export/import_sources.py:28-43](../routes/import_export/import_sources.py#L28-L43)

### Import Workflow

1. **Parse Payload**: Load and validate JSON structure
2. **Process CID Map**: Parse and optionally store `cid_values` in database
3. **Import Sections**: Import selected entity types (aliases, servers, etc.)
4. **Verify Source**: Optionally verify application source matches export
5. **Generate Snapshot**: Create post-import snapshot export
6. **Report Results**: Display summary of imported items and any errors

**Orchestrator**: [routes/import_export/import_engine.py:272-285](../routes/import_export/import_engine.py#L272-L285)

### REST API Import

The import endpoint also supports JSON REST API requests:

**Request**:
```http
POST /import
Content-Type: application/json

{
  "aliases": [...],
  "servers": [...],
  "variables": [...],
  "cid_values": {...}
}
```

**Response**:
```json
{
  "ok": true,
  "summaries": ["2 aliases", "1 server"],
  "imported_names": {
    "aliases": ["alias-1", "alias-2"],
    "servers": ["server-1"]
  },
  "snapshot": {
    "cid": "bafybeicid..."
  }
}
```

**Handler**: [routes/import_export/routes.py:81-128](../routes/import_export/routes.py#L81-L128)

## Export Process

### Export Configuration

**Form Options**:
- **Snapshot Mode**: Quick export with sensible defaults (enabled entities only)
- **Custom Mode**: Fine-grained control over what to include
- **Entity Selection**: Choose specific entities to export
- **Disabled Entities**: Include/exclude disabled items
- **Template Entities**: Include/exclude template items
- **Secrets**: Require encryption key for secret export
- **Change History**: Include entity modification history
- **Application Source**: Include source files for verification
- **CID Map**: Embed content in `cid_values` vs. external storage
- **Unreferenced CIDs**: Include uploaded but unreferenced content

**Form**: [forms.py](../forms.py)

### Export Workflow

1. **Collect Sections**: Gather data for selected entity types
2. **Generate CIDs**: Create CID references for content
3. **Build CID Map**: Optionally collect content for embedding
4. **Assemble Payload**: Construct top-level JSON structure
5. **Store Export**: Save complete export to database
6. **Generate Download**: Provide download link for JSON file

**Builder**: [routes/import_export/export_engine.py:63-171](../routes/import_export/export_engine.py#L63-L171)

### Export Size Estimation

The `/export/size` endpoint provides size estimates without storing:

**Request**:
```http
POST /export/size
Content-Type: application/x-www-form-urlencoded

include_aliases=y&include_servers=y
```

**Response**:
```json
{
  "ok": true,
  "size_bytes": 4567,
  "formatted_size": "4.5 KB"
}
```

**Handler**: [routes/import_export/routes.py:43-63](../routes/import_export/routes.py#L43-L63)

## Snapshot Exports

After a successful import, the system automatically generates a **snapshot export** containing:

- All enabled aliases
- All enabled servers
- All enabled variables
- CID map with referenced content
- Excludes: secrets, change history, application source

**Purpose**: Creates a backup of the current state immediately after import for rollback capability.

**Generator**: [routes/import_export/import_engine.py:203-227](../routes/import_export/import_engine.py#L203-L227)

**Tests**: [tests/test_import_export.py:1847-1992](../tests/test_import_export.py#L1847-L1992)

## Common Use Cases

### Backup and Restore

**Backup**:
1. Navigate to `/export`
2. Enable snapshot mode or select desired entities
3. Download JSON export file
4. Store securely

**Restore**:
1. Navigate to `/import`
2. Upload or paste JSON export
3. Select sections to restore
4. Import and verify snapshot

### Instance Migration

**Source Instance**:
```bash
# Export all data including source verification
POST /export
  include_aliases=y
  include_servers=y
  include_variables=y
  include_secrets=y
  include_source=y
  include_cid_map=y
  secret_key=<passphrase>
```

**Destination Instance**:
```bash
# Import and verify source matches
POST /import
  import_source=file
  import_file=<export.json>
  include_aliases=y
  include_servers=y
  include_variables=y
  include_secrets=y
  include_source=y
  process_cid_map=y
  secret_key=<passphrase>
```

### Configuration Sharing

Share specific configurations without secrets:

```json
{
  "version": 6,
  "runtime": "bafybeicid...",
  "project_files": "bafybeicid...",
  "aliases": "bafybeicid...",
  "servers": "bafybeicid...",
  "cid_values": {
    "bafybeicid...": "[alias definitions]",
    "bafybeicid...": "[server code]"
  }
}
```

## Error Handling

### Common Import Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| "Import data was empty" | Empty payload | Provide valid JSON content |
| "Failed to parse JSON" | Invalid JSON syntax | Check for syntax errors (commas, quotes, brackets) |
| "Import file must contain a JSON object" | Root is array `[]` | Use object `{}` at root |
| "CID content did not match its hash" | Corrupted or tampered content | Re-export from source or fix content |
| "Invalid decryption key for secrets" | Wrong passphrase | Use same key as export |
| "Section referenced CID but content not provided" | Missing CID in map and database | Include `cid_values` or ensure CID stored |
| "Source file differs from the export" | Code has changed | Update source to match or accept drift |

### Common Export Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| "Secret key is required when exporting secrets" | Missing encryption key | Provide passphrase in form |
| Empty export sections | No entities selected or no enabled entities | Enable entities or select disabled entities |

## Best Practices

### For Exports

1. **Use Snapshot Mode** for routine backups (faster, smaller files)
2. **Include CID Map** for self-contained exports
3. **Encrypt Secrets** with strong passphrases
4. **Include Change History** for audit trails
5. **Verify Export Size** before generating large exports
6. **Store Exports Securely** - exports may contain sensitive data

### For Imports

1. **Verify Source** - only import from trusted sources
2. **Check CID Integrity** - ensure content matches hashes
3. **Use Same Encryption Key** - secrets must use same passphrase
4. **Review Snapshot** - check post-import snapshot for correctness
5. **Test in Staging** - test imports in non-production environments first
6. **Monitor Import Results** - review warnings and errors carefully

### For CID Management

1. **Enable CID Map** for portable exports
2. **Store Content** when CIDs referenced by multiple entities
3. **Clean Unreferenced CIDs** periodically to save space
4. **Use Content Addressing** to deduplicate identical content

## Testing

### Unit Tests

**Core Export/Import**: [tests/test_import_export.py](../tests/test_import_export.py)
- Export format validation (lines 292-389)
- Import validation (lines 912-1097)
- CID handling (lines 1071-1097)
- Enablement preservation (lines 390-507)
- UTF-8 encoding (lines 1481-1740)

**Import Helpers**: [tests/test_import_export_helpers.py](../tests/test_import_export_helpers.py)

**Validation**: [tests/test_validate_import_export_integration.py](../tests/test_validate_import_export_integration.py)

### Integration Tests

**Full Transfer Flow**: [tests/integration/test_import_export_flow.py](../tests/integration/test_import_export_flow.py)
- Complete export/import cycle (lines 93-182)
- Cross-instance transfer
- CID resolution
- Server execution after import

**Entity Pages**: Test coverage for each entity type:
- [tests/integration/test_alias_pages.py](../tests/integration/test_alias_pages.py)
- [tests/integration/test_server_pages.py](../tests/integration/test_server_pages.py)
- [tests/integration/test_variable_pages.py](../tests/integration/test_variable_pages.py)
- [tests/integration/test_secret_pages.py](../tests/integration/test_secret_pages.py)

## Reference Implementation

### Minimal Export Example

```python
from routes.import_export.export_engine import build_export_payload
from forms import ExportForm

form = ExportForm()
form.snapshot.data = True
form.include_aliases.data = True
form.include_servers.data = True
form.include_cid_map.data = True

result = build_export_payload(form, store_content=True)
json_payload = result['json_payload']
cid_value = result['cid_value']
download_path = result['download_path']
```

### Minimal Import Example

```python
from routes.import_export.import_engine import process_import_submission
from routes.import_export.import_sources import parse_import_payload
from forms import ImportForm

form = ImportForm()
form.include_aliases.data = True
form.include_servers.data = True
form.process_cid_map.data = True

parsed_payload, error = parse_import_payload(json_text)
if not error:
    process_import_submission(form, 'Import note', render_callback, parsed_payload)
```

## See Also

- [JSON Template Format](json-template-format.md) - Template system documentation
- [Export Routes](../routes/import_export/routes.py) - HTTP endpoint handlers
- [Export Engine](../routes/import_export/export_engine.py) - Export generation
- [Import Engine](../routes/import_export/import_engine.py) - Import processing
- [CID Utilities](../routes/import_export/cid_utils.py) - Content addressing
- [Test Suite](../tests/test_import_export.py) - Comprehensive tests
