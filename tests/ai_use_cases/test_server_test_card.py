"""Tests for AI assistance in server test card.

Use Case 9: Add filtering and sorting to query parameters
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_query_string,
    assert_no_errors_in_response,
)


def test_add_query_filters(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI adds query parameters for filtering and sorting.

    Use Case 9: User testing a server wants to add filtering by status
    and sorting by date descending.
    """
    original_text = "page=1&limit=10"

    payload = {
        "request_text": "Add filtering by status and sorting by date descending",
        "original_text": original_text,
        "target_label": "query parameters",
        "context_data": {"form": "server_test"},
        "form_summary": {"query_params": original_text},
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

    # Verify original params preserved
    assert "page=1" in updated_text or "page%3D1" in updated_text, (
        "Original 'page=1' parameter lost"
    )
    assert "limit=10" in updated_text or "limit%3D10" in updated_text, (
        "Original 'limit=10' parameter lost"
    )

    # Verify status filter added
    assert "status=" in updated_text, "Missing status parameter"

    # Verify sort/order parameters added (flexible naming)
    has_sort = (
        "sort=" in updated_text
        or "order=" in updated_text
        or "orderBy=" in updated_text
        or "sortBy=" in updated_text
    )
    assert has_sort, "Missing sort/order parameter"

    # Verify valid query string format
    assert_valid_query_string(updated_text)

    # Verify reasonable length
    assert len(updated_text) < 500, (
        f"Query string too long: {len(updated_text)} characters"
    )
