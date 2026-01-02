"""Tests for the Coda server definition."""

from reference_templates.servers.definitions import coda


def test_missing_api_token_returns_auth_error():
    result = coda.main(CODA_API_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = coda.main(
        operation="invalid_op",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_doc_requires_doc_id():
    result = coda.main(
        operation="get_doc",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_tables_requires_doc_id():
    result = coda.main(
        operation="list_tables",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_table_requires_doc_id_and_table_id():
    result = coda.main(
        operation="get_table",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_rows_requires_doc_id_and_table_id():
    result = coda.main(
        operation="list_rows",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_row_requires_all_ids():
    result = coda.main(
        operation="get_row",
        doc_id="doc123",
        table_id="table123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_row_requires_doc_table_and_data():
    result = coda.main(
        operation="create_row",
        doc_id="doc123",
        table_id="table123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_row_requires_all_ids_and_data():
    result = coda.main(
        operation="update_row",
        doc_id="doc123",
        table_id="table123",
        row_id="row123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_row_requires_all_ids():
    result = coda.main(
        operation="delete_row",
        doc_id="doc123",
        table_id="table123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_docs():
    result = coda.main(
        operation="list_docs",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"
    assert "docs" in result["output"]["url"]


def test_dry_run_returns_preview_for_get_doc():
    result = coda.main(
        operation="get_doc",
        doc_id="doc123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "doc123" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_tables():
    result = coda.main(
        operation="list_tables",
        doc_id="doc123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "tables" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_rows():
    result = coda.main(
        operation="list_rows",
        doc_id="doc123",
        table_id="table123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "rows" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_row():
    result = coda.main(
        operation="create_row",
        doc_id="doc123",
        table_id="table123",
        data='{"cells": [{"column": "c-abc", "value": "test"}]}',
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"
    assert "payload" in result["output"]


def test_dry_run_returns_preview_for_update_row():
    result = coda.main(
        operation="update_row",
        doc_id="doc123",
        table_id="table123",
        row_id="row123",
        data='{"cells": [{"column": "c-abc", "value": "updated"}]}',
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "PUT"
    assert "row123" in result["output"]["url"]


def test_dry_run_returns_preview_for_delete_row():
    result = coda.main(
        operation="delete_row",
        doc_id="doc123",
        table_id="table123",
        row_id="row123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "DELETE"
    assert "row123" in result["output"]["url"]


def test_dry_run_returns_preview_for_list_columns():
    result = coda.main(
        operation="list_columns",
        doc_id="doc123",
        table_id="table123",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "columns" in result["output"]["url"]


def test_list_rows_with_query():
    result = coda.main(
        operation="list_rows",
        doc_id="doc123",
        table_id="table123",
        query="Name contains test",
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "params" in result["output"]
    assert result["output"]["params"]["query"] == "Name contains test"


def test_invalid_json_in_data_returns_error():
    result = coda.main(
        operation="create_row",
        doc_id="doc123",
        table_id="table123",
        data='{invalid json}',
        CODA_API_TOKEN="test_token",
        dry_run=True,
    )
    assert "error" in result["output"]
    assert "json" in result["output"]["error"]["message"].lower()
