"""Gauge step implementations that exercise the source browser."""
from __future__ import annotations

from typing import Any, Optional

from flask.testing import FlaskClient
from gauge_compat import before_scenario, before_suite, step

from app import create_app

_client: Optional[FlaskClient] = None
_scenario_state: dict[str, Any] = {}


def _make_client(**config: Any) -> FlaskClient:
    """Create a Flask test client with the provided configuration overrides."""
    app = create_app({"TESTING": True, **config})
    return app.test_client()


def _require_response() -> Any:
    """Fetch the most recent response from scenario state."""
    response = _scenario_state.get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    return response


@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    global _client
    _client = _make_client()


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


@step("The response status should be 200")
def then_status_is_200() -> None:
    response = _require_response()
    expected = 200
    actual = int(response.status_code)
    assert (
        actual == expected
    ), f"Expected HTTP {expected} for {response.request.path!r} but received {actual}."


@step("The response should contain Source Browser")
def then_response_contains_source_browser() -> None:
    body = _require_response().get_data(as_text=True)
    expected_text = "Source Browser"
    assert expected_text in body, f"Expected to find {expected_text!r} in the response body."


@step("When I request <path> with screenshot mode enabled")
def when_i_request_path_with_screenshot_mode(path: str) -> None:
    """Request the given path using a client that has screenshot mode enabled."""
    client = _make_client(SCREENSHOT_MODE=True)
    response = client.get(path)
    _scenario_state["response"] = response


@step("The CID screenshot response should include expected content")
def then_cid_screenshot_contains_expected_content() -> None:
    """Assert the CID screenshot demo showcases the static expectations."""
    body = _require_response().get_data(as_text=True)
    for expected in ("CID Screenshot Demo", "#bafybeigd...", "View metadata"):
        assert (
            expected in body
        ), f"Expected to find {expected!r} in the CID screenshot response body."


@step("The uploads screenshot response should include sample data")
def then_uploads_screenshot_contains_sample_data() -> None:
    """Assert the uploads screenshot view renders the canned fixture content."""
    body = _require_response().get_data(as_text=True)
    for expected in ("Your Files", "#bafybeigd...", "Markdown sample text..."):
        assert (
            expected in body
        ), f"Expected to find {expected!r} in the uploads screenshot response body."


@step("The server events screenshot response should include sample data")
def then_server_events_screenshot_contains_sample_data() -> None:
    """Assert the server events screenshot view renders the canned fixture content."""
    body = _require_response().get_data(as_text=True)
    for expected in ("Server Events", "#bafybeigd...", "billing-reporter"):
        assert (
            expected in body
        ), f"Expected to find {expected!r} in the server events screenshot response body."
