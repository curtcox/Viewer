"""Tests for AI assistance in variable form.

Use Case 8: Add feature flags to configuration JSON
"""

from tests.ai_use_cases.assertions import (
    assert_ai_output_valid,
    assert_valid_json,
    assert_no_errors_in_response
)


def test_add_feature_flags(memory_client, requires_openrouter_api_key, ai_interaction_tracker):
    """Test AI adds feature flags to configuration JSON.

    Use Case 8: User configuring application wants to add feature flags
    for dark mode and experimental features.
    """
    original_text = '''{
    "app_name": "Viewer",
    "version": "1.0.0"
}'''

    payload = {
        'request_text': 'Add feature flags for dark mode and experimental features',
        'original_text': original_text,
        'target_label': 'variable value',
        'context_data': {'form': 'variable_form'},
        'form_summary': {'value': original_text}
    }

    response, _ = ai_interaction_tracker.call_with_capture(
        memory_client, 'post', '/ai', json=payload, follow_redirects=True
    )
    ai_interaction_tracker(payload, response.get_json(), response.status_code)

    assert response.status_code == 200
    data = response.get_json()
    assert_no_errors_in_response(data)

    updated_text = data['updated_text']
    assert_ai_output_valid(updated_text)

    # Verify valid JSON
    parsed = assert_valid_json(updated_text)

    # Verify original fields preserved
    assert parsed['app_name'] == 'Viewer', "App name changed"
    assert parsed['version'] == '1.0.0', "Version changed"

    # Verify features object added
    assert 'features' in parsed or 'feature_flags' in parsed, \
        "Missing features/feature_flags object"

    features = parsed.get('features') or parsed.get('feature_flags')
    assert isinstance(features, dict), "Features should be an object"

    # Verify dark mode flag (flexible naming)
    has_dark_mode = any(
        'dark' in key.lower() and 'mode' in key.lower()
        for key in features.keys()
    )
    assert has_dark_mode, "Missing dark mode flag"

    # Get dark mode value
    dark_mode_key = next(
        key for key in features.keys()
        if 'dark' in key.lower() and 'mode' in key.lower()
    )
    dark_mode_value = features[dark_mode_key]
    assert isinstance(dark_mode_value, bool), \
        f"Dark mode should be boolean, got {type(dark_mode_value)}"

    # Verify experimental features flag
    has_experimental = any(
        'experimental' in key.lower() or 'experiment' in key.lower()
        for key in features.keys()
    )
    assert has_experimental, "Missing experimental features flag"
