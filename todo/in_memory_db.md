# In-Memory Database Support Implementation Plan

## Overview

This document outlines a detailed plan for adding support for running the application with a custom in-memory "database". The implementation will:

- Enable most tests to use the in-memory database version
- Include extensive equivalence tests between in-memory and disk databases
- Add a command line flag for running the app with an in-memory database
- Be broken down into small, independently committable changes

## Filesystem Access Constraints

When running in in-memory database mode, the application has the following filesystem access restrictions:

### Read Access
- **`/cids` directory**: The in-memory database will have **read-only access** to all CID files stored in the `/cids` directory
- This allows the application to retrieve existing content-addressed data without modification

### No Other Filesystem Access
- The in-memory database mode **cannot write** to the `/cids` directory or create new CID files on disk
- **No access** to any other filesystem locations outside of `/cids`
- All new CID records created during an in-memory session exist only in memory and are lost when the application terminates
- Database file (`secureapp.db`) is never created or accessed in memory mode

### Implications
- **Testing**: Tests can read existing CID fixtures but cannot persist new CIDs to disk
- **Development**: Useful for experimenting without leaving artifacts on disk
- **Demo Mode**: Can showcase existing content without risk of modification
- **Isolation**: Complete isolation from persistent storage except for read-only CID access

### Implementation Notes
- CID read operations will check the `/cids` directory on disk
- CID write operations will store data only in the in-memory SQLite database
- On shutdown, all in-memory data (including new CIDs) is discarded
- Consider adding a warning on startup when running in memory mode

---

## Questions to Answer Before Implementation

The following questions should be answered before executing this plan:

### Architecture & Design

1. **CID Storage Strategy**: Should new CIDs created in memory mode be stored in the in-memory SQLite DB, or should we maintain a separate in-memory dict/cache for CID binary data?

2. **Hybrid Mode**: Should there be a hybrid mode where the database is in-memory but CIDs are still persisted to disk? Or is complete isolation preferred?

3. **Pre-loading CIDs**: Should all existing CIDs from `/cids` be pre-loaded into memory on startup, or should they be loaded lazily on first access?

4. **Memory Limits**: Should there be a configurable memory limit for the in-memory database? What happens when it's exceeded?

### Testing Strategy

5. **Test Data Fixtures**: Should we create a standard set of CID fixtures in `/cids` that tests can rely on? What data should they contain?

6. **PostgreSQL Equivalence**: Should equivalence tests also run against PostgreSQL to catch SQLite-specific behavior differences?

7. **Performance Benchmarks**: Should we add benchmarks comparing in-memory vs disk database performance?

8. **Existing Test Migration**: Should all existing tests be migrated to use the new fixtures, or only new tests?

### CLI & Configuration

9. **Environment Variable Override**: Should `--in-memory-db` be overridable by `DATABASE_URL` environment variable, or should the flag take precedence?

10. **Startup Warning**: What should the warning message say when starting in memory mode? Should it be suppressible?

11. **Data Seeding**: Should there be an option to seed the in-memory database with sample data for development/demo purposes?

### Operational Concerns

12. **Logging**: Should in-memory mode have different logging behavior to clearly indicate data won't be persisted?

13. **Graceful Shutdown**: Should the application warn about unsaved data on shutdown when in memory mode?

14. **CI/CD Integration**: Should CI always use in-memory mode, or should some tests run against disk databases?

### Compatibility

15. **Existing Workflows**: Are there any existing scripts or workflows that depend on the database file existing on disk?

16. **Plugin/Extension Support**: If the application has plugins, how should they handle in-memory mode?

17. **Import/Export**: Should import/export functionality work in memory mode, or should it be disabled/modified?

### Future Considerations

18. **State Snapshots**: Should we support snapshotting in-memory state to disk for debugging purposes?

19. **Hot Reload**: If running in memory mode during development, how should code hot-reloading affect the database state?

20. **Multi-Process**: If the app runs multiple workers, how should in-memory mode handle this? (SQLite in-memory is not shared across processes)

---

## Current State Analysis

### Existing Infrastructure

- **ORM**: Flask-SQLAlchemy 3.1.1+ with SQLAlchemy 2.0.43+
- **Default DB**: SQLite (`sqlite:///secureapp.db`)
- **Production DB**: PostgreSQL support via psycopg2-binary
- **Test DB**: Already uses `sqlite:///:memory:` in test fixtures
- **Configuration**: Via `DATABASE_URL` environment variable

### Key Files

- `database.py` - Database initialization
- `models.py` - 9 model definitions
- `app.py` - Flask app setup with DB configuration
- `db_access/` - Modular database access package
- `tests/conftest.py` - Test fixtures (already uses in-memory SQLite)

---

## Implementation Phases

### Phase 1: Foundation and Configuration

#### Commit 1.1: Add database configuration module
**File**: `db_config.py`

Create a centralized database configuration module that handles different database modes.

```python
# db_config.py
from enum import Enum
from typing import Optional
import os

class DatabaseMode(Enum):
    DISK = "disk"
    MEMORY = "memory"

class DatabaseConfig:
    """Centralized database configuration manager."""

    _instance: Optional['DatabaseConfig'] = None
    _mode: DatabaseMode = DatabaseMode.DISK

    @classmethod
    def get_instance(cls) -> 'DatabaseConfig':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_mode(cls, mode: DatabaseMode) -> None:
        cls._mode = mode

    @classmethod
    def get_mode(cls) -> DatabaseMode:
        return cls._mode

    @classmethod
    def is_memory_mode(cls) -> bool:
        return cls._mode == DatabaseMode.MEMORY

    @classmethod
    def get_database_uri(cls) -> str:
        if cls._mode == DatabaseMode.MEMORY:
            return "sqlite:///:memory:"
        return os.environ.get("DATABASE_URL", "sqlite:///secureapp.db")

    @classmethod
    def reset(cls) -> None:
        """Reset configuration to defaults (useful for testing)."""
        cls._mode = DatabaseMode.DISK
```

**Tests**: `tests/test_db_config.py`

---

#### Commit 1.2: Add tests for database configuration module
**File**: `tests/test_db_config.py`

```python
import pytest
from db_config import DatabaseConfig, DatabaseMode

class TestDatabaseConfig:
    def setup_method(self):
        DatabaseConfig.reset()

    def test_default_mode_is_disk(self):
        assert DatabaseConfig.get_mode() == DatabaseMode.DISK

    def test_set_memory_mode(self):
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        assert DatabaseConfig.get_mode() == DatabaseMode.MEMORY
        assert DatabaseConfig.is_memory_mode()

    def test_get_database_uri_disk_mode(self):
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        uri = DatabaseConfig.get_database_uri()
        assert "memory" not in uri

    def test_get_database_uri_memory_mode(self):
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        assert DatabaseConfig.get_database_uri() == "sqlite:///:memory:"

    def test_reset_returns_to_disk_mode(self):
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        DatabaseConfig.reset()
        assert DatabaseConfig.get_mode() == DatabaseMode.DISK
```

---

#### Commit 1.3: Integrate DatabaseConfig into app.py
**File**: `app.py`

Modify `create_app()` to use the centralized configuration.

```python
# In app.py, modify the database configuration section
from db_config import DatabaseConfig

def create_app(test_config=None):
    # ... existing code ...

    # Use DatabaseConfig for URI
    if test_config and "SQLALCHEMY_DATABASE_URI" in test_config:
        database_uri = test_config["SQLALCHEMY_DATABASE_URI"]
    else:
        database_uri = DatabaseConfig.get_database_uri()

    flask_app.config.update(
        SQLALCHEMY_DATABASE_URI=database_uri,
        # ... rest of config ...
    )
```

---

#### Commit 1.4: Add command line argument parsing module
**File**: `cli_args.py`

```python
# cli_args.py
import argparse
from db_config import DatabaseConfig, DatabaseMode

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the application."""
    parser = argparse.ArgumentParser(description="Viewer Application")

    parser.add_argument(
        "--in-memory-db",
        action="store_true",
        help="Run the application with an in-memory database"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the server on (default: 5000)"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )

    return parser.parse_args()

def configure_from_args(args: argparse.Namespace) -> None:
    """Configure the application based on parsed arguments."""
    if args.in_memory_db:
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
```

---

#### Commit 1.5: Add tests for CLI argument parsing
**File**: `tests/test_cli_args.py`

```python
import pytest
import sys
from unittest.mock import patch
from cli_args import parse_arguments, configure_from_args
from db_config import DatabaseConfig, DatabaseMode

class TestCLIArgs:
    def setup_method(self):
        DatabaseConfig.reset()

    def test_default_arguments(self):
        with patch.object(sys, 'argv', ['app.py']):
            args = parse_arguments()
            assert args.in_memory_db is False
            assert args.port == 5000
            assert args.host == "127.0.0.1"

    def test_in_memory_db_flag(self):
        with patch.object(sys, 'argv', ['app.py', '--in-memory-db']):
            args = parse_arguments()
            assert args.in_memory_db is True

    def test_configure_from_args_sets_memory_mode(self):
        with patch.object(sys, 'argv', ['app.py', '--in-memory-db']):
            args = parse_arguments()
            configure_from_args(args)
            assert DatabaseConfig.is_memory_mode()

    def test_configure_from_args_keeps_disk_mode(self):
        with patch.object(sys, 'argv', ['app.py']):
            args = parse_arguments()
            configure_from_args(args)
            assert not DatabaseConfig.is_memory_mode()
```

---

#### Commit 1.6: Create main entry point with CLI support
**File**: `main.py`

```python
#!/usr/bin/env python3
# main.py
"""Main entry point for the Viewer application."""

from cli_args import parse_arguments, configure_from_args
from app import create_app

def main():
    """Main entry point with CLI argument support."""
    args = parse_arguments()
    configure_from_args(args)

    app = create_app()
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )

if __name__ == "__main__":
    main()
```

---

### Phase 2: Test Infrastructure

#### Commit 2.1: Add memory database test marker
**File**: `tests/conftest.py`

Add a pytest marker for tests that specifically test in-memory database behavior.

```python
# Add to tests/conftest.py

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "memory_db: mark test as using in-memory database"
    )
    config.addinivalue_line(
        "markers", "db_equivalence: mark test as database equivalence test"
    )
```

---

#### Commit 2.2: Add memory database fixture
**File**: `tests/conftest.py`

```python
@pytest.fixture()
def memory_db_app():
    """Flask app configured with in-memory database."""
    from db_config import DatabaseConfig, DatabaseMode

    DatabaseConfig.set_mode(DatabaseMode.MEMORY)

    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    DatabaseConfig.reset()

@pytest.fixture()
def memory_client(memory_db_app):
    """Test client bound to memory database app."""
    return memory_db_app.test_client()
```

---

#### Commit 2.3: Add disk database fixture for comparison testing
**File**: `tests/conftest.py`

```python
import tempfile
import os

@pytest.fixture()
def disk_db_app(tmp_path):
    """Flask app configured with disk-based SQLite database."""
    from db_config import DatabaseConfig, DatabaseMode

    db_path = tmp_path / "test.db"
    db_uri = f"sqlite:///{db_path}"

    DatabaseConfig.set_mode(DatabaseMode.DISK)
    os.environ["DATABASE_URL"] = db_uri

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": db_uri,
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    # Cleanup
    if db_path.exists():
        db_path.unlink()
    DatabaseConfig.reset()

@pytest.fixture()
def disk_client(disk_db_app):
    """Test client bound to disk database app."""
    return disk_db_app.test_client()
```

---

#### Commit 2.4: Add database fixture factory
**File**: `tests/conftest.py`

Create a parameterized fixture for running tests against both database types.

```python
@pytest.fixture(params=["memory", "disk"])
def any_db_app(request, tmp_path):
    """Parameterized fixture that provides both memory and disk database apps."""
    from db_config import DatabaseConfig, DatabaseMode

    if request.param == "memory":
        DatabaseConfig.set_mode(DatabaseMode.MEMORY)
        db_uri = "sqlite:///:memory:"
    else:
        db_path = tmp_path / "test.db"
        db_uri = f"sqlite:///{db_path}"
        DatabaseConfig.set_mode(DatabaseMode.DISK)
        os.environ["DATABASE_URL"] = db_uri

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": db_uri,
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app, request.param
        db.session.remove()
        db.drop_all()

    DatabaseConfig.reset()

@pytest.fixture()
def any_client(any_db_app):
    """Test client that works with any database type."""
    app, db_type = any_db_app
    return app.test_client(), db_type
```

---

### Phase 3: Database Equivalence Tests

#### Commit 3.1: Create equivalence test base class
**File**: `tests/test_db_equivalence.py`

```python
# tests/test_db_equivalence.py
"""Database equivalence tests ensuring memory and disk databases behave identically."""

import pytest
from models import Server, Alias, Variable, Secret, CID, PageView
from models import EntityInteraction, ServerInvocation, Export
from database import db

@pytest.mark.db_equivalence
class TestDatabaseEquivalenceBase:
    """Base class for database equivalence tests."""

    @staticmethod
    def assert_equivalent_results(memory_result, disk_result, message=""):
        """Assert that results from both databases are equivalent."""
        if hasattr(memory_result, '__iter__') and not isinstance(memory_result, str):
            memory_list = list(memory_result)
            disk_list = list(disk_result)
            assert len(memory_list) == len(disk_list), f"Count mismatch: {message}"
            for m, d in zip(memory_list, disk_list):
                TestDatabaseEquivalenceBase._compare_objects(m, d, message)
        else:
            TestDatabaseEquivalenceBase._compare_objects(memory_result, disk_result, message)

    @staticmethod
    def _compare_objects(obj1, obj2, message):
        """Compare two database objects for equivalence."""
        if obj1 is None and obj2 is None:
            return
        assert type(obj1) == type(obj2), f"Type mismatch: {message}"
        if hasattr(obj1, '__dict__'):
            # Compare relevant attributes, excluding SQLAlchemy internals
            for key in obj1.__dict__:
                if not key.startswith('_'):
                    val1 = getattr(obj1, key)
                    val2 = getattr(obj2, key)
                    assert val1 == val2, f"Attribute {key} mismatch: {message}"
```

---

#### Commit 3.2: Add Server model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestServerEquivalence:
    """Test Server model behaves identically in both database modes."""

    def test_create_server_equivalence(self, memory_db_app, disk_db_app):
        """Creating a server produces equivalent results."""
        server_data = {
            "name": "test-server",
            "definition": "test definition",
            "enabled": True
        }

        # Create in memory DB
        with memory_db_app.app_context():
            memory_server = Server(**server_data)
            db.session.add(memory_server)
            db.session.commit()
            memory_result = {
                "name": memory_server.name,
                "definition": memory_server.definition,
                "enabled": memory_server.enabled
            }

        # Create in disk DB
        with disk_db_app.app_context():
            disk_server = Server(**server_data)
            db.session.add(disk_server)
            db.session.commit()
            disk_result = {
                "name": disk_server.name,
                "definition": disk_server.definition,
                "enabled": disk_server.enabled
            }

        assert memory_result == disk_result

    def test_query_server_equivalence(self, memory_db_app, disk_db_app):
        """Querying servers produces equivalent results."""
        servers = [
            {"name": "server-a", "definition": "def a", "enabled": True},
            {"name": "server-b", "definition": "def b", "enabled": False},
            {"name": "server-c", "definition": "def c", "enabled": True},
        ]

        # Setup memory DB
        with memory_db_app.app_context():
            for s in servers:
                db.session.add(Server(**s))
            db.session.commit()
            memory_count = Server.query.count()
            memory_enabled = Server.query.filter_by(enabled=True).count()
            memory_names = [s.name for s in Server.query.order_by(Server.name).all()]

        # Setup disk DB
        with disk_db_app.app_context():
            for s in servers:
                db.session.add(Server(**s))
            db.session.commit()
            disk_count = Server.query.count()
            disk_enabled = Server.query.filter_by(enabled=True).count()
            disk_names = [s.name for s in Server.query.order_by(Server.name).all()]

        assert memory_count == disk_count
        assert memory_enabled == disk_enabled
        assert memory_names == disk_names

    def test_update_server_equivalence(self, memory_db_app, disk_db_app):
        """Updating a server produces equivalent results."""
        # Setup
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                server = Server(name="update-test", definition="original")
                db.session.add(server)
                db.session.commit()

        # Update in memory DB
        with memory_db_app.app_context():
            server = Server.query.filter_by(name="update-test").first()
            server.definition = "updated"
            db.session.commit()
            memory_result = server.definition

        # Update in disk DB
        with disk_db_app.app_context():
            server = Server.query.filter_by(name="update-test").first()
            server.definition = "updated"
            db.session.commit()
            disk_result = server.definition

        assert memory_result == disk_result

    def test_delete_server_equivalence(self, memory_db_app, disk_db_app):
        """Deleting a server produces equivalent results."""
        # Setup
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                server = Server(name="delete-test", definition="to delete")
                db.session.add(server)
                db.session.commit()

        # Delete in memory DB
        with memory_db_app.app_context():
            server = Server.query.filter_by(name="delete-test").first()
            db.session.delete(server)
            db.session.commit()
            memory_count = Server.query.filter_by(name="delete-test").count()

        # Delete in disk DB
        with disk_db_app.app_context():
            server = Server.query.filter_by(name="delete-test").first()
            db.session.delete(server)
            db.session.commit()
            disk_count = Server.query.filter_by(name="delete-test").count()

        assert memory_count == disk_count == 0
```

---

#### Commit 3.3: Add Alias model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestAliasEquivalence:
    """Test Alias model behaves identically in both database modes."""

    def test_create_alias_equivalence(self, memory_db_app, disk_db_app):
        """Creating an alias produces equivalent results."""
        alias_data = {
            "name": "test-alias",
            "definition": "/api/test",
            "enabled": True
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                alias = Alias(**alias_data)
                db.session.add(alias)
                db.session.commit()
                results[name] = {
                    "name": alias.name,
                    "definition": alias.definition,
                    "enabled": alias.enabled
                }

        assert results["memory"] == results["disk"]

    def test_alias_ordering_equivalence(self, memory_db_app, disk_db_app):
        """Alias ordering is equivalent in both databases."""
        aliases = [
            {"name": "z-alias", "definition": "/z"},
            {"name": "a-alias", "definition": "/a"},
            {"name": "m-alias", "definition": "/m"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for a in aliases:
                    db.session.add(Alias(**a))
                db.session.commit()
                results[name] = [a.name for a in Alias.query.order_by(Alias.name).all()]

        assert results["memory"] == results["disk"]
        assert results["memory"] == ["a-alias", "m-alias", "z-alias"]
```

---

#### Commit 3.4: Add Variable model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestVariableEquivalence:
    """Test Variable model behaves identically in both database modes."""

    def test_create_variable_equivalence(self, memory_db_app, disk_db_app):
        """Creating a variable produces equivalent results."""
        var_data = {
            "name": "TEST_VAR",
            "definition": "test_value",
            "enabled": True
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                var = Variable(**var_data)
                db.session.add(var)
                db.session.commit()
                results[name] = {
                    "name": var.name,
                    "definition": var.definition,
                    "enabled": var.enabled
                }

        assert results["memory"] == results["disk"]

    def test_variable_unique_constraint_equivalence(self, memory_db_app, disk_db_app):
        """Unique constraint behavior is equivalent in both databases."""
        from sqlalchemy.exc import IntegrityError

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                var1 = Variable(name="UNIQUE_VAR", definition="first")
                db.session.add(var1)
                db.session.commit()

                var2 = Variable(name="UNIQUE_VAR", definition="second")
                db.session.add(var2)
                with pytest.raises(IntegrityError):
                    db.session.commit()
                db.session.rollback()
```

---

#### Commit 3.5: Add Secret model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestSecretEquivalence:
    """Test Secret model behaves identically in both database modes."""

    def test_create_secret_equivalence(self, memory_db_app, disk_db_app):
        """Creating a secret produces equivalent results."""
        secret_data = {
            "name": "API_KEY",
            "definition": "secret-value-123",
            "enabled": True
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                secret = Secret(**secret_data)
                db.session.add(secret)
                db.session.commit()
                results[name] = {
                    "name": secret.name,
                    "definition": secret.definition,
                    "enabled": secret.enabled
                }

        assert results["memory"] == results["disk"]
```

---

#### Commit 3.6: Add CID model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestCIDEquivalence:
    """Test CID model behaves identically in both database modes."""

    def test_create_cid_equivalence(self, memory_db_app, disk_db_app):
        """Creating a CID record produces equivalent results."""
        cid_data = {
            "path": "/cid/test123",
            "file_data": b"test binary data",
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = CID(**cid_data)
                db.session.add(cid)
                db.session.commit()
                results[name] = {
                    "path": cid.path,
                    "file_data": cid.file_data,
                    "file_size": cid.file_size
                }

        assert results["memory"] == results["disk"]

    def test_cid_binary_data_equivalence(self, memory_db_app, disk_db_app):
        """Binary data storage is equivalent in both databases."""
        binary_data = bytes(range(256))  # All possible byte values

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = CID(path="/cid/binary", file_data=binary_data)
                db.session.add(cid)
                db.session.commit()

                retrieved = CID.query.filter_by(path="/cid/binary").first()
                results[name] = retrieved.file_data

        assert results["memory"] == results["disk"] == binary_data

    def test_cid_large_data_equivalence(self, memory_db_app, disk_db_app):
        """Large binary data storage is equivalent in both databases."""
        large_data = b"x" * 1_000_000  # 1MB of data

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = CID(path="/cid/large", file_data=large_data)
                db.session.add(cid)
                db.session.commit()

                retrieved = CID.query.filter_by(path="/cid/large").first()
                results[name] = len(retrieved.file_data)

        assert results["memory"] == results["disk"] == 1_000_000
```

---

#### Commit 3.7: Add PageView model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestPageViewEquivalence:
    """Test PageView model behaves identically in both database modes."""

    def test_create_page_view_equivalence(self, memory_db_app, disk_db_app):
        """Creating a page view produces equivalent results."""
        from datetime import datetime, timezone

        view_data = {
            "path": "/test/page",
            "method": "GET",
            "user_agent": "TestAgent/1.0",
            "ip_address": "192.168.1.1"
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                view = PageView(**view_data)
                db.session.add(view)
                db.session.commit()
                results[name] = {
                    "path": view.path,
                    "method": view.method,
                    "user_agent": view.user_agent,
                    "ip_address": view.ip_address
                }

        assert results["memory"] == results["disk"]

    def test_page_view_aggregation_equivalence(self, memory_db_app, disk_db_app):
        """Aggregation queries produce equivalent results."""
        from sqlalchemy import func

        views = [
            {"path": "/page1", "method": "GET"},
            {"path": "/page1", "method": "GET"},
            {"path": "/page2", "method": "POST"},
            {"path": "/page1", "method": "GET"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for v in views:
                    db.session.add(PageView(**v))
                db.session.commit()

                counts = db.session.query(
                    PageView.path, func.count(PageView.id)
                ).group_by(PageView.path).order_by(PageView.path).all()
                results[name] = dict(counts)

        assert results["memory"] == results["disk"]
```

---

#### Commit 3.8: Add EntityInteraction model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestEntityInteractionEquivalence:
    """Test EntityInteraction model behaves identically in both database modes."""

    def test_create_interaction_equivalence(self, memory_db_app, disk_db_app):
        """Creating an entity interaction produces equivalent results."""
        interaction_data = {
            "entity_type": "Server",
            "entity_name": "test-server",
            "action": "create",
            "message": "Server created",
            "content": '{"key": "value"}'
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                interaction = EntityInteraction(**interaction_data)
                db.session.add(interaction)
                db.session.commit()
                results[name] = {
                    "entity_type": interaction.entity_type,
                    "entity_name": interaction.entity_name,
                    "action": interaction.action,
                    "message": interaction.message,
                    "content": interaction.content
                }

        assert results["memory"] == results["disk"]
```

---

#### Commit 3.9: Add ServerInvocation model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestServerInvocationEquivalence:
    """Test ServerInvocation model behaves identically in both database modes."""

    def test_create_invocation_equivalence(self, memory_db_app, disk_db_app):
        """Creating a server invocation produces equivalent results."""
        invocation_data = {
            "server_name": "test-server",
            "result_cid": "/cid/result123",
            "servers_cid": "/cid/servers456",
            "variables_cid": "/cid/vars789",
            "secrets_cid": "/cid/secrets012",
            "request_details_cid": "/cid/request345",
            "invocation_cid": "/cid/invoke678"
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                invocation = ServerInvocation(**invocation_data)
                db.session.add(invocation)
                db.session.commit()
                results[name] = {
                    "server_name": invocation.server_name,
                    "result_cid": invocation.result_cid
                }

        assert results["memory"] == results["disk"]
```

---

#### Commit 3.10: Add Export model equivalence tests
**File**: `tests/test_db_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestExportEquivalence:
    """Test Export model behaves identically in both database modes."""

    def test_create_export_equivalence(self, memory_db_app, disk_db_app):
        """Creating an export record produces equivalent results."""
        export_data = {
            "cid": "/cid/export123"
        }

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                export = Export(**export_data)
                db.session.add(export)
                db.session.commit()
                results[name] = {
                    "cid": export.cid
                }

        assert results["memory"] == results["disk"]
```

---

### Phase 4: db_access Module Equivalence Tests

#### Commit 4.1: Add generic_crud equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
# tests/test_db_access_equivalence.py
"""Equivalence tests for db_access module operations."""

import pytest
from models import Server, Alias, Variable, Secret
from database import db
from db_access.generic_crud import GenericEntityRepository

@pytest.mark.db_equivalence
class TestGenericCrudEquivalence:
    """Test GenericEntityRepository behaves identically in both database modes."""

    def test_get_all_equivalence(self, memory_db_app, disk_db_app):
        """get_all() produces equivalent results."""
        servers = [
            {"name": "server-c", "definition": "c"},
            {"name": "server-a", "definition": "a"},
            {"name": "server-b", "definition": "b"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for s in servers:
                    db.session.add(Server(**s))
                db.session.commit()

                repo = GenericEntityRepository(Server)
                all_servers = repo.get_all()
                results[name] = [s.name for s in all_servers]

        assert results["memory"] == results["disk"]
        # Should be sorted by name
        assert results["memory"] == ["server-a", "server-b", "server-c"]

    def test_get_by_name_equivalence(self, memory_db_app, disk_db_app):
        """get_by_name() produces equivalent results."""
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                db.session.add(Server(name="find-me", definition="found"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                repo = GenericEntityRepository(Server)
                server = repo.get_by_name("find-me")
                results[name] = server.definition if server else None

        assert results["memory"] == results["disk"] == "found"

    def test_count_equivalence(self, memory_db_app, disk_db_app):
        """count() produces equivalent results."""
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                for i in range(5):
                    db.session.add(Server(name=f"server-{i}", definition=f"def-{i}"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                repo = GenericEntityRepository(Server)
                results[name] = repo.count()

        assert results["memory"] == results["disk"] == 5

    def test_exists_equivalence(self, memory_db_app, disk_db_app):
        """exists() produces equivalent results."""
        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                db.session.add(Server(name="exists-test", definition="yes"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                repo = GenericEntityRepository(Server)
                results[name] = {
                    "exists": repo.exists("exists-test"),
                    "not_exists": repo.exists("nonexistent")
                }

        assert results["memory"] == results["disk"]
        assert results["memory"]["exists"] is True
        assert results["memory"]["not_exists"] is False
```

---

#### Commit 4.2: Add servers module equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestServersModuleEquivalence:
    """Test servers.py module behaves identically in both database modes."""

    def test_get_servers_equivalence(self, memory_db_app, disk_db_app):
        """get_servers() produces equivalent results."""
        from db_access.servers import get_servers

        servers = [
            {"name": "srv-2", "definition": "def2", "enabled": True},
            {"name": "srv-1", "definition": "def1", "enabled": False},
            {"name": "srv-3", "definition": "def3", "enabled": True},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for s in servers:
                    db.session.add(Server(**s))
                db.session.commit()

                result = get_servers()
                results[name] = [(s.name, s.enabled) for s in result]

        assert results["memory"] == results["disk"]

    def test_get_server_by_name_equivalence(self, memory_db_app, disk_db_app):
        """get_server_by_name() produces equivalent results."""
        from db_access.servers import get_server_by_name

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                db.session.add(Server(name="target", definition="target-def"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = get_server_by_name("target")
                results[name] = server.definition if server else None

        assert results["memory"] == results["disk"] == "target-def"
```

---

#### Commit 4.3: Add aliases module equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestAliasesModuleEquivalence:
    """Test aliases.py module behaves identically in both database modes."""

    def test_get_aliases_equivalence(self, memory_db_app, disk_db_app):
        """get_aliases() produces equivalent results."""
        from db_access.aliases import get_aliases

        aliases = [
            {"name": "alias-b", "definition": "/b"},
            {"name": "alias-a", "definition": "/a"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for a in aliases:
                    db.session.add(Alias(**a))
                db.session.commit()

                result = get_aliases()
                results[name] = [(a.name, a.definition) for a in result]

        assert results["memory"] == results["disk"]
```

---

#### Commit 4.4: Add cids module equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
from models import CID

@pytest.mark.db_equivalence
class TestCIDsModuleEquivalence:
    """Test cids.py module behaves identically in both database modes."""

    def test_create_cid_record_equivalence(self, memory_db_app, disk_db_app):
        """create_cid_record() produces equivalent results."""
        from db_access.cids import create_cid_record

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                cid = create_cid_record("/cid/test", b"test data")
                results[name] = {
                    "path": cid.path,
                    "data_len": len(cid.file_data)
                }

        assert results["memory"] == results["disk"]

    def test_find_cids_by_prefix_equivalence(self, memory_db_app, disk_db_app):
        """find_cids_by_prefix() produces equivalent results."""
        from db_access.cids import find_cids_by_prefix

        cids = [
            {"path": "/cid/abc123", "file_data": b"1"},
            {"path": "/cid/abc456", "file_data": b"2"},
            {"path": "/cid/xyz789", "file_data": b"3"},
        ]

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                for c in cids:
                    db.session.add(CID(**c))
                db.session.commit()

                found = find_cids_by_prefix("/cid/abc")
                results[name] = sorted([c.path for c in found])

        assert results["memory"] == results["disk"]
        assert len(results["memory"]) == 2
```

---

#### Commit 4.5: Add page_views module equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
from models import PageView

@pytest.mark.db_equivalence
class TestPageViewsModuleEquivalence:
    """Test page_views.py module behaves identically in both database modes."""

    def test_save_page_view_equivalence(self, memory_db_app, disk_db_app):
        """save_page_view() produces equivalent results."""
        from db_access.page_views import save_page_view

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                view = save_page_view(
                    path="/test",
                    method="GET",
                    user_agent="Test",
                    ip_address="127.0.0.1"
                )
                results[name] = {
                    "path": view.path,
                    "method": view.method
                }

        assert results["memory"] == results["disk"]

    def test_count_page_views_equivalence(self, memory_db_app, disk_db_app):
        """count_page_views() produces equivalent results."""
        from db_access.page_views import count_page_views

        for app in [memory_db_app, disk_db_app]:
            with app.app_context():
                for i in range(10):
                    db.session.add(PageView(path=f"/page{i}", method="GET"))
                db.session.commit()

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                results[name] = count_page_views()

        assert results["memory"] == results["disk"] == 10
```

---

#### Commit 4.6: Add interactions module equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestInteractionsModuleEquivalence:
    """Test interactions.py module behaves identically in both database modes."""

    def test_record_entity_interaction_equivalence(self, memory_db_app, disk_db_app):
        """record_entity_interaction() produces equivalent results."""
        from db_access.interactions import record_entity_interaction

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                interaction = record_entity_interaction(
                    entity_type="Server",
                    entity_name="test-server",
                    action="create",
                    message="Created server"
                )
                results[name] = {
                    "entity_type": interaction.entity_type,
                    "action": interaction.action
                }

        assert results["memory"] == results["disk"]
```

---

#### Commit 4.7: Add invocations module equivalence tests
**File**: `tests/test_db_access_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestInvocationsModuleEquivalence:
    """Test invocations.py module behaves identically in both database modes."""

    def test_create_server_invocation_equivalence(self, memory_db_app, disk_db_app):
        """create_server_invocation() produces equivalent results."""
        from db_access.invocations import create_server_invocation

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                invocation = create_server_invocation(
                    server_name="test-server",
                    result_cid="/cid/result",
                    servers_cid="/cid/servers",
                    variables_cid="/cid/vars",
                    secrets_cid="/cid/secrets",
                    request_details_cid="/cid/request",
                    invocation_cid="/cid/invocation"
                )
                results[name] = {
                    "server_name": invocation.server_name,
                    "result_cid": invocation.result_cid
                }

        assert results["memory"] == results["disk"]
```

---

### Phase 5: Transaction and Edge Case Tests

#### Commit 5.1: Add transaction rollback equivalence tests
**File**: `tests/test_db_transaction_equivalence.py`

```python
# tests/test_db_transaction_equivalence.py
"""Transaction behavior equivalence tests."""

import pytest
from models import Server
from database import db

@pytest.mark.db_equivalence
class TestTransactionEquivalence:
    """Test transaction behavior is equivalent in both database modes."""

    def test_rollback_equivalence(self, memory_db_app, disk_db_app):
        """Rollback behavior is equivalent in both databases."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Add a server
                server = Server(name="rollback-test", definition="original")
                db.session.add(server)
                db.session.commit()

                # Modify and rollback
                server.definition = "modified"
                db.session.rollback()

                # Refresh to get the actual database state
                db.session.refresh(server)
                results[name] = server.definition

        assert results["memory"] == results["disk"] == "original"

    def test_nested_transaction_equivalence(self, memory_db_app, disk_db_app):
        """Nested transaction behavior is equivalent."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Outer transaction
                server1 = Server(name="outer", definition="outer-def")
                db.session.add(server1)

                # Inner savepoint
                with db.session.begin_nested():
                    server2 = Server(name="inner", definition="inner-def")
                    db.session.add(server2)
                    # This commit is to the savepoint

                db.session.commit()

                count = Server.query.count()
                results[name] = count

        assert results["memory"] == results["disk"] == 2
```

---

#### Commit 5.2: Add concurrent access equivalence tests
**File**: `tests/test_db_transaction_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestConcurrencyEquivalence:
    """Test concurrent access patterns behave equivalently."""

    def test_isolation_level_equivalence(self, memory_db_app, disk_db_app):
        """Session isolation behaves equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Create initial data
                server = Server(name="isolation-test", definition="initial")
                db.session.add(server)
                db.session.commit()

                # Query and modify
                server1 = Server.query.filter_by(name="isolation-test").first()
                server1.definition = "modified"

                # Query again (should see uncommitted change in same session)
                server2 = Server.query.filter_by(name="isolation-test").first()
                results[name] = server2.definition

        assert results["memory"] == results["disk"] == "modified"
```

---

#### Commit 5.3: Add NULL handling equivalence tests
**File**: `tests/test_db_edge_cases_equivalence.py`

```python
# tests/test_db_edge_cases_equivalence.py
"""Edge case equivalence tests."""

import pytest
from models import Server, CID
from database import db

@pytest.mark.db_equivalence
class TestNullHandlingEquivalence:
    """Test NULL value handling is equivalent in both databases."""

    def test_nullable_field_equivalence(self, memory_db_app, disk_db_app):
        """Nullable fields behave equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Server with nullable definition_cid
                server = Server(
                    name="null-test",
                    definition="has null cid",
                    definition_cid=None
                )
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name="null-test").first()
                results[name] = retrieved.definition_cid

        assert results["memory"] == results["disk"] is None

    def test_empty_string_vs_null_equivalence(self, memory_db_app, disk_db_app):
        """Empty strings and NULL are handled equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server1 = Server(name="empty", definition="")
                server2 = Server(name="null", definition=None)
                db.session.add_all([server1, server2])
                db.session.commit()

                s1 = Server.query.filter_by(name="empty").first()
                s2 = Server.query.filter_by(name="null").first()
                results[name] = {
                    "empty": s1.definition,
                    "null": s2.definition
                }

        assert results["memory"] == results["disk"]
```

---

#### Commit 5.4: Add special character equivalence tests
**File**: `tests/test_db_edge_cases_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestSpecialCharacterEquivalence:
    """Test special character handling is equivalent in both databases."""

    def test_unicode_equivalence(self, memory_db_app, disk_db_app):
        """Unicode characters are handled equivalently."""
        unicode_content = "Hello 世界 🌍 Ñoño"

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(name="unicode-test", definition=unicode_content)
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name="unicode-test").first()
                results[name] = retrieved.definition

        assert results["memory"] == results["disk"] == unicode_content

    def test_sql_injection_characters_equivalence(self, memory_db_app, disk_db_app):
        """SQL injection characters are handled equivalently (safely)."""
        dangerous_content = "'; DROP TABLE servers; --"

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(name="injection-test", definition=dangerous_content)
                db.session.add(server)
                db.session.commit()

                # Table should still exist and data should be stored literally
                count = Server.query.count()
                retrieved = Server.query.filter_by(name="injection-test").first()
                results[name] = {
                    "count": count,
                    "definition": retrieved.definition
                }

        assert results["memory"] == results["disk"]
        assert results["memory"]["definition"] == dangerous_content
```

---

#### Commit 5.5: Add timestamp equivalence tests
**File**: `tests/test_db_edge_cases_equivalence.py`

```python
from datetime import datetime, timezone

@pytest.mark.db_equivalence
class TestTimestampEquivalence:
    """Test timestamp handling is equivalent in both databases."""

    def test_auto_timestamp_equivalence(self, memory_db_app, disk_db_app):
        """Auto-generated timestamps behave equivalently."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                server = Server(name="timestamp-test", definition="test")
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name="timestamp-test").first()
                results[name] = {
                    "has_created_at": retrieved.created_at is not None,
                    "is_utc": retrieved.created_at.tzinfo is not None or
                              retrieved.created_at.tzname() == 'UTC'
                }

        # Both should have timestamps
        assert results["memory"]["has_created_at"] == results["disk"]["has_created_at"] == True

    def test_timestamp_ordering_equivalence(self, memory_db_app, disk_db_app):
        """Timestamp ordering is equivalent in both databases."""
        import time

        results = {}
        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Create servers with slight delay
                server1 = Server(name="first", definition="1")
                db.session.add(server1)
                db.session.commit()

                time.sleep(0.01)  # Small delay

                server2 = Server(name="second", definition="2")
                db.session.add(server2)
                db.session.commit()

                # Order by created_at
                ordered = Server.query.order_by(Server.created_at.asc()).all()
                results[name] = [s.name for s in ordered]

        assert results["memory"] == results["disk"]
        assert results["memory"] == ["first", "second"]
```

---

### Phase 6: API Route Equivalence Tests

#### Commit 6.1: Add server routes equivalence tests
**File**: `tests/test_routes_equivalence.py`

```python
# tests/test_routes_equivalence.py
"""API route equivalence tests."""

import pytest
from models import Server
from database import db

@pytest.mark.db_equivalence
class TestServerRoutesEquivalence:
    """Test server routes behave identically with both database modes."""

    def test_get_servers_route_equivalence(self, memory_client, disk_client):
        """GET /servers produces equivalent results."""
        # Setup data in both
        servers = [
            {"name": "srv-1", "definition": "def-1"},
            {"name": "srv-2", "definition": "def-2"},
        ]

        for client_name, client, app in [
            ("memory", memory_client, memory_client.application),
            ("disk", disk_client, disk_client.application)
        ]:
            with app.app_context():
                for s in servers:
                    db.session.add(Server(**s))
                db.session.commit()

        # Make requests
        memory_response = memory_client.get('/servers')
        disk_response = disk_client.get('/servers')

        assert memory_response.status_code == disk_response.status_code

    def test_create_server_route_equivalence(self, memory_client, disk_client):
        """POST /servers produces equivalent results."""
        server_data = {
            "name": "new-server",
            "definition": "new definition"
        }

        memory_response = memory_client.post('/servers', json=server_data)
        disk_response = disk_client.post('/servers', json=server_data)

        assert memory_response.status_code == disk_response.status_code
```

---

#### Commit 6.2: Add alias routes equivalence tests
**File**: `tests/test_routes_equivalence.py`

```python
@pytest.mark.db_equivalence
class TestAliasRoutesEquivalence:
    """Test alias routes behave identically with both database modes."""

    def test_get_aliases_route_equivalence(self, memory_client, disk_client):
        """GET /aliases produces equivalent results."""
        from models import Alias

        aliases = [{"name": "alias-1", "definition": "/a"}]

        for client_name, client, app in [
            ("memory", memory_client, memory_client.application),
            ("disk", disk_client, disk_client.application)
        ]:
            with app.app_context():
                for a in aliases:
                    db.session.add(Alias(**a))
                db.session.commit()

        memory_response = memory_client.get('/aliases')
        disk_response = disk_client.get('/aliases')

        assert memory_response.status_code == disk_response.status_code
```

---

### Phase 7: Run Script Integration

#### Commit 7.1: Update run script to support --in-memory-db flag
**File**: `run.py`

```python
#!/usr/bin/env python3
# run.py
"""Legacy run script that delegates to main.py."""

from main import main

if __name__ == "__main__":
    main()
```

---

#### Commit 7.2: Add shell script wrapper with in-memory support
**File**: `run.sh`

```bash
#!/bin/bash
# run.sh - Convenience wrapper for running the application

# Default values
IN_MEMORY=""
PORT="5000"
HOST="127.0.0.1"
DEBUG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --in-memory-db)
            IN_MEMORY="--in-memory-db"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run the application
python main.py $IN_MEMORY --port "$PORT" --host "$HOST" $DEBUG
```

---

#### Commit 7.3: Add documentation for in-memory database usage
**File**: `docs/in_memory_database.md`

Create documentation explaining how to use the in-memory database feature.

---

### Phase 8: Test Migration and Cleanup

#### Commit 8.1: Update existing tests to use memory_db fixture
**File**: `tests/test_db_access.py`

Update existing database tests to explicitly use the memory database fixture for clarity.

---

#### Commit 8.2: Add pytest configuration for database tests
**File**: `pytest.ini` or `pyproject.toml`

```ini
[pytest]
markers =
    memory_db: mark test as using in-memory database
    db_equivalence: mark test as database equivalence test
    integration: mark test as integration test
```

---

#### Commit 8.3: Create test runner for equivalence tests
**File**: `run_equivalence_tests.py`

```python
#!/usr/bin/env python3
"""Run database equivalence tests."""

import subprocess
import sys

def main():
    cmd = [
        sys.executable, "-m", "pytest",
        "-m", "db_equivalence",
        "-v",
        "--tb=short"
    ]
    return subprocess.call(cmd)

if __name__ == "__main__":
    sys.exit(main())
```

---

#### Commit 8.4: Update CI configuration for equivalence tests
**File**: `.github/workflows/test.yml` (if exists)

Add a step to run equivalence tests in CI pipeline.

---

### Phase 9: Property-Based Equivalence Tests

#### Commit 9.1: Add Hypothesis strategies for models
**File**: `tests/property/strategies.py`

```python
# tests/property/strategies.py
"""Hypothesis strategies for database models."""

from hypothesis import strategies as st

# Strategy for server names
server_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() == x)

# Strategy for definitions
definitions = st.text(min_size=0, max_size=1000)

# Strategy for binary data
binary_data = st.binary(min_size=0, max_size=10000)

# Strategy for server data
server_data = st.fixed_dictionaries({
    "name": server_names,
    "definition": definitions,
    "enabled": st.booleans()
})
```

---

#### Commit 9.2: Add property-based equivalence tests
**File**: `tests/property/test_db_equivalence_property.py`

```python
# tests/property/test_db_equivalence_property.py
"""Property-based database equivalence tests."""

import pytest
from hypothesis import given, settings
from tests.property.strategies import server_data, binary_data
from models import Server, CID
from database import db

@pytest.mark.db_equivalence
class TestPropertyBasedEquivalence:
    """Property-based tests for database equivalence."""

    @given(data=server_data)
    @settings(max_examples=50)
    def test_server_roundtrip_equivalence(self, memory_db_app, disk_db_app, data):
        """Server data roundtrips equivalently in both databases."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                # Clear any existing data
                Server.query.delete()
                db.session.commit()

                # Create server
                server = Server(**data)
                db.session.add(server)
                db.session.commit()

                # Retrieve
                retrieved = Server.query.filter_by(name=data["name"]).first()
                results[name] = {
                    "name": retrieved.name,
                    "definition": retrieved.definition,
                    "enabled": retrieved.enabled
                }

        assert results["memory"] == results["disk"]

    @given(data=binary_data)
    @settings(max_examples=50)
    def test_binary_data_equivalence(self, memory_db_app, disk_db_app, data):
        """Binary data is stored equivalently in both databases."""
        results = {}

        for name, app in [("memory", memory_db_app), ("disk", disk_db_app)]:
            with app.app_context():
                CID.query.delete()
                db.session.commit()

                cid = CID(path="/cid/prop-test", file_data=data)
                db.session.add(cid)
                db.session.commit()

                retrieved = CID.query.filter_by(path="/cid/prop-test").first()
                results[name] = retrieved.file_data

        assert results["memory"] == results["disk"] == data
```

---

## Implementation Checklist

### Phase 1: Foundation and Configuration
- [ ] 1.1: Add database configuration module
- [ ] 1.2: Add tests for database configuration module
- [ ] 1.3: Integrate DatabaseConfig into app.py
- [ ] 1.4: Add command line argument parsing module
- [ ] 1.5: Add tests for CLI argument parsing
- [ ] 1.6: Create main entry point with CLI support

### Phase 2: Test Infrastructure
- [ ] 2.1: Add memory database test marker
- [ ] 2.2: Add memory database fixture
- [ ] 2.3: Add disk database fixture for comparison testing
- [ ] 2.4: Add database fixture factory

### Phase 3: Database Equivalence Tests
- [ ] 3.1: Create equivalence test base class
- [ ] 3.2: Add Server model equivalence tests
- [ ] 3.3: Add Alias model equivalence tests
- [ ] 3.4: Add Variable model equivalence tests
- [ ] 3.5: Add Secret model equivalence tests
- [ ] 3.6: Add CID model equivalence tests
- [ ] 3.7: Add PageView model equivalence tests
- [ ] 3.8: Add EntityInteraction model equivalence tests
- [ ] 3.9: Add ServerInvocation model equivalence tests
- [ ] 3.10: Add Export model equivalence tests

### Phase 4: db_access Module Equivalence Tests
- [ ] 4.1: Add generic_crud equivalence tests
- [ ] 4.2: Add servers module equivalence tests
- [ ] 4.3: Add aliases module equivalence tests
- [ ] 4.4: Add cids module equivalence tests
- [ ] 4.5: Add page_views module equivalence tests
- [ ] 4.6: Add interactions module equivalence tests
- [ ] 4.7: Add invocations module equivalence tests

### Phase 5: Transaction and Edge Case Tests
- [ ] 5.1: Add transaction rollback equivalence tests
- [ ] 5.2: Add concurrent access equivalence tests
- [ ] 5.3: Add NULL handling equivalence tests
- [ ] 5.4: Add special character equivalence tests
- [ ] 5.5: Add timestamp equivalence tests

### Phase 6: API Route Equivalence Tests
- [ ] 6.1: Add server routes equivalence tests
- [ ] 6.2: Add alias routes equivalence tests

### Phase 7: Run Script Integration
- [ ] 7.1: Update run script to support --in-memory-db flag
- [ ] 7.2: Add shell script wrapper with in-memory support
- [ ] 7.3: Add documentation for in-memory database usage

### Phase 8: Test Migration and Cleanup
- [ ] 8.1: Update existing tests to use memory_db fixture
- [ ] 8.2: Add pytest configuration for database tests
- [ ] 8.3: Create test runner for equivalence tests
- [ ] 8.4: Update CI configuration for equivalence tests

### Phase 9: Property-Based Equivalence Tests
- [ ] 9.1: Add Hypothesis strategies for models
- [ ] 9.2: Add property-based equivalence tests

---

## Usage Examples

### Running the Application with In-Memory Database

```bash
# Using Python directly
python main.py --in-memory-db

# Using the shell wrapper
./run.sh --in-memory-db

# With additional options
python main.py --in-memory-db --port 8080 --debug
```

### Running Tests

```bash
# Run all tests (uses in-memory by default)
python run_tests_clean.py

# Run only equivalence tests
python run_equivalence_tests.py

# Run specific test markers
pytest -m "db_equivalence" -v
pytest -m "memory_db" -v

# Run property-based tests
pytest tests/property/ -v
```

### Environment Variables

```bash
# Force disk database in tests
DATABASE_URL=sqlite:///test.db pytest

# Use in-memory for manual testing
DATABASE_URL=sqlite:///:memory: python app.py
```

---

## Benefits

1. **Test Isolation**: Each test runs with a fresh in-memory database
2. **Speed**: In-memory tests are significantly faster than disk-based tests
3. **Reliability**: No leftover state between test runs
4. **CI/CD Friendly**: No need to manage database files in CI
5. **Development**: Quick iteration during development
6. **Equivalence Guarantee**: Comprehensive tests ensure behavior parity

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| SQLite vs PostgreSQL differences | Test against PostgreSQL in CI with production-like config |
| In-memory lacks persistence | Clear documentation, warning on startup |
| Transaction isolation differences | Explicit isolation level tests |
| Performance characteristics differ | Document that in-memory is for testing only |

---

## Future Enhancements

1. **PostgreSQL In-Memory**: Support for PostgreSQL in-memory mode (using unlogged tables)
2. **Database Snapshots**: Ability to snapshot and restore in-memory state
3. **Test Data Fixtures**: Pre-populated test databases for specific scenarios
4. **Performance Benchmarks**: Compare in-memory vs disk performance metrics
