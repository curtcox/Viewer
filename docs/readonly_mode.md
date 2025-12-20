# Read-Only Mode

## Overview

Read-only mode provides a secure, memory-constrained way to run the Viewer application where state-changing operations are blocked. This is useful for:

- Running untrusted or experimental boot images
- Providing public demo instances
- Testing without affecting persistent storage
- Operating with strict memory constraints

## Quick Start

```bash
# Start in read-only mode with default 1GB memory limit
python main.py --read-only

# Start with custom memory limit (supports K, M, G, T units)
python main.py --read-only --max-cid-memory 512M
```

## Features

### Automatic In-Memory Database

Read-only mode automatically enables an in-memory database. All data is lost when the application stops.

### Secure Boot Image

The application loads `readonly.boot.cid` which excludes dangerous servers that could:
- Execute shell commands (shell server)
- Access the file system (file server)
- Run system utilities (awk, sed, grep, jq servers)

Included servers are safe for read-only operation:
- AI/LLM servers (anthropic_claude, openai_chat, google_gemini, etc.)
- Template processors (jinja, markdown)
- Utility servers (echo, glom, pygments, urleditor, proxy)

### State-Change Blocking

HTTP requests that would change state return `405 Method Not Allowed`:
- POST, PUT, PATCH, DELETE requests
- Routes containing `/delete`, `/enable`, `/disable`, `/toggle`

GET requests continue to work normally.

### CID Memory Management

CIDs (Content-Addressable Storage) are still created and stored in memory, but with limits:

1. **Size Check**: CIDs larger than `--max-cid-memory` are rejected with `413 Content Too Large`
2. **Automatic Eviction**: When memory limit is reached, the largest CIDs are automatically deleted to make room
3. **Memory Tracking**: Total CID storage is continuously monitored

### Minimal Observability Impact

To preserve the read-only nature:
- Page views are NOT logged to the database
- Entity interactions are NOT recorded
- Server invocations proceed normally but aren't persisted

## Command-Line Options

### `--read-only`

Enable read-only mode. This automatically:
- Enables in-memory database
- Loads the readonly boot image
- Activates state-change blocking
- Enables CID memory management

### `--max-cid-memory SIZE`

Set maximum memory for CID storage (default: `1G`).

**Supported formats:**
- Plain bytes: `1073741824`
- Kilobytes: `1024K` or `1024KB`
- Megabytes: `512M` or `512MB`
- Gigabytes: `2G` or `2GB`
- Terabytes: `1T` or `1TB`

**Examples:**
```bash
python main.py --read-only --max-cid-memory 100M   # 100 megabytes
python main.py --read-only --max-cid-memory 2G     # 2 gigabytes
python main.py --read-only --max-cid-memory 512MB  # 512 megabytes
```

## Boot Images

### readonly.boot.cid

The read-only boot image is generated from `reference_templates/readonly.boot.source.json`.

To regenerate all boot images including readonly:
```bash
python generate_boot_image.py
```

### Customizing the Readonly Boot Image

Edit `reference_templates/readonly.boot.source.json` to:
- Add or remove servers
- Modify aliases
- Update variables

Then regenerate:
```bash
python generate_boot_image.py
```

The new CID will be saved to `reference_templates/readonly.boot.cid`.

## Technical Details

### Configuration Classes

**ReadOnlyConfig** (`readonly_config.py`)
- Singleton pattern for global state
- Methods: `set_read_only_mode()`, `is_read_only_mode()`, `set_max_cid_memory()`, `get_max_cid_memory()`

**CIDMemoryManager** (`cid_memory_manager.py`)
- Checks CID sizes before creation
- Tracks total memory usage
- Evicts largest CIDs when needed (LRU-like behavior)

### Middleware

**check_readonly_mode** (`app.py`)
- Flask `before_request` handler
- Checks if request would change state
- Returns 405 for blocked operations

**block_in_readonly_mode** (`readonly_middleware.py`)
- Decorator for protecting specific routes
- Can be applied to individual route functions

### Modified Components

**Analytics** (`analytics.py`)
- `track_page_view()` returns early in read-only mode

**Interactions** (`db_access/interactions.py`)
- `record_entity_interaction()` returns None in read-only mode

**CID Creation** (`db_access/cids.py`)
- `create_cid_record()` enforces memory limits in read-only mode

## Testing

### Unit Tests

```bash
# Test configuration
python test-unit -- tests/test_readonly_config.py -v

# Test CLI argument parsing
python test-unit -- tests/test_cli_args_readonly.py -v

# Test memory management
python test-unit -- tests/test_cid_memory_manager.py -v
```

### Integration Tests

```bash
# Test HTTP blocking and observability
python test-unit -- tests/integration/test_readonly_mode.py -v
```

### Demo Script

```bash
# Interactive demonstration of all features
python demo_readonly_mode.py
```

The demo script shows:
- Normal mode vs read-only mode behavior
- HTTP method blocking
- Memory limit enforcement
- Configuration management

## Examples

### Public Demo Server

```bash
# Run with minimal memory for a public demo
python main.py --read-only --max-cid-memory 256M --port 8080 --show
```

### Testing Experimental Boot Images

```bash
# Test a new boot image in read-only mode
python main.py --read-only experimental_boot_cid
```

### Development with Memory Constraints

```bash
# Simulate low-memory environment
python main.py --read-only --max-cid-memory 50M
```

## Limitations

- All data is lost when the application stops (in-memory database)
- Cannot create, update, or delete servers, aliases, variables, or secrets
- Cannot upload new files or CIDs beyond memory limit
- Page view history and interaction logs are not available
- Largest CIDs may be evicted without warning when memory limit is reached

## Security Considerations

Read-only mode is designed for safety but is not a complete security solution:

- ✅ Blocks state-changing HTTP requests
- ✅ Prevents execution of shell commands via excluded servers
- ✅ Limits memory consumption for CID storage
- ⚠️ Safe servers (AI, templates) can still make external API calls
- ⚠️ Does not sandbox Python code execution
- ⚠️ Does not prevent DoS via excessive CID creation (within memory limit)

For production deployments, combine with:
- Network firewalls and rate limiting
- Container resource limits
- Monitoring and alerting
- Regular security updates

## See Also

- [Boot Images](reference_templates/README.md) - Boot image documentation
- [Database Configuration](db_config.py) - Database mode management
- [CLI Arguments](cli_args.py) - All command-line options
