"""Step implementations for pipeline debug specs."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from getgauge.python import step

from step_impl.shared_app import get_shared_app
from step_impl.shared_state import get_scenario_state


def _request_debug_path_and_store_response(path: str) -> None:
    """Request a path and store response in scenario state."""
    state = get_scenario_state()
    app = get_shared_app()

    with app.test_client() as client:
        response = client.get(path, follow_redirects=False)
        state["debug_response"] = response
        state["debug_response_data"] = response.get_data(as_text=True)


def _get_debug_response_json() -> Optional[Dict[str, Any]]:
    """Get the debug response as parsed JSON."""
    state = get_scenario_state()
    data = state.get("debug_response_data")
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None


@step("And the response should be valid JSON")
def and_response_should_be_valid_json() -> None:
    """Assert the stored debug response body is valid JSON."""
    parsed = _get_debug_response_json()
    assert parsed is not None, "Response is not valid JSON"


@step(
    [
        "When I request /<path>?debug=true",
    ]
)
def when_request_with_debug_true(path: str) -> None:
    """Request a path with debug=true query parameter."""
    state = get_scenario_state()

    if "{stored CID}" in path:
        cid = state.get("last_cid")
        assert cid, "No CID stored. Use 'And a CID containing' first."
        path = path.replace("{stored CID}", cid)

    if "{echo server}" in path:
        path = path.replace("{echo server}", "echo")

    _request_debug_path_and_store_response(f"/{path}?debug=true")


@step("When I request /<path>?debug=1")
def when_request_with_debug_1(path: str) -> None:
    """Request a path with debug=1 query parameter."""
    state = get_scenario_state()
    if "{stored CID}" in path:
        cid = state.get("last_cid")
        assert cid, "No CID stored. Use 'And a CID containing' first."
        path = path.replace("{stored CID}", cid)
    if "{echo server}" in path:
        path = path.replace("{echo server}", "echo")
    _request_debug_path_and_store_response(f"/{path}?debug=1")


@step("When I request /<path>?debug=yes")
def when_request_with_debug_yes(path: str) -> None:
    """Request a path with debug=yes query parameter."""
    state = get_scenario_state()
    if "{stored CID}" in path:
        cid = state.get("last_cid")
        assert cid, "No CID stored. Use 'And a CID containing' first."
        path = path.replace("{stored CID}", cid)
    if "{echo server}" in path:
        path = path.replace("{echo server}", "echo")
    _request_debug_path_and_store_response(f"/{path}?debug=yes")


@step("When I request /<path>?debug=on")
def when_request_with_debug_on(path: str) -> None:
    """Request a path with debug=on query parameter."""
    state = get_scenario_state()
    if "{stored CID}" in path:
        cid = state.get("last_cid")
        assert cid, "No CID stored. Use 'And a CID containing' first."
        path = path.replace("{stored CID}", cid)
    if "{echo server}" in path:
        path = path.replace("{echo server}", "echo")
    _request_debug_path_and_store_response(f"/{path}?debug=on")


@step("When I request /<path>?debug=TRUE")
def when_request_with_debug_true_upper(path: str) -> None:
    """Request a path with debug=TRUE query parameter."""
    state = get_scenario_state()
    if "{stored CID}" in path:
        cid = state.get("last_cid")
        assert cid, "No CID stored. Use 'And a CID containing' first."
        path = path.replace("{stored CID}", cid)
    if "{echo server}" in path:
        path = path.replace("{echo server}", "echo")
    _request_debug_path_and_store_response(f"/{path}?debug=TRUE")


@step("When I request /<path>?debug=random")
def when_request_with_debug_random(path: str) -> None:
    """Request a path with debug=random query parameter."""
    state = get_scenario_state()
    if "{stored CID}" in path:
        cid = state.get("last_cid")
        assert cid, "No CID stored. Use 'And a CID containing' first."
        path = path.replace("{stored CID}", cid)
    if "{echo server}" in path:
        path = path.replace("{echo server}", "echo")
    _request_debug_path_and_store_response(f"/{path}?debug=random")


@step("When I request /{echo server}/{stored CID}?debug=true")
def when_request_echo_with_cid_debug() -> None:
    """Request echo server with CID and debug mode."""
    state = get_scenario_state()
    cid = state.get("last_cid")
    assert cid, "No CID stored. Use 'And a CID containing' first."
    _request_debug_path_and_store_response(f"/echo/{cid}?debug=true")


@step("When I request /{stored CID}.py/next?debug=true")
def when_request_cid_py_debug() -> None:
    """Request CID with .py extension and debug mode."""
    state = get_scenario_state()
    cid = state.get("last_cid")
    assert cid, "No CID stored. Use 'And a CID containing' first."
    _request_debug_path_and_store_response(f"/{cid}.py/next?debug=true")


@step("Then the response should be JSON")
def then_response_is_json() -> None:
    """Assert the response is valid JSON."""
    state = get_scenario_state()
    data = state.get("debug_response_data")
    assert data, "No response data recorded."

    try:
        json.loads(data)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Response is not valid JSON: {e}") from e


@step("Then the response should be valid JSON")
def then_response_is_valid_json() -> None:
    """Assert the response is valid JSON (alias)."""
    then_response_is_json()


@step(
    [
        'Then the response Content-Type should be "<content_type>"',
        "Then the response Content-Type should be <content_type>",
    ]
)
def then_content_type_is(content_type: str) -> None:
    """Assert the response has the expected content type."""
    state = get_scenario_state()
    response = state.get("debug_response")
    assert response, "No response recorded."

    actual = response.content_type
    # Content-Type may include charset
    assert content_type in actual, (
        f"Expected Content-Type '{content_type}' but got '{actual}'"
    )


@step(
    [
        "And the response should contain <count> segment entries",
        "Then the response should contain <count> segment entries",
    ]
)
def response_contains_segment_count(count: str) -> None:
    """Assert the response contains the expected number of segments."""
    expected_count = int(count)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert len(segments) == expected_count, (
        f"Expected {expected_count} segments but found {len(segments)}"
    )


@step("And the response should contain segment entries")
def response_contains_segments() -> None:
    """Assert the response contains at least one segment."""
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert len(segments) > 0, "Expected at least one segment entry"


@step("And the response should contain 1 segment entry")
def response_contains_one_segment() -> None:
    """Assert the response contains exactly one segment."""
    response_contains_segment_count("1")


@step(
    [
        'And segment <index> should have type "<segment_type>"',
        'Then segment <index> should have type "<segment_type>"',
    ]
)
def segment_has_type(index: str, segment_type: str) -> None:
    """Assert a segment has the expected type."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found (only {len(segments)} segments)"

    actual = segments[idx].get("segment_type")
    assert actual == segment_type, (
        f"Expected segment {idx} type '{segment_type}' but got '{actual}'"
    )


@step(
    [
        'And segment <index> should have server_name "<name>"',
        'Then segment <index> should have server_name "<name>"',
    ]
)
def segment_has_server_name(index: str, name: str) -> None:
    """Assert a segment has the expected server name."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    actual = segments[idx].get("server_name")
    assert actual == name, (
        f"Expected segment {idx} server_name '{name}' but got '{actual}'"
    )


@step("And segment <index> should have is_valid_cid true")
def segment_has_valid_cid(index: str) -> None:
    """Assert a segment has is_valid_cid true."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    is_valid = segments[idx].get("is_valid_cid")
    assert is_valid is True, f"Expected segment {idx} is_valid_cid to be true"


@step(
    [
        'And segment <index> should have intermediate_output "<output>"',
        'Then segment <index> should have intermediate_output "<output>"',
    ]
)
def segment_has_intermediate_output(index: str, output: str) -> None:
    """Assert a segment has the expected intermediate output."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    actual = segments[idx].get("intermediate_output")
    assert actual == output, (
        f"Expected segment {idx} intermediate_output '{output}' but got '{actual}'"
    )


@step(
    [
        'And the response final_output should contain "<text>"',
        'Then the response final_output should contain "<text>"',
    ]
)
def final_output_contains(text: str) -> None:
    """Assert the final output contains the expected text."""
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    final_output = data.get("final_output", "")
    assert text in str(final_output), (
        f"Expected final_output to contain '{text}' but got '{final_output}'"
    )


@step(
    [
        'And segment <index> should have errors containing "<error_text>"',
        'Then segment <index> should have errors containing "<error_text>"',
    ]
)
def segment_has_error_containing(index: str, error_text: str) -> None:
    """Assert a segment has an error containing the expected text."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    errors = segments[idx].get("errors", [])
    error_found = any(error_text in e for e in errors)
    assert error_found, (
        f"Expected segment {idx} errors to contain '{error_text}', got: {errors}"
    )


@step(
    [
        'And segment <index> should have implementation_language "<language>"',
        'Then segment <index> should have implementation_language "<language>"',
    ]
)
def segment_has_language(index: str, language: str) -> None:
    """Assert a segment has the expected implementation language."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    actual = segments[idx].get("implementation_language")
    assert actual == language, (
        f"Expected segment {idx} implementation_language '{language}' but got '{actual}'"
    )


@step("And segment <index> should have supports_chaining true")
def segment_supports_chaining(index: str) -> None:
    """Assert a segment supports chaining."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    supports = segments[idx].get("supports_chaining")
    assert supports is True, f"Expected segment {idx} supports_chaining to be true"


@step(
    [
        'And segment <index> should have resolution_type "<res_type>"',
        'Then segment <index> should have resolution_type "<res_type>"',
    ]
)
def segment_has_resolution_type(index: str, res_type: str) -> None:
    """Assert a segment has the expected resolution type."""
    idx = int(index)
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    segments = data.get("segments", [])
    assert idx < len(segments), f"Segment {idx} not found"

    actual = segments[idx].get("resolution_type")
    assert actual == res_type, (
        f"Expected segment {idx} resolution_type '{res_type}' but got '{actual}'"
    )


@step("And the response success should be true")
def response_success_is_true() -> None:
    """Assert the response success field is true."""
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    success = data.get("success")
    assert success is True, f"Expected success to be true but got {success}"


@step("And the response success should be false")
def response_success_is_false() -> None:
    """Assert the response success field is false."""
    data = _get_debug_response_json()
    assert data, "Response is not valid JSON."

    success = data.get("success")
    assert success is False, f"Expected success to be false but got {success}"


@step("Then the response should NOT be JSON debug output")
def response_is_not_debug_json() -> None:
    """Assert the response is not a JSON debug output."""
    data = _get_debug_response_json()
    if data is None:
        # Not JSON at all, which is fine
        return

    # If it is JSON, it should not have a "segments" key
    if "segments" in data:
        raise AssertionError(
            "Expected non-debug response but got JSON with 'segments' key"
        )


@step("And the response status should be a redirect")
def response_is_redirect() -> None:
    """Assert the response is a redirect."""
    state = get_scenario_state()
    response = state.get("debug_response")
    assert response, "No response recorded."

    status = response.status_code
    assert 300 <= status < 400, f"Expected redirect status but got {status}"
