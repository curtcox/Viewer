# Add Datasette and SQLite-Utils Servers
 
Status: Not implemented yet. No `reference_templates/servers/definitions/datasette.py` or `reference_templates/servers/definitions/sqlite_utils.py` present.

## Overview

This document outlines the plan for adding two new servers to the Viewer application:
- **datasette**: A web-based database browser for exploring SQLite databases
- **sqlite-utils**: A command-line tool and Python library for manipulating SQLite databases

Both servers should be mounted in the default boot template and support server chaining patterns.

## References

- Datasette: https://datasette.io/
- Datasette GitHub: https://github.com/simonw/datasette
- SQLite-Utils: https://sqlite-utils.datasette.io/en/stable/

---

## Prompt for AI Agents

When implementing the datasette and sqlite-utils servers, follow these steps:

### Implementation Order

1. **Dependencies First**: Add `datasette>=1.0` and `sqlite-utils>=3.36` to `requirements.txt` before any code changes.

2. **Server Definitions**: Create both server definition files in `reference_templates/servers/definitions/`:
   - `datasette.py` - Use proxy pattern (recommended) to run datasette subprocess
   - `sqlite_utils.py` - Use subprocess pattern similar to existing shell.py server

3. **Boot Template Integration**: Add both servers to `reference_templates/default.boot.source.json` and regenerate boot image.

4. **Testing Strategy**: Implement tests in this order:
   - Unit tests first (test server logic in isolation)
   - Integration tests second (test full request/response cycle)
   - Gauge specs last (test end-to-end behavior)

### Key Implementation Details

**For datasette.py:**
- Accept `database` parameter for chained input (binary SQLite data)
- Use proxy pattern: spawn datasette subprocess on available port
- Handle temp file creation/cleanup for chained database content
- Return HTML with iframe or redirect to datasette UI
- Clean up subprocess on request completion

**For sqlite_utils.py:**
- Accept `command` parameter for CLI operations
- Accept `database` parameter for chained input
- Show HTML form when no command provided
- Execute sqlite-utils CLI via subprocess
- Support output formats: json, csv, tsv, table
- Sanitize command input to prevent injection

**Chaining Support:**
- Both servers receive database content via `database` parameter
- Write binary content to temp file with `.db` suffix
- Use temp file path for datasette/sqlite-utils operations
- Clean up temp files after use

### Security Checklist

- [ ] Validate database file paths (no directory traversal)
- [ ] Sanitize sqlite-utils command input (prevent injection)
- [ ] Limit database file size from chained input (suggest 100MB max)
- [ ] Set timeout for subprocess operations (prevent hanging)
- [ ] Use read-only database access where possible

### Testing Requirements

Each server needs:
- 5+ unit tests covering: default DB, custom DB path, chained input, error handling
- 3+ integration tests covering: app DB usage, CID input, server chaining
- 2+ gauge specs covering: basic usage and chaining scenarios

---

## Requirements

### Datasette Server

1. **Name**: `datasette`
2. **URL Pattern**: `/datasette/`
3. **Default Behavior**: Browse the app database (`secureapp.db`)
4. **Chaining Support**: Accept DB contents from a following server or CID
   - `/datasette/{CID}` - Browse database from CID content
   - `/datasette/server_name` - Browse database from server output
   - `/datasette/server2/server1` - Browse database from chained servers
5. **Boot Template**: Mounted in `default.boot.source.json`

### SQLite-Utils Server

1. **Name**: `sqlite-utils`
2. **URL Pattern**: `/sqlite-utils/`
3. **Default Behavior**: Provide CLI/API access to the app database
4. **Chaining Support**: Accept DB contents from a following server or CID
   - `/sqlite-utils/{CID}` - Execute against database from CID
   - `/sqlite-utils/server_name` - Execute against database from server output
   - `/sqlite-utils/server2/server1` - Execute against chained servers
5. **Boot Template**: Mounted in `default.boot.source.json`

### Testing Coverage

1. **Unit Tests**: Core functionality and logic
2. **Integration Tests**: Full request/response cycle
3. **Gauge Specs**: End-to-end behavior verification

## Implementation Plan

### Phase 1: Dependencies and Environment Setup

#### 1.1 Add Python Package Dependencies

**Files to modify:**
- `requirements.txt` (or equivalent)

**Actions:**
```
datasette>=1.0
sqlite-utils>=3.36
```

**Notes:**
- Datasette requires Python 3.8+
- SQLite-Utils is a dependency of Datasette but should be explicitly listed
- Check compatibility with existing Flask/SQLAlchemy versions

#### 1.2 Verify Package Installation

**Testing approach:**
- Run pip install locally
- Verify datasette CLI is available
- Verify sqlite-utils CLI is available
- Check for any dependency conflicts

### Phase 2: Server Definition Implementation

#### 2.1 Create Datasette Server Definition

**File:** `reference_templates/servers/definitions/datasette.py`

**Implementation approach:**
```python
# ruff: noqa: F821, F706
"""Datasette server for browsing SQLite databases."""

import os
import tempfile
from pathlib import Path
from datasette.app import Datasette
import asyncio

def get_app_database_path() -> str:
    """Return the path to the app database."""
    # Check for DATABASE_URL environment variable
    db_url = os.environ.get("DATABASE_URL", "sqlite:///secureapp.db")
    # Extract path from SQLite URL
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "secureapp.db"

async def create_datasette_app(db_path: str, base_url: str = "/datasette"):
    """Create a Datasette app instance."""
    return Datasette(
        files=[db_path],
        settings={
            "base_url": base_url,
            "default_page_size": 100,
        }
    )

def main(
    database: str = "",
    endpoint: str | None = None,
    path_info: str = "",
    _context: object | None = None,
) -> dict[str, str]:
    """
    Serve Datasette for database browsing.

    Args:
        database: Path to database file or database content from chained input
        endpoint: The server mount point (default: /datasette)
        path_info: The path after the server mount
        _context: Viewer context (contains app DB path)

    Returns:
        Dict with 'output' and 'content_type' keys
    """

    # Determine database path
    if database:
        # Database content provided (from chained input)
        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.db',
            delete=False
        ) as tmp_db:
            if isinstance(database, str):
                tmp_db.write(database.encode('latin-1'))
            else:
                tmp_db.write(database)
            db_path = tmp_db.name
    else:
        # Use app database
        db_path = get_app_database_path()

    # Verify database exists
    if not Path(db_path).exists():
        return {
            "output": f"Database not found: {db_path}",
            "content_type": "text/plain",
        }

    # Parse path to extract datasette route
    datasette_endpoint = endpoint or "/datasette"
    datasette_path = path_info.lstrip("/")

    # Create and run datasette
    try:
        ds = asyncio.run(create_datasette_app(db_path, datasette_endpoint))

        # Return HTML with iframe or redirect to datasette UI
        # For now, return simple HTML with link
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Datasette - Database Browser</title>
        </head>
        <body>
            <h1>Datasette Database Browser</h1>
            <p>Database: {db_path}</p>
            <p><a href="{datasette_endpoint}/">Open Datasette</a></p>
        </body>
        </html>
        """

        return {
            "output": html,
            "content_type": "text/html",
        }
    except Exception as e:
        return {
            "output": f"Error starting Datasette: {str(e)}",
            "content_type": "text/plain",
        }
```

**Design considerations:**
- Datasette is an ASGI app, not WSGI - requires special handling
- May need to run Datasette as a subprocess or use ASGI-WSGI adapter
- Should support both direct database path and chained input
- Needs to handle temporary database files from chained content
- Must properly clean up temporary files

**Alternative approaches to evaluate:**
1. **Subprocess approach**: Run datasette CLI as subprocess (similar to shell.py)
2. **ASGI adapter**: Use asgiref.wsgi.WsgiToAsgi adapter
3. **Proxy approach**: Run datasette on localhost port and proxy requests (similar to proxy.py)

**Recommended approach**: Proxy approach
- Most reliable and maintainable
- Allows datasette to run in its natural environment
- Similar pattern to existing proxy server

#### 2.2 Create SQLite-Utils Server Definition

**File:** `reference_templates/servers/definitions/sqlite_utils.py`

**Implementation approach:**
```python
# ruff: noqa: F821, F706
"""SQLite-Utils server for database manipulation."""

import os
import tempfile
import subprocess
import json
from pathlib import Path
from html import escape

def get_app_database_path() -> str:
    """Return the path to the app database."""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///secureapp.db")
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "secureapp.db"

def main(
    command: str = "",
    database: str = "",
    format: str = "json",
    endpoint: str | None = None,
    _context: object | None = None,
) -> dict[str, str]:
    """
    Execute sqlite-utils commands against a database.

    Args:
        command: sqlite-utils command to execute (e.g., "tables", "query 'SELECT * FROM users'")
        database: Path to database file or database content from chained input
        format: Output format (json, csv, tsv, table)
        endpoint: The server mount point (default: /sqlite-utils)
        _context: Viewer context (contains app DB path)

    Returns:
        Dict with 'output' and 'content_type' keys
    """

    # Determine database path
    if database:
        # Database content provided (from chained input)
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.db',
            delete=False
        ) as tmp_db:
            if isinstance(database, str):
                tmp_db.write(database.encode('latin-1'))
            else:
                tmp_db.write(database)
            db_path = tmp_db.name
    else:
        # Use app database
        db_path = get_app_database_path()

    # Verify database exists
    if not Path(db_path).exists():
        return {
            "output": f"Database not found: {db_path}",
            "content_type": "text/plain",
        }

    sqlite_utils_endpoint = endpoint or "/sqlite-utils"

    # If no command, show form
    if not command:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SQLite-Utils</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                input[type="text"] {{ width: 600px; padding: 5px; }}
                select {{ padding: 5px; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>SQLite-Utils</h1>
            <p>Database: {escape(db_path)}</p>

            <form method="post" action="{escape(sqlite_utils_endpoint, quote=True)}">
                <div>
                    <input type="text" name="command" placeholder="tables" autofocus>
                    <select name="format">
                        <option value="json">JSON</option>
                        <option value="csv">CSV</option>
                        <option value="tsv">TSV</option>
                        <option value="table">Table</option>
                    </select>
                    <button type="submit">Execute</button>
                </div>
            </form>

            <h3>Common Commands:</h3>
            <ul>
                <li><code>tables</code> - List all tables</li>
                <li><code>tables --counts</code> - List tables with row counts</li>
                <li><code>rows TABLE_NAME</code> - Show rows from a table</li>
                <li><code>schema TABLE_NAME</code> - Show table schema</li>
                <li><code>query "SELECT * FROM table_name LIMIT 10"</code> - Run SQL query</li>
            </ul>
        </body>
        </html>
        """
        return {
            "output": html,
            "content_type": "text/html",
        }

    # Execute sqlite-utils command
    try:
        # Build command
        cmd_parts = ["sqlite-utils", db_path]

        # Parse command string into parts
        cmd_parts.extend(command.split())

        # Add format flag if applicable
        if format != "json" and format in ["csv", "tsv", "table"]:
            cmd_parts.append(f"--{format}")

        # Run command
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout if result.returncode == 0 else result.stderr

        # Determine content type based on format
        content_types = {
            "json": "application/json",
            "csv": "text/csv",
            "tsv": "text/tab-separated-values",
            "table": "text/plain",
        }
        content_type = content_types.get(format, "text/plain")

        # Wrap in HTML if error
        if result.returncode != 0:
            html_output = f"""
            <!DOCTYPE html>
            <html>
            <body>
                <h2>Error executing command</h2>
                <pre>{escape(output)}</pre>
                <p><a href="{escape(sqlite_utils_endpoint)}">Back</a></p>
            </body>
            </html>
            """
            return {
                "output": html_output,
                "content_type": "text/html",
            }

        return {
            "output": output,
            "content_type": content_type,
        }

    except Exception as e:
        return {
            "output": f"Error: {str(e)}",
            "content_type": "text/plain",
        }
```

**Design considerations:**
- SQLite-Utils is primarily a CLI tool - subprocess approach is natural
- Should support common operations: tables, rows, schema, query
- Output format options: JSON, CSV, TSV, table
- Similar pattern to shell.py server
- Needs input sanitization for security

#### 2.3 Handle Server Chaining

**Key integration points:**

Both servers need to handle chained input properly by accepting the `chained_input` parameter that the Viewer runtime provides.

**Pattern to follow** (from code_execution.py):
```python
def main(
    database: str = "",  # This receives chained_input
    _context: object | None = None,
) -> dict[str, str]:
    # If database content provided via chaining
    if database:
        # Handle as binary content
        # Write to temp file
        pass
```

**Server chaining scenarios to test:**
1. `/datasette/{CID}` - CID contains SQLite database binary
2. `/datasette/db_generator` - Server returns SQLite database
3. `/sqlite-utils/rows users/{CID}` - Execute against DB from CID
4. `/sqlite-utils/schema/{CID}` - Show schema of DB from CID

### Phase 3: Boot Template Integration

#### 3.1 Add to Default Boot Template

**File:** `reference_templates/default.boot.source.json`

**Changes:**
```json
{
  "version": 6,
  "servers": [
    // ... existing servers ...
    {
      "name": "datasette",
      "definition_cid": "reference_templates/servers/definitions/datasette.py",
      "enabled": true
    },
    {
      "name": "sqlite-utils",
      "definition_cid": "reference_templates/servers/definitions/sqlite_utils.py",
      "enabled": true
    }
  ]
}
```

**Note:** Order matters - add after existing servers to maintain compatibility

#### 3.2 Regenerate Boot Image

**Command:**
```bash
python generate_boot_image.py
```

**Files affected:**
- `reference_templates/default.boot.json` - Generated with CIDs
- `cids/` - New CID entries for server definitions

#### 3.3 Verify Boot Template

**Validation steps:**
1. Check that boot.json contains new server entries
2. Verify CIDs are generated correctly
3. Ensure server definitions are stored in CID storage
4. Test loading the boot template in a fresh instance

### Phase 4: Unit Tests

#### 4.1 Datasette Server Unit Tests

**File:** `tests/test_datasette_server.py`

**Test cases:**
```python
import unittest
from pathlib import Path
import tempfile
import sqlite3

class TestDatasetteSerer(unittest.TestCase):
    """Test datasette server functionality."""

    def setUp(self):
        """Create a test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        # Create test schema
        conn = sqlite3.connect(self.temp_db.name)
        conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('INSERT INTO users VALUES (1, "Alice")')
        conn.execute('INSERT INTO users VALUES (2, "Bob")')
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test database."""
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_datasette_server_with_default_database(self):
        """Test datasette server uses app database by default."""
        # Test implementation
        pass

    def test_datasette_server_with_custom_database_path(self):
        """Test datasette server with explicit database path."""
        pass

    def test_datasette_server_with_chained_database_content(self):
        """Test datasette server receives database from chained input."""
        pass

    def test_datasette_server_database_not_found(self):
        """Test datasette server handles missing database."""
        pass

    def test_datasette_server_invalid_database_content(self):
        """Test datasette server handles invalid database content."""
        pass
```

**Test coverage targets:**
- Default database path resolution
- Custom database path handling
- Chained input (binary database content)
- Error handling (missing DB, invalid content)
- HTML output generation
- Endpoint configuration

#### 4.2 SQLite-Utils Server Unit Tests

**File:** `tests/test_sqlite_utils_server.py`

**Test cases:**
```python
import unittest
from pathlib import Path
import tempfile
import sqlite3

class TestSqliteUtilsServer(unittest.TestCase):
    """Test sqlite-utils server functionality."""

    def setUp(self):
        """Create a test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()

        conn = sqlite3.connect(self.temp_db.name)
        conn.execute('CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)')
        conn.execute('INSERT INTO products VALUES (1, "Widget", 9.99)')
        conn.execute('INSERT INTO products VALUES (2, "Gadget", 19.99)')
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test database."""
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_sqlite_utils_no_command_shows_form(self):
        """Test sqlite-utils server shows form when no command provided."""
        pass

    def test_sqlite_utils_tables_command(self):
        """Test sqlite-utils 'tables' command."""
        pass

    def test_sqlite_utils_rows_command(self):
        """Test sqlite-utils 'rows TABLE' command."""
        pass

    def test_sqlite_utils_schema_command(self):
        """Test sqlite-utils 'schema TABLE' command."""
        pass

    def test_sqlite_utils_query_command(self):
        """Test sqlite-utils 'query' command."""
        pass

    def test_sqlite_utils_with_chained_database(self):
        """Test sqlite-utils with database from chained input."""
        pass

    def test_sqlite_utils_output_format_json(self):
        """Test sqlite-utils JSON output format."""
        pass

    def test_sqlite_utils_output_format_csv(self):
        """Test sqlite-utils CSV output format."""
        pass

    def test_sqlite_utils_invalid_command(self):
        """Test sqlite-utils handles invalid commands."""
        pass

    def test_sqlite_utils_database_not_found(self):
        """Test sqlite-utils handles missing database."""
        pass
```

**Test coverage targets:**
- Form rendering (no command)
- Command execution (tables, rows, schema, query)
- Output formats (JSON, CSV, TSV, table)
- Chained input handling
- Error handling
- Database path resolution

#### 4.3 Server Chaining Logic Unit Tests

**File:** `tests/test_datasette_sqlite_chaining.py`

**Test cases:**
```python
import unittest

class TestDatabaseServerChaining(unittest.TestCase):
    """Test chaining behavior for database servers."""

    def test_datasette_receives_cid_database(self):
        """Test datasette server receives database from CID."""
        pass

    def test_datasette_receives_server_database(self):
        """Test datasette server receives database from another server."""
        pass

    def test_sqlite_utils_receives_cid_database(self):
        """Test sqlite-utils receives database from CID."""
        pass

    def test_sqlite_utils_receives_server_database(self):
        """Test sqlite-utils receives database from another server."""
        pass

    def test_chained_server_creates_and_passes_database(self):
        """Test a server that creates a database can pass it to datasette."""
        pass
```

### Phase 5: Integration Tests

#### 5.1 Datasette Integration Tests

**File:** `tests/integration/test_datasette_integration.py`

**Test cases:**
```python
import pytest

def test_datasette_default_database_browsing(client, integration_app):
    """Test browsing the default app database with datasette."""
    response = client.get("/datasette/")
    assert response.status_code in {200, 302, 303}
    # Verify can browse database

def test_datasette_with_cid_database(client, integration_app):
    """Test datasette with database from CID."""
    # Store a database as CID
    # Request /datasette/{CID}
    # Verify database is browsable
    pass

def test_datasette_with_chained_server(client, integration_app):
    """Test datasette receives database from another server."""
    # Create a server that outputs a database
    # Request /datasette/db_generator_server
    # Verify database is browsable
    pass

def test_datasette_multi_table_database(client, integration_app):
    """Test datasette with multi-table database."""
    pass

def test_datasette_empty_database(client, integration_app):
    """Test datasette with empty database."""
    pass
```

#### 5.2 SQLite-Utils Integration Tests

**File:** `tests/integration/test_sqlite_utils_integration.py`

**Test cases:**
```python
import pytest

def test_sqlite_utils_form_display(client, integration_app):
    """Test sqlite-utils displays form when accessed without command."""
    response = client.get("/sqlite-utils")
    assert response.status_code == 200
    assert b"sqlite-utils" in response.data.lower()
    assert b"<form" in response.data

def test_sqlite_utils_list_tables(client, integration_app):
    """Test listing tables from app database."""
    response = client.post("/sqlite-utils", data={"command": "tables"})
    # Verify tables are listed
    pass

def test_sqlite_utils_query_execution(client, integration_app):
    """Test executing a SQL query."""
    response = client.post("/sqlite-utils", data={
        "command": 'query "SELECT * FROM servers LIMIT 5"',
        "format": "json"
    })
    # Verify query results
    pass

def test_sqlite_utils_with_cid_database(client, integration_app):
    """Test sqlite-utils with database from CID."""
    pass

def test_sqlite_utils_csv_output(client, integration_app):
    """Test sqlite-utils CSV output format."""
    pass

def test_sqlite_utils_invalid_sql(client, integration_app):
    """Test sqlite-utils handles invalid SQL gracefully."""
    pass
```

#### 5.3 Cross-Server Integration Tests

**File:** `tests/integration/test_database_server_interaction.py`

**Test cases:**
```python
import pytest

def test_create_database_with_sqlite_utils_browse_with_datasette(client, integration_app):
    """Test creating a database with sqlite-utils and browsing with datasette."""
    pass

def test_server_generates_database_for_datasette(client, integration_app):
    """Test a custom server generates a database that datasette can browse."""
    pass

def test_both_servers_work_with_same_cid_database(client, integration_app):
    """Test both servers can work with the same CID database."""
    pass
```

### Phase 6: Gauge Specs (End-to-End Tests)

#### 6.1 Datasette Gauge Specs

**File:** `specs/datasette_server.spec`

**Content:**
```gherkin
# Datasette Server

These tests verify the datasette server can browse SQLite databases.

## Datasette browses default app database
* Given the default server "datasette" is available
* When I request the resource /datasette/
* Then the response should contain "Database"
* And the response should contain "tables"

## Datasette receives CID database as input
* Given a CID containing a SQLite database with a "test_users" table
* When I request the resource /datasette/{stored CID}
* Then the response should redirect to a CID or return HTML
* And the response should allow browsing the database
* And the database should contain the "test_users" table

## Datasette receives database from chained server
* Given a server named "db_creator" that returns a SQLite database
* When I request the resource /datasette/db_creator
* Then the response should allow browsing the generated database

## Datasette chains with another server to receive database
* Given a server named "inner" that returns a SQLite database
* And a server named "modifier" that passes through its input
* When I request the resource /datasette/modifier/inner
* Then the response should allow browsing the database
* And the database should be accessible through datasette

## Datasette handles empty database
* Given a CID containing an empty SQLite database
* When I request the resource /datasette/{stored CID}
* Then the response should show an empty database
* And the response should not show any errors

## Datasette handles missing database
* When I request the resource /datasette with an invalid database path
* Then the response should show a "not found" error message
```

#### 6.2 SQLite-Utils Gauge Specs

**File:** `specs/sqlite_utils_server.spec`

**Content:**
```gherkin
# SQLite-Utils Server

These tests verify the sqlite-utils server can manipulate SQLite databases.

## SQLite-utils shows form without command
* Given the default server "sqlite-utils" is available
* When I request the resource /sqlite-utils
* Then the response should contain a form
* And the response should contain input for command
* And the response should list common commands

## SQLite-utils lists tables from app database
* Given the default server "sqlite-utils" is available
* When I request the resource /sqlite-utils with command "tables"
* Then the response should list database tables
* And the response should include "servers"
* And the response should include "aliases"

## SQLite-utils executes query on app database
* Given the default server "sqlite-utils" is available
* When I request the resource /sqlite-utils with command "query 'SELECT name FROM servers LIMIT 3'"
* Then the response should show query results
* And the response format should be JSON

## SQLite-utils receives CID database as input
* Given a CID containing a SQLite database with a "products" table
* When I request the resource /sqlite-utils/tables/{stored CID}
* Then the response should list "products" table

## SQLite-utils receives database from chained server
* Given a server named "db_generator" that returns a SQLite database
* When I request the resource /sqlite-utils/tables/db_generator
* Then the response should list tables from the generated database

## SQLite-utils outputs CSV format
* Given the default server "sqlite-utils" is available
* When I request the resource /sqlite-utils with command "rows servers" and format "csv"
* Then the response content-type should be "text/csv"
* And the response should contain comma-separated values

## SQLite-utils handles invalid SQL
* Given the default server "sqlite-utils" is available
* When I request the resource /sqlite-utils with command "query 'INVALID SQL'"
* Then the response should show an error message
* And the error message should explain the SQL problem

## SQLite-utils chains with server output
* Given a server named "inner" that returns a SQLite database
* And the default server "sqlite-utils" is available
* When I request the resource /sqlite-utils/schema users/inner
* Then the response should show the schema for the "users" table
```

#### 6.3 Combined Database Server Gauge Specs

**File:** `specs/database_server_integration.spec`

**Content:**
```gherkin
# Database Server Integration

These tests verify datasette and sqlite-utils servers work together and with other servers.

## Both servers work with same CID database
* Given a CID containing a SQLite database with "employees" table
* When I request the resource /datasette/{stored CID}
* Then the response should allow browsing the database
* When I request the resource /sqlite-utils/tables/{stored CID}
* Then the response should list "employees" table

## Server chain creates and browses database
* Given a server named "db_builder" that creates a SQLite database
* When I request the resource /datasette/db_builder
* Then the response should allow browsing the generated database
* When I request the resource /sqlite-utils/tables/db_builder
* Then the response should list tables from the same database

## Three-level chain with database generation
* Given a server named "data_source" that returns CSV data
* And a server named "csv_to_db" that converts CSV to SQLite
* When I request the resource /datasette/csv_to_db/data_source
* Then the response should allow browsing the converted database
```

### Phase 7: Gauge Step Implementations

#### 7.1 Datasette Step Implementations

**File:** `step_impl/datasette_steps.py`

**Key step implementations:**
```python
from getgauge.python import step
import sqlite3
import tempfile
from pathlib import Path

@step("a CID containing a SQLite database with a <table_name> table")
def create_cid_with_database(table_name):
    """Create a CID containing a SQLite database."""
    # Implementation
    pass

@step("the response should allow browsing the database")
def verify_datasette_browsing():
    """Verify datasette allows database browsing."""
    pass

@step("the database should contain the <table_name> table")
def verify_table_exists(table_name):
    """Verify table exists in browsable database."""
    pass
```

#### 7.2 SQLite-Utils Step Implementations

**File:** `step_impl/sqlite_utils_steps.py`

**Key step implementations:**
```python
from getgauge.python import step

@step("I request the resource /sqlite-utils with command <command>")
def request_sqlite_utils_with_command(command):
    """Request sqlite-utils with specific command."""
    pass

@step("the response should list database tables")
def verify_tables_listed():
    """Verify tables are listed in response."""
    pass

@step("the response format should be JSON")
def verify_json_format():
    """Verify response is valid JSON."""
    pass

@step("I request the resource /sqlite-utils with command <command> and format <format>")
def request_sqlite_utils_with_format(command, format):
    """Request sqlite-utils with command and output format."""
    pass
```

### Phase 8: Documentation

#### 8.1 Update Server Documentation

**Files to update:**
- README.md (if exists)
- docs/servers.md (if exists)
- Reference documentation for servers

**Documentation should include:**
- Overview of datasette and sqlite-utils servers
- Usage examples
- URL patterns
- Chaining examples
- Common use cases

#### 8.2 Add Example Use Cases

**Example 1: Browse app database**
```
/datasette/
```

**Example 2: Inspect a database CID**
```
/datasette/{CID}
```

**Example 3: Query database with sqlite-utils**
```
/sqlite-utils?command=tables
```

**Example 4: Generate and browse a database**
```
/datasette/db_generator
```

**Example 5: Chain multiple operations**
```
/datasette/csv_to_db/data_source
```

### Phase 9: Security Considerations

#### 9.1 Input Validation

**Datasette server:**
- Validate database file paths
- Sanitize path parameters
- Prevent directory traversal
- Limit database file size from chained input

**SQLite-Utils server:**
- Sanitize command input
- Prevent command injection
- Validate SQL queries
- Restrict dangerous operations (DROP, DELETE without WHERE)
- Limit output size

#### 9.2 Resource Limits

- Set timeout for datasette operations
- Limit subprocess execution time for sqlite-utils
- Prevent excessive memory usage from large databases
- Clean up temporary database files

#### 9.3 Access Control

- Consider if datasette/sqlite-utils should have read-only access
- Document security implications of exposing database browser
- Consider adding authentication/authorization checks

### Phase 10: Performance Considerations

#### 10.1 Caching

- Consider caching datasette app instances
- Cache database metadata for sqlite-utils
- Implement request caching where appropriate

#### 10.2 Resource Management

- Properly clean up temporary database files
- Limit concurrent datasette instances
- Monitor memory usage with large databases

#### 10.3 Optimization

- Use datasette's built-in caching mechanisms
- Optimize database queries in sqlite-utils
- Consider connection pooling

## Testing Checklist

### Unit Tests
- [ ] Datasette server basic functionality
- [ ] Datasette server with default database
- [ ] Datasette server with custom database
- [ ] Datasette server with chained input
- [ ] Datasette server error handling
- [ ] SQLite-utils server form rendering
- [ ] SQLite-utils server command execution (tables, rows, schema, query)
- [ ] SQLite-utils server output formats (JSON, CSV, TSV, table)
- [ ] SQLite-utils server with chained input
- [ ] SQLite-utils server error handling
- [ ] Database path resolution logic
- [ ] Temporary file management

### Integration Tests
- [ ] Datasette browses app database end-to-end
- [ ] Datasette browses CID database end-to-end
- [ ] Datasette receives database from server chain
- [ ] SQLite-utils executes commands on app database
- [ ] SQLite-utils executes commands on CID database
- [ ] SQLite-utils receives database from server chain
- [ ] Both servers work with same database
- [ ] Multi-level server chaining with databases
- [ ] Error handling in full request cycle

### Gauge Specs
- [ ] All datasette gauge scenarios pass
- [ ] All sqlite-utils gauge scenarios pass
- [ ] All combined integration gauge scenarios pass
- [ ] Chaining patterns verified end-to-end
- [ ] Error cases verified end-to-end

## Acceptance Criteria

### Datasette Server
1. ✅ Server named "datasette" exists in default boot template
2. ✅ Accessible via URLs under `/datasette/`
3. ✅ Browses app database (`secureapp.db`) by default
4. ✅ Accepts database from CID: `/datasette/{CID}`
5. ✅ Accepts database from chained server: `/datasette/server_name`
6. ✅ Accepts database from multi-level chain: `/datasette/s2/s1`
7. ✅ Handles missing database gracefully
8. ✅ Handles invalid database content gracefully
9. ✅ All unit tests pass
10. ✅ All integration tests pass
11. ✅ All gauge specs pass

### SQLite-Utils Server
1. ✅ Server named "sqlite-utils" exists in default boot template
2. ✅ Accessible via URLs under `/sqlite-utils/`
3. ✅ Uses app database (`secureapp.db`) by default
4. ✅ Shows form UI when no command provided
5. ✅ Executes commands: tables, rows, schema, query
6. ✅ Supports output formats: JSON, CSV, TSV, table
7. ✅ Accepts database from CID: `/sqlite-utils/{CID}`
8. ✅ Accepts database from chained server: `/sqlite-utils/server_name`
9. ✅ Accepts database from multi-level chain: `/sqlite-utils/s2/s1`
10. ✅ Handles invalid commands gracefully
11. ✅ Handles invalid SQL gracefully
12. ✅ All unit tests pass
13. ✅ All integration tests pass
14. ✅ All gauge specs pass

### General
1. ✅ Both servers are in default boot template
2. ✅ Boot image regenerates correctly
3. ✅ Dependencies installed correctly
4. ✅ No security vulnerabilities introduced
5. ✅ Documentation updated
6. ✅ All tests pass in CI/CD pipeline

## Open Questions

1. **Datasette ASGI handling**: What's the best approach for integrating Datasette's ASGI app?
   - Options: subprocess, ASGI adapter, proxy pattern
   - Recommendation: Evaluate each approach with prototype

2. **Database size limits**: Should we limit the size of databases from chained input?
   - Consider: Memory usage, performance, security
   - Recommendation: Start with reasonable limit (e.g., 100MB)

3. **Read-only access**: Should these servers have read-only access to the app database?
   - Pro: Prevents accidental modifications
   - Con: Limits sqlite-utils functionality
   - Recommendation: Start with read-only, add write capability later if needed

4. **Authentication**: Should these servers require authentication?
   - Consider: Security model of the Viewer app
   - Recommendation: Follow existing server authentication patterns

5. **Concurrent access**: How to handle multiple concurrent datasette instances?
   - Consider: Resource usage, connection limits
   - Recommendation: Implement instance pooling or connection limits

## Implementation Timeline

**Phase 1-2 (Setup & Implementation)**: Foundation work
**Phase 3 (Boot Template)**: Integration with existing system
**Phase 4-5 (Testing)**: Core test coverage
**Phase 6-7 (Gauge Specs)**: End-to-end verification
**Phase 8-10 (Polish)**: Documentation, security, performance

## Success Metrics

1. Both servers successfully added to default boot template
2. All tests passing (100% of unit, integration, and gauge tests)
3. No performance regression in existing servers
4. No security vulnerabilities introduced
5. Documentation complete and accurate
6. Positive user feedback on database browsing capabilities

## References

- Server execution logic: `server_execution/code_execution.py`
- Server chaining: `server_execution/server_lookup.py`
- Existing server examples: `reference_templates/servers/definitions/`
- Test patterns: `tests/test_server_*.py`
- Gauge specs: `specs/server_*.spec`
- Boot template: `reference_templates/default.boot.source.json`
- Database config: `db_config.py`
