"""Tests for AI assistance in upload form.

Use Case 5: Convert plain text to markdown list with descriptions
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_no_errors_in_response,
)


def test_convert_to_markdown_list(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI converts plain text to markdown list.

    Use Case 5: User uploading content wants to convert a plain feature list
    to a formatted markdown list with descriptions.
    """
    original_text = """Product Features
Fast Performance
Easy to Use
Secure"""

    payload = {
        "request_text": "Convert to markdown list with descriptions",
        "original_text": original_text,
        "target_label": "text content",
        "context_data": {"form": "upload"},
        "form_summary": {"text_content": original_text},
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

    # Verify markdown list markers present
    has_markers = "-" in updated_text or "*" in updated_text or "1." in updated_text
    assert has_markers, "No markdown list markers found"

    # Verify bold markers for emphasis
    assert "**" in updated_text or "__" in updated_text, "No bold formatting found"

    # Verify original items present (case insensitive)
    updated_lower = updated_text.lower()
    assert "fast" in updated_lower and "performance" in updated_lower, (
        "Missing 'Fast Performance'"
    )
    assert "easy" in updated_lower and "use" in updated_lower, "Missing 'Easy to Use'"
    assert "secure" in updated_lower, "Missing 'Secure'"

    # Verify descriptions added (result should be significantly longer)
    assert len(updated_text) > len(original_text) * 1.3, (
        f"Output not expanded enough: {len(updated_text)} vs {len(original_text)}"
    )
