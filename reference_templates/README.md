# Reference Templates

This directory contains reference templates for aliases, servers, variables, and uploads, along with the boot image generation system.

## Directory Structure

```
reference_templates/
├── aliases/              # Alias definition files
│   └── ai.txt
├── servers/              # Server template files
│   ├── templates/        # JSON metadata for servers
│   └── definitions/      # Python server implementations
├── uploads/              # Upload template files
│   ├── templates/        # JSON metadata for uploads
│   └── contents/         # Upload file contents
├── variables/            # Variable definition files
│   └── example_var.txt
├── boot.source.json      # Boot configuration (with filenames)
├── boot.json             # Generated boot configuration (with CIDs)
├── templates.source.json # Template definitions (with filenames)
├── templates.json        # Generated template definitions (with CIDs)
└── README.md            # This file
```

## Overview

The reference_templates system provides:

1. **Template Definitions**: Reusable templates for aliases, servers, variables, and uploads
2. **Boot Image**: A bootable configuration that can be loaded on startup
3. **CID-based Storage**: Content-addressed storage for reliable, verifiable content

## Files

### Source Files (Editable)

These files use **filenames** to reference content and are meant to be edited:

- **`boot.source.json`**: Defines the initial state (aliases, servers, variables) that should be loaded on boot
- **`templates.source.json`**: Defines template entities that users can instantiate
- **`aliases/`**: Text files containing alias definitions
- **`servers/definitions/`**: Python files containing server code
- **`uploads/contents/`**: Files that can be uploaded
- **`variables/`**: Text files containing variable values

### Generated Files (Auto-generated)

These files use **CIDs** to reference content and are automatically generated:

- **`boot.json`**: Generated from `boot.source.json` with CIDs replacing filenames
- **`templates.json`**: Generated from `templates.source.json` with CIDs replacing filenames

## How to Regenerate Boot Image

After editing any source files, regenerate the boot image:

```bash
python generate_boot_image.py
```

This script will:
1. Read all files referenced in `templates.source.json` and `boot.source.json`
2. Generate CIDs for each file
3. Store CIDs in the `/cids` directory
4. Create `templates.json` with CIDs replacing filenames
5. Create `boot.json` with CIDs replacing filenames
6. Print the boot CID that can be used to start the application

### Example Output

```
============================================================
Boot Image Generation Complete
============================================================
Templates CID: AAAAABL9cuRlcPsce4iVbnW0pjCPKx_Ipc0s2-Wvzv_l1VZAK_Qijnw7ok_Fglw6vY9Ih-GZ4EI1VRqbMkzT0JVgeNF6YQ
Boot CID:      AAAAAALZrCS1EktlckPye1xrrUdlfTsTp8w1t7B5rD80tYbrg0JIv2XO-Syu8KXYaN6AuPV4FUXTIGo9BwNSx43TowAIGQ

Total files processed: 20

To boot with this image, run:
  python main.py --boot-cid AAAAAALZrCS1EktlckPye1xrrUdlfTsTp8w1t7B5rD80tYbrg0JIv2XO-Syu8KXYaN6AuPV4FUXTIGo9BwNSx43TowAIGQ
```

## Using the Boot CID

To start the application with the generated boot image:

```bash
python main.py --boot-cid <BOOT_CID>
```

This will:
1. Load all CIDs from the `/cids` directory into the database
2. Import the boot CID, which includes:
   - Aliases defined in `boot.source.json`
   - Servers defined in `boot.source.json`
   - Variables defined in `boot.source.json` (including the `templates` variable)
3. Start the application normally

## File Formats

### boot.source.json

This file uses the import/export format (see `/docs/import-export-json-format.md`) but with filenames instead of CIDs:

```json
{
  "version": 6,
  "runtime": "{\"python\": {\"version\": \"3.11.0\", \"implementation\": \"CPython\"}}",
  "project_files": "{}",
  "aliases": [
    {
      "name": "ai",
      "definition_cid": "reference_templates/aliases/ai.txt",
      "enabled": true
    },
    {
      "name": "ai_about",
      "definition_cid": "reference_templates/aliases/ai_about.txt",
      "enabled": true
    }
  ],
  "servers": [
    {
      "name": "ai_stub",
      "definition_cid": "reference_templates/servers/definitions/ai_stub.py",
      "enabled": true
    }
  ],
  "variables": [
    {
      "name": "templates",
      "definition": "GENERATED:templates.json",
      "enabled": true
    }
  ]
}
```

**Special marker**: `"GENERATED:templates.json"` is replaced with the CID of `templates.json` during generation.

### templates.source.json

This file uses the template variable format (see `/docs/json-template-format.md`) but with filenames instead of CIDs:

```json
{
  "aliases": {
    "ai-shortcut": {
      "name": "AI Alias",
      "description": "Shortcut alias to AI stub server",
      "definition_cid": "reference_templates/aliases/ai.txt"
    }
  },
  "servers": {
    "echo": {
      "name": "Echo request context",
      "description": "Render the incoming request and context as HTML for debugging",
      "definition_cid": "reference_templates/servers/definitions/echo.py"
    }
  },
  "variables": {
    "example-variable": {
      "name": "Example Variable",
      "description": "An example variable for demonstration",
      "definition_cid": "reference_templates/variables/example_var.txt"
    }
  },
  "secrets": {},
  "uploads": {
    "hello-world": {
      "name": "Hello World HTML page",
      "description": "A minimal HTML page that renders a friendly greeting",
      "content_cid": "reference_templates/uploads/contents/hello_world.html"
    }
  }
}
```

## Adding New Templates

### Adding an Alias

1. Create a file in `aliases/` (e.g., `aliases/myalias.txt`):
   ```
   literal /mypath -> /target/path
   ```

2. Add an entry to `templates.source.json`:
   ```json
   "aliases": {
     "my-alias": {
       "name": "My Alias",
       "description": "Description of my alias",
       "definition_cid": "reference_templates/aliases/myalias.txt"
     }
   }
   ```

3. Optionally, add to `boot.source.json` to load on startup:
   ```json
   "aliases": [
     {
       "name": "myalias",
       "definition_cid": "reference_templates/aliases/myalias.txt",
       "enabled": true
     }
   ]
   ```

4. Regenerate: `python generate_boot_image.py`

### Adding a Server

1. Create a file in `servers/definitions/` (e.g., `servers/definitions/myserver.py`):
   ```python
   def main():
       return "Hello from my server!"
   ```

2. Add an entry to `templates.source.json`:
   ```json
   "servers": {
     "my-server": {
       "name": "My Server",
       "description": "Description of my server",
       "definition_cid": "reference_templates/servers/definitions/myserver.py"
     }
   }
   ```

3. Optionally, add to `boot.source.json` to load on startup

4. Regenerate: `python generate_boot_image.py`

### Adding a Variable

1. Create a file in `variables/` (e.g., `variables/myvar.txt`):
   ```
   my variable value
   ```

2. Add an entry to `templates.source.json`:
   ```json
   "variables": {
     "my-variable": {
       "name": "My Variable",
       "description": "Description of my variable",
       "definition_cid": "reference_templates/variables/myvar.txt"
     }
   }
   ```

3. Optionally, add to `boot.source.json` to load on startup

4. Regenerate: `python generate_boot_image.py`

## Testing

### Unit Tests

Run unit tests for the boot image generator:

```bash
python -m pytest tests/test_generate_boot_image.py -v
```

### Integration Tests

Run integration tests to verify boot image loading:

```bash
python -m pytest tests/integration/test_boot_image_reference_templates.py -v -m integration
```

These tests verify that:
- Aliases from `boot.source.json` are loaded correctly
- Servers from `boot.source.json` are loaded correctly
- The `templates` variable is loaded with the correct CID
- Templates from `templates.source.json` are accessible
- Template definitions resolve correctly from CIDs

## Technical Details

### CID Generation

CIDs (Content Identifiers) are generated using the system's content-addressing format:
- Content <= 64 bytes: Embedded directly in the CID
- Content > 64 bytes: SHA-512 hash of the content

See `/docs/import-export-json-format.md` for more details on CID format.

### Boot Process

1. Application starts with `--boot-cid <CID>`
2. CID directory loader runs (loads all `/cids/*` files into database)
3. Boot CID importer validates all dependencies are present
4. Boot CID content is parsed as import/export JSON
5. Entities (aliases, servers, variables) are imported
6. Application starts normally with entities loaded

See `/docs/BOOT_CID_USAGE.md` for more details on boot CID usage.

### Template System

Templates are stored in the `templates` variable and use the template JSON format:
- All five entity types must be present: `aliases`, `servers`, `variables`, `secrets`, `uploads`
- Each template has a `name` field (required) and optional `description`
- Content can be specified directly or via CID reference

See `/docs/json-template-format.md` for more details on template format.

## See Also

- `/docs/import-export-json-format.md` - Import/export JSON format documentation
- `/docs/BOOT_CID_USAGE.md` - Boot CID usage documentation
- `/docs/json-template-format.md` - JSON template format documentation
- `generate_boot_image.py` - Boot image generation script
- `tests/test_generate_boot_image.py` - Unit tests
- `tests/integration/test_boot_image_reference_templates.py` - Integration tests
