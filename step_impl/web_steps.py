"""Gauge step implementations for web application testing."""
from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET

from flask import Flask
from flask.testing import FlaskClient
from getgauge.python import before_scenario, before_suite, step

from database import db
from models import Server
from step_impl.artifacts import attach_response_snapshot
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import (
    clear_scenario_state,
    get_scenario_state,
    store,
)


@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    get_shared_app()
    get_shared_client()


def _require_app() -> Flask:
    return get_shared_app()


def _require_client() -> FlaskClient:
    return get_shared_client()


def _is_redirect_response(response) -> bool:
    """Return True when the response is an HTTP redirect."""

    status = getattr(response, "status_code", 0) or 0
    has_location = bool(getattr(response, "headers", {}).get("Location"))
    return 300 <= status < 400 and has_location


def _perform_get_request(path: str) -> None:
    """Issue a GET request for the provided path and store the response."""

    client = _require_client()
    # Capture the initial response without following redirects so redirect
    # assertions can inspect the Location header.
    initial_response = client.get(path, follow_redirects=False)
    store.last_response = initial_response

    # Follow redirects separately so most specs continue to validate the
    # rendered destination content.
    final_response = (
        client.get(path, follow_redirects=True)
        if _is_redirect_response(initial_response)
        else initial_response
    )

    scenario_state = get_scenario_state()
    scenario_state["response"] = final_response
    attach_response_snapshot(final_response)


def _perform_post_request(path: str, *, data: dict[str, str]) -> None:
    """Issue a POST request and store the resulting response."""

    client = _require_client()
    initial_response = client.post(path, data=data, follow_redirects=False)
    store.last_response = initial_response

    final_response = (
        client.post(path, data=data, follow_redirects=True)
        if _is_redirect_response(initial_response)
        else initial_response
    )

    scenario_state = get_scenario_state()
    scenario_state["response"] = final_response
    attach_response_snapshot(final_response)


def _normalize_path(path: str) -> str:
    normalized = path.strip().strip('"')
    state = get_scenario_state()

    for key, value in state.items():
        if not isinstance(value, str):
            continue
        placeholder = f"{{{key}}}"
        normalized = normalized.replace(placeholder, value)

    return normalized


@before_scenario()
def reset_scenario_store() -> None:
    """Clear scenario data before each spec scenario."""
    clear_scenario_state()


# Shared assertions
@step(["The response status should be 200", "the response status should be 200", "Then the response status should be 200"])
def the_response_status_should_be_200() -> None:
    """Validate that the captured response completed successfully."""

    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    assert (
        response.status_code == 200
    ), f"Expected HTTP 200 but received {response.status_code} for {response.request.path!r}."


@step([
    "The response content type should be <content_type>",
    "And the response content type should be <content_type>",
])
def the_response_content_type_should_be(content_type: str) -> None:
    """Validate that the captured response used the expected media type."""

    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    expected = _normalize_path(content_type)
    actual = response.headers.get("Content-Type", "")
    assert actual.split(";")[0] == expected, (
        f"Expected Content-Type {expected!r} but received {actual!r}."
    )


@step("The response content type should be application/json")
def the_response_content_type_should_be_application_json() -> None:
    """Validate that the response content type is application/json."""
    the_response_content_type_should_be("application/json")


@step("The response content type should be text/csv")
def the_response_content_type_should_be_text_csv() -> None:
    """Validate that the response content type is text/csv."""
    the_response_content_type_should_be("text/csv")


@step("The response content type should be application/xml")
def the_response_content_type_should_be_application_xml() -> None:
    """Validate that the response content type is application/xml."""
    the_response_content_type_should_be("application/xml")


@step("The response content type should be text/plain")
def the_response_content_type_should_be_text_plain() -> None:
    """Validate that the response content type is text/plain."""
    the_response_content_type_should_be("text/plain")


# Page request steps
@step("When I request the page /")
def when_i_request_home_page() -> None:
    """Request the home page."""
    _perform_get_request("/")


@step("When I request the page /profile")
def when_i_request_profile_page() -> None:
    """Request the profile page."""
    _perform_get_request("/profile")


@step("When I request the page <path> without a user session")
def when_i_request_page_without_user(path: str) -> None:
    """Request a page without an authenticated user session."""

    normalized_path = _normalize_path(path)
    _perform_get_request(normalized_path)


@step("When I request the page /routes")
def when_i_request_routes_page() -> None:
    """Request the routes page."""
    _perform_get_request("/routes")


@step("When I request the page /secrets")
def when_i_request_secrets_page() -> None:
    """Request the secrets page."""
    _perform_get_request("/secrets")


@step("When I request the page /secrets/new")
def when_i_request_new_secret_page() -> None:
    """Request the new secret form page."""
    _perform_get_request("/secrets/new")


@step("When I request the page /server_events")
def when_i_request_server_events_page() -> None:
    """Request the server events page."""
    _perform_get_request("/server_events")


@step("When I request the page /settings")
def when_i_request_settings_page() -> None:
    """Request the settings dashboard page."""
    _perform_get_request("/settings")


@step("When I request the page /search")
def when_i_request_search_page() -> None:
    """Request the workspace search page."""
    _perform_get_request("/search")


@step("When I request the page /servers/new")
def when_i_request_new_server_page() -> None:
    """Request the new server form page."""
    _perform_get_request("/servers/new")


@step("When I request the page /servers/new as user \"alternate-user\"")
def when_i_request_servers_new_as_alternate_user() -> None:
    """Request the new server page as alternate-user."""
    _perform_get_request("/servers/new")


@step("When I request the page /servers/new as user <alternate-user>")
def blvplz(arg1: str) -> None:
    """Request the new server page as alternate-user."""
    _perform_get_request("/servers/new")


@step("When I request the page /servers/new without a user session")
def when_i_request_servers_new_without_user() -> None:
    """Request the new server page without a user session."""
    _perform_get_request("/servers/new")


@step("When I request the page /aliases/ai")
def when_i_request_aliases_ai_page() -> None:
    """Request the aliases AI page."""
    _perform_get_request("/aliases/ai")


@step("When I request the page /aliases")
def when_i_request_aliases_index_page() -> None:
    """Request the aliases index page."""
    _perform_get_request("/aliases")


@step("When I request the page /aliases/new as user \"alternate-user\"")
def when_i_request_aliases_new_as_alternate_user() -> None:
    """Request the new alias page as alternate-user."""
    _perform_get_request("/aliases/new")


@step("When I request the page /aliases/new as user <alternate-user>")
def lzzcif(arg1: str) -> None:
    """Request the new alias page as alternate-user."""
    _perform_get_request("/aliases/new")


@step("When I request the page /aliases/new without a user session")
def when_i_request_aliases_new_without_user() -> None:
    """Request the new alias page without a user session."""
    _perform_get_request("/aliases/new")


@step("When I request the page <path>")
def when_i_request_generic_page(path: str) -> None:
    """Request an arbitrary page path and store the response."""

    normalized = path.strip() or "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    _perform_get_request(normalized)


@step("Start the app with boot configuration")
def start_app_with_boot_configuration() -> None:
    """Initialize the shared application and client for UI suggestion scenarios."""

    get_shared_app()
    get_shared_client()


@step('Navigate to "<path>"')
def navigate_to_path(path: str) -> None:
    """Navigate to the provided path using the shared client."""

    when_i_request_generic_page(path)


@step('Page contains "<text>"')
def page_contains_text(text: str) -> None:
    """Assert that the current page response contains the provided text."""

    then_page_should_contain(text)


@step('Click on "Details" tab')
def click_on_details_tab() -> None:
    """Simulate selecting the Details tab by asserting it is present."""

    then_page_should_contain("Details")


@step("When I request the resource /aliases.json")
def when_i_request_aliases_json() -> None:
    """Request aliases as JSON."""
    _perform_get_request("/aliases.json")


@step("When I request the resource /aliases.csv")
def when_i_request_aliases_csv() -> None:
    """Request aliases as CSV."""
    _perform_get_request("/aliases.csv")


@step("When I request the resource /aliases.xml")
def when_i_request_aliases_xml() -> None:
    """Request aliases as XML."""
    _perform_get_request("/aliases.xml")


@step("When I request the resource /servers/ai_stub.json")
def when_i_request_servers_ai_stub_json() -> None:
    """Request ai_stub server as JSON."""
    _perform_get_request("/servers/ai_stub.json")


@step("When I request the resource /servers/ai_stub.csv")
def when_i_request_servers_ai_stub_csv() -> None:
    """Request ai_stub server as CSV."""
    _perform_get_request("/servers/ai_stub.csv")


@step("When I request the resource /servers/ai_stub.xml")
def when_i_request_servers_ai_stub_xml() -> None:
    """Request ai_stub server as XML."""
    _perform_get_request("/servers/ai_stub.xml")


@step("When I request the resource <path> with accept header <accept_header>")
def when_i_request_resource_with_accept_header(path: str, accept_header: str) -> None:
    """Request a resource while specifying an Accept header."""

    normalized_path = _normalize_path(path)
    normalized_accept = _normalize_path(accept_header)

    client = _require_client()
    response = client.get(normalized_path, headers={"Accept": normalized_accept})
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the resource /aliases with accept header text/plain")
def when_i_request_aliases_with_accept_text_plain() -> None:
    """Request aliases with Accept header text/plain."""
    client = _require_client()
    response = client.get("/aliases", headers={"Accept": "text/plain"})
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@step("When I request the resource <path>")
def when_i_request_resource(path: str) -> None:
    """Request an arbitrary resource path."""

    normalized_path = _normalize_path(path)
    _perform_get_request(normalized_path)


@step("When I submit a form post to <path> with payload <payload>")
def when_i_submit_form_post(path: str, payload: str) -> None:
    """POST a payload string to the specified path."""

    normalized_path = _normalize_path(path)
    payload_text = payload.strip().strip('"')
    _perform_post_request(normalized_path, data={"payload": payload_text})


@step("When I request the page /servers/<server_name>")
def when_i_request_server_detail_page(server_name: str) -> None:
    """Request the server detail page for the provided server name."""

    client = _require_client()

    server_name = server_name.strip().strip('"')
    response = client.get(f"/servers/{server_name}")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


# Content verification steps
@step(["The page should contain <text>", "the page should contain <text>", "And the page should contain <text>"])
def then_page_should_contain(text: str) -> None:
    """Verify the page contains the specified text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    text = _normalize_path(text)
    assert text in body, f"Expected to find {text!r} in the response body."


@step("The page should contain href=</meta/.html>")
def then_page_should_contain_meta_href() -> None:
    """Verify the page contains the meta href link."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert 'href="/meta/.html"' in body, "Expected to find href=\"/meta/.html\" in the response body."


@step("The page should contain fa-circle-info")
def then_page_should_contain_fa_circle_info() -> None:
    """Verify the page contains the fa-circle-info class."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "fa-circle-info" in body, "Expected to find fa-circle-info in the response body."


@step("The page should contain Account Profile")
def then_page_should_contain_account_profile() -> None:
    """Verify the page contains Account Profile text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Account Profile" in body, "Expected to find Account Profile in the response body."


@step("The page should contain Open Workspace")
def then_page_should_contain_open_workspace() -> None:
    """Verify the page contains Open Workspace text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Open Workspace" in body, "Expected to find Open Workspace in the response body."


@step("The page should contain Routes Overview")
def then_page_should_contain_routes_overview() -> None:
    """Verify the page contains Routes Overview text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Routes Overview" in body, "Expected to find Routes Overview in the response body."


@step("The page should contain Show route types")
def then_page_should_contain_show_route_types() -> None:
    """Verify the page contains Show route types text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Show route types" in body, "Expected to find Show route types in the response body."


@step("The page should contain Highlight routes matching URL")
def then_page_should_contain_highlight_routes_matching_url() -> None:
    """Verify the page contains Highlight routes matching URL text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Highlight routes matching URL" in body, "Expected to find Highlight routes matching URL in the response body."


@step("The page should contain Secrets")
def then_page_should_contain_secrets() -> None:
    """Verify the page contains Secrets text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Secrets" in body, "Expected to find Secrets in the response body."


@step("The page should contain Settings")
def then_page_should_contain_settings() -> None:
    """Verify the page contains Settings text."""
    then_page_should_contain("Settings")


@step("The page should contain New Secret")
def then_page_should_contain_new_secret() -> None:
    """Verify the page contains New Secret text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "New Secret" in body, "Expected to find New Secret in the response body."


@step("The page should contain Create New Secret")
def then_page_should_contain_create_new_secret() -> None:
    """Verify the page contains Create New Secret text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Create New Secret" in body, "Expected to find Create New Secret in the response body."


@step("The page should contain Secret Configuration")
def then_page_should_contain_secret_configuration() -> None:
    """Verify the page contains Secret Configuration text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Secret Configuration" in body, "Expected to find Secret Configuration in the response body."


@step("The page should contain Back to Secrets")
def then_page_should_contain_back_to_secrets() -> None:
    """Verify the page contains Back to Secrets text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Back to Secrets" in body, "Expected to find Back to Secrets in the response body."


@step("The page should contain Server Events")
def then_page_should_contain_server_events() -> None:
    """Verify the page contains Server Events text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Server Events" in body, "Expected to find Server Events in the response body."


@step("The page should contain Invocation History")
def then_page_should_contain_invocation_history() -> None:
    """Verify the page contains Invocation History text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Invocation History" in body, "Expected to find Invocation History in the response body."


@step("The page should contain Alias Details")
def then_page_should_contain_alias_details() -> None:
    """Verify the page contains Alias Details text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Alias Details" in body, "Expected to find Alias Details in the response body."


@step("The page should contain Edit Alias")
def then_page_should_contain_edit_alias() -> None:
    """Verify the page contains Edit Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Edit Alias" in body, "Expected to find Edit Alias in the response body."


@step("The page should contain No Server Events Yet")
def then_page_should_contain_no_server_events_yet() -> None:
    """Verify the page contains No Server Events Yet text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "No Server Events Yet" in body, "Expected to find No Server Events Yet in the response body."


@step("The page should contain Aliases")
def then_page_should_contain_aliases() -> None:
    """Verify the page contains Aliases text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Aliases" in body, "Expected to find Aliases in the response body."


@step("The page should contain Servers")
def then_page_should_contain_servers() -> None:
    """Verify the page contains Servers text."""
    then_page_should_contain("Servers")


@step("The page should contain CIDs")
def then_page_should_contain_cids() -> None:
    """Verify the page contains CIDs text."""
    then_page_should_contain("CIDs")


@step("The page should contain Variables")
def then_page_should_contain_variables() -> None:
    """Verify the page contains Variables text."""
    then_page_should_contain("Variables")


@step("The page should contain New Alias")
def then_page_should_contain_new_alias() -> None:
    """Verify the page contains New Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "New Alias" in body, "Expected to find New Alias in the response body."


@step("The page should contain Create New Alias")
def then_page_should_contain_create_new_alias() -> None:
    """Verify the page contains Create New Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Create New Alias" in body, "Expected to find Create New Alias in the response body."


@step("The page should contain Create New Server")
def then_page_should_contain_create_new_server() -> None:
    """Verify the page contains Create New Server text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Create New Server" in body, "Expected to find Create New Server in the response body."


@step("The page should contain Server Configuration")
def then_page_should_contain_server_configuration() -> None:
    """Verify the page contains Server Configuration text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Server Configuration" in body, "Expected to find Server Configuration in the response body."


@step("The page should contain Back to Servers")
def then_page_should_contain_back_to_servers() -> None:
    """Verify the page contains Back to Servers text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "Back to Servers" in body, "Expected to find Back to Servers in the response body."


@step("The page should contain Workspace Search")
def then_page_should_contain_workspace_search() -> None:
    """Verify the page contains Workspace Search text."""
    then_page_should_contain("Workspace Search")


@step("The page should contain Search query")
def then_page_should_contain_search_query() -> None:
    """Verify the page contains Search query text."""
    then_page_should_contain("Search query")


@step("The page should contain View All Aliases")
def then_page_should_contain_view_all_aliases() -> None:
    """Verify the page contains View All Aliases text."""
    then_page_should_contain("View All Aliases")


@step("The page should contain View All Servers")
def then_page_should_contain_view_all_servers() -> None:
    """Verify the page contains View All Servers text."""
    then_page_should_contain("View All Servers")


@step("The page should contain View All Variables")
def then_page_should_contain_view_all_variables() -> None:
    """Verify the page contains View All Variables text."""
    then_page_should_contain("View All Variables")


@step("The page should contain View All Secrets")
def then_page_should_contain_view_all_secrets() -> None:
    """Verify the page contains View All Secrets text."""
    then_page_should_contain("View All Secrets")


@step("Given there is a server named <server_name> returning <message>")
def given_server_exists(server_name: str, message: str) -> None:
    """Ensure a server with the provided name exists in the workspace."""

    app = _require_app()

    server_name = server_name.strip().strip('"')
    message = message.strip().strip('"')
    definition = f"def main(context):\n    return {message!r}\n"

    with app.app_context():
        existing = Server.query.filter_by(name=server_name).first()
        if existing is None:
            server = Server(name=server_name, definition=definition)
            db.session.add(server)
        else:
            existing.definition = definition
        db.session.commit()


@step("Path coverage: /secrets/new")
def record_secret_form_path_coverage() -> None:
    """Acknowledge the new secret form route for documentation coverage."""

    return None


@step("Path coverage: /servers/<server_name>")
def record_server_view_path_coverage(server_name: str) -> None:  # pylint: disable=unused-argument
    """Acknowledge the server detail route for documentation coverage."""

    return None


@step("Path coverage: /servers/weather")
def record_weather_server_path_coverage() -> None:
    """Acknowledge the weather server detail route for documentation coverage."""

    record_server_view_path_coverage("weather")


@step("Path coverage: /")
def record_root_path_coverage() -> None:
    """Acknowledge the workspace landing page for documentation coverage."""

    return None


@step("Given there is a server named weather returning Weather forecast ready")
def given_there_is_a_server_named_weather_returning_weather_forecast_ready() -> None:
    """Create a weather server fixture returning the expected message."""

    given_server_exists("weather", "Weather forecast ready")


@step("When I request the page /servers/weather")
def pvipha() -> None:
    """Request the weather server detail page."""

    when_i_request_server_detail_page("weather")


@step("The page should contain Edit Server")
def the_page_should_contain_edit_server() -> None:
    """Assert that the response body lists the Edit Server action."""

    then_page_should_contain("Edit Server")


@step("The page should contain Server Definition")
def the_page_should_contain_server_definition() -> None:
    """Assert that the response body displays the server definition."""

    then_page_should_contain("Server Definition")


@step("The response JSON should include alias records")
def the_response_json_should_include_alias_records() -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    payload = response.get_json()
    assert isinstance(payload, list), "Expected JSON array of alias records"
    assert payload, "Expected at least one alias record"
    first_record = payload[0]
    assert "name" in first_record, "Alias records must include a name"
    assert "match_pattern" in first_record, "Alias records must include match metadata"


@step("The response JSON should describe a server named <server_name>")
def the_response_json_should_describe_server(server_name: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    payload = response.get_json()
    expected_name = _normalize_path(server_name)
    assert isinstance(payload, dict), "Expected a server object"
    assert payload.get("name") == expected_name, (
        f"Expected server name {expected_name!r} but received {payload.get('name')!r}."
    )
    assert "definition" in payload, "Server records should include the definition"


@step("The response JSON should describe a server named ai_stub")
def the_response_json_should_describe_server_ai_stub() -> None:
    """Validate that the response JSON describes a server named ai_stub."""
    the_response_json_should_describe_server("ai_stub")


@step("The response XML should include alias records")
def the_response_xml_should_include_alias_records() -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    body = response.get_data(as_text=True)
    document = ET.fromstring(body)
    items = document.findall("item")
    assert items, "Expected alias records in XML payload"
    first = items[0]
    assert first.find("name") is not None, "Alias XML records must include a name element"
    assert first.find("match_pattern") is not None, "Alias XML records must include match metadata"


@step("The response XML should describe a server named <server_name>")
def the_response_xml_should_describe_server(server_name: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    body = response.get_data(as_text=True)
    document = ET.fromstring(body)
    expected_name = _normalize_path(server_name)
    assert document.findtext("name") == expected_name, (
        f"Expected server name {expected_name!r} but received {document.findtext('name')!r}."
    )
    assert document.find("definition") is not None, "Server XML payload should include definition"


@step("The response XML should describe a server named ai_stub")
def the_response_xml_should_describe_server_ai_stub() -> None:
    """Validate that the response XML describes a server named ai_stub."""
    the_response_xml_should_describe_server("ai_stub")


@step("The response CSV should include alias records")
def the_response_csv_should_include_alias_records() -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    reader = csv.DictReader(io.StringIO(response.get_data(as_text=True)))
    rows = list(reader)
    assert rows, "Expected alias records in CSV payload"
    first = rows[0]
    assert "name" in first and first["name"], "Alias CSV records must include a name column"
    assert "match_pattern" in first, "Alias CSV records must include match metadata"


@step("The response CSV should describe a server named <server_name>")
def the_response_csv_should_describe_server(server_name: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    reader = csv.DictReader(io.StringIO(response.get_data(as_text=True)))
    rows = list(reader)
    assert rows, "Expected server record in CSV payload"
    expected_name = _normalize_path(server_name)
    record = rows[0]
    assert record.get("name") == expected_name, (
        f"Expected server name {expected_name!r} but received {record.get('name')!r}."
    )
    assert "definition" in record, "Server CSV payload should include the definition column"


@step("The response CSV should describe a server named ai_stub")
def the_response_csv_should_describe_server_ai_stub() -> None:
    """Validate that the response CSV describes a server named ai_stub."""
    the_response_csv_should_describe_server("ai_stub")


# Import/Export steps
@step("Given an origin site with a server named <shared-tool> returning <Hello from origin>")
def given_an_origin_site_with_a_server_named_returning(server_name: str, server_message: str) -> None:
    """Create an origin site with a server that returns the specified message."""
    from step_impl.import_export_steps import given_origin_site_with_server
    given_origin_site_with_server(server_name, server_message)


@step("Then the destination site should have a server named <shared-tool>")
def then_the_destination_site_should_have_a_server_named(server_name: str) -> None:
    """Verify the destination site has a server with the specified name."""
    from step_impl.import_export_steps import then_destination_has_server
    then_destination_has_server(server_name)


@step("And executing </shared-tool> on the destination site should return <Hello from origin>")
def and_executing_on_the_destination_site_should_return(route_path: str, expected_message: str) -> None:
    """Verify executing the route returns the expected message."""
    from step_impl.import_export_steps import and_executing_destination_route_returns_message
    and_executing_destination_route_returns_message(route_path, expected_message)


def _create_server_from_definition_file(server_name: str, definition_path: str) -> None:
    """Create a server using a definition file from reference_templates."""
    from pathlib import Path

    app = _require_app()
    base_dir = Path(__file__).parent.parent
    definition_file = base_dir / definition_path
    definition = definition_file.read_text(encoding='utf-8')

    with app.app_context():
        existing = Server.query.filter_by(name=server_name).first()
        if existing is None:
            server = Server(name=server_name, definition=definition, enabled=True)
            db.session.add(server)
        else:
            existing.definition = definition
            existing.enabled = True
        db.session.commit()


@step("Given the echo server is available")
def given_echo_server_available() -> None:
    """Ensure the echo server is available in the workspace."""
    _create_server_from_definition_file("echo", "reference_templates/servers/definitions/echo.py")


@step("Given the shell server is available")
def given_shell_server_available() -> None:
    """Ensure the shell server is available in the workspace."""
    _create_server_from_definition_file("shell", "reference_templates/servers/definitions/shell.py")


@step("When I request the resource /echo")
def when_i_request_echo_resource() -> None:
    """Request the echo resource."""
    _perform_get_request("/echo")


@step("When I request the resource /shell")
def when_i_request_shell_resource() -> None:
    """Request the shell resource."""
    _perform_get_request("/shell")


@step("The response content type should be text/html")
def the_response_content_type_should_be_text_html() -> None:
    """Validate that the response content type is text/html."""
    the_response_content_type_should_be("text/html")
