"""Tests for the Salesforce server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import salesforce


def test_missing_access_token_returns_auth_error():
    result = salesforce.main(
        SALESFORCE_ACCESS_TOKEN="",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_missing_instance_url_returns_auth_error():
    result = salesforce.main(
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = salesforce.main(
        operation="invalid_op",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
    )
    assert "error" in result["output"]


def test_query_requires_soql_query():
    result = salesforce.main(
        operation="query",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_record_requires_sobject_and_id():
    result = salesforce.main(
        operation="get_record",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_record_requires_sobject_and_data():
    result = salesforce.main(
        operation="create_record",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_record_requires_sobject_id_and_data():
    result = salesforce.main(
        operation="update_record",
        sobject_type="Account",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_record_requires_sobject_and_id():
    result = salesforce.main(
        operation="delete_record",
        sobject_type="Account",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_describe_object_requires_sobject():
    result = salesforce.main(
        operation="describe_object",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_query():
    result = salesforce.main(
        operation="query",
        soql_query="SELECT Id, Name FROM Account LIMIT 10",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "GET"


def test_dry_run_returns_preview_for_create():
    result = salesforce.main(
        operation="create_record",
        sobject_type="Account",
        data={"Name": "Test Company"},
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = salesforce.main(
        operation="query",
        soql_query="SELECT Id FROM Account",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_invalid_json_response_returns_error():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.status_code = 200
    mock_response.text = "Not JSON"

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = salesforce.main(
        operation="query",
        soql_query="SELECT Id FROM Account",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = [
        {"message": "Invalid query", "errorCode": "MALFORMED_QUERY"}
    ]

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = salesforce.main(
        operation="query",
        soql_query="INVALID QUERY",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_delete_success_returns_success():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 204

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = salesforce.main(
        operation="delete_record",
        sobject_type="Account",
        record_id="001xx000003DHP0AAO",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["success"] is True


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "totalSize": 1,
        "records": [{"Id": "001xx000003DHP0AAO", "Name": "Test Company"}],
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = salesforce.main(
        operation="query",
        soql_query="SELECT Id, Name FROM Account LIMIT 1",
        SALESFORCE_ACCESS_TOKEN="test-token",
        SALESFORCE_INSTANCE_URL="https://na1.salesforce.com",
        dry_run=False,
        client=mock_client,
    )
    assert "records" in result["output"]
