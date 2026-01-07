# Viewer Help - Default Boot Image

You are using the **Default Boot Image**, which provides a full-featured configuration with example servers, aliases, and comprehensive functionality.

## What's Included in Default Boot

The default boot image includes:

### Example Servers
- Sample AI server demonstrating LLM integration
- Cookie editor for managing browser cookies
- URL editor for building and testing requests
- Various utility servers for common tasks

### Pre-configured Aliases
- `/help` - This help documentation
- `/ai` - AI action editor
- `/cookies` - Cookie management interface
- Common shortcuts for frequently accessed features

### Template Library
The `templates` variable contains reusable templates for:
- Aliases
- Servers
- Variables
- Uploads

These templates can be instantiated to quickly create new entities.

### Full Feature Access
All Viewer features are available:
- Create and edit aliases, servers, variables, and secrets
- Import and export configurations
- Access change history
- Browse source code

## Other Available Boot Images

You can restart Viewer with different boot images:

### Minimal Boot Image
- Bare-bones configuration
- No pre-configured aliases or servers
- Best for starting completely from scratch
- Use when you want full control over initial state

```bash
python main.py --boot-cid $(cat reference/templates/minimal.boot.cid)
```

### Readonly Boot Image
- Read-only mode enabled
- Cannot create, edit, or delete entities
- Ideal for demonstration or viewing-only scenarios
- Prevents accidental modifications

```bash
python main.py --boot-cid $(cat reference/templates/readonly.boot.cid)
```

## Key Features Available

With the default boot image, you have access to:

1. **Complete CRUD Operations** - Create, read, update, and delete all entity types
2. **Testing Tools** - Built-in testing for aliases and servers
3. **AI Integration** - Example AI servers showing LLM capabilities
4. **Import/Export** - Full import and export functionality
5. **Change History** - Track all modifications over time
6. **Template System** - Reusable templates for quick entity creation

## Getting Started

1. **Explore Examples** - Visit [Servers](/servers) to see pre-configured example servers
2. **Browse Aliases** - Check out [Aliases](/aliases) to see the pre-configured shortcuts
3. **Review Templates** - View the templates variable to see reusable entity definitions
4. **Create Your Own** - Start creating your own aliases, servers, and variables

## Example Workflows

### Create a Simple Alias
1. Go to [Aliases](/aliases)
2. Click "Create New Alias"
3. Define your alias: `literal /myshortcut -> /target/path`
4. Test it to ensure it works
5. Save your alias

### Test a Server
1. Go to [Servers](/servers)
2. Select an example server (e.g., "Hello World")
3. Click "Test" to execute it
4. Review the response
5. Modify and test again

### Export Your Configuration
1. Go to [Export](/export)
2. Select what to export (aliases, servers, etc.)
3. Download the export file
4. Save it as a backup or share with another instance

## Common Tasks

- **View all entities**: Use the navigation dropdown menu to access lists of aliases, servers, variables, and secrets
- **Search**: Use the search feature to find specific entities
- **History**: Check [History](/history) to see recent changes
- **API Access**: See [API Documentation](/openapi) for programmatic access

## Help Resources

- [General Help](/help) - Complete help documentation
- [Boot CID Documentation](/help/BOOT_CID_USAGE.md) - Boot image system details
- [Import/Export Guide](/help/import-export-json-format.md) - Data transfer format
- [Gauge Specs](/source/specs/) - Behavioral specifications

---

*Need a different configuration? Consider switching to the [minimal](#minimal-boot-image) or [readonly](#readonly-boot-image) boot images.*
