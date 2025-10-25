"""Gauge step implementations that exercise the source browser."""
from __future__ import annotations

from typing import Optional

from flask.testing import FlaskClient
from getgauge.python import before_scenario, before_suite, step

from app import create_app
from step_impl.artifacts import attach_response_snapshot
from step_impl.shared_state import clear_scenario_state, get_scenario_state

_client: Optional[FlaskClient] = None


@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    # pylint: disable=global-statement
    # Gauge test framework requires global state to share context between steps
    global _client
    app = create_app({"TESTING": True})
    _client = app.test_client()


@before_scenario()
def reset_scenario_store() -> None:
    """Clear scenario data before each spec scenario."""
    clear_scenario_state()


@step("When I request /source")
def when_i_request_source() -> None:
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/source")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the page <path>")
def when_i_request_the_page(path: str) -> None:
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get(path)
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("The response status should be <status_code>")
def then_status_is(status_code: str) -> None:
    """Validate that the captured response returned the expected status code."""

    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    try:
        expected = int(status_code)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise AssertionError(f"Invalid status code value: {status_code!r}") from exc

    actual = int(response.status_code)
    assert (
        actual == expected
    ), f"Expected HTTP {expected} for {response.request.path!r} but received {actual}."


@step("The response should contain <text>")
def then_response_contains(text: str) -> None:
    """Ensure the raw response body includes the provided text fragment."""

    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    body = response.get_data(as_text=True)
    assert text in body, f"Expected to find {text!r} in the response body."


@step("The page should contain <text>")
def then_page_should_contain(text: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert text in body, f"Expected to find {text!r} in the response body."
