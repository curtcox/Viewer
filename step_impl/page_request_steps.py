"""Gauge steps for requesting pages."""
from __future__ import annotations
from getgauge.python import step
from database import db
from models import Server
from step_impl.shared_state import get_scenario_state
from step_impl.artifacts import attach_response_snapshot
from step_impl.http_helpers import (
    _perform_get_request,
    _perform_post_request,
    _require_app,
    _require_client,
    _normalize_path
)

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

    _require_app()
    _require_client()



@step('Navigate to "<path>"')
def navigate_to_path(path: str) -> None:
    """Navigate to the provided path using the shared client."""

    when_i_request_generic_page(path)



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



@step("Given there is a server named weather returning Weather forecast ready")
def given_there_is_a_server_named_weather_returning_weather_forecast_ready() -> None:
    """Create a weather server fixture returning the expected message."""

    given_server_exists("weather", "Weather forecast ready")



@step("When I request the page /servers/weather")
def pvipha() -> None:
    """Request the weather server detail page."""

    when_i_request_server_detail_page("weather")



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



@step("When I request the page /servers")
def when_i_request_servers_page() -> None:
    """Request the servers list page."""
    _perform_get_request("/servers")



@step("When I request the page /api/routes")
def when_i_request_api_routes_page() -> None:
    """Request the API routes page."""
    _perform_get_request("/api/routes")

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
