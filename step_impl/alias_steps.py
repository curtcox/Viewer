"""Gauge step implementations for alias management scenarios."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from flask.testing import FlaskClient
from getgauge.python import after_scenario, before_scenario, step

from alias_definition import format_primary_alias_line
from app import create_app
from database import db
from identity import ensure_default_user
from models import Alias
from step_impl.artifacts import attach_response_snapshot

_app = None
_client: Optional[FlaskClient] = None
_db_path: Optional[Path] = None
_scenario_state: dict[str, Any] = {}


def _create_isolated_app() -> tuple[Any, FlaskClient, Path]:
    fd, path = tempfile.mkstemp(prefix="gauge-alias-", suffix=".sqlite3")
    os.close(fd)
    db_path = Path(path)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
        }
    )
    client = app.test_client()
    return app, client, db_path


def _require_client() -> FlaskClient:
    if _client is None:
        raise RuntimeError("Gauge test client is not initialized for alias steps.")
    return _client


def _app_context():
    if _app is None:
        raise RuntimeError("Gauge test app is not initialized for alias steps.")
    return _app.app_context()


def _login_default_user(client: FlaskClient) -> str:
    with _app_context():
        user = ensure_default_user()
        user_id = user.id

    with client.session_transaction() as session:
        session["_user_id"] = user_id
        session["_fresh"] = True

    return user_id


@before_scenario()
def setup_alias_scenario() -> None:
    """Spin up an isolated Flask app and client for each scenario."""

    # pylint: disable=global-statement
    # Gauge test framework requires global state to share context between steps
    global _app, _client, _db_path
    _scenario_state.clear()

    # Clean up any lingering database file from a previous scenario first.
    if _db_path and _db_path.exists():
        _db_path.unlink()

    _app, _client, _db_path = _create_isolated_app()
    if _client is not None:
        _login_default_user(_client)


@after_scenario()
def teardown_alias_scenario() -> None:
    """Dispose of database connections and temporary files between scenarios."""

    # pylint: disable=global-statement
    # Gauge test framework requires global state to share context between steps
    global _app, _client, _db_path

    if _app is not None:
        with _app.app_context():
            db.session.remove()
    _app = None
    _client = None

    if _db_path and _db_path.exists():
        _db_path.unlink()
    _db_path = None

    _scenario_state.clear()


@step("Given I am signed in to the workspace")
def given_i_am_signed_in() -> None:
    """Attach the default user session to the Gauge test client."""

    client = _require_client()
    user_id = _login_default_user(client)
    _scenario_state["user_id"] = user_id


@step("When I navigate to /aliases/new")
def when_i_navigate_to_new_alias() -> None:
    """Load the new-alias form and record the response for later checks."""

    client = _require_client()
    response = client.get("/aliases/new")
    _scenario_state["response"] = response
    attach_response_snapshot(response)
    assert response.status_code == 200, "Expected alias form to load successfully."


@step("Then I can enter an alias name and target path")
def then_alias_form_has_fields() -> None:
    """Verify the alias creation form renders the expected input fields."""

    response = _scenario_state.get("response")
    assert response is not None, "Alias form response is unavailable."
    body = response.get_data(as_text=True)
    assert "name=\"name\"" in body, "Alias name input field is missing."
    assert "name=\"definition\"" in body, "Alias definition field is missing."


@step("And submitting the form creates the alias")
def then_submitting_form_creates_alias() -> None:
    """Submit the alias form and ensure a new record is persisted."""

    client = _require_client()
    alias_name = "gauge-alias"
    response = client.post(
        "/aliases/new",
        data={
            "name": alias_name,
            "definition": "gauge-alias -> /guides",
            "submit": "Save Alias",
        },
        follow_redirects=False,
    )
    attach_response_snapshot(response, label="POST /aliases/new")
    assert response.status_code == 302, "Alias creation should redirect on success."

    with _app_context():
        user = ensure_default_user()
        created = Alias.query.filter_by(user_id=user.id, name=alias_name).first()
        assert created is not None, "Alias record was not created."
        assert created.target_path == "/guides", "Alias target path did not persist."


@step('Given there is an alias named <alias_name> pointing to <target_path>')
def given_alias_exists(alias_name: str, target_path: str) -> None:
    """Persist an alias with the provided name and target path."""

    client = _require_client()
    _login_default_user(client)

    alias_name = alias_name.strip().strip('"')
    target_path = target_path.strip().strip('"')

    with _app_context():
        user = ensure_default_user()
        definition_text = format_primary_alias_line(
            match_type="literal",
            match_pattern=None,
            target_path=target_path,
            alias_name=alias_name,
        )
        alias = Alias(
            name=alias_name,
            user_id=user.id,
            definition=definition_text,
        )
        db.session.add(alias)
        db.session.commit()

    _scenario_state["alias_name"] = alias_name


@step('Given there is an alias named <docs> pointing to /guides')
def ypefci(docs: str) -> None:
    """Specialised fixture for an alias pointing to /guides."""

    given_alias_exists(docs, "/guides")


@step("When I visit <path>")
def when_i_visit_path(path: str) -> None:
    """Perform a GET request against the provided path."""

    client = _require_client()
    response = client.get(path)
    _scenario_state["response"] = response
    _scenario_state["last_path"] = path
    attach_response_snapshot(response)
    assert response.status_code == 200, f"Expected GET {path} to succeed."


@step("When I visit /aliases/docs/edit")
def ypdcaf() -> None:
    """Load the edit page for the docs alias."""

    when_i_visit_path("/aliases/docs/edit")


@step("Then I can update the alias target and save the changes")
def then_update_alias_target() -> None:
    """Submit the edit form and verify the alias target is updated."""

    client = _require_client()
    alias_name = _scenario_state.get("alias_name")
    assert alias_name, "Alias name context is unavailable."
    edit_path = _scenario_state.get("last_path")
    assert edit_path, "Edit path was not recorded."

    response = client.post(
        edit_path,
        data={
            "name": alias_name,
            "definition": f"{alias_name} -> /{alias_name}/updated",
            "submit": "Save Alias",
        },
        follow_redirects=False,
    )
    attach_response_snapshot(response, label=f"POST {edit_path}")
    assert response.status_code == 302, "Alias update should redirect to the detail page."

    with _app_context():
        user = ensure_default_user()
        alias = Alias.query.filter_by(user_id=user.id, name=alias_name).first()
        assert alias is not None, "Alias was not found after attempting to update it."
        expected_target = f"/{alias_name}/updated"
        assert alias.target_path == expected_target, "Alias target path did not update."


@step("Path coverage: /aliases/ai")
def aplfaz() -> None:
    """Acknowledge the /aliases/ai route for documentation coverage."""

    record_alias_path_coverage("ai")


@step("Path coverage: /aliases")
def record_alias_index_path_coverage() -> None:
    """Acknowledge alias index path coverage for documentation purposes."""

    return None


@step("Path coverage: /aliases/<alias_name>")
def record_alias_path_coverage(alias_name: str) -> None:
    """Acknowledge alias detail path coverage for documentation purposes."""

    assert alias_name, "Alias name placeholder should not be empty."


@step('When I visit the alias detail page for <alias_name>')
def when_i_visit_alias_detail_page(alias_name: str) -> None:
    """Navigate to the alias detail page for the specified alias."""

    alias_name = alias_name.strip().strip('"')
    path = f"/aliases/{alias_name}"
    when_i_visit_path(path)


@step('Given there is an enabled alias named <alias_name> pointing to <target_path>')
def given_enabled_alias_exists(alias_name: str, target_path: str) -> None:
    """Persist an enabled alias with the provided name and target path."""

    client = _require_client()
    _login_default_user(client)

    alias_name = alias_name.strip().strip('"')
    target_path = target_path.strip().strip('"')

    with _app_context():
        user = ensure_default_user()
        definition_text = format_primary_alias_line(
            match_type="literal",
            match_pattern=None,
            target_path=target_path,
            alias_name=alias_name,
        )
        alias = Alias(
            name=alias_name,
            user_id=user.id,
            definition=definition_text,
            enabled=True,
        )
        db.session.add(alias)
        db.session.commit()

    _scenario_state["alias_name"] = alias_name
