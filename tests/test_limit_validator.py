"""Tests for limit validation utilities."""

from __future__ import annotations

import pytest

from server_utils.external_api.limit_validator import (
    AWS_S3_MAX_KEYS,
    GITHUB_MAX_PER_PAGE,
    MONGODB_MAX_LIMIT,
    get_limit_info,
    validate_limit,
    validate_pagination_params,
)


class TestValidateLimit:
    """Tests for the validate_limit function."""

    def test_valid_limit(self):
        """Test that a valid limit passes validation."""
        error = validate_limit(50, 100, "limit")
        assert error is None

    def test_limit_at_maximum(self):
        """Test that a limit equal to the maximum is valid."""
        error = validate_limit(100, 100, "limit")
        assert error is None

    def test_limit_at_minimum(self):
        """Test that a limit equal to the minimum is valid."""
        error = validate_limit(1, 100, "limit")
        assert error is None

    def test_limit_exceeds_maximum(self):
        """Test that a limit exceeding the maximum returns an error."""
        error = validate_limit(150, 100, "limit")
        assert error is not None
        assert "output" in error
        assert "error" in error["output"]
        assert "exceeds maximum" in error["output"]["error"]["message"]
        assert error["output"]["error"]["details"]["field"] == "limit"

    def test_limit_below_minimum(self):
        """Test that a limit below the minimum returns an error."""
        error = validate_limit(0, 100, "limit")
        assert error is not None
        assert "output" in error
        assert "error" in error["output"]
        assert "must be at least 1" in error["output"]["error"]["message"]
        assert error["output"]["error"]["details"]["field"] == "limit"

    def test_negative_limit(self):
        """Test that a negative limit returns an error."""
        error = validate_limit(-10, 100, "limit")
        assert error is not None
        assert "must be at least" in error["output"]["error"]["message"]

    def test_custom_field_name(self):
        """Test that custom field names appear in error messages."""
        error = validate_limit(150, 100, "per_page")
        assert error is not None
        assert error["output"]["error"]["details"]["field"] == "per_page"
        assert "per_page" in error["output"]["error"]["message"]

    def test_custom_min_value(self):
        """Test validation with a custom minimum value."""
        error = validate_limit(5, 100, "limit", min_value=10)
        assert error is not None
        assert "must be at least 10" in error["output"]["error"]["message"]

    def test_error_includes_details(self):
        """Test that validation errors include detailed context."""
        error = validate_limit(200, 100, "limit")
        assert error is not None
        details = error["output"]["error"]["details"]
        assert details["provided"] == 200
        assert details["maximum"] == 100
        assert details["minimum"] == 1
        assert "rationale" in details


class TestServiceSpecificLimits:
    """Tests for service-specific limit constants."""

    def test_aws_s3_limit_validation(self):
        """Test AWS S3 max_keys validation."""
        # Valid
        assert validate_limit(500, AWS_S3_MAX_KEYS, "max_keys") is None
        assert validate_limit(AWS_S3_MAX_KEYS, AWS_S3_MAX_KEYS, "max_keys") is None

        # Invalid
        error = validate_limit(1500, AWS_S3_MAX_KEYS, "max_keys")
        assert error is not None
        assert "exceeds maximum" in error["output"]["error"]["message"]

    def test_github_per_page_validation(self):
        """Test GitHub per_page validation."""
        # Valid
        assert validate_limit(30, GITHUB_MAX_PER_PAGE, "per_page") is None
        assert validate_limit(GITHUB_MAX_PER_PAGE, GITHUB_MAX_PER_PAGE, "per_page") is None

        # Invalid
        error = validate_limit(200, GITHUB_MAX_PER_PAGE, "per_page")
        assert error is not None
        assert "exceeds maximum" in error["output"]["error"]["message"]

    def test_mongodb_limit_validation(self):
        """Test MongoDB limit validation."""
        # Valid
        assert validate_limit(100, MONGODB_MAX_LIMIT, "limit") is None
        assert validate_limit(5000, MONGODB_MAX_LIMIT, "limit") is None

        # Invalid
        error = validate_limit(15000, MONGODB_MAX_LIMIT, "limit")
        assert error is not None
        assert "exceeds maximum" in error["output"]["error"]["message"]


class TestValidatePaginationParams:
    """Tests for the validate_pagination_params function."""

    def test_all_valid_params(self):
        """Test that all valid pagination parameters pass."""
        error = validate_pagination_params(limit=50, offset=0, page=1, max_allowed=100)
        assert error is None

    def test_limit_only(self):
        """Test validation with only limit parameter."""
        error = validate_pagination_params(limit=50, max_allowed=100)
        assert error is None

    def test_invalid_limit(self):
        """Test that invalid limit is caught."""
        error = validate_pagination_params(limit=200, max_allowed=100)
        assert error is not None
        assert "exceeds maximum" in error["output"]["error"]["message"]

    def test_negative_offset(self):
        """Test that negative offset is caught."""
        error = validate_pagination_params(offset=-5, max_allowed=100)
        assert error is not None
        assert "offset must be non-negative" in error["output"]["error"]["message"]

    def test_zero_offset_valid(self):
        """Test that zero offset is valid."""
        error = validate_pagination_params(offset=0, max_allowed=100)
        assert error is None

    def test_invalid_page(self):
        """Test that page < 1 is caught."""
        error = validate_pagination_params(page=0, max_allowed=100)
        assert error is not None
        assert "page must be at least 1" in error["output"]["error"]["message"]

    def test_none_values_ignored(self):
        """Test that None values are not validated."""
        error = validate_pagination_params(
            limit=None, offset=None, page=None, max_allowed=100
        )
        assert error is None


class TestGetLimitInfo:
    """Tests for the get_limit_info function."""

    def test_valid_limit_info(self):
        """Test limit info for a valid limit."""
        info = get_limit_info(50, 100, "per_page")
        assert info["parameter"] == "per_page"
        assert info["current"] == 50
        assert info["maximum"] == 100
        assert info["status"] == "valid"
        assert info["constraint_source"] == "external_api_documentation"

    def test_limit_at_maximum_info(self):
        """Test limit info when at maximum."""
        info = get_limit_info(100, 100, "limit")
        assert info["current"] == 100
        assert info["maximum"] == 100
        assert info["status"] == "valid"

    def test_exceeds_maximum_info(self):
        """Test limit info when exceeding maximum."""
        info = get_limit_info(150, 100, "limit")
        assert info["current"] == 150
        assert info["maximum"] == 100
        assert info["status"] == "exceeds_maximum"

    def test_custom_parameter_name(self):
        """Test that custom parameter names are included."""
        info = get_limit_info(50, 100, "max_keys")
        assert info["parameter"] == "max_keys"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_valid_limit(self):
        """Test validation with very large but valid limit."""
        error = validate_limit(9999, 10000, "limit")
        assert error is None

    def test_very_large_invalid_limit(self):
        """Test validation with very large invalid limit."""
        error = validate_limit(1000000, 100, "limit")
        assert error is not None
        assert "exceeds maximum" in error["output"]["error"]["message"]

    def test_limit_one(self):
        """Test that limit of 1 is valid."""
        error = validate_limit(1, 100, "limit")
        assert error is None

    def test_zero_max_allowed(self):
        """Test behavior when max_allowed is 0."""
        error = validate_limit(1, 0, "limit")
        assert error is not None
        assert "exceeds maximum" in error["output"]["error"]["message"]


class TestIntegrationWithServerDefinitions:
    """Integration tests with actual server definitions."""

    def test_aws_s3_limit_validation_integration(self):
        """Test limit validation in AWS S3 context."""
        from reference_templates.servers.definitions import aws_s3

        # Test valid limit
        result = aws_s3.main(
            operation="list_objects",
            bucket="test-bucket",
            max_keys=500,
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            dry_run=True,
        )
        assert "output" in result
        assert "preview" not in result.get("output", {}).get("error", {})

        # Test exceeding limit
        result = aws_s3.main(
            operation="list_objects",
            bucket="test-bucket",
            max_keys=2000,  # Exceeds AWS_S3_MAX_KEYS (1000)
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            dry_run=True,
        )
        assert "output" in result
        assert "error" in result["output"]
        assert "exceeds maximum" in result["output"]["error"]["message"]

        # Test negative limit
        result = aws_s3.main(
            operation="list_objects",
            bucket="test-bucket",
            max_keys=-10,
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            dry_run=True,
        )
        assert "output" in result
        assert "error" in result["output"]
        assert "must be at least" in result["output"]["error"]["message"]

    def test_github_limit_validation_integration(self):
        """Test limit validation in GitHub context."""
        from reference_templates.servers.definitions import github

        # Test valid limit
        result = github.main(
            owner="test",
            repo="test",
            operation="list_issues",
            per_page=50,
            GITHUB_TOKEN="test",
            dry_run=True,
        )
        assert "output" in result
        assert "preview" in result["output"]

        # Test exceeding limit
        result = github.main(
            owner="test",
            repo="test",
            operation="list_issues",
            per_page=200,  # Exceeds GITHUB_MAX_PER_PAGE (100)
            GITHUB_TOKEN="test",
            dry_run=True,
        )
        assert "output" in result
        assert "error" in result["output"]
        assert "exceeds maximum" in result["output"]["error"]["message"]

    def test_mongodb_limit_validation_integration(self):
        """Test limit validation in MongoDB context."""
        from reference_templates.servers.definitions import mongodb

        # Test valid limit
        result = mongodb.main(
            operation="find",
            collection="test",
            limit=100,
            MONGODB_URI="mongodb://localhost:27017/test",
            dry_run=True,
        )
        assert "output" in result
        # Should have preview, not error
        assert "operation" in result["output"]

        # Test exceeding limit
        result = mongodb.main(
            operation="find",
            collection="test",
            limit=15000,  # Exceeds MONGODB_MAX_LIMIT (10000)
            MONGODB_URI="mongodb://localhost:27017/test",
            dry_run=True,
        )
        assert "output" in result
        assert "error" in result["output"]
        assert "exceeds maximum" in result["output"]["error"]["message"]


class TestPreviewWithLimitConstraint:
    """Tests for limit constraint information in preview responses."""

    def test_aws_s3_preview_includes_limit_constraint(self):
        """Test that AWS S3 preview includes limit constraint info."""
        from reference_templates.servers.definitions import aws_s3

        result = aws_s3.main(
            operation="list_objects",
            bucket="test-bucket",
            max_keys=500,
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            dry_run=True,
        )
        assert "output" in result
        preview = result["output"]
        assert "limit_constraint" in preview
        assert preview["limit_constraint"]["current"] == 500
        assert preview["limit_constraint"]["maximum"] == AWS_S3_MAX_KEYS
        assert preview["limit_constraint"]["status"] == "valid"

    def test_github_preview_includes_limit_constraint(self):
        """Test that GitHub preview includes limit constraint info."""
        from reference_templates.servers.definitions import github

        result = github.main(
            owner="test",
            repo="test",
            operation="list_issues",
            per_page=30,
            GITHUB_TOKEN="test",
            dry_run=True,
        )
        assert "output" in result
        preview = result["output"]["preview"]
        assert "limit_constraint" in preview
        assert preview["limit_constraint"]["current"] == 30
        assert preview["limit_constraint"]["maximum"] == GITHUB_MAX_PER_PAGE
        assert preview["limit_constraint"]["parameter"] == "per_page"

    def test_mongodb_preview_includes_limit_constraint(self):
        """Test that MongoDB preview includes limit constraint info."""
        from reference_templates.servers.definitions import mongodb

        result = mongodb.main(
            operation="find",
            collection="test",
            limit=100,
            MONGODB_URI="mongodb://localhost:27017/test",
            dry_run=True,
        )
        assert "output" in result
        preview = result["output"]
        assert "limit_constraint" in preview
        assert preview["limit_constraint"]["current"] == 100
        assert preview["limit_constraint"]["maximum"] == MONGODB_MAX_LIMIT
        assert preview["limit_constraint"]["parameter"] == "limit"

    def test_limit_constraint_not_in_non_list_operations(self):
        """Test that limit constraint is not included for non-list operations."""
        from reference_templates.servers.definitions import aws_s3

        result = aws_s3.main(
            operation="get_object",
            bucket="test-bucket",
            key="test.txt",
            AWS_ACCESS_KEY_ID="test",
            AWS_SECRET_ACCESS_KEY="test",
            dry_run=True,
        )
        assert "output" in result
        preview = result["output"]
        assert "limit_constraint" not in preview
