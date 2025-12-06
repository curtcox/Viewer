"""Step implementations for URL Editor server specs."""

from getgauge.python import step

from step_impl.shared_state import store


@step("When I check the available servers")
def check_available_servers():
    """Check which servers are available."""
    from db_access import get_servers
    
    servers = get_servers()
    store.available_servers = [s.name for s in servers]


@step("Then the server <server_name> should be present")
def check_server_present(server_name):
    """Verify that a server is present."""
    assert hasattr(store, 'available_servers'), "No servers checked yet"
    assert server_name in store.available_servers, f"Server {server_name} not found in {store.available_servers}"


@step("Then the response should be a redirect")
def check_response_is_redirect():
    """Verify that the response is a redirect."""
    assert hasattr(store, 'last_response'), "No response stored"
    # Check if it's a redirect (status code 300-399)
    assert 300 <= store.last_response.status_code < 400, \
        f"Expected redirect, got status {store.last_response.status_code}"


@step("And the redirect location should be <expected_location>")
def check_redirect_location(expected_location):
    """Verify the redirect location."""
    assert hasattr(store, 'last_response'), "No response stored"
    
    # Get the Location header
    location = store.last_response.headers.get('Location', '')
    
    # Normalize expected location (remove quotes if present)
    expected = expected_location.strip('"\'')
    
    assert location == expected, \
        f"Expected redirect to {expected}, got {location}"


@step("And the response status should be <expected_status>")
def check_response_status(expected_status):
    """Verify the response status code."""
    assert hasattr(store, 'last_response'), "No response stored"
    
    # Normalize expected status (remove quotes if present)
    expected = int(expected_status.strip('"\''))
    
    actual = store.last_response.status_code
    assert actual == expected, \
        f"Expected status {expected}, got {actual}"
