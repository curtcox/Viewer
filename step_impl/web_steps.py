"""Gauge step implementations for web application testing."""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient
from getgauge.python import before_scenario, before_suite, step

from database import db
from models import Server
from step_impl.artifacts import attach_response_snapshot
from step_impl.shared_app import get_shared_app, get_shared_client, login_default_user
from step_impl.shared_state import clear_scenario_state, get_scenario_state


@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    get_shared_app()
    get_shared_client()


def _require_app() -> Flask:
    return get_shared_app()


def _require_client() -> FlaskClient:
    return get_shared_client()


def _login_default_user() -> str:
    """Attach the default user session to the Gauge test client."""

    return login_default_user()


def _perform_get_request(path: str) -> None:
    """Issue a GET request for the provided path and store the response."""

    client = _require_client()
    _login_default_user()
    response = client.get(path)
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


@before_scenario()
def reset_scenario_store() -> None:
    """Clear scenario data before each spec scenario."""
    clear_scenario_state()


# Shared assertions
@step("The response status should be 200")
def the_response_status_should_be_200() -> None:
    """Validate that the captured response completed successfully."""

    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."
    assert (
        response.status_code == 200
    ), f"Expected HTTP 200 but received {response.status_code} for {response.request.path!r}."


# Page request steps
@step("When I request the page /")
def when_i_request_home_page() -> None:
    """Request the home page."""
    _perform_get_request("/")


@step("When I request the page /profile")
def when_i_request_profile_page() -> None:
    """Request the profile page."""
    _perform_get_request("/profile")


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


@step("When I request the page /aliases/ai")
def when_i_request_aliases_ai_page() -> None:
    """Request the aliases AI page."""
    _perform_get_request("/aliases/ai")


@step("When I request the page /aliases")
def when_i_request_aliases_index_page() -> None:
    """Request the aliases index page."""
    _perform_get_request("/aliases")


@step("When I request the page /servers/<server_name>")
def when_i_request_server_detail_page(server_name: str) -> None:
    """Request the server detail page for the provided server name."""

    client = _require_client()
    _login_default_user()

    server_name = server_name.strip().strip('"')
    response = client.get(f"/servers/{server_name}")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)


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
    """Ensure a server with the provided name exists for the default user."""

    user_id = _login_default_user()
    app = _require_app()

    server_name = server_name.strip().strip('"')
    message = message.strip().strip('"')
    definition = "def main(context):\n    return {message!r}\n".format(message=message)

    with app.app_context():
        existing = Server.query.filter_by(user_id=user_id, name=server_name).first()
        if existing is None:
            server = Server(name=server_name, definition=definition, user_id=user_id)
            db.session.add(server)
        else:
            existing.definition = definition
        db.session.commit()


@step("Path coverage: /secrets/new")
def record_secret_form_path_coverage() -> None:
    """Acknowledge the new secret form route for documentation coverage."""

    return None


@step("Path coverage: /servers/<server_name>")
def record_server_view_path_coverage(server_name: str) -> None:  # noqa: ARG001 - placeholder only
    """Acknowledge the server detail route for documentation coverage."""

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
