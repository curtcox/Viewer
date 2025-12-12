"""Gauge step implementations for server dependencies (main parameters matching variables/secrets)."""
from __future__ import annotations

from getgauge.python import step

from database import db
from models import Secret, Server, Variable
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state


def _require_app():
    return get_shared_app()


def _require_client():
    return get_shared_client()


def _normalize_path(value: str) -> str:
    return value.strip().strip('"')


@step([
    "Given there is a variable named <name> with value <value>",
    "And there is a variable named <name> with value <value>",
])
def given_variable_with_value(name: str, value: str) -> None:
    """Ensure a variable with the provided name and value exists in the workspace."""
    app = _require_app()

    name = _normalize_path(name)
    value = _normalize_path(value)
    definition = f"return {value!r}"

    with app.app_context():
        existing = Variable.query.filter_by(name=name).first()
        if existing is None:
            variable = Variable(name=name, definition=definition)
            db.session.add(variable)
        else:
            existing.definition = definition
        db.session.commit()


@step([
    "Given there is a secret named <name> with value <value>",
    "And there is a secret named <name> with value <value>",
])
def given_secret_with_value(name: str, value: str) -> None:
    """Ensure a secret with the provided name and value exists in the workspace."""
    app = _require_app()

    name = _normalize_path(name)
    value = _normalize_path(value)
    definition = f"return {value!r}"

    with app.app_context():
        existing = Secret.query.filter_by(name=name).first()
        if existing is None:
            secret = Secret(name=name, definition=definition)
            db.session.add(secret)
        else:
            existing.definition = definition
        db.session.commit()


@step([
    "Given there is a server named <server_name> with main parameters <param1> and <param2>",
    "And there is a server named <server_name> with main parameters <param1> and <param2>",
])
def given_server_with_two_main_parameters(server_name: str, param1: str, param2: str) -> None:
    """Ensure a server with the provided name and main parameters exists."""
    app = _require_app()

    server_name = _normalize_path(server_name)
    param1 = _normalize_path(param1)
    param2 = _normalize_path(param2)
    definition = f"""def main({param1}, {param2}):
    return {{"result": f"{{{param1}}} - {{{param2}}}"}}
"""

    with app.app_context():
        existing = Server.query.filter_by(name=server_name).first()
        if existing is None:
            server = Server(name=server_name, definition=definition)
            db.session.add(server)
        else:
            existing.definition = definition
        db.session.commit()


@step([
    "Given there is a server named <server_name> with main parameter <param>",
    "And there is a server named <server_name> with main parameter <param>",
])
def given_server_with_one_main_parameter(server_name: str, param: str) -> None:
    """Ensure a server with the provided name and single main parameter exists."""
    app = _require_app()

    server_name = _normalize_path(server_name)
    param = _normalize_path(param)
    definition = f"""def main({param}):
    return {{"result": {param}}}
"""

    with app.app_context():
        existing = Server.query.filter_by(name=server_name).first()
        if existing is None:
            server = Server(name=server_name, definition=definition)
            db.session.add(server)
        else:
            existing.definition = definition
        db.session.commit()


@step("The page should not contain <text>")
def then_page_should_not_contain(text: str) -> None:
    """Assert that the current page response does not contain the provided text."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded. Call `When I request ...` first."

    text = _normalize_path(text)
    body = response.get_data(as_text=True)
    assert text not in body, f"Expected NOT to find {text!r} in the response body, but it was present."
