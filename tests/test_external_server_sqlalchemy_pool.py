from __future__ import annotations

from reference_templates.servers.definitions import sqlalchemy_pool


def test_requires_database_url():
    result = sqlalchemy_pool.main()
    assert result["output"]["error"] == "Missing DATABASE_URL"
    assert result["output"]["status_code"] == 401


def test_requires_query():
    result = sqlalchemy_pool.main(DATABASE_URL="postgresql://user:pass@localhost/testdb")
    assert result["output"]["error"]["message"] == "Missing required query"


def test_invalid_operation():
    result = sqlalchemy_pool.main(
        operation="invalid",
        query="SELECT * FROM users",
        DATABASE_URL="postgresql://user:pass@localhost/testdb",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_query():
    result = sqlalchemy_pool.main(
        operation="query",
        query="SELECT * FROM users",
        DATABASE_URL="postgresql://user:pass@localhost/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "query"
    assert result["output"]["query"] == "SELECT * FROM users"
    # Check credentials are hidden
    assert "***" in result["output"]["database_url"]


def test_dry_run_execute():
    result = sqlalchemy_pool.main(
        operation="execute",
        query="INSERT INTO users (name) VALUES ('John')",
        DATABASE_URL="mysql://user:pass@localhost/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "execute"


def test_dry_run_with_params():
    result = sqlalchemy_pool.main(
        operation="query",
        query="SELECT * FROM users WHERE id = :id",
        params='{"id": 1}',
        DATABASE_URL="postgresql://user:pass@localhost/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["params"] == {"id": 1}


def test_invalid_params_json():
    result = sqlalchemy_pool.main(
        operation="query",
        query="SELECT * FROM users",
        params='invalid json',
        DATABASE_URL="postgresql://user:pass@localhost/testdb",
        dry_run=True,
    )
    assert result["output"]["error"]["message"] == "Invalid JSON for params"


def test_hides_credentials_in_preview():
    result = sqlalchemy_pool.main(
        operation="query",
        query="SELECT 1",
        DATABASE_URL="postgresql://myuser:mypassword@localhost:5432/mydb",
        dry_run=True,
    )
    assert "output" in result
    assert "mypassword" not in result["output"]["database_url"]
    assert "***" in result["output"]["database_url"]
    assert "localhost:5432/mydb" in result["output"]["database_url"]


def test_sqlite_url():
    result = sqlalchemy_pool.main(
        operation="query",
        query="SELECT 1",
        DATABASE_URL="sqlite:///test.db",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["database_url"] == "sqlite:///test.db"


def test_mysql_url():
    result = sqlalchemy_pool.main(
        operation="query",
        query="SELECT 1",
        DATABASE_URL="mysql://user:pass@host:3306/db",
        dry_run=True,
    )
    assert "output" in result
    assert "***" in result["output"]["database_url"]
