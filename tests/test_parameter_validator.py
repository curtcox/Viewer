"""Tests for parameter validator utility."""

from __future__ import annotations

from server_utils.external_api.parameter_validator import ParameterValidator


class TestParameterValidator:
    """Tests for ParameterValidator class."""

    def test_validate_required_all_present(self):
        """Test validation when all required parameters are present."""
        validator = ParameterValidator({
            "get_object": ["bucket", "key"],
        })
        error = validator.validate_required(
            "get_object",
            {"bucket": "my-bucket", "key": "my-key"},
        )
        assert error is None

    def test_validate_required_one_missing(self):
        """Test validation when one required parameter is missing."""
        validator = ParameterValidator({
            "get_object": ["bucket", "key"],
        })
        error = validator.validate_required(
            "get_object",
            {"bucket": "my-bucket"},
        )
        assert error is not None
        assert "output" in error
        assert "error" in error["output"]
        assert "Missing required key" in error["output"]["error"]["message"]

    def test_validate_required_empty_string(self):
        """Test that empty string is treated as missing."""
        validator = ParameterValidator({
            "create_issue": ["title"],
        })
        error = validator.validate_required(
            "create_issue",
            {"title": ""},
        )
        assert error is not None
        assert "Missing required title" in error["output"]["error"]["message"]

    def test_validate_required_none_value(self):
        """Test that None value is treated as missing."""
        validator = ParameterValidator({
            "get_user": ["user_id"],
        })
        error = validator.validate_required(
            "get_user",
            {"user_id": None},
        )
        assert error is not None
        assert "Missing required user_id" in error["output"]["error"]["message"]

    def test_validate_required_no_requirements(self):
        """Test operation with no required parameters."""
        validator = ParameterValidator({
            "list_all": [],
        })
        error = validator.validate_required("list_all", {})
        assert error is None

    def test_validate_required_unknown_operation(self):
        """Test operation not in requirements dict."""
        validator = ParameterValidator({
            "list": ["type"],
        })
        # Operation not in requirements should have no requirements
        error = validator.validate_required("unknown", {})
        assert error is None

    def test_error_includes_details(self):
        """Test that error includes operation and required parameters."""
        validator = ParameterValidator({
            "create": ["name", "email"],
        })
        error = validator.validate_required(
            "create",
            {"name": "John"},
        )
        assert error is not None
        details = error["output"]["error"]["details"]
        assert details["operation"] == "create"
        assert "required_parameters" in details
        assert set(details["required_parameters"]) == {"name", "email"}

    def test_get_required_params(self):
        """Test getting required parameters for an operation."""
        validator = ParameterValidator({
            "create_issue": ["title", "body"],
            "get_issue": ["issue_id"],
        })
        
        assert set(validator.get_required_params("create_issue")) == {"title", "body"}
        assert validator.get_required_params("get_issue") == ["issue_id"]
        assert validator.get_required_params("unknown") == []


class TestParameterValidatorStatic:
    """Tests for static validate_required_for_operation method."""

    def test_static_method_all_present(self):
        """Test static method with all parameters present."""
        requirements = {
            "list_buckets": ["project_id"],
            "get_object": ["bucket", "key"],
        }
        error = ParameterValidator.validate_required_for_operation(
            "get_object",
            requirements,
            {"bucket": "my-bucket", "key": "my-key"},
        )
        assert error is None

    def test_static_method_one_missing(self):
        """Test static method with missing parameter."""
        requirements = {
            "get_object": ["bucket", "key"],
        }
        error = ParameterValidator.validate_required_for_operation(
            "get_object",
            requirements,
            {"bucket": "my-bucket"},
        )
        assert error is not None
        assert "Missing required key" in error["output"]["error"]["message"]

    def test_static_method_convenience(self):
        """Test static method for one-off validation."""
        error = ParameterValidator.validate_required_for_operation(
            "delete",
            {"delete": ["id"]},
            {"id": "123"},
        )
        assert error is None


class TestParameterValidatorIntegration:
    """Integration tests with server patterns."""

    def test_github_operations(self):
        """Test with GitHub-style operations."""
        validator = ParameterValidator({
            "list_issues": ["owner", "repo"],
            "get_issue": ["owner", "repo", "issue_number"],
            "create_issue": ["owner", "repo", "title"],
        })
        
        # list_issues - valid
        assert validator.validate_required(
            "list_issues",
            {"owner": "github", "repo": "hub"},
        ) is None
        
        # get_issue - valid
        assert validator.validate_required(
            "get_issue",
            {"owner": "github", "repo": "hub", "issue_number": 123},
        ) is None
        
        # create_issue - missing title
        error = validator.validate_required(
            "create_issue",
            {"owner": "github", "repo": "hub"},
        )
        assert error is not None
        assert "title" in error["output"]["error"]["message"]

    def test_aws_s3_operations(self):
        """Test with AWS S3-style operations."""
        validator = ParameterValidator({
            "list_buckets": [],
            "list_objects": ["bucket"],
            "get_object": ["bucket", "key"],
            "put_object": ["bucket", "key", "body"],
        })
        
        # list_buckets - no requirements
        assert validator.validate_required("list_buckets", {}) is None
        
        # list_objects - valid
        assert validator.validate_required(
            "list_objects",
            {"bucket": "my-bucket"},
        ) is None
        
        # get_object - missing key
        error = validator.validate_required(
            "get_object",
            {"bucket": "my-bucket"},
        )
        assert error is not None

    def test_mongodb_operations(self):
        """Test with MongoDB-style operations."""
        validator = ParameterValidator({
            "find": ["collection"],
            "insert_one": ["collection", "document"],
            "update_one": ["collection", "filter", "update"],
        })
        
        # find - valid
        assert validator.validate_required(
            "find",
            {"collection": "users"},
        ) is None
        
        # update_one - valid
        assert validator.validate_required(
            "update_one",
            {
                "collection": "users",
                "filter": {"id": 1},
                "update": {"$set": {"name": "John"}},
            },
        ) is None


class TestParameterValidatorEdgeCases:
    """Edge cases and special scenarios."""

    def test_parameter_with_zero_value(self):
        """Test that zero is treated as present."""
        validator = ParameterValidator({
            "get": ["count"],
        })
        # 0 should be treated as present (not missing)
        error = validator.validate_required("get", {"count": 0})
        assert error is None

    def test_parameter_with_false_value(self):
        """Test that False is treated as present."""
        validator = ParameterValidator({
            "update": ["enabled"],
        })
        # False should be treated as present
        error = validator.validate_required("update", {"enabled": False})
        assert error is None

    def test_parameter_with_empty_list(self):
        """Test that empty list is treated as present."""
        validator = ParameterValidator({
            "filter": ["tags"],
        })
        # Empty list should be treated as present
        error = validator.validate_required("filter", {"tags": []})
        assert error is None

    def test_parameter_with_empty_dict(self):
        """Test that empty dict is treated as present."""
        validator = ParameterValidator({
            "query": ["filters"],
        })
        # Empty dict should be treated as present
        error = validator.validate_required("query", {"filters": {}})
        assert error is None

    def test_whitespace_string_treated_as_present(self):
        """Test that whitespace string is treated as present."""
        validator = ParameterValidator({
            "search": ["query"],
        })
        # Note: Current implementation treats whitespace as present
        # This matches the behavior where only empty string is "missing"
        error = validator.validate_required("search", {"query": "   "})
        assert error is None

    def test_multiple_missing_parameters(self):
        """Test that first missing parameter is reported."""
        validator = ParameterValidator({
            "create": ["name", "email", "password"],
        })
        error = validator.validate_required("create", {})
        assert error is not None
        # Should report first missing parameter
        assert "Missing required" in error["output"]["error"]["message"]

    def test_extra_parameters_ignored(self):
        """Test that extra parameters are ignored."""
        validator = ParameterValidator({
            "get": ["id"],
        })
        error = validator.validate_required(
            "get",
            {"id": "123", "extra": "ignored", "another": "also ignored"},
        )
        assert error is None


class TestParameterValidatorUsagePatterns:
    """Tests demonstrating common usage patterns."""

    def test_pattern_validate_at_operation_start(self):
        """Test validation pattern at start of operation."""
        validator = ParameterValidator({
            "send_email": ["to", "subject", "body"],
        })
        
        # Simulate server function
        def send_email(to="", subject="", body=""):
            error = validator.validate_required(
                "send_email",
                {"to": to, "subject": subject, "body": body},
            )
            if error:
                return error
            return {"output": "Email sent"}
        
        # Valid call
        result = send_email("user@example.com", "Hello", "Message")
        assert result == {"output": "Email sent"}
        
        # Invalid call
        result = send_email("user@example.com", "Hello", "")
        assert "error" in result["output"]

    def test_pattern_with_locals(self):
        """Test using locals() for provided params."""
        validator = ParameterValidator({
            "create_user": ["username", "email"],
        })
        
        def create_user(username="", email="", role="user"):
            # Common pattern: use locals() to pass all parameters
            error = validator.validate_required("create_user", locals())
            if error:
                return error
            return {"output": f"Created {username}"}
        
        result = create_user("john", "john@example.com")
        assert "Created john" in result["output"]

    def test_pattern_conditional_requirements(self):
        """Test pattern with conditional requirements."""
        # Different operations have different requirements
        validator = ParameterValidator({
            "authenticate_password": ["username", "password"],
            "authenticate_token": ["token"],
        })
        
        def authenticate(method, username="", password="", token=""):
            error = validator.validate_required(
                f"authenticate_{method}",
                {"username": username, "password": password, "token": token},
            )
            if error:
                return error
            return {"output": "Authenticated"}
        
        # Password auth
        result = authenticate("password", "user", "pass123")
        assert result == {"output": "Authenticated"}
        
        # Token auth
        result = authenticate("token", token="abc123")
        assert result == {"output": "Authenticated"}
