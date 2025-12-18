"""Gauge steps for exercising the import and export workflow."""
from __future__ import annotations

import base64
import binascii
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from flask.testing import FlaskClient
from getgauge.python import after_scenario, before_scenario, step

from app import create_app
from cid_presenter import cid_path
from database import db
from identity import ensure_default_resources
from models import CID, Server
from step_impl.artifacts import attach_response_snapshot

_scenario_state: dict[str, Any] = {}
_created_apps: list[Any] = []
_created_db_paths: list[Path] = []
_active_patchers: list[Any] = []


def _load_export_cid_content(cid_value: str) -> bytes:
    """Return the raw bytes for the provided CID reference within the export payload."""
    parsed_export = _scenario_state.get("parsed_export")
    assert parsed_export is not None, "Export metadata is missing."

    cid_map = parsed_export.get("cid_values") or {}
    entry = cid_map.get(cid_value)
    content_bytes: bytes | None = None

    # Handle both old format (dict with encoding/value) and new format (string)
    if isinstance(entry, dict):
        encoding = (entry.get("encoding") or "utf-8").strip().lower()
        value = entry.get("value")
        assert isinstance(value, str), (
            f'CID "{cid_value}" entry did not include string content.'
        )

        if encoding == "base64":
            try:
                content_bytes = base64.b64decode(value.encode("ascii"))
            except (binascii.Error, ValueError) as exc:
                raise AssertionError(
                    f'CID "{cid_value}" entry specified invalid base64 content.'
                ) from exc
        else:
            content_bytes = value.encode("utf-8")
    elif isinstance(entry, str):
        # New format: entry is directly a UTF-8 string
        content_bytes = entry.encode("utf-8")

    if content_bytes is None:
        origin_app = _scenario_state.get("origin_app")
        assert origin_app is not None, "Origin site is not configured."
        with origin_app.app_context():
            record = CID.query.filter_by(path=cid_path(cid_value)).first()
            assert record is not None, (
                f'CID "{cid_value}" content was not stored on the origin site.'
            )
            file_data = record.file_data
            assert file_data is not None, (
                f'CID "{cid_value}" entry on the origin site did not include content.'
            )
            content_bytes = bytes(file_data)

    return content_bytes


def _resolve_export_section(section_name: str) -> Any:
    """Decode and return a structured export section referenced by CID."""
    parsed_export = _scenario_state.get("parsed_export")
    assert parsed_export is not None, "Export metadata is missing."

    section_reference = parsed_export.get(section_name)
    if section_reference is None:
        return None

    if isinstance(section_reference, str):
        content_bytes = _load_export_cid_content(section_reference)
        try:
            section_text = content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AssertionError(
                f'Section "{section_name}" referenced CID "{section_reference}" '
                "with non UTF-8 content."
            ) from exc

        try:
            return json.loads(section_text)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f'Section "{section_name}" referenced CID "{section_reference}" '
                "that did not contain valid JSON."
            ) from exc

    return section_reference


def _create_isolated_site(label: str) -> tuple[Any, FlaskClient]:
    """Return a Flask app and client backed by an isolated database."""
    fd, db_path_str = tempfile.mkstemp(prefix=f"gauge-{label}-", suffix=".sqlite3")
    os.close(fd)
    db_path = Path(db_path_str)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,
        }
    )

    client = app.test_client()

    _created_apps.append(app)
    _created_db_paths.append(db_path)

    return app, client


@before_scenario()
def reset_scenario_state() -> None:
    """Clear per-scenario state before each scenario begins."""
    _scenario_state.clear()


@after_scenario()
def cleanup_created_sites() -> None:
    """Dispose of database connections and temporary files created in a scenario."""
    while _active_patchers:
        patcher = _active_patchers.pop()
        try:
            patcher.stop()
        except RuntimeError:
            pass

    for app in _created_apps:
        with app.app_context():
            db.session.remove()
    _created_apps.clear()

    for db_path in _created_db_paths:
        if db_path.exists():
            db_path.unlink()
    _created_db_paths.clear()


@step('Given an origin site with a server named "{}" returning "{}"')
def given_origin_site_with_server(server_name: str, server_message: str) -> None:
    """Create an origin site that hosts the provided server implementation."""
    origin_app, origin_client = _create_isolated_site("origin")

    server_definition = (
        "return {\"output\": \""
        + server_message
        + "\", \"content_type\": \"text/plain\"}"
    )

    with origin_app.app_context():
        ensure_default_resources()
        db.session.add(
            Server(name=server_name, definition=server_definition)
        )
        db.session.commit()

    _scenario_state.update(
        {
            "origin_app": origin_app,
            "origin_client": origin_client,
            "server_name": server_name,
            "server_message": server_message,
            "server_definition": server_definition,
        }
    )


@step("And I export servers and their CID map from the origin site")
def and_i_export_servers_from_origin() -> None:
    """Run an export that includes servers and the CID map, capturing the payload."""
    origin_app = _scenario_state.get("origin_app")
    origin_client = _scenario_state.get("origin_client")
    assert origin_app is not None and origin_client is not None, "Origin site is not configured."

    export_response = origin_client.post(
        "/export",
        data={
            "include_servers": "y",
            "include_cid_map": "y",
            "submit": True,
        },
    )
    attach_response_snapshot(export_response)
    assert (
        export_response.status_code == 200
    ), f"Expected export to succeed, received {export_response.status_code}."

    with origin_app.app_context():
        export_record = next(
            (
                record
                for record in CID.query.order_by(CID.id.desc()).all()
                if b'"servers"' in record.file_data
            ),
            None,
        )
        assert export_record is not None, "Expected a stored export payload."
        export_payload = export_record.file_data.decode("utf-8")
        parsed_payload = json.loads(export_payload)

    assert "cid_values" in parsed_payload, "Export payload did not include the CID map."

    _scenario_state.update(
        {
            "export_payload": export_payload,
            "parsed_export": parsed_payload,
        }
    )


@step("When I import the exported data into a fresh destination site")
def when_i_import_exported_data_into_destination() -> None:
    """Import the captured payload into a new destination site."""
    export_payload = _scenario_state.get("export_payload")
    assert export_payload, "No export payload is available to import."

    destination_app, destination_client = _create_isolated_site("destination")

    import_response = destination_client.post(
        "/import",
        data={
            "import_source": "text",
            "import_text": export_payload,
            "include_servers": "y",
            "process_cid_map": "y",
            "submit": True,
        },
        follow_redirects=False,
    )
    attach_response_snapshot(import_response)
    assert (
        import_response.status_code == 302
    ), f"Expected import to redirect on success, received {import_response.status_code}."

    _scenario_state.update(
        {
            "destination_app": destination_app,
            "destination_client": destination_client,
        }
    )


@step('Then the destination site should have a server named "{}"')
def then_destination_has_server(server_name: str) -> None:
    """Verify the imported site now owns a server with the expected name and content."""
    from cid_core import is_literal_cid  # pylint: disable=import-outside-toplevel

    destination_app = _scenario_state.get("destination_app")
    parsed_export = _scenario_state.get("parsed_export")
    server_definition = _scenario_state.get("server_definition")
    assert destination_app is not None, "Destination site is not available."
    assert parsed_export is not None, "Export metadata is missing."
    assert server_definition is not None, "Origin server definition is missing."

    servers_section = _resolve_export_section("servers")
    assert isinstance(
        servers_section, list
    ), "Export payload did not include a servers section."
    exported_entry = next(
        (entry for entry in servers_section if entry.get("name") == server_name),
        None,
    )
    assert exported_entry is not None, "Export payload did not include the server entry."
    expected_cid = exported_entry.get("definition_cid")
    assert expected_cid, "Exported server did not record a definition CID."

    cid_map = parsed_export.get("cid_values") or {}
    assert expected_cid in cid_map, (
        f"Export payload did not include CID map content for definition {expected_cid}."
    )

    cid_bytes = _load_export_cid_content(expected_cid)
    try:
        cid_text = cid_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(
            f'CID "{expected_cid}" content was not UTF-8 encoded.'
        ) from exc
    assert cid_text == server_definition, "CID map content did not match the server definition."

    with destination_app.app_context():
        imported_server = Server.query.filter_by(name=server_name).first()
        assert imported_server is not None, "Imported server was not found."
        assert (
            imported_server.definition == server_definition
        ), "Imported server definition does not match the origin definition."
        assert (
            imported_server.definition_cid == expected_cid
        ), "Imported server definition CID does not match export metadata."

        if not is_literal_cid(expected_cid):
            cid_record = CID.query.filter_by(path=cid_path(expected_cid)).first()
            assert cid_record is not None, "Definition CID file was not stored on import."
            assert (
                cid_record.file_data.decode("utf-8") == server_definition
            ), "Imported CID content does not match the server definition."

    _scenario_state["destination_server_name"] = server_name


@step('And executing "{}" on the destination site should return "{}"')
def and_executing_destination_route_returns_message(route_path: str, expected_message: str) -> None:
    """Execute the imported server and confirm the expected response content."""
    destination_client = _scenario_state.get("destination_client")
    assert destination_client is not None, "Destination client is not configured."

    execution_response = destination_client.get(route_path, follow_redirects=False)
    attach_response_snapshot(execution_response)
    assert (
        execution_response.status_code == 302
    ), f"Expected execution redirect, received {execution_response.status_code}."

    redirect_location = execution_response.headers.get("Location")
    assert redirect_location, "Execution redirect did not specify a location."

    content_response = destination_client.get(redirect_location)
    attach_response_snapshot(content_response)
    assert content_response.status_code == 200, "CID content request failed."
    assert (
        expected_message in content_response.get_data(as_text=True)
    ), "Imported server did not return the expected output."


@step('Given an origin site with a server named "shared-tool" returning "Hello from origin"')
def given_origin_site_with_shared_tool() -> None:
    """Create an origin site with shared-tool server."""
    given_origin_site_with_server("shared-tool", "Hello from origin")


@step('Then the destination site should have a server named "shared-tool"')
def then_destination_has_shared_tool() -> None:
    """Verify destination has shared-tool server."""
    then_destination_has_server("shared-tool")


@step('And executing "/shared-tool" on the destination site should return "Hello from origin"')
def and_executing_shared_tool_returns_hello() -> None:
    """Execute shared-tool and verify output."""
    and_executing_destination_route_returns_message("/shared-tool", "Hello from origin")


@step('When I export the server to a GitHub PR with mock repository "{}"')
def when_i_export_server_to_github_pr_with_mock_repo(target_repo: str) -> None:
    """Export from the origin site via the /export GitHub PR flow (mocked)."""

    origin_client = _scenario_state.get("origin_client")
    assert origin_client is not None, "Origin site is not configured."

    captured: dict[str, Any] = {}

    def _mock_create_export_pr(*, export_json: str, target_repo: str | None = None, **kwargs: Any) -> dict[str, Any]:
        captured["export_json"] = export_json
        captured["target_repo"] = target_repo
        captured["kwargs"] = dict(kwargs)
        return {
            "url": "https://api.github.com/repos/owner/repo/pulls/1",
            "number": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
            "branch_name": "viewer-export-test",
            "target_repo": target_repo or "",
            "mode": "github",
        }

    patcher = patch("routes.import_export.github_pr.create_export_pr", side_effect=_mock_create_export_pr)
    patcher.start()
    _active_patchers.append(patcher)

    export_response = origin_client.post(
        "/export",
        data={
            "include_servers": "y",
            "include_cid_map": "y",
            "github_target_repo": target_repo,
            "github_token": "test_token",
            "github_pr_title": "Test PR",
            "github_pr_description": "Test description",
            "submit_github_pr": "Create Pull Request",
        },
        follow_redirects=False,
    )
    attach_response_snapshot(export_response)
    _scenario_state["last_response"] = export_response
    _scenario_state["github_export_capture"] = captured


@step("Then the PR should be created successfully")
def then_pr_should_be_created_successfully() -> None:
    """Verify export response includes success messaging and mock data was captured."""

    response = _scenario_state.get("last_response")
    assert response is not None, "No response available to validate."
    assert response.status_code == 200, f"Expected 200 response, got {response.status_code}."

    body = response.get_data(as_text=True)
    assert "Pull request created successfully" in body, "Expected PR success message in response body."

    captured = _scenario_state.get("github_export_capture")
    assert captured is not None, "Expected GitHub PR mock capture metadata."
    assert captured.get("target_repo") is not None, "Expected target repo passed to create_export_pr."


@step("And the PR should contain the boot image file with the exported server")
def and_pr_should_contain_boot_image_file_with_exported_server() -> None:
    """Verify the exported JSON payload contains the server entry."""

    server_name = _scenario_state.get("server_name")
    assert isinstance(server_name, str) and server_name, "Server name metadata is missing."

    captured = _scenario_state.get("github_export_capture")
    assert captured is not None, "Expected GitHub PR mock capture metadata."

    export_json = captured.get("export_json")
    assert isinstance(export_json, str) and export_json.strip(), "Expected export JSON to be passed to create_export_pr."
    assert server_name in export_json, "Expected exported server name to appear in export JSON payload."


@step('Given a GitHub PR with mock URL containing a server named "{}"')
def given_github_pr_with_mock_url_containing_server(server_name: str) -> None:
    """Prepare a mocked GitHub PR export payload and patch PR fetch to return it."""

    # Build a valid export payload by using the existing export flow on an isolated site.
    pr_source_app, pr_source_client = _create_isolated_site("github-pr-source")

    server_definition = (
        'return {"output": "Hello from PR", "content_type": "text/plain"}'
    )

    with pr_source_app.app_context():
        ensure_default_resources()
        db.session.add(Server(name=server_name, definition=server_definition))
        db.session.commit()

    export_response = pr_source_client.post(
        "/export",
        data={
            "include_servers": "y",
            "include_cid_map": "y",
            "submit": True,
        },
    )
    attach_response_snapshot(export_response)
    assert export_response.status_code == 200, "Expected export to succeed for mock PR payload."

    with pr_source_app.app_context():
        export_record = next(
            (
                record
                for record in CID.query.order_by(CID.id.desc()).all()
                if record.file_data and b'"servers"' in record.file_data
            ),
            None,
        )
        assert export_record is not None, "Expected a stored export payload for mock PR."
        export_payload = export_record.file_data.decode("utf-8")

    parsed_export = json.loads(export_payload)
    assert isinstance(parsed_export, dict), "Mock PR export payload was not a JSON object."

    pr_url = "https://github.com/owner/repo/pull/123"

    patcher = patch(
        "routes.import_export.github_pr.fetch_pr_export_data",
        return_value=(export_payload, None),
    )
    patcher.start()
    _active_patchers.append(patcher)

    _scenario_state.update(
        {
            "github_pr_url": pr_url,
            "mock_pr_server_name": server_name,
            "parsed_export": parsed_export,
            "server_definition": server_definition,
        }
    )


@step("When I import from the GitHub PR URL")
def when_i_import_from_the_github_pr_url() -> None:
    """Import the mocked PR payload into a fresh destination site."""

    pr_url = _scenario_state.get("github_pr_url")
    assert isinstance(pr_url, str) and pr_url, "Mock PR URL is missing."

    destination_app, destination_client = _create_isolated_site("destination")

    import_response = destination_client.post(
        "/import",
        data={
            "import_source": "github_pr",
            "github_pr_url": pr_url,
            "github_import_token": "test_token",
            "include_servers": "y",
            "process_cid_map": "y",
            "submit": True,
        },
        follow_redirects=False,
    )
    attach_response_snapshot(import_response)
    _scenario_state["last_response"] = import_response
    assert import_response.status_code == 302, (
        f"Expected import to redirect on success, received {import_response.status_code}."
    )

    _scenario_state.update(
        {
            "destination_app": destination_app,
            "destination_client": destination_client,
        }
    )


@step('And executing "/imported-server" on the destination site should return "Hello from PR"')
def and_executing_imported_server_returns_hello_from_pr() -> None:
    and_executing_destination_route_returns_message("/imported-server", "Hello from PR")


@step("When I attempt to export to GitHub PR without a token")
def when_i_attempt_export_to_github_pr_without_token() -> None:
    """Attempt to export via GitHub PR flow while simulating missing token error."""

    from routes.import_export.github_pr import GitHubPRError

    origin_client = _scenario_state.get("origin_client")
    assert origin_client is not None, "Origin site is not configured."

    def _raise_missing_token(*args: Any, **kwargs: Any) -> Any:
        raise GitHubPRError("GitHub token is required")

    patcher = patch("routes.import_export.github_pr.create_export_pr", side_effect=_raise_missing_token)
    patcher.start()
    _active_patchers.append(patcher)

    export_response = origin_client.post(
        "/export",
        data={
            "include_servers": "y",
            "include_cid_map": "y",
            "github_target_repo": "owner/repo",
            "github_token": "",
            "submit_github_pr": "Create Pull Request",
        },
        follow_redirects=False,
    )
    attach_response_snapshot(export_response)
    _scenario_state["last_response"] = export_response


@step('Then I should see an error message "{}"')
def then_i_should_see_error_message(expected_message: str) -> None:
    """Assert the last response body includes the expected message."""

    response = _scenario_state.get("last_response")
    assert response is not None, "No response available to validate."
    body = response.get_data(as_text=True)
    assert expected_message in body, f"Expected to find '{expected_message}' in the response body."


@step("Given a GitHub PR URL that doesn't modify the boot image file")
def given_github_pr_url_that_does_not_modify_boot_image() -> None:
    """Patch PR fetch to return the expected error message."""

    pr_url = "https://github.com/owner/repo/pull/456"
    message = "Pull request does not modify the boot image file"

    patcher = patch(
        "routes.import_export.github_pr.fetch_pr_export_data",
        return_value=(None, message),
    )
    patcher.start()
    _active_patchers.append(patcher)
    _scenario_state["github_pr_url"] = pr_url


@step("When I attempt to import from that PR URL")
def when_i_attempt_to_import_from_that_pr_url() -> None:
    """Attempt to import from the mocked failing PR URL."""

    pr_url = _scenario_state.get("github_pr_url")
    assert isinstance(pr_url, str) and pr_url, "Mock PR URL is missing."

    destination_app, destination_client = _create_isolated_site("destination")

    response = destination_client.post(
        "/import",
        data={
            "import_source": "github_pr",
            "github_pr_url": pr_url,
            "include_servers": "y",
            "process_cid_map": "y",
            "submit": True,
        },
        follow_redirects=False,
    )
    attach_response_snapshot(response)
    _scenario_state["last_response"] = response
    _scenario_state["destination_app"] = destination_app
    _scenario_state["destination_client"] = destination_client
