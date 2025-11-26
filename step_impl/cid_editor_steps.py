"""Gauge step implementations for CID editor functionality."""
from __future__ import annotations

from getgauge.python import step

from database import db
from models import Variable
from step_impl.artifacts import attach_response_snapshot
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state


def _require_app():
    return get_shared_app()


def _require_client():
    return get_shared_client()


def _normalize_path(path: str) -> str:
    return path.strip().strip('"')


@step("When I request the page /variables/new")
def when_i_request_variables_new_page() -> None:
    """Request the new variable form page."""
    client = _require_client()
    response = client.get("/variables/new")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("Path coverage: /variables/new")
def record_variables_new_path_coverage() -> None:
    """Acknowledge the new variable form route for documentation coverage."""
    return None


@step("The page should contain Convert to CID")
def then_page_should_contain_convert_to_cid() -> None:
    """Verify the page contains Convert to CID button."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Convert to CID" in body, "Expected to find Convert to CID in the response body."


@step("The page should contain Expand CID")
def then_page_should_contain_expand_cid() -> None:
    """Verify the page contains Expand CID button."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Expand CID" in body, "Expected to find Expand CID in the response body."


@step('Given there is a variable named <name> with definition <definition>')
def given_variable_exists(name: str, definition: str) -> None:
    """Ensure a variable with the provided name exists in the workspace."""
    app = _require_app()

    name = _normalize_path(name)
    definition = _normalize_path(definition)

    with app.app_context():
        existing = Variable.query.filter_by(name=name).first()
        if existing is None:
            variable = Variable(name=name, definition=definition)
            db.session.add(variable)
        else:
            existing.definition = definition
        db.session.commit()


@step("When I request the page /variables/<name>/edit")
def when_i_request_variable_edit_page(name: str) -> None:
    """Request the variable edit page."""
    client = _require_client()
    name = _normalize_path(name)
    response = client.get(f"/variables/{name}/edit")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step('When I POST to /api/cid/check with JSON content <content>')
def when_i_post_to_cid_check(content: str) -> None:
    """POST to the CID check API with the given content."""
    client = _require_client()
    content = _normalize_path(content)
    response = client.post(
        '/api/cid/check',
        json={'content': content},
        content_type='application/json'
    )
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step('When I POST to /api/cid/generate with JSON content <content>')
def when_i_post_to_cid_generate(content: str) -> None:
    """POST to the CID generate API with the given content."""
    client = _require_client()
    content = _normalize_path(content)
    response = client.post(
        '/api/cid/generate',
        json={'content': content, 'store': False},
        content_type='application/json'
    )
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("The response should contain is_cid false")
def then_response_contains_is_cid_false() -> None:
    """Verify the response contains is_cid: false."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert data.get('is_cid') is False, f"Expected is_cid to be false, got {data.get('is_cid')}"


@step("The response should contain is_cid true")
def then_response_contains_is_cid_true() -> None:
    """Verify the response contains is_cid: true."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert data.get('is_cid') is True, f"Expected is_cid to be true, got {data.get('is_cid')}"


@step("The response should contain status not_a_cid")
def then_response_contains_status_not_a_cid() -> None:
    """Verify the response contains status: not_a_cid."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert data.get('status') == 'not_a_cid', f"Expected status not_a_cid, got {data.get('status')}"


@step("The response should contain status content_embedded")
def then_response_contains_status_content_embedded() -> None:
    """Verify the response contains status: content_embedded."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert data.get('status') == 'content_embedded', f"Expected status content_embedded, got {data.get('status')}"


@step("The response should contain has_content true")
def then_response_contains_has_content_true() -> None:
    """Verify the response contains has_content: true."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert data.get('has_content') is True, f"Expected has_content to be true, got {data.get('has_content')}"


@step("The response should contain cid_value")
def then_response_contains_cid_value() -> None:
    """Verify the response contains cid_value field."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert 'cid_value' in data, "Expected response to contain cid_value field."
    assert data['cid_value'], "Expected cid_value to be non-empty."


@step("The response should contain cid_link_html")
def then_response_contains_cid_link_html() -> None:
    """Verify the response contains cid_link_html field."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    data = response.get_json()
    assert 'cid_link_html' in data, "Expected response to contain cid_link_html field."
    assert data['cid_link_html'], "Expected cid_link_html to be non-empty."
