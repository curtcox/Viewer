"""Gauge step implementations for alias and upload management scenarios."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from flask.testing import FlaskClient
from getgauge.python import after_scenario, before_scenario, step

from alias_definition import format_primary_alias_line
from app import create_app
from database import db
from models import Alias, CID, Variable
from step_impl.artifacts import attach_response_snapshot
from step_impl.shared_state import clear_scenario_state, get_scenario_state

_app = None
_client: Optional[FlaskClient] = None
_db_path: Optional[Path] = None
_TEMPLATE_JSON_PATTERN = re.compile(r"const templates = (?P<json>\[.*?\]);", re.S)


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


def _get_response_body() -> str:
    response = get_scenario_state().get("response")
    assert response is not None, (
        "No HTTP response is available. Navigate to a page first."
    )
    return response.get_data(as_text=True)


def _normalize_quoted_text(value: str) -> str:
    return value.strip().strip('"')


def _slugify_label(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "template"


def _save_upload_templates(uploads: dict[str, dict[str, str]]) -> None:
    config = {
        "aliases": {},
        "servers": {},
        "variables": {},
        "secrets": {},
        "uploads": uploads,
    }
    with _app_context():
        Variable.query.filter_by(name="templates").delete()
        var = Variable(name="templates", definition=json.dumps(config))
        db.session.add(var)
        db.session.commit()


def _clear_upload_templates() -> None:
    with _app_context():
        Variable.query.filter_by(name="templates").delete()
        db.session.commit()


def _extract_upload_templates(body: str) -> list[dict[str, Any]]:
    match = _TEMPLATE_JSON_PATTERN.search(body)
    if not match:
        return []
    json_text = match.group("json").strip()
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:  # pragma: no cover - defensive guard
        return []


def _select_template_from_response(
    *, template_name: Optional[str] = None, template_id: Optional[str] = None
) -> dict[str, Any]:
    body = _get_response_body()
    templates = _extract_upload_templates(body)
    if not templates:
        raise AssertionError(
            "Upload templates payload is missing from the page response."
        )

    for template in templates:
        if template_name and template.get("name") == template_name:
            get_scenario_state()["selected_upload_template"] = template
            return template
        if template_id and template.get("id") == template_id:
            get_scenario_state()["selected_upload_template"] = template
            return template

    descriptor = template_name or template_id or "template"
    raise AssertionError(f"Could not find upload template '{descriptor}'.")


def _extract_anchor_text(body: str, href: str) -> Optional[str]:
    pattern = re.compile(rf"<a[^>]+href=\"{re.escape(href)}\"[^>]*>(.*?)</a>", re.S)
    match = pattern.search(body)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return None


@before_scenario()
def setup_alias_scenario() -> None:
    """Spin up an isolated Flask app and client for each scenario."""

    # pylint: disable=global-statement
    # Gauge test framework requires global state to share context between steps
    global _app, _client, _db_path
    clear_scenario_state()

    # Clean up any lingering database file from a previous scenario first.
    if _db_path and _db_path.exists():
        _db_path.unlink()

    _app, _client, _db_path = _create_isolated_app()
    if _client is not None:
        with _client.session_transaction() as session:
            session["_fresh"] = True


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

    clear_scenario_state()


@step("Given I am signed in to the workspace")
def given_i_am_signed_in() -> None:
    """Attach the default user session to the Gauge test client."""

    client = _require_client()
    with client.session_transaction() as session:
        session["_fresh"] = True


@step("When I navigate to /aliases/new")
def when_i_navigate_to_new_alias() -> None:
    """Load the new-alias form and record the response for later checks."""

    client = _require_client()
    response = client.get("/aliases/new")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)
    assert response.status_code == 200, "Expected alias form to load successfully."


@step("Then I can enter an alias name and target path")
def then_alias_form_has_fields() -> None:
    """Verify the alias creation form renders the expected input fields."""

    response = get_scenario_state().get("response")
    assert response is not None, "Alias form response is unavailable."
    body = response.get_data(as_text=True)
    assert 'name="name"' in body, "Alias name input field is missing."
    assert 'name="definition"' in body, "Alias definition field is missing."


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
        created = Alias.query.filter_by(name=alias_name).first()
        assert created is not None, "Alias record was not created."
        assert created.target_path == "/guides", "Alias target path did not persist."


@step("Given there is an alias named <alias_name> pointing to <target_path>")
def given_alias_exists(alias_name: str, target_path: str) -> None:
    """Persist an alias with the provided name and target path."""

    alias_name = alias_name.strip().strip('"')
    target_path = target_path.strip().strip('"')

    with _app_context():
        definition_text = format_primary_alias_line(
            match_type="literal",
            match_pattern=None,
            target_path=target_path,
            alias_name=alias_name,
        )
        alias = Alias(
            name=alias_name,
            definition=definition_text,
        )
        db.session.add(alias)
        db.session.commit()

    get_scenario_state()["alias_name"] = alias_name


@step('Given there is an alias named "test-alias" pointing to /test-target')
def given_test_alias_exists() -> None:
    given_alias_exists("test-alias", "/test-target")


@step('Given there is an alias named "nav-test" pointing to /guides')
def given_nav_test_alias_exists() -> None:
    given_alias_exists("nav-test", "/guides")


@step('Given there is an alias named "def-test" pointing to /definition-target')
def given_def_test_alias_exists() -> None:
    given_alias_exists("def-test", "/definition-target")


@step('Given there is an enabled alias named "active-alias" pointing to /active')
def given_active_alias_exists() -> None:
    with _app_context():
        definition_text = format_primary_alias_line(
            match_type="literal",
            match_pattern=None,
            target_path="/active",
            alias_name="active-alias",
        )
        alias = Alias(
            name="active-alias",
            definition=definition_text,
            enabled=True,
        )
        db.session.add(alias)
        db.session.commit()

    get_scenario_state()["alias_name"] = "active-alias"


@step("Given there is an alias named <docs> pointing to /guides")
def ypefci(docs: str) -> None:
    """Specialised fixture for an alias pointing to /guides."""

    given_alias_exists(docs, "/guides")


# ---------------------------------------------------------------------------
# Upload template helpers and Gauge steps
# ---------------------------------------------------------------------------


@step("And I have upload templates configured")
def and_i_have_upload_templates_configured() -> None:
    """Persist a default set of upload templates for testing."""

    uploads = {
        "hello_world": {
            "name": "Hello World",
            "content": "Hello, World!\n",
        },
        "json_example": {
            "name": "JSON Example",
            "content": '{\n  "key": "value"\n}',
            "description": "Quick JSON starter template.",
        },
        "cid_guide": {
            "name": "Embedded CID execution guide",
            "content": "CID execution walkthrough",
            "description": "Explains CID path elements and how to execute them.",
        },
    }
    _save_upload_templates(uploads)
    state = get_scenario_state()
    state["upload_template_count"] = len(uploads)


@step("And I have no upload templates configured")
def and_i_have_no_upload_templates_configured() -> None:
    """Remove all upload templates from the workspace."""

    _clear_upload_templates()
    get_scenario_state()["upload_template_count"] = 0


@step("When I navigate to /upload")
def when_i_navigate_to_upload() -> None:
    """Load the upload page and capture the response for assertions."""

    client = _require_client()
    response = client.get("/upload")
    scenario_state = get_scenario_state()
    scenario_state["response"] = response
    attach_response_snapshot(response)
    assert response.status_code == 200, "Expected the upload page to load successfully."


@step(
    [
        'Then I should see "Start from a Template" label',
        "Then I should see <text> label",
    ]
)
def then_i_should_see_start_from_template_label(text: str | None = None) -> None:
    body = _get_response_body()
    expected = "Start from a Template" if text is None else text.strip('"')
    assert expected in body, "Upload template label is missing."


@step("And I should see template selection buttons")
def and_i_should_see_template_selection_buttons() -> None:
    body = _get_response_body()
    assert "data-upload-template-id" in body, (
        "Template selection buttons were not rendered."
    )


@step(
    [
        'Then I should see a link to "/variables/templates?type=uploads"',
        "Then I should see a link to <link>",
    ]
)
def then_i_should_see_template_status_link(link: str | None = None) -> None:
    body = _get_response_body()
    target = (
        "/variables/templates?type=uploads"
        if link is None
        else link.strip('"')
    )
    assert target in body, ("Template status link is missing.")


@step("And the link should show the template count")
def and_the_link_should_show_the_template_count() -> None:
    state = get_scenario_state()
    expected = state.get("upload_template_count")
    assert expected is not None, "Template count context is unavailable."

    body = _get_response_body()
    link_text = _extract_anchor_text(body, "/variables/templates?type=uploads")
    assert link_text, "Template status link text is missing."
    assert str(expected) in link_text, (
        f"Expected link text to include count {expected}, but saw {link_text!r}."
    )


@step(
    [
        'Then I should not see "Start from a Template" buttons',
        "Then I should not see <text> buttons",
    ]
)
def then_i_should_not_see_start_from_template_buttons(text: str | None = None) -> None:
    body = _get_response_body()
    marker = "data-upload-template-id"
    if text:
        marker = text.strip('"')
    assert marker not in body, ("Unexpected template buttons were rendered.")


@step(
    "And I have an upload template named <template_name> with content <template_content>"
)
def and_i_have_named_upload_template(template_name: str, template_content: str) -> None:
    name = _normalize_quoted_text(template_name)
    content = _normalize_quoted_text(template_content)
    key = _slugify_label(name)

    uploads = {
        key: {
            "name": name,
            "content": content,
        }
    }
    _save_upload_templates(uploads)
    state = get_scenario_state()
    state["upload_template_count"] = 1
    state["last_upload_template_key"] = key
    state["last_upload_template_name"] = name


@step("And I click the <template_name> template button")
def and_i_click_the_named_template_button(template_name: str) -> None:
    name = _normalize_quoted_text(template_name)
    _select_template_from_response(template_name=name)


@step("Then the text content field should contain <expected_content>")
def then_the_text_content_field_should_contain(expected_content: str) -> None:
    expected = _normalize_quoted_text(expected_content)
    selected = get_scenario_state().get("selected_upload_template")
    assert selected is not None, "No template selection was recorded."
    actual = selected.get("content", "")
    assert actual == expected, (
        f"Expected template content {expected!r} but found {actual!r}."
    )


@step("And I have a CID containing <cid_content>")
def and_i_have_a_cid_containing(cid_content: str) -> None:
    content = _normalize_quoted_text(cid_content).encode("utf-8")
    cid_value = f"TEMPLATECID{uuid4().hex[:8].upper()}"

    with _app_context():
        record = CID(path=f"/{cid_value}", file_data=content, file_size=len(content))
        db.session.add(record)
        db.session.commit()

    state = get_scenario_state()
    state["last_cid_value"] = cid_value
    state["last_cid_content"] = _normalize_quoted_text(cid_content)


@step("And I have an upload template referencing that CID")
def and_i_have_an_upload_template_referencing_that_cid() -> None:
    state = get_scenario_state()
    cid_value = state.get("last_cid_value")
    assert cid_value, "CID context is missing. Define a CID before referencing it."

    uploads = {
        "cid-template": {
            "name": "CID Template",
            "content_cid": cid_value,
        }
    }
    _save_upload_templates(uploads)
    state["upload_template_count"] = 1
    state["cid_template_key"] = "cid-template"


@step("Then the template should be available for selection")
def then_the_template_should_be_available_for_selection() -> None:
    key = get_scenario_state().get("cid_template_key") or "cid-template"
    body = _get_response_body()
    assert f'data-upload-template-id="{key}"' in body, "CID template button is missing."


@step("And clicking it should populate with the CID content")
def and_clicking_it_should_populate_with_the_cid_content() -> None:
    state = get_scenario_state()
    expected_content = state.get("last_cid_content")
    assert expected_content is not None, (
        "CID content context is missing. Define a CID before verifying template population."
    )

    key = state.get("cid_template_key") or "cid-template"
    selected = _select_template_from_response(template_id=key)
    actual_content = selected.get("content", "")
    assert actual_content == expected_content, (
        f"Expected CID template content {expected_content!r} but found {actual_content!r}."
    )


@step("Then I should see a template named <template_name>")
def then_i_should_see_a_template_named(template_name: str) -> None:
    """Confirm that the rendered upload page lists the provided template name."""

    name = _normalize_quoted_text(template_name)
    body = _get_response_body()
    assert name in body, (
        f"Expected template named {name!r} to appear in the upload page."
    )


@step("And its description should mention <snippet>")
def and_its_description_should_mention(snippet: str) -> None:
    """Verify the upload template description includes the provided text."""

    expected = _normalize_quoted_text(snippet)
    body = _get_response_body()
    assert expected in body, f"Expected template description to include {expected!r}."


# @step('Given there is an alias named <docs> pointing to /guides')
# def ypefci(docs: str) -> None:
#     """Specialised fixture for an alias pointing to /guides."""
#
#     given_alias_exists(docs, "/guides")


@step("When I visit the alias detail page for <alias_name>")
def when_i_visit_alias_detail_page(alias_name: str) -> None:
    """Navigate to the alias detail page for the specified alias."""

    alias_name = alias_name.strip().strip('"')
    path = f"/aliases/{alias_name}"
    when_i_visit_path(path)


@step("When I visit <path>")
def when_i_visit_path(path: str) -> None:
    """Perform a GET request against the provided path."""

    client = _require_client()
    response = client.get(path)
    scenario_state = get_scenario_state()
    scenario_state["response"] = response
    scenario_state["last_path"] = path
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
    alias_name = get_scenario_state().get("alias_name")
    assert alias_name, "Alias name context is unavailable."
    edit_path = get_scenario_state().get("last_path")
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
    assert response.status_code == 302, (
        "Alias update should redirect to the detail page."
    )

    with _app_context():
        alias = Alias.query.filter_by(name=alias_name).first()
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


@step("Given there is an enabled alias named <alias_name> pointing to <target_path>")
def given_enabled_alias_exists(alias_name: str, target_path: str) -> None:
    """Persist an enabled alias with the provided name and target path."""

    alias_name = alias_name.strip().strip('"')
    target_path = target_path.strip().strip('"')

    with _app_context():
        definition_text = format_primary_alias_line(
            match_type="literal",
            match_pattern=None,
            target_path=target_path,
            alias_name=alias_name,
        )
        alias = Alias(
            name=alias_name,
            definition=definition_text,
            enabled=True,
        )
        db.session.add(alias)
        db.session.commit()

    get_scenario_state()["alias_name"] = alias_name


@step('Given there is an alias named "docs" pointing to /guides')
def given_docs_alias_exists() -> None:
    """Create docs alias pointing to /guides."""
    given_alias_exists("docs", "/guides")


# Alias view page assertions
@step("Then the response status should be 200")
def then_response_status_should_be_200() -> None:
    """Assert the response status is 200."""
    response = get_scenario_state().get("response")
    assert response is not None, "No response recorded."
    assert response.status_code == 200, (
        f"Expected status 200, got {response.status_code}"
    )


@step('And the page should contain "Alias Details"')
def and_page_should_contain_alias_details() -> None:
    """Assert page contains Alias Details."""
    body = _get_response_body()
    assert "Alias Details" in body, "Expected to find 'Alias Details' in page"


@step('And the page should contain "test-alias"')
def and_page_should_contain_test_alias() -> None:
    """Assert page contains test-alias."""
    body = _get_response_body()
    assert "test-alias" in body, "Expected to find 'test-alias' in page"


@step('And the page should contain "/test-target"')
def and_page_should_contain_test_target() -> None:
    """Assert page contains /test-target."""
    body = _get_response_body()
    assert "/test-target" in body, "Expected to find '/test-target' in page"


@step('And the page should contain "Back to Aliases"')
def and_page_should_contain_back_to_aliases() -> None:
    """Assert page contains Back to Aliases."""
    body = _get_response_body()
    assert "Back to Aliases" in body, "Expected to find 'Back to Aliases' in page"


@step('And the page should contain "Edit Alias"')
def and_page_should_contain_edit_alias() -> None:
    """Assert page contains Edit Alias."""
    body = _get_response_body()
    assert "Edit Alias" in body, "Expected to find 'Edit Alias' in page"


@step('And the page should contain "Enabled"')
def and_page_should_contain_enabled() -> None:
    """Assert page contains Enabled."""
    body = _get_response_body()
    assert "Enabled" in body, "Expected to find 'Enabled' in page"


@step('And the page should contain "Alias Definition"')
def and_page_should_contain_alias_definition() -> None:
    """Assert page contains Alias Definition."""
    body = _get_response_body()
    assert "Alias Definition" in body, "Expected to find 'Alias Definition' in page"


@step('And the page should contain "How it Works"')
def and_page_should_contain_how_it_works() -> None:
    """Assert page contains How it Works."""
    body = _get_response_body()
    assert "How it Works" in body, "Expected to find 'How it Works' in page"


@step('When I request the page /aliases/new as user "alternate-user"')
def when_i_request_aliases_new_as_alternate() -> None:
    """Request /aliases/new as alternate-user."""
    client = _require_client()
    response = client.get("/aliases/new")
    get_scenario_state()["response"] = response
    attach_response_snapshot(response)
