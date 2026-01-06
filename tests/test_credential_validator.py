"""Tests for credential validator utility."""

from __future__ import annotations

from server_utils.external_api.credential_validator import CredentialValidator


class TestCredentialValidator:
    """Tests for CredentialValidator class."""

    def test_require_secrets_all_present(self):
        """Test that require_secrets passes when all secrets are provided."""
        error = CredentialValidator.require_secrets(
            API_KEY="my-key",
            API_SECRET="my-secret",
        )
        assert error is None

    def test_require_secrets_one_missing(self):
        """Test that require_secrets fails when one secret is missing."""
        error = CredentialValidator.require_secrets(
            API_KEY="my-key",
            API_SECRET="",
        )
        assert error is not None
        assert "output" in error
        assert "error" in error["output"]
        assert "Missing API_SECRET" in error["output"]["error"]

    def test_require_secrets_all_missing(self):
        """Test that require_secrets fails when all secrets are missing."""
        error = CredentialValidator.require_secrets(
            API_KEY="",
            API_SECRET="",
        )
        assert error is not None
        # Should return error for the first missing secret
        assert "Missing" in error["output"]["error"]

    def test_require_secrets_with_status_code(self):
        """Test that error includes 401 status code."""
        error = CredentialValidator.require_secrets(
            API_KEY="",
        )
        assert error is not None
        assert error["output"]["status_code"] == 401

    def test_require_secret_present(self):
        """Test require_secret with present secret."""
        error = CredentialValidator.require_secret("my-key", "API_KEY")
        assert error is None

    def test_require_secret_missing(self):
        """Test require_secret with missing secret."""
        error = CredentialValidator.require_secret("", "API_KEY")
        assert error is not None
        assert "Missing API_KEY" in error["output"]["error"]
        assert error["output"]["status_code"] == 401

    def test_require_secret_none_value(self):
        """Test require_secret with None value."""
        error = CredentialValidator.require_secret(None, "API_KEY")
        assert error is not None
        assert "Missing API_KEY" in error["output"]["error"]

    def test_require_one_of_first_present(self):
        """Test require_one_of when first secret is present."""
        error = CredentialValidator.require_one_of(
            API_KEY="my-key",
            ACCESS_TOKEN="",
        )
        assert error is None

    def test_require_one_of_second_present(self):
        """Test require_one_of when second secret is present."""
        error = CredentialValidator.require_one_of(
            API_KEY="",
            ACCESS_TOKEN="my-token",
        )
        assert error is None

    def test_require_one_of_both_present(self):
        """Test require_one_of when both secrets are present."""
        error = CredentialValidator.require_one_of(
            API_KEY="my-key",
            ACCESS_TOKEN="my-token",
        )
        assert error is None

    def test_require_one_of_none_present(self):
        """Test require_one_of when no secrets are present."""
        error = CredentialValidator.require_one_of(
            API_KEY="",
            ACCESS_TOKEN="",
        )
        assert error is not None
        assert "Missing required authentication" in error["output"]["error"]
        assert "API_KEY or ACCESS_TOKEN" in error["output"]["error"]
        assert error["output"]["status_code"] == 401

    def test_require_one_of_multiple_options(self):
        """Test require_one_of with multiple options."""
        error = CredentialValidator.require_one_of(
            API_KEY="",
            ACCESS_TOKEN="",
            SERVICE_ACCOUNT="my-account",
        )
        assert error is None


class TestCredentialValidatorIntegration:
    """Integration tests with server patterns."""

    def test_aws_credentials_pattern(self):
        """Test with AWS-style credentials."""
        error = CredentialValidator.require_secrets(
            AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE",
            AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        assert error is None

    def test_aws_missing_secret_key(self):
        """Test AWS pattern with missing secret key."""
        error = CredentialValidator.require_secrets(
            AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE",
            AWS_SECRET_ACCESS_KEY="",
        )
        assert error is not None
        assert "AWS_SECRET_ACCESS_KEY" in error["output"]["error"]

    def test_github_token_pattern(self):
        """Test with GitHub token pattern."""
        error = CredentialValidator.require_secret(
            "ghp_1234567890abcdef",
            "GITHUB_TOKEN",
        )
        assert error is None

    def test_oauth_token_or_key_pattern(self):
        """Test OAuth token or API key pattern."""
        # With token
        error = CredentialValidator.require_one_of(
            API_KEY="",
            OAUTH_TOKEN="oauth-token-123",
        )
        assert error is None

        # With API key
        error = CredentialValidator.require_one_of(
            API_KEY="api-key-123",
            OAUTH_TOKEN="",
        )
        assert error is None


class TestCredentialValidatorEdgeCases:
    """Edge cases and special scenarios."""

    def test_empty_string_vs_none(self):
        """Test that both empty string and None are treated as missing."""
        error1 = CredentialValidator.require_secret("", "KEY")
        error2 = CredentialValidator.require_secret(None, "KEY")

        assert error1 is not None
        assert error2 is not None
        assert "Missing KEY" in error1["output"]["error"]
        assert "Missing KEY" in error2["output"]["error"]

    def test_whitespace_only_secret(self):
        """Test that whitespace-only secret is treated as present."""
        # Note: Current implementation treats whitespace as present
        # This is intentional as some APIs might use whitespace in keys
        error = CredentialValidator.require_secret("   ", "KEY")
        assert error is None

    def test_secret_names_preserved_in_error(self):
        """Test that secret names are preserved exactly in error messages."""
        error = CredentialValidator.require_secrets(
            MY_CUSTOM_API_KEY="",
        )
        assert error is not None
        assert "MY_CUSTOM_API_KEY" in error["output"]["error"]

    def test_multiple_missing_secrets_returns_first(self):
        """Test that only first missing secret is reported."""
        error = CredentialValidator.require_secrets(
            FIRST_KEY="",
            SECOND_KEY="",
            THIRD_KEY="",
        )
        assert error is not None
        # Should mention at least one missing key
        assert "Missing" in error["output"]["error"]

    def test_require_one_of_single_option(self):
        """Test require_one_of with only one option."""
        error = CredentialValidator.require_one_of(API_KEY="my-key")
        assert error is None

        error = CredentialValidator.require_one_of(API_KEY="")
        assert error is not None


class TestCredentialValidatorUsagePatterns:
    """Tests demonstrating common usage patterns."""

    def test_basic_api_key_validation(self):
        """Test basic API key validation pattern."""
        api_key = "test-key"
        error = CredentialValidator.require_secret(api_key, "API_KEY")
        assert error is None

    def test_multiple_required_credentials(self):
        """Test validating multiple required credentials."""
        access_key = "access-123"
        secret_key = "secret-456"
        error = CredentialValidator.require_secrets(
            AWS_ACCESS_KEY_ID=access_key,
            AWS_SECRET_ACCESS_KEY=secret_key,
        )
        assert error is None

    def test_optional_auth_methods(self):
        """Test pattern with multiple auth methods (use one)."""
        # Scenario: User provides OAuth token, not API key
        api_key = ""
        oauth_token = "token-123"
        error = CredentialValidator.require_one_of(
            API_KEY=api_key,
            OAUTH_TOKEN=oauth_token,
        )
        assert error is None

    def test_azure_connection_string_or_keys(self):
        """Test Azure pattern with connection string OR keys."""
        # With connection string
        connection_string = "DefaultEndpointsProtocol=https;..."
        error = CredentialValidator.require_one_of(
            AZURE_CONNECTION_STRING=connection_string,
            AZURE_ACCOUNT_KEY="",
        )
        assert error is None
