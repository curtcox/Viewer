from __future__ import annotations

from reference_templates.servers.definitions import mongodb


def test_requires_uri():
    result = mongodb.main()
    assert result["output"]["error"] == "Missing MONGODB_URI"
    assert result["output"]["status_code"] == 401


def test_requires_collection():
    result = mongodb.main(MONGODB_URI="mongodb://localhost:27017/testdb")
    assert result["output"]["error"]["message"] == "Missing required collection"


def test_invalid_operation():
    result = mongodb.main(
        operation="invalid",
        collection="users",
        MONGODB_URI="mongodb://localhost:27017/testdb",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_find():
    result = mongodb.main(
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
    result = mongodb.main(
        operation="find_one",
        collection="users",
        query='{"id": 1}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "find_one"


def test_dry_run_insert_one():
    result = mongodb.main(
        operation="insert_one",
        collection="users",
        document='{"name": "Jane", "age": 30}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "insert_one"
    assert result["output"]["document"] == {"name": "Jane", "age": 30}


def test_dry_run_update_one():
    result = mongodb.main(
        operation="update_one",
        collection="users",
        query='{"name": "John"}',
        update='{"$set": {"age": 31}}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "update_one"


def test_dry_run_delete_one():
    result = mongodb.main(
        operation="delete_one",
        collection="users",
        query='{"name": "John"}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "delete_one"


def test_dry_run_count():
    result = mongodb.main(
        operation="count",
        collection="users",
        query='{"age": {"$gt": 25}}',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "count"


def test_invalid_query_json():
    result = mongodb.main(
        operation="find",
        collection="users",
        query='invalid json',
        MONGODB_URI="mongodb://localhost:27017/testdb",
        dry_run=True,
    )
    assert "Invalid JSON" in result["output"]["error"]["message"]


def test_uri_hides_credentials():
    result = mongodb.main(
        operation="find",
        collection="users",
        MONGODB_URI="mongodb://user:pass@localhost:27017/testdb",
        dry_run=True,
    )
    assert "output" in result
    assert "user:pass" not in result["output"]["uri"]
    assert "localhost:27017/testdb" in result["output"]["uri"]
