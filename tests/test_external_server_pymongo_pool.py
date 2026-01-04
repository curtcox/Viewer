from __future__ import annotations

from reference.templates.servers.definitions import pymongo_pool


def test_requires_uri():
    result = pymongo_pool.main()
    assert result["output"]["error"] == "Missing MONGODB_URI"
    assert result["output"]["status_code"] == 401


def test_requires_collection():
    result = pymongo_pool.main(MONGODB_URI="mongodb://localhost:27017/testdb")
    assert result["output"]["error"]["message"] == "Missing required collection"


def test_invalid_operation():
    result = pymongo_pool.main(
        operation="invalid",
        collection="users",
        MONGODB_URI="mongodb://localhost:27017/testdb",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_find():
    result = pymongo_pool.main(
        operation="find",
        collection="users",
        query='{"name": "John"}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "find"
    assert result["output"]["collection"] == "users"
    assert result["output"]["query"] == {"name": "John"}


def test_dry_run_find_one():
    result = pymongo_pool.main(
        operation="find_one",
        collection="users",
        query='{"id": 1}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "find_one"


def test_dry_run_insert_one():
    result = pymongo_pool.main(
        operation="insert_one",
        collection="users",
        document='{"name": "Jane", "age": 30}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "insert_one"


def test_dry_run_count():
    result = pymongo_pool.main(
        operation="count",
        collection="users",
        query='{"age": {"$gt": 25}}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "count"


def test_invalid_query_json():
    result = pymongo_pool.main(
        operation="find",
        collection="users",
        query='invalid json',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "Invalid JSON" in result["output"]["error"]["message"]


def test_uri_hides_credentials():
    result = pymongo_pool.main(
        operation="find",
        collection="users",
        MONGODB_URI="mongodb://user:pass@localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert "user:pass" not in result["output"]["uri"]
    assert "localhost:27017/testdb" in result["output"]["uri"]


def test_pool_configuration():
    result = pymongo_pool.main(
        operation="find",
        collection="users",
        MONGODB_URI="mongodb://localhost:27017/testdb",
        max_pool_size=50,
        min_pool_size=10,
        dry_run=True,
    )
    assert "output" in result
    # Pool configuration doesn't appear in preview but is used in actual calls
