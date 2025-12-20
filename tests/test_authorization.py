"""Unit tests for authorization module."""

import pytest

from authorization import AuthorizationResult, authorize_request


class TestAuthorizationResult:
    """Tests for AuthorizationResult class."""

    def test_allowed_result(self):
        """Test creating an allowed authorization result."""
        result = AuthorizationResult(allowed=True)
        assert result.allowed is True
        assert result.status_code is None
        assert result.message is None

    def test_rejected_result_with_401(self):
        """Test creating a rejected result with 401 status."""
        result = AuthorizationResult(
            allowed=False, status_code=401, message="Authentication required"
        )
        assert result.allowed is False
        assert result.status_code == 401
        assert result.message == "Authentication required"

    def test_rejected_result_with_403(self):
        """Test creating a rejected result with 403 status."""
        result = AuthorizationResult(
            allowed=False, status_code=403, message="Access denied"
        )
        assert result.allowed is False
        assert result.status_code == 403
        assert result.message == "Access denied"

    def test_rejected_without_status_raises_error(self):
        """Test that rejected result without status code raises ValueError."""
        with pytest.raises(ValueError, match="status_code is required"):
            AuthorizationResult(allowed=False, message="Error")

    def test_rejected_without_message_raises_error(self):
        """Test that rejected result without message raises ValueError."""
        with pytest.raises(ValueError, match="message is required"):
            AuthorizationResult(allowed=False, status_code=401)

    def test_invalid_status_code_raises_error(self):
        """Test that invalid status code raises ValueError."""
        with pytest.raises(ValueError, match="status_code must be"):
            AuthorizationResult(
                allowed=False, status_code=500, message="Internal error"
            )


class TestAuthorizeRequest:
    """Tests for authorize_request function."""

    def test_placeholder_allows_all_requests(self, memory_db_app):
        """Test that placeholder function allows all requests."""
        with memory_db_app.test_request_context("/"):
            from flask import request

            result = authorize_request(request)
            assert result.allowed is True

    def test_placeholder_allows_authenticated_paths(self, memory_db_app):
        """Test that placeholder allows authenticated paths."""
        with memory_db_app.test_request_context("/profile"):
            from flask import request

            result = authorize_request(request)
            assert result.allowed is True

    def test_placeholder_allows_api_requests(self, memory_db_app):
        """Test that placeholder allows API requests."""
        with memory_db_app.test_request_context("/api/cid/check", method="POST"):
            from flask import request

            result = authorize_request(request)
            assert result.allowed is True

    def test_placeholder_allows_admin_paths(self, memory_db_app):
        """Test that placeholder allows admin paths."""
        with memory_db_app.test_request_context("/secrets"):
            from flask import request

            result = authorize_request(request)
            assert result.allowed is True
