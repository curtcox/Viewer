"""Tests for the Dynamics 365 server definition."""

from unittest.mock import Mock

import requests

from reference_templates.servers.definitions import dynamics365


def test_missing_credentials_returns_auth_error():
    result = dynamics365.main(
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN=None,
        DYNAMICS365_TENANT_ID=None,
        DYNAMICS365_CLIENT_ID=None,
        DYNAMICS365_CLIENT_SECRET=None,
        dry_run=False,
    )
    assert "error" in result["output"]


def test_missing_instance_url_returns_validation_error():
    result = dynamics365.main(
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = dynamics365.main(
        operation="invalid_op",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_account_requires_account_id():
    result = dynamics365.main(
        operation="get_account",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_account_requires_account_name_and_data():
    result = dynamics365.main(
        operation="create_account",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_update_account_requires_account_id_and_data():
    result = dynamics365.main(
        operation="update_account",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_list_accounts():
    result = dynamics365.main(
        operation="list_accounts",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert "crm.dynamics.com" in result["output"]["url"]


def test_dry_run_returns_preview_for_create_account():
    result = dynamics365.main(
        operation="create_account",
        instance_url="https://org.crm.dynamics.com",
        account_name="Test Account",
        data='{"telephone1": "555-1234"}',
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "operation" in result["output"]
    assert result["output"]["method"] == "POST"


def test_list_accounts_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": [{"accountid": "acc1", "name": "Test Account"}]}
    mock_client.get.return_value = mock_response

    result = dynamics365.main(
        operation="list_accounts",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "value" in result["output"]


def test_get_account_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"accountid": "acc1", "name": "Test Account"}
    mock_client.get.return_value = mock_response

    result = dynamics365.main(
        operation="get_account",
        instance_url="https://org.crm.dynamics.com",
        account_id="acc1",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["accountid"] == "acc1"


def test_create_account_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 204
    mock_client.post.return_value = mock_response

    result = dynamics365.main(
        operation="create_account",
        instance_url="https://org.crm.dynamics.com",
        account_name="New Account",
        data='{"telephone1": "555-1234"}',
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["success"] is True


def test_update_account_success_with_mock():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 204
    mock_client.patch.return_value = mock_response

    result = dynamics365.main(
        operation="update_account",
        instance_url="https://org.crm.dynamics.com",
        account_id="acc1",
        data='{"name": "Updated Account"}',
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["success"] is True


def test_invalid_json_data_returns_error():
    result = dynamics365.main(
        operation="create_account",
        instance_url="https://org.crm.dynamics.com",
        account_name="Test",
        data='invalid json',
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_api_error_handling():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": {"message": "Account not found"}}
    mock_client.get.return_value = mock_response

    result = dynamics365.main(
        operation="get_account",
        instance_url="https://org.crm.dynamics.com",
        account_id="nonexistent",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_request_exception_handling():
    mock_client = Mock()
    mock_client.get.side_effect = requests.RequestException("Network error")

    result = dynamics365.main(
        operation="list_accounts",
        instance_url="https://org.crm.dynamics.com",
        DYNAMICS365_ACCESS_TOKEN="test-token",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]
