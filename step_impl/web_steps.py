"""Gauge step implementations for web application testing."""
from __future__ import annotations
from getgauge.python import before_scenario, before_suite, step
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import clear_scenario_state

@before_suite()
def setup_suite() -> None:
    """Create a Flask test client once for the entire suite."""
    get_shared_app()
    get_shared_client()


@before_scenario()
def reset_scenario_store() -> None:
    """Clear scenario data before each spec scenario."""
    clear_scenario_state()


# Shared assertions

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
