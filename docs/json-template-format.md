# JSON Template Format Documentation

## Overview

The JSON template format provides a centralized way to define reusable templates for aliases, servers, variables, secrets, and uploads. Templates are stored in a single `templates` variable and can reference content either directly in JSON or through CID (Content Identifier) references.

Templates are **read-only** entities that appear alongside user-created entities but cannot be modified or deleted through the standard entity interface. They serve as starting points or examples for creating new entities.

## Storage Location

Templates are stored in the `templates` variable in the database, which can contain:
- **Direct JSON**: The complete template structure as a JSON string
- **CID Reference**: A CID string pointing to stored JSON content (e.g., `"TESTCID123"` or `"/TESTCID123"`)

Source: [template_manager.py:33-83](../template_manager.py#L33-L83)

## JSON Schema

### Top-Level Structure

```json
{
  "aliases": { /* alias templates */ },
  "servers": { /* server templates */ },
  "variables": { /* variable templates */ },
  "secrets": { /* secret templates */ },
  "uploads": { /* upload templates */ }
}
```

**Important**: All five entity type keys (`aliases`, `servers`, `variables`, `secrets`, `uploads`) MUST be present in the JSON, even if empty.

Validation: [template_manager.py:109-116](../template_manager.py#L109-L116)

### Entity Type Schemas

#### Aliases

```json
"aliases": {
  "template-key": {
    "name": "Template Display Name",           // REQUIRED
    "description": "Optional description",     // optional
    "definition": "literal /path -> /target",  // optional - direct definition
    "definition_cid": "CID_VALUE",            // optional - CID reference
    "target_path_cid": "CID_VALUE",           // optional - legacy CID reference
    "metadata": {                             // optional - freeform metadata
      "created": "2025-01-01T00:00:00Z",
      "author": "username"
    }
  }
}
```

**Definition Priority**:
1. `definition` - Direct alias definition string
2. `definition_cid` - CID reference to alias definition
3. `target_path_cid` - Legacy CID reference (maintained for backward compatibility)

**Example**:
```json
"aliases": {
  "home-shortcut": {
    "name": "Home Directory Shortcut",
    "description": "Quick access to home directory",
    "definition": "literal /home -> /home/user"
  }
}
```

DB Access: [db_access/aliases.py:41-71](../db_access/aliases.py#L41-L71)

#### Servers

```json
"servers": {
  "template-key": {
    "name": "Server Template Name",            // REQUIRED
    "description": "Optional description",     // optional
    "definition": "def main():\n    ...",     // optional - direct Python code
    "definition_cid": "CID_VALUE",            // optional - CID reference
    "metadata": { /* optional metadata */ }
  }
}
```

**Definition Priority**:
1. `definition` - Direct Python code string
2. `definition_cid` - CID reference to Python code

**Example**:
```json
"servers": {
  "hello-world": {
    "name": "Hello World Server",
    "description": "Simple HTTP server example",
    "definition": "def main():\n    return 'Hello, World!'"
  }
}
```

DB Access: [db_access/servers.py:18-46](../db_access/servers.py#L18-L46)

#### Variables

```json
"variables": {
  "template-key": {
    "name": "Variable Name",                   // REQUIRED
    "description": "Optional description",     // optional
    "definition": "variable value",           // optional - direct value
    "definition_cid": "CID_VALUE",            // optional - CID reference
    "metadata": { /* optional metadata */ }
  }
}
```

**Definition Priority**:
1. `definition` - Direct value string
2. `definition_cid` - CID reference to value

**Example**:
```json
"variables": {
  "api-endpoint": {
    "name": "API Endpoint",
    "description": "Default API endpoint URL",
    "definition": "https://api.example.com/v1"
  }
}
```

DB Access: [db_access/variables.py:17-45](../db_access/variables.py#L17-L45)

#### Secrets

```json
"secrets": {
  "template-key": {
    "name": "Secret Name",                     // REQUIRED
    "description": "Optional description",     // optional
    "definition": "secret value",             // optional - direct value
    "definition_cid": "CID_VALUE",            // optional - CID reference
    "value_cid": "CID_VALUE",                 // optional - alternative CID field
    "metadata": { /* optional metadata */ }
  }
}
```

**Definition Priority**:
1. `definition` - Direct secret value
2. `definition_cid` - CID reference to secret value
3. `value_cid` - Alternative CID reference field

**Example**:
```json
"secrets": {
  "example-token": {
    "name": "Example API Token",
    "description": "Template for API token format",
    "definition": "sk-example-token-format-here"
  }
}
```

DB Access: [db_access/secrets.py:17-47](../db_access/secrets.py#L17-L47)

#### Uploads

```json
"uploads": {
  "template-key": {
    "name": "Upload Template Name",            // REQUIRED
    "description": "Optional description",     // optional
    "content": "file content here",           // optional - direct content
    "content_cid": "CID_VALUE",               // optional - CID reference
    "metadata": { /* optional metadata */ }
  }
}
```

**Content Priority**:
1. `content` - Direct file content
2. `content_cid` - CID reference to file content

**Example**:
```json
"uploads": {
  "readme-template": {
    "name": "README Template",
    "description": "Standard README.md template",
    "content": "# Project Name\n\n## Description\n\nAdd your description here."
  }
}
```

DB Access: [db_access/uploads.py:6-37](../db_access/uploads.py#L6-L37)

## Common Fields

All entity types share these common fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | Auto-added | Template identifier (the dictionary key, automatically added by system) |
| `name` | string | **Yes** | Display name for the template |
| `description` | string | No | Human-readable description of the template |
| `metadata` | object | No | Freeform metadata object for additional information |

## CID Resolution

CID (Content Identifier) fields allow templates to reference externally stored content. When a field name ends with `_cid`, the system automatically resolves it to the actual content.

**Supported CID Fields**:
- `definition_cid` - Used by aliases, servers, variables, secrets
- `target_path_cid` - Used by aliases (legacy)
- `value_cid` - Used by secrets (alternative)
- `content_cid` - Used by uploads

**Resolution Logic**: [template_manager.py:246-280](../template_manager.py#L246-L280)

**Example**:
```json
{
  "servers": {
    "web-server": {
      "name": "Web Server",
      "definition_cid": "QmXYZ123..."  // Resolves to actual Python code
    }
  }
}
```

## Validation Rules

Templates undergo strict validation when saved:

1. **JSON must not be empty** - Template content cannot be blank
2. **Valid JSON syntax** - Must parse as valid JSON
3. **Root must be an object** - Top level must be a dictionary/object, not an array
4. **All entity type keys required** - Must include all five keys: `aliases`, `servers`, `variables`, `secrets`, `uploads`
5. **Entity types must be objects** - Each entity type value must be a dictionary
6. **Templates must be objects** - Each individual template must be an object, not a primitive
7. **Name field required** - Every template must have a `name` field

**Validator Function**: [template_manager.py:85-127](../template_manager.py#L85-L127)

**Validation Errors Return**:
- `(False, "error message")` on failure
- `(True, None)` on success

## Processing and Usage

### Core Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `get_templates_config()` | [template_manager.py:33-82](../template_manager.py#L33-L82) | Retrieves and parses templates variable |
| `get_templates_for_type(entity_type)` | [template_manager.py:177-208](../template_manager.py#L177-L208) | Gets all templates for a specific entity type |
| `get_template_by_key(entity_type, key)` | [template_manager.py:211-243](../template_manager.py#L211-L243) | Retrieves specific template by key |
| `resolve_cid_value(cid_or_value)` | [template_manager.py:246-280](../template_manager.py#L246-L280) | Resolves CID references to content |
| `validate_templates_json(json_data)` | [template_manager.py:85-127](../template_manager.py#L85-L127) | Validates template JSON structure |

### Template Attributes

When templates are converted to entity objects, they receive special attributes:

- `id = None` - Templates are not persisted in entity tables
- `template_key = "template-key"` - The dictionary key for UI identification
- `template = True` - Flag for backward compatibility
- Standard entity fields (`name`, `description`, etc.) populated from template

### Processing Flow

1. User's `templates` variable is retrieved from database
2. System attempts JSON parsing; if it fails, treats as CID and resolves
3. For each entity type, templates are extracted and validated
4. CID fields are automatically resolved to actual content
5. Template objects are created with special attributes
6. Templates appear in UI alongside regular entities
7. Results are sorted by name

## Complete Example

```json
{
  "aliases": {
    "docs": {
      "name": "Documentation Shortcut",
      "description": "Quick access to documentation",
      "definition": "literal /docs -> /usr/share/doc"
    },
    "logs": {
      "name": "Logs Directory",
      "definition_cid": "QmABCD1234..."
    }
  },
  "servers": {
    "api-server": {
      "name": "REST API Server",
      "description": "Basic REST API template",
      "definition": "def main():\n    return {'status': 'ok'}",
      "metadata": {
        "version": "1.0",
        "author": "admin"
      }
    }
  },
  "variables": {
    "app-version": {
      "name": "Application Version",
      "definition": "1.0.0"
    }
  },
  "secrets": {
    "api-key": {
      "name": "API Key Template",
      "description": "Template showing API key format",
      "definition": "sk-..."
    }
  },
  "uploads": {
    "config-file": {
      "name": "Configuration File",
      "description": "Default configuration template",
      "content": "{\n  \"setting1\": \"value1\",\n  \"setting2\": \"value2\"\n}"
    }
  }
}
```

## Reference Templates

In addition to user-defined templates, the system includes built-in reference templates loaded from the filesystem:

- **Server Templates**: [reference/templates/servers/](../reference/templates/servers/)
- **Upload Templates**: [reference/templates/uploads/](../reference/templates/uploads/)

These are Python modules that load templates from JSON files and are merged with user-defined templates.

Loaders:
- [reference/templates/servers/__init__.py:13-72](../reference/templates/servers/__init__.py#L13-L72)
- [reference/templates/uploads/__init__.py:14-40](../reference/templates/uploads/__init__.py#L14-L40)

## Testing

### Unit Tests

**Template Manager Tests**: [tests/test_template_manager.py](../tests/test_template_manager.py)
- Tests validation rules
- Tests CID resolution
- Tests template retrieval by type and key
- Example template structures (lines 43-73)

**DB Access Tests**: [tests/test_db_access_templates.py](../tests/test_db_access_templates.py)
- Tests template retrieval through database access layer
- Tests entity object creation
- Tests template attributes

**Upload Tests**: [tests/test_db_access_uploads.py:85-124](../tests/test_db_access_uploads.py#L85-L124)
- Tests CID content resolution for upload templates

### Integration Tests

Entity-specific template tests:
- **Aliases**: [tests/integration/test_alias_pages.py:185-264](../tests/integration/test_alias_pages.py#L185-L264)
- **Servers**: [tests/integration/test_server_pages.py:230-306](../tests/integration/test_server_pages.py#L230-L306)
- **Variables**: [tests/integration/test_variable_pages.py:170-230](../tests/integration/test_variable_pages.py#L170-L230)
- **Secrets**: [tests/integration/test_secret_pages.py:51-91](../tests/integration/test_secret_pages.py#L51-L91)
- **Uploads**: [tests/integration/test_upload_pages.py:141-189](../tests/integration/test_upload_pages.py#L141-L189)

## UI Integration

**Form**: [forms.py:328-349](../forms.py#L328-L349) - `TemplatesConfigForm` for editing templates JSON

**Status Display**: Template counts and validity status shown on entity creation pages

## Best Practices

1. **Always include all five entity types** - Even if empty, include `"aliases": {}`, etc.
2. **Use descriptive template keys** - Keys like `web-server` are more readable than `template1`
3. **Provide descriptions** - Help users understand what each template is for
4. **Use CID for large content** - Store large definitions externally and reference via CID
5. **Add metadata** - Include creation date, author, version, etc. for tracking
6. **Validate before saving** - Use `validate_templates_json()` to check validity
7. **Test your templates** - Verify templates can be successfully instantiated

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "JSON cannot be empty" | Empty string provided | Provide valid JSON template structure |
| "Invalid JSON syntax" | Malformed JSON | Check for missing commas, brackets, quotes |
| "Root must be an object" | JSON is an array `[]` | Use object `{}` at root level |
| "Missing required key: X" | Missing entity type | Add all five entity type keys |
| "Each template must be an object" | Template is a string/number | Wrap in object with `name` field |
| "Template missing required 'name' field" | No `name` property | Add `"name": "Template Name"` to each template |

## See Also

- Template Manager Implementation: [template_manager.py](../template_manager.py)
- Database Access Layer: [db_access/](../db_access/)
- Test Suite: [tests/test_template_manager.py](../tests/test_template_manager.py)
- Reference Templates: [reference/templates/](../reference/templates/)
