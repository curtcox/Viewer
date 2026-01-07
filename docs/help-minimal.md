# Viewer Help - Minimal Boot Image

You are using the **Minimal Boot Image**, which provides a bare-bones starting point with no pre-configured aliases, servers, or templates.

## What's Included in Minimal Boot

The minimal boot image includes:

### Essential Only
- Basic routing infrastructure
- Database schema
- Core application features
- **No pre-configured aliases**
- **No example servers**
- **No template library**

### Clean Slate
This image is designed for users who:
- Want complete control over their configuration
- Need to start from scratch without examples
- Prefer to build everything themselves
- Want to avoid cleaning up pre-configured content

## Other Available Boot Images

You can restart Viewer with different boot images:

### Default Boot Image
- Full-featured configuration with examples
- Pre-configured aliases and servers
- Template library for quick entity creation
- AI integration examples
- Best for learning and quick start

```bash
python main.py --boot-cid $(cat reference/templates/default.boot.cid)
```

### Readonly Boot Image
- Read-only mode enabled
- Cannot create, edit, or delete entities
- Ideal for demonstration or viewing-only scenarios
- Prevents accidental modifications

```bash
python main.py --boot-cid $(cat reference/templates/readonly.boot.cid)
```

## Getting Started with Minimal Boot

Since you're starting with a clean slate, here's how to begin:

### 1. Create Your First Alias
1. Visit [Aliases](/aliases)
2. Click "Create New Alias"
3. Define a simple mapping: `literal /home -> /`
4. Test and save it

### 2. Create Your First Server
1. Visit [Servers](/servers)
2. Click "Create New Server"
3. Write a simple Python function:
   ```python
   def main():
       return "Hello from my first server!"
   ```
4. Test and save it

### 3. Create Variables for Reusability
1. Visit [Variables](/variables)
2. Create variables for values you'll reuse
3. Reference them in your servers

### 4. Import Existing Configuration
If you have an export from another instance:
1. Visit [Import](/import)
2. Upload your export file
3. Select what to import
4. Review and confirm

## Building Your Configuration

### Recommended Order

1. **Start with Variables** - Define reusable values first
2. **Add Aliases** - Create shortcuts to common paths
3. **Build Servers** - Implement dynamic functionality
4. **Add Secrets** - Store sensitive credentials securely
5. **Export Regularly** - Back up your configuration

### Testing as You Go

- Use the built-in testing features for aliases and servers
- Check the [History](/history) page to track your changes
- Export your configuration periodically as backup

## Key Differences from Default Boot

Unlike the default boot image, minimal boot:

- ❌ No example servers to learn from
- ❌ No pre-configured aliases for shortcuts
- ❌ No template library
- ❌ No AI integration examples
- ✅ Clean database with no clutter
- ✅ Full control over all content
- ✅ Smaller initial state
- ✅ No need to delete unwanted examples

## Common Tasks

### Create Everything from Scratch
1. Design your alias structure
2. Implement your servers
3. Define your variables
4. Configure secrets as needed

### Import from Another Instance
1. Export from your source instance
2. Visit [Import](/import) on this instance
3. Upload and import the configuration

### Build a Template Library
1. Create reusable entity definitions
2. Store them as a variable named `templates`
3. Format according to the [template specification](/help/json-template-format.md)

## Help Resources

- [General Help](/help) - Complete help documentation
- [Creating Aliases](/help#aliases) - Alias syntax and examples
- [Creating Servers](/help#servers) - Server development guide
- [Import/Export Guide](/help/import-export-json-format.md) - Data transfer format
- [Template Format](/help/json-template-format.md) - Build your own templates
- [Gauge Specs](/source/specs/) - Behavioral specifications

## Need Examples?

If you decide you want examples and templates, consider:

1. **Switch to Default Boot** - Restart with the default boot image
2. **Import Examples** - Ask for an export containing examples
3. **View Source** - Browse [reference templates](/source/reference/templates) in the source browser

---

*Want a different starting point? Consider the [default](#default-boot-image) boot image for examples or [readonly](#readonly-boot-image) for demonstration mode.*
