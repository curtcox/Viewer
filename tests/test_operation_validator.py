"""Tests for operation validator utility."""

from __future__ import annotations

from server_utils.external_api.operation_validator import OperationValidator


class TestOperationValidator:
    """Tests for OperationValidator class."""

    def test_valid_operation(self):
        """Test that a valid operation passes validation."""
        validator = OperationValidator({"list_issues", "get_issue", "create_issue"})
        error = validator.validate("list_issues")
        assert error is None

    def test_valid_operation_case_insensitive(self):
        """Test that operation validation is case-insensitive."""
        validator = OperationValidator({"list_issues", "get_issue"})
        assert validator.validate("LIST_ISSUES") is None
        assert validator.validate("List_Issues") is None
        assert validator.validate("list_issues") is None

    def test_invalid_operation(self):
        """Test that an invalid operation returns an error."""
        validator = OperationValidator({"list_issues", "get_issue"})
        error = validator.validate("delete_issue")
        assert error is not None
        assert "output" in error
        assert "error" in error["output"]
        assert "Unsupported operation" in error["output"]["error"]["message"]

    def test_error_includes_details(self):
        """Test that error includes operation details."""
        validator = OperationValidator({"list", "get", "create"})
        error = validator.validate("delete")
        assert error is not None
        details = error["output"]["error"]["details"]
        assert details["provided"] == "delete"
        assert "valid_operations" in details
        assert set(details["valid_operations"]) == {"create", "get", "list"}

    def test_normalize_operation(self):
        """Test operation normalization."""
        validator = OperationValidator({"list_issues", "get_issue"})
        assert validator.normalize("LIST_ISSUES") == "list_issues"
        assert validator.normalize("List_Issues") == "list_issues"
        assert validator.normalize("list_issues") == "list_issues"

    def test_is_valid(self):
        """Test is_valid method."""
        validator = OperationValidator({"list", "get", "create"})
        assert validator.is_valid("list") is True
        assert validator.is_valid("LIST") is True
        assert validator.is_valid("delete") is False

    def test_empty_operations_set(self):
        """Test validator with empty operations set."""
        validator = OperationValidator(set())
        error = validator.validate("anything")
        assert error is not None
        assert "Unsupported operation" in error["output"]["error"]["message"]

    def test_single_operation(self):
        """Test validator with single operation."""
        validator = OperationValidator({"list"})
        assert validator.validate("list") is None
        assert validator.validate("get") is not None


class TestOperationValidatorIntegration:
    """Integration tests with server patterns."""

    def test_github_operations(self):
        """Test with GitHub-style operations."""
        validator = OperationValidator({"list_issues", "get_issue", "create_issue"})

        # Valid operations
        assert validator.validate("list_issues") is None
        assert validator.validate("get_issue") is None
        assert validator.validate("create_issue") is None

        # Invalid operations
        assert validator.validate("delete_issue") is not None
        assert validator.validate("update_issue") is not None

    def test_aws_s3_operations(self):
        """Test with AWS S3-style operations."""
        validator = OperationValidator({
            "list_buckets",
            "list_objects",
            "get_object",
            "put_object",
            "delete_object",
        })

        # Valid operations
        assert validator.validate("list_buckets") is None
        assert validator.validate("get_object") is None

        # Invalid operations
        assert validator.validate("copy_object") is not None

    def test_mongodb_operations(self):
        """Test with MongoDB-style operations."""
        validator = OperationValidator({
            "find",
            "insert_one",
            "update_one",
            "delete_one",
        })

        # Valid operations
        assert validator.validate("find") is None
        assert validator.validate("insert_one") is None

        # Invalid operations
        assert validator.validate("find_one") is not None
        assert validator.validate("insert_many") is not None


class TestOperationValidatorEdgeCases:
    """Edge cases and special scenarios."""

    def test_operations_with_underscores(self):
        """Test operations containing underscores."""
        validator = OperationValidator({
            "list_all_items",
            "get_single_item",
        })
        assert validator.validate("list_all_items") is None
        assert validator.validate("get_single_item") is None

    def test_operations_with_numbers(self):
        """Test operations containing numbers."""
        validator = OperationValidator({"get_v2_data", "list_top10"})
        assert validator.validate("get_v2_data") is None
        assert validator.validate("list_top10") is None

    def test_mixed_case_in_constructor(self):
        """Test that constructor normalizes operations."""
        validator = OperationValidator({"List_Issues", "GET_Issue", "CREATE_issue"})
        # All should be normalized to lowercase
        assert validator.is_valid("list_issues") is True
        assert validator.is_valid("get_issue") is True
        assert validator.is_valid("create_issue") is True

    def test_empty_string_operation(self):
        """Test validation of empty string."""
        validator = OperationValidator({"list", "get"})
        error = validator.validate("")
        assert error is not None
        assert "Unsupported operation" in error["output"]["error"]["message"]

    def test_whitespace_operation(self):
        """Test validation of whitespace."""
        validator = OperationValidator({"list", "get"})
        error = validator.validate("  ")
        assert error is not None
