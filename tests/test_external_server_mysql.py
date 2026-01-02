from __future__ import annotations

from reference_templates.servers.definitions import mysql


def test_requires_host():
    result = mysql.main()
    assert result["output"]["error"] == "Missing MYSQL_HOST"
    assert result["output"]["status_code"] == 401


def test_requires_user():
    result = mysql.main(MYSQL_HOST="localhost")
    assert result["output"]["error"] == "Missing MYSQL_USER"
    assert result["output"]["status_code"] == 401


def test_requires_password():
    result = mysql.main(MYSQL_HOST="localhost", MYSQL_USER="user")
    assert result["output"]["error"] == "Missing MYSQL_PASSWORD"
    assert result["output"]["status_code"] == 401


def test_requires_database():
    result = mysql.main(MYSQL_HOST="localhost", MYSQL_USER="user", MYSQL_PASSWORD="pass")
    assert result["output"]["error"] == "Missing MYSQL_DATABASE"
    assert result["output"]["status_code"] == 401


def test_requires_query():
    result = mysql.main(
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
    )
    assert result["output"]["error"]["message"] == "Missing required query"


def test_invalid_operation():
    result = mysql.main(
        operation="invalid",
        query="SELECT * FROM users",
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_query():
    result = mysql.main(
        operation="query",
        query="SELECT * FROM users",
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "query"
    assert result["output"]["host"] == "localhost"
    assert result["output"]["database"] == "testdb"
    assert result["output"]["query"] == "SELECT * FROM users"


def test_dry_run_execute():
    result = mysql.main(
        operation="execute",
        query="INSERT INTO users (name) VALUES ('John')",
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "execute"


def test_dry_run_fetchone():
    result = mysql.main(
        operation="fetchone",
        query="SELECT * FROM users WHERE id = 1",
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "fetchone"


def test_dry_run_with_params():
    result = mysql.main(
        operation="query",
        query="SELECT * FROM users WHERE id = %s",
        params='[1]',
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["params"] == [1]


def test_invalid_params_json():
    result = mysql.main(
        operation="query",
        query="SELECT * FROM users",
        params='invalid json',
        MYSQL_HOST="localhost",
        MYSQL_USER="user",
        MYSQL_PASSWORD="pass",
        MYSQL_DATABASE="testdb",
        dry_run=True,
    )
    assert result["output"]["error"]["message"] == "Invalid JSON for params"
