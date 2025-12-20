"""Tests for AI assistance in CID content editor.

Use Case 4: Add email field to JSON user objects
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_json,
    assert_no_errors_in_response,
)


def test_add_email_field(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI adds email field to JSON objects.

    Use Case 4: User editing CID content wants to add an email field
    to each user in a JSON structure.
    """
    original_text = """{"users": [
    {"name": "Alice", "role": "admin"},
    {"name": "Bob", "role": "user"}
]}"""

    payload = {
        "request_text": "Add an email field to each user",
        "original_text": original_text,
        "target_label": "CID content",
        "context_data": {"form": "cid_editor"},
        "form_summary": {"content": original_text},
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

    # Verify structure
    assert "users" in parsed, "Missing 'users' key"
    assert isinstance(parsed["users"], list), "Users should be a list"
    assert len(parsed["users"]) == 2, f"Expected 2 users, got {len(parsed['users'])}"

    # Verify all users have email field
    for user in parsed["users"]:
        assert "email" in user, (
            f"User {user.get('name', 'unknown')} missing email field"
        )
        assert "@" in user["email"], f"Email doesn't look valid: {user['email']}"

    # Verify original fields preserved
    assert parsed["users"][0]["name"] == "Alice", "Alice's name changed"
    assert parsed["users"][0]["role"] == "admin", "Alice's role changed"
    assert parsed["users"][1]["name"] == "Bob", "Bob's name changed"
    assert parsed["users"][1]["role"] == "user", "Bob's role changed"
