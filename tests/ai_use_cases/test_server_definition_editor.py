"""Tests for AI assistance in server definition editor.

Use Cases:
1. Add input validation to a server definition
2. Add logging to a server definition
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_python,
    assert_no_errors_in_response,
)


def test_add_input_validation(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI adds input validation to server definition.

    Use Case 1: User editing hello_world server wants to add validation
    to reject empty names.
    """
    # Use Case 1 initial content
    original_text = '''def main(name="World"):
    """Simple greeting server."""
    return {
        "output": f"Hello, {name}!",
        "content_type": "text/plain"
    }'''

    payload = {
        "request_text": "Add input validation to reject empty names",
        "original_text": original_text,
        "target_label": "server definition",
        "context_data": {"form": "server_form", "server_name": "hello_world"},
        "form_summary": {"definition": original_text},
    }

    response, _ = ai_interaction_tracker.call_with_capture(
        memory_client, "post", "/ai", json=payload, follow_redirects=True
    )
    ai_interaction_tracker(payload, response.get_json(), response.status_code)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.content_type == "application/json"

    data = response.get_json()
    assert "updated_text" in data, "Response missing 'updated_text' field"

    # Verify no errors
    assert_no_errors_in_response(data)

    updated_text = data["updated_text"]

    # Verify AI produced output
    assert_ai_output_valid(updated_text)

    # Verify input validation added
    assert "if" in updated_text, "Missing conditional for validation"
    assert "name" in updated_text.lower(), "Missing validation of 'name' parameter"

    # Verify original logic preserved
    assert "Hello" in updated_text, "Original greeting logic lost"

    # Verify valid Python
    assert_valid_python(updated_text)

    # Verify function signature preserved
    assert "def main(" in updated_text, "Function signature changed"


def test_add_logging(
    memory_client, requires_openrouter_api_key, ai_interaction_tracker
):
    """Test AI adds logging to server definition.

    Use Case 2: User wants to add logging before and after data processing.
    """
    original_text = '''def main(data=""):
    """Process incoming data."""
    processed = data.upper()
    return {
        "output": processed,
        "content_type": "text/plain"
    }'''

    payload = {
        "request_text": "Add logging before and after processing",
        "original_text": original_text,
        "target_label": "server definition",
        "context_data": {"form": "server_form"},
        "form_summary": {"definition": original_text},
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

    # Verify logging import added
    assert "import logging" in updated_text or "from logging" in updated_text, (
        "Missing logging import"
    )

    # Verify logging calls present (look for logging.info, logging.debug, etc.)
    logging_call_count = (
        updated_text.count("logging.info")
        + updated_text.count("logging.debug")
        + updated_text.count("logging.warning")
    )
    assert logging_call_count >= 2, (
        f"Expected at least 2 logging calls, found {logging_call_count}"
    )

    # Verify original logic preserved
    assert ".upper()" in updated_text, "Original processing logic lost"
    assert "processed" in updated_text, "Processed variable lost"

    # Verify valid Python
    assert_valid_python(updated_text)
