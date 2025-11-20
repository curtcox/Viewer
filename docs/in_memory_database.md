# In-Memory Database Usage

The Viewer application supports running with an in-memory database for testing, development, and demo purposes.

## Quick Start

```bash
# Using the shell wrapper
./run.sh --in-memory-db

# Using Python directly
python main.py --in-memory-db

# With additional options
python main.py --in-memory-db --port 8080
```

## Features

### Filesystem Access

When running in in-memory database mode:

- **Read-only access to `/cids`**: Can read existing CID files from disk
- **No write access**: Cannot create new files on disk
- **Complete isolation**: All data exists only in memory

### Memory Limits

- **100 MB limit**: Hardcoded limit for in-memory database
- **Exception on exceed**: `MemoryLimitExceededError` raised when exceeded

### Startup Warning

When starting in memory mode, the application displays:
```
WARNING - Using memory-only database
```

## Use Cases

### Testing

Most tests use the in-memory database automatically:
```bash
python run_tests_clean.py
```

### Development

Experiment without leaving artifacts on disk:
```bash
./run.sh --in-memory-db --boot-cid <some-cid>
```

### Demo Mode

Showcase existing content without risk of modification:
```bash
./run.sh --in-memory-db --show
```

## CLI Flag Precedence

The `--in-memory-db` flag takes precedence over the `DATABASE_URL` environment variable:

```bash
# This will use in-memory database despite DATABASE_URL
DATABASE_URL=postgresql://localhost/mydb python main.py --in-memory-db
```

## Running Tests

### Unit Tests
```bash
python run_tests_clean.py
```

### Equivalence Tests
```bash
pytest -m "db_equivalence" -v
```

### All Tests
```bash
pytest tests/ -v
```

## Important Notes

1. **Data is not persisted**: All data is lost when the application stops
2. **Read-only CID access**: New CIDs created during a session only exist in memory
3. **State snapshots**: Use `--snapshot` to save in-memory state for debugging (when implemented)

## Configuration

The in-memory database is configured through `db_config.py`:

```python
from db_config import DatabaseConfig, DatabaseMode

# Set memory mode
DatabaseConfig.set_mode(DatabaseMode.MEMORY)

# Check current mode
if DatabaseConfig.is_memory_mode():
    print("Running in memory mode")

# Get database URI
uri = DatabaseConfig.get_database_uri()  # Returns "sqlite:///:memory:"
```

## Troubleshooting

### Memory Limit Exceeded

If you see `MemoryLimitExceededError`, the 100 MB limit has been exceeded. Options:
- Reduce the amount of data being stored
- Use disk-based database instead

### Warning Not Appearing

Ensure logging is configured:
```python
import logging
logging.basicConfig(level=logging.WARNING)
```
