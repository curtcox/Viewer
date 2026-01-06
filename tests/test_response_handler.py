"""Tests for response handler utility."""

from __future__ import annotations

from unittest.mock import Mock

import requests

from server_utils.external_api.response_handler import ResponseHandler


class TestHandleRequestException:
    """Tests for handle_request_exception method."""

    def test_exception_with_status_code(self):
        """Test handling exception with status code."""
        mock_response = Mock()
        mock_response.status_code = 404

        exc = requests.RequestException()
        exc.response = mock_response

        result = ResponseHandler.handle_request_exception(exc)
        assert "output" in result
        assert "error" in result["output"]
        assert result["output"]["status_code"] == 404

    def test_exception_without_response(self):
        """Test handling exception without response object."""
        exc = requests.RequestException("Connection failed")
        result = ResponseHandler.handle_request_exception(exc)

        assert "output" in result
        assert "error" in result["output"]
        assert result["output"]["status_code"] == 500

    def test_exception_message_preserved(self):
        """Test that exception message is preserved in details."""
        exc = requests.RequestException("Connection timeout")
        result = ResponseHandler.handle_request_exception(exc)

        assert "details" in result["output"]
        assert "Connection timeout" in result["output"]["details"]

    def test_exception_with_none_response(self):
        """Test handling exception with None response."""
        exc = requests.RequestException()
        exc.response = None

        result = ResponseHandler.handle_request_exception(exc)
        assert result["output"]["status_code"] == 500


class TestHandleJsonResponse:
    """Tests for handle_json_response method."""

    def test_successful_json_response(self):
        """Test handling successful JSON response."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "value"}

        result = ResponseHandler.handle_json_response(mock_response)
        assert "output" in result
        assert result["output"] == {"data": "value"}

    def test_failed_json_response(self):
        """Test handling failed JSON response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}

        result = ResponseHandler.handle_json_response(mock_response)
        assert "output" in result
        assert "error" in result["output"]
        assert result["output"]["status_code"] == 400

    def test_invalid_json_response(self):
        """Test handling response with invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Not JSON content"

        result = ResponseHandler.handle_json_response(mock_response)
        assert "output" in result
        assert "error" in result["output"]
        assert "Invalid JSON response" in result["output"]["error"]

    def test_custom_error_extractor(self):
        """Test with custom error message extractor."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "Custom error", "code": 1001}
        }

        def extract_error(data):
            return data["error"]["message"]

        result = ResponseHandler.handle_json_response(mock_response, extract_error)
        assert "output" in result
        assert "error" in result["output"]
        assert result["output"]["error"] == "Custom error"

    def test_error_extractor_fallback(self):
        """Test error extractor fallback to generic message."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.json.return_value = {"status": "error"}

        def extract_error(data):
            # Returns None if message not found
            return data.get("message")

        result = ResponseHandler.handle_json_response(mock_response, extract_error)
        assert "output" in result
        assert "error" in result["output"]
        # Should use default message when extractor returns None/falsy
        assert result["output"]["error"] == "API error"

    def test_long_text_truncated(self):
        """Test that long error text is truncated."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "x" * 1000  # 1000 characters

        result = ResponseHandler.handle_json_response(mock_response)
        assert "details" in result["output"]
        assert len(result["output"]["details"]) <= 500


class TestCheckResponseOk:
    """Tests for check_response_ok method."""

    def test_ok_response(self):
        """Test checking OK response."""
        mock_response = Mock()
        mock_response.ok = True

        assert ResponseHandler.check_response_ok(mock_response) is True

    def test_not_ok_response(self):
        """Test checking not OK response."""
        mock_response = Mock()
        mock_response.ok = False

        assert ResponseHandler.check_response_ok(mock_response) is False

    def test_response_without_ok_attribute(self):
        """Test response without ok attribute."""
        mock_response = Mock(spec=[])  # No attributes

        assert ResponseHandler.check_response_ok(mock_response) is False


class TestExtractJsonOrError:
    """Tests for extract_json_or_error method."""

    def test_valid_json_extraction(self):
        """Test extracting valid JSON."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "value"}

        data, error = ResponseHandler.extract_json_or_error(mock_response)
        assert data == {"data": "value"}
        assert error is None

    def test_invalid_json_returns_error(self):
        """Test that invalid JSON returns error."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.status_code = 200
        mock_response.text = "Not JSON"

        data, error = ResponseHandler.extract_json_or_error(mock_response)
        assert data is None
        assert error is not None
        assert "Invalid JSON response" in error["output"]["error"]

    def test_empty_json(self):
        """Test extracting empty JSON object."""
        mock_response = Mock()
        mock_response.json.return_value = {}

        data, error = ResponseHandler.extract_json_or_error(mock_response)
        assert data == {}
        assert error is None

    def test_json_array(self):
        """Test extracting JSON array."""
        mock_response = Mock()
        mock_response.json.return_value = [1, 2, 3]

        data, error = ResponseHandler.extract_json_or_error(mock_response)
        assert data == [1, 2, 3]
        assert error is None


class TestResponseHandlerIntegration:
    """Integration tests with typical server patterns."""

    def test_github_success_pattern(self):
        """Test GitHub API success pattern."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": 1,
            "title": "Test Issue",
            "state": "open",
        }

        result = ResponseHandler.handle_json_response(mock_response)
        assert result["output"]["id"] == 1
        assert result["output"]["title"] == "Test Issue"

    def test_github_error_pattern(self):
        """Test GitHub API error pattern."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Not Found",
            "documentation_url": "https://docs.github.com",
        }

        def extract_github_error(data):
            return data.get("message", "GitHub API error")

        result = ResponseHandler.handle_json_response(
            mock_response, extract_github_error
        )
        assert result["output"]["error"] == "Not Found"
        assert result["output"]["status_code"] == 404

    def test_aws_error_pattern(self):
        """Test AWS API error pattern."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "Access Denied",
            }
        }

        def extract_aws_error(data):
            return data.get("Error", {}).get("Message", "AWS API error")

        result = ResponseHandler.handle_json_response(
            mock_response, extract_aws_error
        )
        assert result["output"]["error"] == "Access Denied"

    def test_request_exception_pattern(self):
        """Test common request exception handling pattern."""
        exc = requests.ConnectionError("Failed to connect")
        result = ResponseHandler.handle_request_exception(exc)

        assert "output" in result
        assert "error" in result["output"]
        assert result["output"]["error"] == "Request failed"
        assert "Failed to connect" in result["output"]["details"]


class TestResponseHandlerEdgeCases:
    """Edge cases and special scenarios."""

    def test_response_with_null_values(self):
        """Test response with null values."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"key": None, "value": "test"}

        result = ResponseHandler.handle_json_response(mock_response)
        assert result["output"]["key"] is None
        assert result["output"]["value"] == "test"

    def test_nested_error_response(self):
        """Test deeply nested error response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": [
                {"field": "email", "message": "Invalid email"},
                {"field": "password", "message": "Too short"},
            ]
        }

        result = ResponseHandler.handle_json_response(mock_response)
        assert "response" in result["output"]
        assert result["output"]["response"]["errors"]

    def test_unicode_in_response(self):
        """Test response with unicode characters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"message": "Hello 世界 🌍"}

        result = ResponseHandler.handle_json_response(mock_response)
        assert result["output"]["message"] == "Hello 世界 🌍"

    def test_large_response_body(self):
        """Test handling of large response body."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "x" * 10000}

        result = ResponseHandler.handle_json_response(mock_response)
        assert len(result["output"]["data"]) == 10000
