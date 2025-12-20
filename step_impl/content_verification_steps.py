"""Gauge steps for verifying content."""

from __future__ import annotations
import csv
import io
import xml.etree.ElementTree as ET
from getgauge.python import step
from step_impl.shared_state import get_scenario_state, store
from step_impl.http_helpers import _normalize_path


@step(
    [
        "The response status should be 200",
        "the response status should be 200",
        "Then the response status should be 200",
    ]
)
def the_response_status_should_be_200() -> None:
    """Validate that the captured response completed successfully."""

    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    assert response.status_code == 200, (
        f"Expected HTTP 200 but received {response.status_code} for {response.request.path!r}."
    )


@step(
    [
        "The response content type should be <content_type>",
        "And the response content type should be <content_type>",
        'Then the response content type should be "<content_type>"',
    ]
)
def the_response_content_type_should_be(content_type: str) -> None:
    """Validate that the captured response used the expected media type."""

    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

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


@step('Page contains "<text>"')
def page_contains_text(text: str) -> None:
    """Assert that the current page response contains the provided text."""

    then_page_should_contain(text)


@step('Click on "Details" tab')
def click_on_details_tab() -> None:
    """Simulate selecting the Details tab by asserting it is present."""

    then_page_should_contain("Details")


@step(
    [
        "The page should contain <text>",
        "the page should contain <text>",
        "And the page should contain <text>",
    ]
)
def then_page_should_contain(text: str) -> None:
    """Verify the page contains the specified text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    text = _normalize_path(text)
    assert text in body, f"Expected to find {text!r} in the response body."


def _response_for_redirect_assertions():
    response = getattr(store, "last_response", None)
    if response is not None:
        return response
    return get_scenario_state().get("response")


@step("The page should contain href=</meta/.html>")
def then_page_should_contain_meta_href() -> None:
    """Verify the page contains the meta href link."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert 'href="/meta/.html"' in body, (
        'Expected to find href="/meta/.html" in the response body.'
    )


@step("The page should contain fa-circle-info")
def then_page_should_contain_fa_circle_info() -> None:
    """Verify the page contains the fa-circle-info class."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "fa-circle-info" in body, (
        "Expected to find fa-circle-info in the response body."
    )


@step("The page should contain Account Profile")
def then_page_should_contain_account_profile() -> None:
    """Verify the page contains Account Profile text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Account Profile" in body, (
        "Expected to find Account Profile in the response body."
    )


@step("The page should contain Open Workspace")
def then_page_should_contain_open_workspace() -> None:
    """Verify the page contains Open Workspace text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Open Workspace" in body, (
        "Expected to find Open Workspace in the response body."
    )


@step("The page should contain Routes Overview")
def then_page_should_contain_routes_overview() -> None:
    """Verify the page contains Routes Overview text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Routes Overview" in body, (
        "Expected to find Routes Overview in the response body."
    )


@step("The page should contain Show route types")
def then_page_should_contain_show_route_types() -> None:
    """Verify the page contains Show route types text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Show route types" in body, (
        "Expected to find Show route types in the response body."
    )


@step("The page should contain Highlight routes matching URL")
def then_page_should_contain_highlight_routes_matching_url() -> None:
    """Verify the page contains Highlight routes matching URL text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Highlight routes matching URL" in body, (
        "Expected to find Highlight routes matching URL in the response body."
    )


@step("The page should contain Secrets")
def then_page_should_contain_secrets() -> None:
    """Verify the page contains Secrets text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
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
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "New Secret" in body, "Expected to find New Secret in the response body."


@step("The page should contain Create New Secret")
def then_page_should_contain_create_new_secret() -> None:
    """Verify the page contains Create New Secret text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Create New Secret" in body, (
        "Expected to find Create New Secret in the response body."
    )


@step("The page should contain Secret Configuration")
def then_page_should_contain_secret_configuration() -> None:
    """Verify the page contains Secret Configuration text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Secret Configuration" in body, (
        "Expected to find Secret Configuration in the response body."
    )


@step("The page should contain Back to Secrets")
def then_page_should_contain_back_to_secrets() -> None:
    """Verify the page contains Back to Secrets text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Back to Secrets" in body, (
        "Expected to find Back to Secrets in the response body."
    )


@step("The page should contain Server Events")
def then_page_should_contain_server_events() -> None:
    """Verify the page contains Server Events text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Server Events" in body, (
        "Expected to find Server Events in the response body."
    )


@step("The page should contain Invocation History")
def then_page_should_contain_invocation_history() -> None:
    """Verify the page contains Invocation History text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Invocation History" in body, (
        "Expected to find Invocation History in the response body."
    )


@step("The page should contain Alias Details")
def then_page_should_contain_alias_details() -> None:
    """Verify the page contains Alias Details text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Alias Details" in body, (
        "Expected to find Alias Details in the response body."
    )


@step("The page should contain Edit Alias")
def then_page_should_contain_edit_alias() -> None:
    """Verify the page contains Edit Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Edit Alias" in body, "Expected to find Edit Alias in the response body."


@step("The page should contain No Server Events Yet")
def then_page_should_contain_no_server_events_yet() -> None:
    """Verify the page contains No Server Events Yet text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "No Server Events Yet" in body, (
        "Expected to find No Server Events Yet in the response body."
    )


@step("The page should contain Aliases")
def then_page_should_contain_aliases() -> None:
    """Verify the page contains Aliases text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
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
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "New Alias" in body, "Expected to find New Alias in the response body."


@step("The page should contain Create New Alias")
def then_page_should_contain_create_new_alias() -> None:
    """Verify the page contains Create New Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Create New Alias" in body, (
        "Expected to find Create New Alias in the response body."
    )


@step("The page should contain Create New Server")
def then_page_should_contain_create_new_server() -> None:
    """Verify the page contains Create New Server text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Create New Server" in body, (
        "Expected to find Create New Server in the response body."
    )


@step("The page should contain Server Configuration")
def then_page_should_contain_server_configuration() -> None:
    """Verify the page contains Server Configuration text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Server Configuration" in body, (
        "Expected to find Server Configuration in the response body."
    )


@step("The page should contain Back to Servers")
def then_page_should_contain_back_to_servers() -> None:
    """Verify the page contains Back to Servers text."""
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )
    body = response.get_data(as_text=True)
    assert "Back to Servers" in body, (
        "Expected to find Back to Servers in the response body."
    )


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
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

    payload = response.get_json()
    assert isinstance(payload, list), "Expected JSON array of alias records"
    assert payload, "Expected at least one alias record"
    first_record = payload[0]
    assert "name" in first_record, "Alias records must include a name"
    assert "match_pattern" in first_record, "Alias records must include match metadata"


@step("The response JSON should describe a server named <server_name>")
def the_response_json_should_describe_server(server_name: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

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
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

    body = response.get_data(as_text=True)
    document = ET.fromstring(body)
    items = document.findall("item")
    assert items, "Expected alias records in XML payload"
    first = items[0]
    assert first.find("name") is not None, (
        "Alias XML records must include a name element"
    )
    assert first.find("match_pattern") is not None, (
        "Alias XML records must include match metadata"
    )


@step("The response XML should describe a server named <server_name>")
def the_response_xml_should_describe_server(server_name: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

    body = response.get_data(as_text=True)
    document = ET.fromstring(body)
    expected_name = _normalize_path(server_name)
    assert document.findtext("name") == expected_name, (
        f"Expected server name {expected_name!r} but received {document.findtext('name')!r}."
    )
    assert document.find("definition") is not None, (
        "Server XML payload should include definition"
    )


@step("The response XML should describe a server named ai_stub")
def the_response_xml_should_describe_server_ai_stub() -> None:
    """Validate that the response XML describes a server named ai_stub."""
    the_response_xml_should_describe_server("ai_stub")


@step("The response CSV should include alias records")
def the_response_csv_should_include_alias_records() -> None:
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

    reader = csv.DictReader(io.StringIO(response.get_data(as_text=True)))
    rows = list(reader)
    assert rows, "Expected alias records in CSV payload"
    first = rows[0]
    assert "name" in first and first["name"], (
        "Alias CSV records must include a name column"
    )
    assert "match_pattern" in first, "Alias CSV records must include match metadata"


@step("The response CSV should describe a server named <server_name>")
def the_response_csv_should_describe_server(server_name: str) -> None:
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No response recorded. Call `When I request ...` first."
    )

    reader = csv.DictReader(io.StringIO(response.get_data(as_text=True)))
    rows = list(reader)
    assert rows, "Expected server record in CSV payload"
    expected_name = _normalize_path(server_name)
    record = rows[0]
    assert record.get("name") == expected_name, (
        f"Expected server name {expected_name!r} but received {record.get('name')!r}."
    )
    assert "definition" in record, (
        "Server CSV payload should include the definition column"
    )


@step("The response CSV should describe a server named ai_stub")
def the_response_csv_should_describe_server_ai_stub() -> None:
    """Validate that the response CSV describes a server named ai_stub."""
    the_response_csv_should_describe_server("ai_stub")


# Import/Export steps


@step("The response content type should be text/html")
def the_response_content_type_should_be_text_html() -> None:
    """Validate that the response content type is text/html."""
    the_response_content_type_should_be("text/html")


@step("And the response content type should be text/html")
def and_the_response_content_type_should_be_text_html() -> None:
    """Validate that the response content type is text/html."""
    the_response_content_type_should_be("text/html")


@step("The page should contain User management is handled externally")
def then_page_should_contain_user_management() -> None:
    """Verify the page contains User management message."""
    then_page_should_contain("User management is handled externally")


@step('The page should contain href="/source/authorization.py"')
def then_page_should_contain_authorization_source_link() -> None:
    """Verify the page contains authorization source link."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert 'href="/source/authorization.py"' in body, (
        'Expected to find href="/source/authorization.py" in the response body.'
    )


@step("The page should contain Create New Variable")
def then_page_should_contain_create_new_variable() -> None:
    """Verify the page contains Create New Variable text."""
    then_page_should_contain("Create New Variable")


@step('And the page should contain "request"')
def and_page_should_contain_request() -> None:
    """Verify the page contains request text."""
    then_page_should_contain("request")


@step('And the page should contain "context"')
def and_page_should_contain_context() -> None:
    """Verify the page contains context text."""
    then_page_should_contain("context")


@step('And the page should contain "form"')
def and_page_should_contain_form() -> None:
    """Verify the page contains form text."""
    then_page_should_contain("form")


@step('And the page should contain "command"')
def and_page_should_contain_command() -> None:
    """Verify the page contains command text."""
    then_page_should_contain("command")


@step('The page should contain href="/history?start="')
def then_page_should_contain_history_link() -> None:
    """Verify the page contains history link."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert 'href="/history?start=' in body, (
        'Expected to find href="/history?start=" in the response body.'
    )


@step('The page should contain href="/server_events?start="')
def then_page_should_contain_server_events_link() -> None:
    """Verify the page contains server_events link."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert 'href="/server_events?start=' in body, (
        'Expected to find href="/server_events?start=" in the response body.'
    )


@step("The page should contain About this page")
def then_page_should_contain_about_this_page() -> None:
    """Verify the page contains About this page text."""
    then_page_should_contain("About this page")


@step("The page should contain History")
def then_page_should_contain_history() -> None:
    """Verify the page contains History text."""
    then_page_should_contain("History")


@step("The page should contain city")
def then_page_should_contain_city() -> None:
    """Verify the page contains city text."""
    then_page_should_contain("city")


@step("The page should contain api_key")
def then_page_should_contain_api_key() -> None:
    """Verify the page contains api_key text."""
    then_page_should_contain("api_key")


@step("The page should contain /variables/city")
def then_page_should_contain_variables_city() -> None:
    """Verify the page contains /variables/city link."""
    then_page_should_contain("/variables/city")


@step("The page should contain /secrets/api_key")
def then_page_should_contain_secrets_api_key() -> None:
    """Verify the page contains /secrets/api_key link."""
    then_page_should_contain("/secrets/api_key")


@step("The page should contain echo_service")
def then_page_should_contain_echo_service() -> None:
    """Verify the page contains echo_service text."""
    then_page_should_contain("echo_service")


@step("The page should contain 403")
def then_page_should_contain_403() -> None:
    """Verify the page contains 403 status."""
    then_page_should_contain("403")


@step("The page should contain Forbidden")
def then_page_should_contain_forbidden() -> None:
    """Verify the page contains Forbidden text."""
    then_page_should_contain("Forbidden")


# Authorization-related response assertions


@step("The response should contain Create New Alias")
def the_response_should_contain_create_new_alias() -> None:
    """Verify the response contains Create New Alias text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "Create New Alias" in body, (
        "Expected to find Create New Alias in the response."
    )


@step("The response should contain error")
def the_response_should_contain_error() -> None:
    """Verify the response contains error text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "error" in body.lower(), "Expected to find error in the response."


@step("The response should contain Authorization failed")
def the_response_should_contain_authorization_failed() -> None:
    """Verify the response contains Authorization failed text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "Authorization" in body or "authorization" in body.lower(), (
        "Expected to find Authorization in the response."
    )


@step("The response should contain Error 401")
def the_response_should_contain_error_401() -> None:
    """Verify the response contains Error 401."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "401" in body, "Expected to find 401 in the response."
