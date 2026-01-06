"""Tests for preview builder utility."""

from __future__ import annotations

from server_utils.external_api.preview_builder import PreviewBuilder


class TestPreviewBuilder:
    """Tests for PreviewBuilder class."""

    def test_basic_preview(self):
        """Test building a basic preview."""
        preview = PreviewBuilder.build(
            operation="list_issues",
            url="https://api.github.com/repos/owner/repo/issues",
            method="GET",
            auth_type="Bearer Token",
        )
        assert preview["operation"] == "list_issues"
        assert preview["url"] == "https://api.github.com/repos/owner/repo/issues"
        assert preview["method"] == "GET"
        assert preview["auth"] == "Bearer Token"

    def test_preview_with_params(self):
        """Test preview with query parameters."""
        preview = PreviewBuilder.build(
            operation="list_issues",
            url="https://api.github.com/repos/owner/repo/issues",
            method="GET",
            auth_type="Bearer Token",
            params={"state": "open", "per_page": 30},
        )
        assert "params" in preview
        assert preview["params"]["state"] == "open"
        assert preview["params"]["per_page"] == 30

    def test_preview_with_payload(self):
        """Test preview with request payload."""
        preview = PreviewBuilder.build(
            operation="create_issue",
            url="https://api.github.com/repos/owner/repo/issues",
            method="POST",
            auth_type="Bearer Token",
            payload={"title": "Bug report", "body": "Description"},
        )
        assert "payload" in preview
        assert preview["payload"]["title"] == "Bug report"
        assert preview["payload"]["body"] == "Description"

    def test_preview_with_headers(self):
        """Test preview with headers."""
        preview = PreviewBuilder.build(
            operation="list_issues",
            url="https://api.github.com",
            method="GET",
            auth_type="Bearer Token",
            headers={
                "Accept": "application/json",
                "User-Agent": "Test",
            },
        )
        assert "headers" in preview
        assert preview["headers"]["Accept"] == "application/json"
        assert preview["headers"]["User-Agent"] == "Test"

    def test_preview_redacts_sensitive_headers(self):
        """Test that sensitive headers are redacted."""
        preview = PreviewBuilder.build(
            operation="list",
            url="https://api.example.com",
            method="GET",
            auth_type="API Key",
            headers={
                "Authorization": "Bearer secret-token",
                "X-API-Key": "secret-key",
                "Accept": "application/json",
            },
        )
        assert "headers" in preview
        assert preview["headers"]["Authorization"] == "***"
        assert preview["headers"]["X-API-Key"] == "***"
        assert preview["headers"]["Accept"] == "application/json"

    def test_preview_with_extra_fields(self):
        """Test preview with extra server-specific fields."""
        preview = PreviewBuilder.build(
            operation="list_buckets",
            url="https://s3.amazonaws.com",
            method="GET",
            auth_type="AWS Signature V4",
            bucket="my-bucket",
            region="us-east-1",
        )
        assert preview["bucket"] == "my-bucket"
        assert preview["region"] == "us-east-1"

    def test_preview_without_optional_fields(self):
        """Test that optional fields are not included when not provided."""
        preview = PreviewBuilder.build(
            operation="list",
            url="https://api.example.com",
            method="GET",
            auth_type="Bearer Token",
        )
        assert "params" not in preview
        assert "payload" not in preview
        assert "headers" not in preview

    def test_dry_run_response(self):
        """Test wrapping preview in dry-run response."""
        preview = PreviewBuilder.build(
            operation="list",
            url="https://api.example.com",
            method="GET",
            auth_type="Token",
        )
        response = PreviewBuilder.dry_run_response(preview)

        assert "output" in response
        assert "preview" in response["output"]
        assert "message" in response["output"]
        assert response["output"]["message"] == "Dry run - no API call made"
        assert response["output"]["preview"] == preview


class TestPreviewBuilderHeaderRedaction:
    """Tests for header redaction functionality."""

    def test_redacts_authorization_header(self):
        """Test that Authorization header is redacted."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Bearer",
            headers={"Authorization": "Bearer secret"},
        )
        assert preview["headers"]["Authorization"] == "***"

    def test_redacts_api_key_headers(self):
        """Test that API key headers are redacted."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="API Key",
            headers={
                "X-API-Key": "secret",
                "API-Token": "secret",
                "X-Auth-Token": "secret",
            },
        )
        assert preview["headers"]["X-API-Key"] == "***"
        assert preview["headers"]["API-Token"] == "***"
        assert preview["headers"]["X-Auth-Token"] == "***"

    def test_redacts_cookie_header(self):
        """Test that Cookie header is redacted."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Session",
            headers={"Cookie": "session=secret"},
        )
        assert preview["headers"]["Cookie"] == "***"

    def test_case_insensitive_redaction(self):
        """Test that header redaction is case-insensitive."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Token",
            headers={
                "AUTHORIZATION": "Bearer secret",
                "Authorization": "Bearer secret2",
                "authorization": "Bearer secret3",
            },
        )
        assert preview["headers"]["AUTHORIZATION"] == "***"
        assert preview["headers"]["Authorization"] == "***"
        assert preview["headers"]["authorization"] == "***"

    def test_preserves_non_sensitive_headers(self):
        """Test that non-sensitive headers are preserved."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "MyApp/1.0",
                "X-Request-ID": "12345",
            },
        )
        assert preview["headers"]["Accept"] == "application/json"
        assert preview["headers"]["Content-Type"] == "application/json"
        assert preview["headers"]["User-Agent"] == "MyApp/1.0"
        assert preview["headers"]["X-Request-ID"] == "12345"


class TestPreviewBuilderIntegration:
    """Integration tests with server patterns."""

    def test_github_list_issues_preview(self):
        """Test GitHub list issues preview."""
        preview = PreviewBuilder.build(
            operation="list_issues",
            url="https://api.github.com/repos/owner/repo/issues",
            method="GET",
            auth_type="Bearer Token",
            params={"state": "open", "per_page": 30},
        )
        response = PreviewBuilder.dry_run_response(preview)

        assert response["output"]["preview"]["operation"] == "list_issues"
        assert response["output"]["preview"]["method"] == "GET"
        assert "params" in response["output"]["preview"]

    def test_github_create_issue_preview(self):
        """Test GitHub create issue preview."""
        preview = PreviewBuilder.build(
            operation="create_issue",
            url="https://api.github.com/repos/owner/repo/issues",
            method="POST",
            auth_type="Bearer Token",
            payload={"title": "Bug", "body": "Description"},
        )

        assert preview["operation"] == "create_issue"
        assert preview["method"] == "POST"
        assert "payload" in preview

    def test_aws_s3_list_objects_preview(self):
        """Test AWS S3 list objects preview."""
        preview = PreviewBuilder.build(
            operation="list_objects",
            url="https://my-bucket.s3.amazonaws.com/",
            method="GET",
            auth_type="AWS Signature V4",
            params={"max-keys": 1000, "prefix": "folder/"},
            bucket="my-bucket",
            region="us-east-1",
        )

        assert preview["bucket"] == "my-bucket"
        assert preview["region"] == "us-east-1"
        assert preview["params"]["max-keys"] == 1000

    def test_mongodb_find_preview(self):
        """Test MongoDB find operation preview."""
        preview = PreviewBuilder.build(
            operation="find",
            url="mongodb://localhost:27017",
            method="QUERY",
            auth_type="MongoDB Auth",
            collection="users",
            query={"status": "active"},
            limit=100,
        )

        assert preview["collection"] == "users"
        assert preview["query"] == {"status": "active"}
        assert preview["limit"] == 100


class TestPreviewBuilderEdgeCases:
    """Edge cases and special scenarios."""

    def test_empty_params_dict(self):
        """Test with empty params dictionary."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Token",
            params={},
        )
        # Empty dict should not be included
        assert "params" not in preview

    def test_empty_payload_dict(self):
        """Test with empty payload dictionary."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="POST",
            auth_type="Token",
            payload={},
        )
        # Empty dict should not be included
        assert "payload" not in preview

    def test_empty_headers_dict(self):
        """Test with empty headers dictionary."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Token",
            headers={},
        )
        # Empty dict should not be included
        assert "headers" not in preview

    def test_none_values_in_params(self):
        """Test params with None values."""
        preview = PreviewBuilder.build(
            operation="test",
            url="https://api.example.com",
            method="GET",
            auth_type="Token",
            params={"key": "value", "empty": None},
        )
        # None values should be preserved
        assert preview["params"]["key"] == "value"
        assert preview["params"]["empty"] is None

    def test_complex_nested_payload(self):
        """Test with complex nested payload."""
        preview = PreviewBuilder.build(
            operation="create",
            url="https://api.example.com",
            method="POST",
            auth_type="Token",
            payload={
                "user": {
                    "name": "John",
                    "email": "john@example.com",
                    "metadata": {"role": "admin"},
                },
                "items": [1, 2, 3],
            },
        )
        assert preview["payload"]["user"]["name"] == "John"
        assert preview["payload"]["items"] == [1, 2, 3]
