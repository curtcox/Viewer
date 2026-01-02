from __future__ import annotations

from reference_templates.servers.definitions import postgresql


def test_requires_host():
    result = postgresql.main()
    assert result["output"]["error"] == "Missing POSTGRESQL_HOST"
    assert result["output"]["status_code"] == 401


def test_requires_user():
    result = postgresql.main(POSTGRESQL_HOST="localhost")
    assert result["output"]["error"] == "Missing POSTGRESQL_USER"
    assert result["output"]["status_code"] == 401


def test_requires_password():
    result = postgresql.main(POSTGRESQL_HOST="localhost", POSTGRESQL_USER="user")
    assert result["output"]["error"] == "Missing POSTGRESQL_PASSWORD"
    assert result["output"]["status_code"] == 401


def test_requires_database():
    result = postgresql.main(POSTGRESQL_HOST="localhost", POSTGRESQL_USER="user", POSTGRESQL_PASSWORD="pass")
    assert result["output"]["error"] == "Missing POSTGRESQL_DATABASE"
    assert result["output"]["status_code"] == 401


def test_requires_query():
    result = postgresql.main(
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
    )
    assert result["output"]["error"]["message"] == "Missing required query"


def test_invalid_operation():
    result = postgresql.main(
        operation="invalid",
        query="SELECT * FROM users",
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_query():
    result = postgresql.main(
        operation="query",
        query="SELECT * FROM users",
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "query"
    assert result["output"]["host"] == "localhost"
    assert result["output"]["database"] == "testdb"
    assert result["output"]["query"] == "SELECT * FROM users"


def test_dry_run_execute():
    result = postgresql.main(
        operation="execute",
        query="INSERT INTO users (name) VALUES ('John')",
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "execute"


def test_dry_run_fetchone():
    result = postgresql.main(
        operation="fetchone",
        query="SELECT * FROM users WHERE id = 1",
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "fetchone"


def test_dry_run_with_params():
    result = postgresql.main(
        operation="query",
        query="SELECT * FROM users WHERE id = %s",
        params='[1]',
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["params"] == [1]


def test_invalid_params_json():
    result = postgresql.main(
        operation="query",
        query="SELECT * FROM users",
        params='invalid json',
        POSTGRESQL_HOST="localhost",
        POSTGRESQL_USER="user",
        POSTGRESQL_PASSWORD="pass",
        POSTGRESQL_DATABASE="testdb",
        dry_run=True,
    )
    assert result["output"]["error"]["message"] == "Invalid JSON for params"
