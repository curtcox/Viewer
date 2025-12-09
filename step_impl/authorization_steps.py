"""Gauge step implementations for authorization testing."""

import json
from getgauge.python import step
from unittest.mock import patch

from authorization import AuthorizationResult
from step_impl.shared_app import get_shared_client
from step_impl.shared_state import get_scenario_state
from step_impl.artifacts import attach_response_snapshot


@step("Given authorization is configured to reject requests with <status_code>")
def configure_authorization_rejection(status_code: str):
    """Configure authorization to reject requests with specified status code."""
    status = int(status_code)

    # Create a mock that will reject requests
    def mock_authorize(_request):
        if status == 401:
            return AuthorizationResult(
                allowed=False,
                status_code=401,
                message="Authentication required for testing"
            )
        if status == 403:
            return AuthorizationResult(
                allowed=False,
                status_code=403,
                message="Access denied for testing"
            )

        return AuthorizationResult(allowed=True)

    # Store the mock in scenario state so it can be used by request steps
    state = get_scenario_state()
    state['auth_mock'] = mock_authorize
    state['auth_status'] = status


@step("When I request the page <path> with Accept header <accept_header>")
def request_page_with_accept_header(path: str, accept_header: str):
    """Request a page with a specific Accept header."""
    path = path.strip().strip('"')
    accept = accept_header.strip().strip('"')

    client = get_shared_client()
    state = get_scenario_state()

    # Check if we need to mock authorization
    if 'auth_mock' in state:
        with patch('app.authorize_request', side_effect=state['auth_mock']):
            response = client.get(path, headers={'Accept': accept})
    else:
        response = client.get(path, headers={'Accept': accept})

    state['response'] = response
    attach_response_snapshot(response)


@step("The response status should be <status_code>")
def the_response_status_should_be(status_code: str):
    """Validate that the response has the expected status code."""
    expected_status = int(status_code)
    response = get_scenario_state().get('response')

    assert response is not None, "No response recorded. Call `When I request ...` first."
    assert response.status_code == expected_status, (
        f"Expected HTTP {expected_status} but received {response.status_code} "
        f"for {response.request.path!r}."
    )


@step("The response should be valid JSON")
def the_response_should_be_valid_json():
    """Validate that the response contains valid JSON."""
    response = get_scenario_state().get('response')
    assert response is not None, "No response recorded."

    try:
        json.loads(response.get_data(as_text=True))
    except json.JSONDecodeError as e:
        raise AssertionError(f"Response is not valid JSON: {e}") from e


@step("When I POST to <path> with form data name <name> and target <target>")
def post_form_data(path: str, name: str, target: str):
    """POST form data to the specified path."""
    path = path.strip().strip('"')
    name_value = name.strip().strip('"')
    target_value = target.strip().strip('"')

    client = get_shared_client()
    response = client.post(path, data={'name': name_value, 'target': target_value})

    state = get_scenario_state()
    state['response'] = response
    attach_response_snapshot(response)
