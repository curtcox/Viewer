"""Property tests for Authorization module."""

from hypothesis import assume, example, given, strategies as st
import pytest

from authorization import AuthorizationResult


# ============================================================================
# Strategies
# ============================================================================


def valid_status_codes():
    """Generate valid status codes for authorization (401, 403)."""
    return st.sampled_from([401, 403])


def invalid_status_codes():
    """Generate invalid status codes (not 401 or 403)."""
    return st.integers(min_value=200, max_value=599).filter(lambda x: x not in (401, 403))


def rejection_messages():
    """Generate rejection messages."""
    return st.text(min_size=1, max_size=200)


# ============================================================================
# Property Tests
# ============================================================================


@given(st.booleans())
@example(True)
@example(False)
def test_authorization_result_allowed_creation(allowed):
    """Creating an AuthorizationResult with allowed=True should not require status or message."""
    if allowed:
        # Should succeed without status_code or message
        result = AuthorizationResult(allowed=True)
        assert result.allowed is True
        assert result.status_code is None
        assert result.message is None
    else:
        # Should fail without status_code and message
        with pytest.raises(ValueError, match="status_code is required"):
            AuthorizationResult(allowed=False)


@given(valid_status_codes(), rejection_messages())
@example(401, "Authentication required")
@example(403, "Access denied")
def test_authorization_result_rejection_with_valid_status(status_code, message):
    """Creating a rejected AuthorizationResult with valid status and message should succeed."""
    result = AuthorizationResult(
        allowed=False,
        status_code=status_code,
        message=message,
    )
    
    assert result.allowed is False
    assert result.status_code == status_code
    assert result.message == message


@given(rejection_messages())
@example("Authentication required")
@example("Access denied")
def test_authorization_result_rejection_without_status_code(message):
    """Creating a rejected AuthorizationResult without status_code should raise ValueError."""
    with pytest.raises(ValueError, match="status_code is required"):
        AuthorizationResult(
            allowed=False,
            status_code=None,
            message=message,
        )


@given(valid_status_codes())
@example(401)
@example(403)
def test_authorization_result_rejection_without_message(status_code):
    """Creating a rejected AuthorizationResult without message should raise ValueError."""
    with pytest.raises(ValueError, match="message is required"):
        AuthorizationResult(
            allowed=False,
            status_code=status_code,
            message=None,
        )


@given(invalid_status_codes(), rejection_messages())
@example(200, "OK")
@example(404, "Not Found")
@example(500, "Internal Server Error")
def test_authorization_result_invalid_status_code(status_code, message):
    """Creating an AuthorizationResult with invalid status code should raise ValueError."""
    assume(status_code not in (401, 403))
    
    with pytest.raises(ValueError, match="status_code must be 401 or 403"):
        AuthorizationResult(
            allowed=False,
            status_code=status_code,
            message=message,
        )


@given(valid_status_codes(), rejection_messages())
@example(401, "Auth needed")
@example(403, "Forbidden")
def test_authorization_result_properties_preserved(status_code, message):
    """AuthorizationResult should preserve all properties correctly."""
    result = AuthorizationResult(
        allowed=False,
        status_code=status_code,
        message=message,
    )
    
    # Properties should be preserved
    assert result.allowed is False
    assert result.status_code == status_code
    assert result.message == message
    assert isinstance(result.allowed, bool)
    assert isinstance(result.status_code, int)
    assert isinstance(result.message, str)


def test_authorization_result_allowed_true_defaults():
    """When allowed=True, status_code and message should default to None."""
    result = AuthorizationResult(allowed=True)
    
    assert result.allowed is True
    assert result.status_code is None
    assert result.message is None


@given(st.sampled_from([401, 403]))
@example(401)
@example(403)
def test_authorization_result_only_valid_codes_accepted(status_code):
    """Only 401 and 403 should be accepted as valid rejection status codes."""
    # This should succeed
    result = AuthorizationResult(
        allowed=False,
        status_code=status_code,
        message="Test message",
    )
    assert result.status_code in (401, 403)


@given(rejection_messages())
@example("Authentication required")
def test_authorization_result_message_not_empty(message):
    """Rejection messages should not be empty strings."""
    assume(len(message) > 0)
    
    result = AuthorizationResult(
        allowed=False,
        status_code=401,
        message=message,
    )
    
    assert len(result.message) > 0
    assert result.message == message
