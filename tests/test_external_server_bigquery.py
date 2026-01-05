from __future__ import annotations

from reference.templates.servers.definitions import bigquery


def test_requires_credentials():
    result = bigquery.main()
    assert "Missing GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_ACCESS_TOKEN" in result["output"]["error"]
    assert result["output"]["status_code"] == 401


def test_requires_project_id():
    result = bigquery.main(GOOGLE_ACCESS_TOKEN="token")
    assert result["output"]["error"]["message"] == "Missing required project_id"


def test_query_requires_query():
    result = bigquery.main(
        operation="query",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
    )
    assert result["output"]["error"]["message"] == "Missing required query"


def test_list_tables_requires_dataset():
    result = bigquery.main(
        operation="list_tables",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
    )
    assert result["output"]["error"]["message"] == "Missing required dataset_id"


def test_invalid_operation():
    result = bigquery.main(
        operation="invalid",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
    )
    assert result["output"]["error"]["message"] == "Unsupported operation"


def test_dry_run_query():
    result = bigquery.main(
        operation="query",
        query="SELECT * FROM `project.dataset.table`",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "query"
    assert result["output"]["project_id"] == "my-project"
    assert result["output"]["query"] == "SELECT * FROM `project.dataset.table`"
    assert result["output"]["method"] == "POST"


def test_dry_run_list_datasets():
    result = bigquery.main(
        operation="list_datasets",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "list_datasets"


def test_dry_run_list_tables():
    result = bigquery.main(
        operation="list_tables",
        project_id="my-project",
        dataset_id="my_dataset",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "list_tables"


def test_with_service_account():
    result = bigquery.main(
        operation="query",
        query="SELECT 1",
        project_id="my-project",
        GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account"}',
        dry_run=True,
    )
    assert "output" in result
    assert result["output"]["operation"] == "query"


def test_url_structure():
    result = bigquery.main(
        operation="query",
        query="SELECT 1",
        project_id="my-project",
        GOOGLE_ACCESS_TOKEN="token",
        dry_run=True,
    )
    assert "bigquery.googleapis.com" in result["output"]["url"]
    assert "my-project" in result["output"]["url"]
