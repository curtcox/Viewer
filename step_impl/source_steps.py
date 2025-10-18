"""Gauge step implementations that exercise the source browser."""
from __future__ import annotations

from typing import Any, Optional

from flask.testing import FlaskClient
from getgauge.python import before_scenario, before_suite, step

from app import create_app

_client: Optional[FlaskClient] = None
_scenario_state: dict[str, Any] = {}


@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    global _client
    app = create_app({"TESTING": True})
    _client = app.test_client()


@before_scenario()
def reset_scenario_store() -> None:
    """Clear scenario data before each spec scenario."""
    _scenario_state.clear()


@step("When I request /source")
def when_i_request_source() -> None:
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/source")
    _scenario_state["response"] = response


@step("When I request the page <path>")
def when_i_request_the_page(path: str) -> None:
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get(path)
    _scenario_state["response"] = response


@step("The response status should be 200")
def then_status_is_200() -> None:
    response = _scenario_state.get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    expected = 200
    actual = int(response.status_code)
    assert (
        actual == expected
    ), f"Expected HTTP {expected} for {response.request.path!r} but received {actual}."


@step("The response should contain Source Browser")
def then_response_contains_source_browser() -> None:
    response = _scenario_state.get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    expected_text = "Source Browser"
    assert expected_text in body, f"Expected to find {expected_text!r} in the response body."


@step("The page should contain <text>")
def then_page_should_contain(text: str) -> None:
    response = _scenario_state.get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert text in body, f"Expected to find {text!r} in the response body."
