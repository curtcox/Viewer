"""Gauge step implementations that exercise the source browser."""
from __future__ import annotations

from typing import Any, Optional

from flask.testing import FlaskClient
from getgauge.python import DataStoreFactory, before_scenario, before_suite, step

from app import create_app

_client: Optional[FlaskClient] = None


def _response_store() -> dict[str, Any]:
    return DataStoreFactory.scenario_data_store()


@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    global _client
    app = create_app({"TESTING": True})
    _client = app.test_client()


@before_scenario()
def reset_scenario_store() -> None:
    """Clear scenario data before each spec scenario."""
    _response_store().clear()


@step("When I request <path>")
def when_i_request(path: str) -> None:
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get(path)
    _response_store()["response"] = response


@step("The response status should be <code>")
def then_status_is(code: str) -> None:
    response = _response_store().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    expected = int(code)
    actual = int(response.status_code)
    assert (
        actual == expected
    ), f"Expected HTTP {expected} for {response.request.path!r} but received {actual}."


@step("The response should contain <text>")
def then_response_contains(text: str) -> None:
    response = _response_store().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert text in body, f"Expected to find {text!r} in the response body."
