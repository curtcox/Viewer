"""Tests for AI assistance in alias definition editor.

Use Case 3: Add query parameters to an alias definition
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_query_string,
    assert_no_errors_in_response
)


def test_add_query_parameters(memory_client, requires_openrouter_api_key, ai_interaction_tracker):
    """Test AI adds query parameters to alias.

    Use Case 3: User wants to add query parameters for name and greeting style
    to the hello_world server alias.
    """
    original_text = '/servers/hello_world'

    payload = {
        'request_text': 'Add query parameters for name and greeting style',
        'original_text': original_text,
        'target_label': 'alias definition',
        'context_data': {'form': 'alias_form'},
        'form_summary': {'definition': original_text}
    }

    response = memory_client.post('/ai', json=payload, follow_redirects=True)
    ai_interaction_tracker(payload, response.get_json(), response.status_code)

    assert response.status_code == 200
    data = response.get_json()
    assert_no_errors_in_response(data)

    updated_text = data['updated_text']
    assert_ai_output_valid(updated_text)

    # Verify original path preserved
    assert '/servers/hello_world' in updated_text, "Original path lost"

    # Verify query parameters added
    assert '?' in updated_text, "No query string separator found"
    assert 'name=' in updated_text, "Missing 'name' parameter"
    assert 'style=' in updated_text or 'greeting=' in updated_text, \
        "Missing style/greeting parameter"

    # Verify reasonable length (not too long)
    assert len(updated_text) < 500, f"Alias too long: {len(updated_text)} characters"

    # Verify valid query string format
    assert_valid_query_string(updated_text)
