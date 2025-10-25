"""Gauge step implementations for web application testing."""
from __future__ import annotations

from typing import Optional

from flask.testing import FlaskClient
from getgauge.python import before_scenario, before_suite, step

from app import create_app
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


# Page request steps
@step("When I request the page /")
def when_i_request_home_page() -> None:
    """Request the home page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/")
    get_scenario_state()["response"] = response


@step("When I request the page /profile")
def when_i_request_profile_page() -> None:
    """Request the profile page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/profile")
    get_scenario_state()["response"] = response


@step("When I request the page /routes")
def when_i_request_routes_page() -> None:
    """Request the routes page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/routes")
    get_scenario_state()["response"] = response


@step("When I request the page /secrets")
def when_i_request_secrets_page() -> None:
    """Request the secrets page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/secrets")
    get_scenario_state()["response"] = response


@step("When I request the page /server_events")
def when_i_request_server_events_page() -> None:
    """Request the server events page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/server_events")
    get_scenario_state()["response"] = response


@step("When I request the page /servers/new")
def when_i_request_new_server_page() -> None:
    """Request the new server form page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/servers/new")
    get_scenario_state()["response"] = response


@step("When I request the page /aliases/ai")
def when_i_request_aliases_ai_page() -> None:
    """Request the aliases AI page."""
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized.")
    response = _client.get("/aliases/ai")
    get_scenario_state()["response"] = response


# Content verification steps
@step("The page should contain <text>")
def then_page_should_contain(text: str) -> None:
    """Verify the page contains the specified text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
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


@step("The page should contain New Secret")
def then_page_should_contain_new_secret() -> None:
    """Verify the page contains New Secret text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "New Secret" in body, "Expected to find New Secret in the response body."


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


@step("The page should contain New Alias")
def then_page_should_contain_new_alias() -> None:
    """Verify the page contains New Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    body = response.get_data(as_text=True)
    assert "New Alias" in body, "Expected to find New Alias in the response body."


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
