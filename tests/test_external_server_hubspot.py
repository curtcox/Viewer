"""Tests for the HubSpot server definition."""

from unittest.mock import Mock

import pytest
import requests

from reference_templates.servers.definitions import hubspot


def test_missing_token_returns_auth_error():
    result = hubspot.main(HUBSPOT_ACCESS_TOKEN="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = hubspot.main(operation="invalid_op", HUBSPOT_ACCESS_TOKEN="test-token")
    assert "error" in result["output"]


def test_get_contact_requires_contact_id():
    result = hubspot.main(
        operation="get_contact",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_contact_requires_properties():
    result = hubspot.main(
        operation="create_contact",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_company_requires_company_id():
    result = hubspot.main(
        operation="get_company",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_company_requires_properties():
    result = hubspot.main(
        operation="create_company",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_contacts():
    result = hubspot.main(
        operation="list_contacts",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "preview" in result["output"] or "operation" in result["output"]


def test_dry_run_returns_preview_for_create_contact():
    result = hubspot.main(
        operation="create_contact",
        properties={"email": "test@example.com", "firstname": "John"},
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_client.request.side_effect = requests.RequestException("Network error")

    result = hubspot.main(
        operation="list_contacts",
        HUBSPOT_ACCESS_TOKEN="test-token",
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

    result = hubspot.main(
        operation="list_contacts",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    # error_output returns {"output": {"error": "...", ...}}
    assert result["output"]["error"] == "Invalid JSON response"


def test_api_error_propagates_message_and_status():
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "message": "Invalid request",
        "category": "VALIDATION_ERROR",
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = hubspot.main(
        operation="list_contacts",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_success_returns_payload():
    mock_response = Mock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "results": [
            {"id": "123", "properties": {"email": "test@example.com"}},
        ]
    }

    mock_client = Mock()
    mock_client.request.return_value = mock_response

    result = hubspot.main(
        operation="list_contacts",
        HUBSPOT_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "results" in result["output"]
