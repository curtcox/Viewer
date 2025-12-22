# Viewer Help - Readonly Boot Image

You are using the **Readonly Boot Image**, which provides a demonstration and viewing-only configuration where no modifications are permitted.

## What's Included in Readonly Boot

The readonly boot image includes:

### Read-Only Mode Enabled
- All create, update, and delete operations are blocked
- Viewing all entities is permitted
- Testing features are available (without saving)
- Export functionality works
- Import is disabled

### Example Content
- Pre-configured aliases for demonstration
- Example servers showing capabilities
- Sample variables and configuration

### Protection Against Changes
This image is designed for:
- Demonstrations and presentations
- Viewing-only scenarios
- Learning and exploration without risk
- Environments where modifications should be prevented

## What You Can Do

In readonly mode, you can:

- ✅ **View** all aliases, servers, variables, and secrets
- ✅ **Test** aliases and servers (without saving)
- ✅ **Browse** source code and documentation
- ✅ **Export** current configuration
- ✅ **Search** for entities
- ✅ **View History** of changes (if any were made before readonly mode)
- ✅ **Access API Documentation**

## What You Cannot Do

In readonly mode, you cannot:

- ❌ **Create** new aliases, servers, variables, or secrets
- ❌ **Edit** existing entities
- ❌ **Delete** any entities
- ❌ **Import** configurations
- ❌ **Save** changes from tests
- ❌ **Modify** any stored data

## Other Available Boot Images

You can restart Viewer with different boot images:

### Default Boot Image
- Full-featured configuration with examples
- Complete read-write access
- Pre-configured aliases and servers
- Template library for quick entity creation
- Best for normal operation and development

```bash
python main.py --boot-cid $(cat reference_templates/default.boot.cid)
```

### Minimal Boot Image
- Bare-bones configuration
- No pre-configured content
- Full read-write access
- Best for starting from scratch

```bash
python main.py --boot-cid $(cat reference_templates/minimal.boot.cid)
```

## Use Cases for Readonly Mode

### Demonstrations
Perfect for showing Viewer capabilities without risking accidental changes:
- Present to stakeholders
- Demo to potential users
- Showcase features safely

### Learning Environment
Explore Viewer without worrying about breaking things:
- Try out different features
- Test servers and aliases
- Learn the interface

### Auditing
Review configurations without modification risk:
- Inspect existing setup
- Export for documentation
- Verify current state

### Shared Access
Provide view-only access to:
- Team members who shouldn't modify
- External reviewers
- Compliance auditors

## Exploring in Readonly Mode

### View Pre-configured Entities

1. **Browse Aliases** - Visit [Aliases](/aliases) to see configured shortcuts
2. **Examine Servers** - Check [Servers](/servers) to view example implementations
3. **Review Variables** - See [Variables](/variables) for stored values
4. **Inspect Secrets** - View secret names (not values) at [Secrets](/secrets)

### Test Without Saving

You can test functionality without making changes:

1. **Test Aliases** - Try the alias testing feature
2. **Execute Servers** - Run servers to see their output
3. **Experiment** - Play with configurations knowing nothing will be saved

### Export Current State

If you want to use this configuration elsewhere:

1. Visit [Export](/export)
2. Select what to export
3. Download the export file
4. Import it into a writable instance

## Switching to Writable Mode

If you need to make changes:

1. **Stop the current instance**
2. **Restart with default or minimal boot**:
   ```bash
   # For full features with examples:
   python main.py --boot-cid $(cat reference_templates/default.boot.cid)
   
   # For clean slate:
   python main.py --boot-cid $(cat reference_templates/minimal.boot.cid)
   ```
3. **Import your configuration** if you exported it

## Readonly Mode Features

### Still Available

- Full navigation and browsing
- Search functionality
- History viewing
- Source code browser
- API documentation
- All GET endpoints
- Export functionality

### Blocked Operations

Any attempt to:
- Create entities
- Update entities
- Delete entities
- Import data

Will result in an error message explaining that the operation is not permitted in readonly mode.

## Help Resources

- [General Help](/help) - Complete help documentation
- [Readonly Mode Documentation](/help/readonly_mode.md) - Technical details
- [Boot CID Usage](/help/BOOT_CID_USAGE.md) - Boot image system
- [Export Format](/help/import-export-json-format.md) - Export file structure
- [Gauge Specs](/source/specs/) - Behavioral specifications

## Common Questions

### Can I test servers without saving them?
Yes! The testing feature works in readonly mode. You just can't save the results.

### Can I export the configuration?
Yes! Export functionality is available so you can take the configuration to a writable instance.

### How do I make changes?
Restart with the default or minimal boot image to enable write access.

### Is this secure?
Readonly mode prevents modifications at the application level. For true security, use proper authentication and authorization.

---

*Need to make changes? Restart with the [default](#default-boot-image) or [minimal](#minimal-boot-image) boot images.*
