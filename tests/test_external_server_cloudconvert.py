"""Tests for the CloudConvert server definition."""

from unittest.mock import Mock

import requests

from reference.templates.servers.definitions import cloudconvert


def test_missing_api_key_returns_auth_error():
    result = cloudconvert.main(CLOUDCONVERT_API_KEY="", dry_run=False)
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = cloudconvert.main(
        operation="invalid_op",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_job_requires_input_format():
    result = cloudconvert.main(
        operation="create_job",
        output_format="txt",
        file_url="https://example.com/doc.pdf",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_job_requires_output_format():
    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        file_url="https://example.com/doc.pdf",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_job_requires_file_url():
    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        output_format="txt",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_job_requires_job_id():
    result = cloudconvert.main(
        operation="get_job",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_task_requires_task_id():
    result = cloudconvert.main(
        operation="get_task",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_cancel_task_requires_task_id():
    result = cloudconvert.main(
        operation="cancel_task",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_delete_task_requires_task_id():
    result = cloudconvert.main(
        operation="delete_task",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_export_file_requires_task_id():
    result = cloudconvert.main(
        operation="export_file",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_dry_run_returns_preview_for_create_job():
    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        output_format="txt",
        file_url="https://example.com/doc.pdf",
        filename="document.pdf",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "create_job"
    assert result["output"]["conversion"]["input_format"] == "pdf"
    assert result["output"]["conversion"]["output_format"] == "txt"


def test_dry_run_returns_preview_for_get_job():
    result = cloudconvert.main(
        operation="get_job",
        job_id="job123",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "get_job"
    assert result["output"]["job_id"] == "job123"


def test_dry_run_returns_preview_for_list_jobs():
    result = cloudconvert.main(
        operation="list_jobs",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "list_jobs"


def test_dry_run_returns_preview_for_get_task():
    result = cloudconvert.main(
        operation="get_task",
        task_id="task123",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["operation"] == "get_task"
    assert result["output"]["task_id"] == "task123"


def test_dry_run_returns_preview_for_cancel_task():
    result = cloudconvert.main(
        operation="cancel_task",
        task_id="task123",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["task_id"] == "task123"


def test_dry_run_returns_preview_for_export_file():
    result = cloudconvert.main(
        operation="export_file",
        task_id="task123",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["task_id"] == "task123"


def test_create_job_with_options():
    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        output_format="txt",
        file_url="https://example.com/doc.pdf",
        options='{"quality": 90, "page": 1}',
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert result["output"]["conversion"]["options"]["quality"] == 90
    assert result["output"]["conversion"]["options"]["page"] == 1


def test_invalid_json_in_options_returns_error():
    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        output_format="txt",
        file_url="https://example.com/doc.pdf",
        options='invalid json',
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_request_exception_returns_error():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_client.post.side_effect = requests.RequestException(response=mock_response)

    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        output_format="txt",
        file_url="https://example.com/doc.pdf",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert "error" in result["output"]


def test_successful_create_job_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"job_id": "abc123", "status": "processing"}
    mock_response.raise_for_status = Mock()
    mock_client.post.return_value = mock_response

    result = cloudconvert.main(
        operation="create_job",
        input_format="pdf",
        output_format="txt",
        file_url="https://example.com/doc.pdf",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["job_id"] == "abc123"
    assert result["output"]["status"] == "processing"


def test_successful_get_job_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"job_id": "job123", "status": "finished"}
    mock_response.raise_for_status = Mock()
    mock_client.get.return_value = mock_response

    result = cloudconvert.main(
        operation="get_job",
        job_id="job123",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert result["output"]["job_id"] == "job123"
    assert result["output"]["status"] == "finished"


def test_successful_list_jobs_request_returns_data():
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"jobs": [{"job_id": "job1"}, {"job_id": "job2"}]}
    mock_response.raise_for_status = Mock()
    mock_client.get.return_value = mock_response

    result = cloudconvert.main(
        operation="list_jobs",
        CLOUDCONVERT_API_KEY="test_key",
        dry_run=False,
        client=mock_client,
    )
    assert len(result["output"]["jobs"]) == 2
