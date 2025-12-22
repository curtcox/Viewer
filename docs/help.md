# Viewer Help Documentation

Welcome to Viewer, a secure content management platform that combines flexible aliasing, dynamic server execution, and content-addressed storage.

## Quick Navigation

- [Aliases](#aliases) - Create shortcuts and route transformations
- [Servers](#servers) - Execute Python code to handle requests
- [Variables](#variables) - Store and reference reusable values
- [Secrets](#secrets) - Securely store encrypted credentials
- [CIDs](#cids-content-identifiers) - Content-addressed storage system
- [Boot Images](#boot-images) - Pre-configured application states
- [Import/Export](#importing-and-exporting) - Transfer configuration between instances
- [Server Chaining](#server-chaining) - Connect servers in request pipelines
- [Variable Resolution](#variable-resolution) - Dynamic value lookup in servers

## Aliases

Aliases allow you to create URL shortcuts and route transformations. They define mappings from one path to another, enabling flexible request routing.

### Creating Aliases

Visit the [Aliases page](/aliases) to view and manage all aliases. You can:
- Create new aliases with custom definitions
- Edit existing aliases
- Delete aliases you no longer need

### Alias Definition Syntax

Aliases use a simple yet powerful syntax:

```
literal /docs -> /usr/share/doc
```

This creates a literal path mapping from `/docs` to `/usr/share/doc`.

### Testing Aliases

The [Alias Editor](/aliases/new) includes testing capabilities to verify your alias definitions work as expected before saving them.

For more details, see the [alias creation specs](/source/specs/create_alias.spec).

## Servers

Servers are Python functions that process HTTP requests and return responses. They enable dynamic content generation and can interact with external services.

### Server Definition

A server is defined as a Python function named `main()` that receives request context and returns a response:

```python
def main():
    return "Hello, World!"
```

### Creating Servers

Visit the [Servers page](/servers) to view and manage all servers. The server editor includes:
- Syntax highlighting
- Testing capabilities
- Documentation for available request context

### Server Execution Context

Servers have access to:
- Request parameters via `request` object
- Variables via variable resolution
- Secrets (when properly configured)
- Uploaded files and content

For examples, see the [default boot servers](/source/reference_templates/servers/definitions).

## Variables

Variables store reusable values that can be referenced by servers and other entities.

### Managing Variables

Visit the [Variables page](/variables) to:
- Create new variables
- Edit existing variables
- View all defined variables

### Using Variables in Servers

Servers can reference variables during execution. Variable values are resolved and made available to the server code.

### Variable Resolution

Variable resolution happens when a server executes. The system:
1. Identifies variable references in the server definition
2. Fetches variable values from the database
3. Makes values available to the executing server

## Secrets

Secrets provide secure storage for sensitive information like API keys and passwords.

### Creating Secrets

Visit the [Secrets page](/secrets) to manage encrypted secrets. Secrets are:
- Encrypted at rest
- Never displayed in plain text in the UI
- Only accessible to authorized servers

### Using Secrets

Secrets can be referenced by servers that need access to sensitive credentials. The encryption ensures secrets remain protected.

## CIDs (Content Identifiers)

CIDs are content-addressed identifiers used throughout Viewer for reliable content storage and verification.

### What is a CID?

A CID is a cryptographic hash of content that serves as both:
- A unique identifier
- A verification mechanism

Example CID: `AAAAAA3yP8vZp0NCu8wTFW0Rnptg_hAsDFIirsPLwML4zn9ZPfHc1yGMe3HQWB_nLSm-d40KGIhJyQM8FqkdWnyLO6Ozbg`

### CID Storage

CIDs are stored in the `/cids` directory. Each file:
- Is named by its CID
- Contains the actual content
- Can be verified by re-computing the hash

### CID Usage

CIDs are used for:
- Server definitions
- Alias definitions
- Variable values
- Import/export payloads
- Boot image content

For technical details, see [CID documentation](/help/import-export-json-format.md#cid-content-identifier-references).

## Boot Images

Boot images are pre-configured application states that can be loaded at startup. They define the initial set of aliases, servers, variables, and other entities.

### Available Boot Images

Viewer provides three boot images:

1. **Default** - Full-featured configuration with example servers and aliases
2. **Minimal** - Bare-bones configuration for starting from scratch
3. **Readonly** - Read-only mode for viewing content without modifications

### Using Boot Images

Start the application with a boot image:

```bash
python main.py --boot-cid <BOOT_CID>
```

The boot CID can be found in `reference_templates/*.boot.cid` files.

### Creating Boot Images

Boot images are defined in `reference_templates/` and generated using:

```bash
python generate_boot_image.py
```

This reads the source files and creates CID-based boot images. See [Boot CID Usage](/help/BOOT_CID_USAGE.md) for more information.

## Importing and Exporting

Viewer supports importing and exporting complete configurations as JSON files with CID references.

### Exporting Data

Visit the [Export page](/export) to create an export containing:
- Aliases
- Servers
- Variables
- Secrets (encrypted)
- Change history
- Application source

### Importing Data

Visit the [Import page](/import) to import configuration from:
- Previous exports
- Other Viewer instances
- Backup files

### Export Format

Exports use a JSON format with CID references for efficient content storage. The format supports:
- Version tracking
- Content deduplication
- Integrity verification

See [Import/Export Format](/help/import-export-json-format.md) for the complete specification.

### Command-Line Import

You can also import at startup using the `--boot-cid` parameter. This is useful for:
- Automated deployments
- Testing with specific configurations
- Resetting to known states

## Server Chaining

Server chaining allows servers to call other servers, creating request processing pipelines.

### How Server Chaining Works

A server can reference another server in its definition. When executed:
1. The first server processes the request
2. It can call another server by referencing it
3. The second server executes with the modified context
4. Results flow back through the chain

### Use Cases

Server chaining enables:
- Authentication and authorization layers
- Request transformation
- Content aggregation
- Multi-step processing

## Variable Resolution

Variable resolution is the process of looking up and providing variable values to executing servers.

### Resolution Process

When a server executes:
1. Variable references are identified
2. Variables are fetched from the database
3. Values are decoded and prepared
4. Variables are made available to the server

### Variable Prefetching

For performance, variables can be prefetched before server execution. This reduces database queries and improves response times.

### Special Variables

Some variables have special meaning:
- `templates` - Contains template definitions for reusable entities

## Additional Resources

### Application Pages

- [Home Page](/) - Dashboard and observability links
- [Aliases](/aliases) - Manage all aliases
- [Servers](/servers) - Manage all servers
- [Variables](/variables) - Manage all variables
- [Secrets](/secrets) - Manage all secrets
- [History](/history) - View change history
- [Export Data](/export) - Export configuration
- [Import Data](/import) - Import configuration
- [API Documentation](/openapi) - OpenAPI specification
- [Routes Overview](/routes) - All application routes
- [Source Browser](/source) - Browse application source code

### Gauge Specifications

Viewer includes comprehensive behavioral specifications:
- [Create Alias Spec](/source/specs/create_alias.spec)
- [Default Boot Servers Spec](/source/specs/default_boot_servers.spec)
- [All Specs](/source/specs/) - Complete specification suite

### Documentation Files

- [Boot CID Usage](/help/BOOT_CID_USAGE.md)
- [Import/Export Format](/help/import-export-json-format.md)
- [JSON Template Format](/help/json-template-format.md)
- [Readonly Mode](/help/readonly_mode.md)

## Getting Help

If you need assistance:
1. Review this help documentation
2. Check the [gauge specifications](/source/specs/) for behavioral examples
3. Browse the [source code](/source) for implementation details
4. Consult the [API documentation](/openapi) for programmatic access

---

*This documentation applies to all boot images with image-specific variations. See boot image-specific help for details on your current configuration.*
