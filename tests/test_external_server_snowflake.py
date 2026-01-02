from __future__ import annotations

from reference_templates.servers.definitions import snowflake


def test_requires_account():
    result = snowflake.main()
    assert result["output"]["error"] == "Missing SNOWFLAKE_ACCOUNT"
    assert result["output"]["status_code"] == 401


def test_requires_user():
    result = snowflake.main(SNOWFLAKE_ACCOUNT="myaccount")
    assert result["output"]["error"] == "Missing SNOWFLAKE_USER"
    assert result["output"]["status_code"] == 401


def test_requires_password():
    result = snowflake.main(SNOWFLAKE_ACCOUNT="myaccount", SNOWFLAKE_USER="user")
    assert result["output"]["error"] == "Missing SNOWFLAKE_PASSWORD"
    assert result["output"]["status_code"] == 401


def test_requires_warehouse():
    result = snowflake.main(
        SNOWFLAKE_ACCOUNT="myaccount",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="pass",
    )
    assert result["output"]["error"] == "Missing SNOWFLAKE_WAREHOUSE"
    assert result["output"]["status_code"] == 401


def test_requires_query():
    result = snowflake.main(
        SNOWFLAKE_ACCOUNT="myaccount",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="pass",
        SNOWFLAKE_WAREHOUSE="warehouse",
    )
    assert result["output"]["error"]["message"] == "Missing required query"


def test_invalid_operation():
    result = snowflake.main(
        operation="invalid",
        query="SELECT 1",
        SNOWFLAKE_ACCOUNT="myaccount",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="pass",
        SNOWFLAKE_WAREHOUSE="warehouse",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_query():
    result = snowflake.main(
        operation="query",
        query="SELECT * FROM users",
        SNOWFLAKE_ACCOUNT="myaccount",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="pass",
        SNOWFLAKE_WAREHOUSE="warehouse",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "query"
    assert result["output"]["account"] == "myaccount"
    assert result["output"]["warehouse"] == "warehouse"
    assert result["output"]["query"] == "SELECT * FROM users"
    assert result["output"]["method"] == "POST"


def test_dry_run_execute():
    result = snowflake.main(
        operation="execute",
        query="INSERT INTO users (name) VALUES ('John')",
        SNOWFLAKE_ACCOUNT="myaccount",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="pass",
        SNOWFLAKE_WAREHOUSE="warehouse",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "execute"


def test_url_structure():
    result = snowflake.main(
        operation="query",
        query="SELECT 1",
        SNOWFLAKE_ACCOUNT="myaccount",
        SNOWFLAKE_USER="user",
        SNOWFLAKE_PASSWORD="pass",
        SNOWFLAKE_WAREHOUSE="warehouse",
        dry_run=True,
    )
    assert "myaccount.snowflakecomputing.com" in result["output"]["url"]
    assert "/api/v2/statements" in result["output"]["url"]
