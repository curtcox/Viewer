"""Tests for AI assistance in import form.

Use Case 6: Convert CSV data to JSON array
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_json,
    assert_no_errors_in_response,
)


def test_csv_to_json_conversion(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI converts CSV to JSON array.

    Use Case 6: User importing data wants to convert CSV format to JSON
    for easier manipulation.
    """
    original_text = """Name,Status,Priority
Task 1,open,high
Task 2,closed,low
Task 3,open,medium"""

    payload = {
        "request_text": "Convert to JSON array of objects",
        "original_text": original_text,
        "target_label": "import data",
        "context_data": {"form": "import"},
        "form_summary": {"import_text": original_text},
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

    # Verify array structure
    assert isinstance(parsed, list), f"Expected JSON array, got {type(parsed)}"
    assert len(parsed) == 3, f"Expected 3 items, got {len(parsed)}"

    # Verify all fields present in each object
    for i, item in enumerate(parsed):
        assert isinstance(item, dict), f"Item {i} is not an object"

        # Check for name field (case insensitive)
        has_name = any(k.lower() == "name" for k in item.keys())
        assert has_name, f"Item {i} missing name field"

        # Check for status field (case insensitive)
        has_status = any(k.lower() == "status" for k in item.keys())
        assert has_status, f"Item {i} missing status field"

        # Check for priority field (case insensitive)
        has_priority = any(k.lower() == "priority" for k in item.keys())
        assert has_priority, f"Item {i} missing priority field"

    # Verify data values preserved
    all_text = str(parsed).lower()
    assert "task 1" in all_text, "Missing 'Task 1'"
    assert "open" in all_text, "Missing 'open' status"
    assert "high" in all_text, "Missing 'high' priority"
