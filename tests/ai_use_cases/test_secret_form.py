"""Tests for AI assistance in secret form.

Use Case 7: Add retry configuration to JSON secret
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_json,
    assert_no_errors_in_response,
)


def test_add_retry_configuration(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI adds retry configuration to JSON.

    Use Case 7: User configuring API secrets wants to add retry logic
    with exponential backoff.
    """
    original_text = """{
    "endpoint": "https://api.example.com",
    "timeout": 30
}"""

    payload = {
        "request_text": "Add retry configuration with 3 attempts and exponential backoff",
        "original_text": original_text,
        "target_label": "secret value",
        "context_data": {"form": "secret_form"},
        "form_summary": {"value": original_text},
    }

    response, _ = ai_interaction_tracker.call_with_capture(
        memory_client, "post", "/ai", json=payload, follow_redirects=True
    )
    ai_interaction_tracker(payload, response.get_json(), response.status_code)

    assert response.status_code == 200
    data = response.get_json()
    assert_no_errors_in_response(data)

    updated_text = data["updated_text"]
    assert_ai_output_valid(updated_text)

    # Verify valid JSON
    parsed = assert_valid_json(updated_text)

    # Verify original fields preserved
    assert parsed["endpoint"] == "https://api.example.com", "Endpoint changed"
    assert parsed["timeout"] == 30, "Timeout changed"

    # Verify retry configuration added
    assert "retry" in parsed, "Missing retry configuration"
    retry = parsed["retry"]
    assert isinstance(retry, dict), "Retry should be an object"

    # Check for max attempts (flexible field naming)
    attempts_field = (
        retry.get("max_attempts")
        or retry.get("maxAttempts")
        or retry.get("attempts")
        or retry.get("max_retries")
    )
    assert attempts_field == 3, f"Expected 3 attempts, got {attempts_field}"

    # Check for exponential backoff mention
    retry_str = str(retry).lower()
    assert "exponential" in retry_str, "Missing exponential backoff strategy"
