"""Step implementations for bash path parameters specs."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlsplit

from getgauge.python import step

from cid_storage import get_cid_content, store_cid_from_bytes
from database import db
from models import Server
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state


def _store_server(name: str, definition: str) -> None:
    """Persist a server definition."""
    app = get_shared_app()
    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        try:
            existing = Server.query.filter_by(name=name).first()
            if existing:
                existing.definition = normalized
            else:
                db.session.add(Server(name=name, definition=normalized, enabled=True))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise


def _store_cid(content: bytes) -> str:
    """Store content as a CID and return the CID value."""
    app = get_shared_app()
    with app.app_context():
        return store_cid_from_bytes(content)


def _resolve_cid_content(location: str) -> Optional[str]:
    """Retrieve CID content from a redirect location."""
    app = get_shared_app()
    raw_path = urlsplit(location).path or location

    candidates = [raw_path]
    if "." in raw_path:
        candidates.append(raw_path.rsplit(".", 1)[0])

    with app.app_context():
        for candidate in candidates:
            record = get_cid_content(candidate)
            if record is not None:
                return record.file_data.decode("utf-8")

    return None


def _load_server_from_reference(name: str) -> str:
    """Load a server definition from reference templates."""
    definition_path = (
        Path("reference_templates") / "servers" / "definitions" / f"{name}.sh"
    )
    if definition_path.exists():
        return definition_path.read_text(encoding="utf-8")

    # Try .py extension
    definition_path = (
        Path("reference_templates") / "servers" / "definitions" / f"{name}.py"
    )
    assert definition_path.exists(), f"Server {name} not found"
    return definition_path.read_text(encoding="utf-8")


# Server availability steps

@step("Given the awk server is available")
def given_awk_server_available() -> None:
    """Load the awk server definition."""
    definition = _load_server_from_reference("awk")
    _store_server("awk", definition)


@step("Given the sed server is available")
def given_sed_server_available() -> None:
    """Load the sed server definition."""
    definition = _load_server_from_reference("sed")
    _store_server("sed", definition)


@step("Given the grep server is available")
def given_grep_server_available() -> None:
    """Load the grep server definition."""
    definition = _load_server_from_reference("grep")
    _store_server("grep", definition)


@step("Given the jq server is available")
def given_jq_server_available() -> None:
    """Load the jq server definition."""
    definition = _load_server_from_reference("jq")
    _store_server("jq", definition)


@step("Given a simple bash server without path parameters")
def given_simple_bash_server() -> None:
    """Create a bash server that doesn't use $1."""
    definition = """#!/bin/bash
echo "Simple bash output"
cat
"""
    _store_server("simple-bash", definition)


# CID storage steps

@step('And a CID containing "<content>" as pattern_cid')
def and_cid_as_pattern(content: str) -> None:
    """Store a CID with the given content as pattern_cid."""
    state = get_scenario_state()
    cid_value = _store_cid(content.encode("utf-8"))
    state["pattern_cid"] = cid_value
    state["last_cid"] = cid_value


@step("And a CID containing multiline grep test data")
def and_multiline_grep_data() -> None:
    """Store a CID with multiline data for grep testing."""
    state = get_scenario_state()
    content = b"apple pie\nbanana bread\napricot jam\ncherry tart"
    cid_value = _store_cid(content)
    state["last_cid"] = cid_value


@step("And a CID containing JSON data '<json_content>'")
def and_json_cid(json_content: str) -> None:
    """Store a CID with JSON content."""
    state = get_scenario_state()
    cid_value = _store_cid(json_content.encode("utf-8"))
    state["last_cid"] = cid_value


# Request steps for servers with path parameters

@step('When I request the awk server with pattern "<pattern>" and the stored CID')
def when_request_awk_with_pattern(pattern: str) -> None:
    """Request the awk server with a pattern and stored CID."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    # URL-encode the pattern
    encoded_pattern = quote(pattern, safe="")
    request_path = f"/awk/{encoded_pattern}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step("When I request the awk server with CID pattern and the stored CID")
def when_request_awk_with_cid_pattern() -> None:
    """Request the awk server with a CID as pattern and another CID as input."""
    state = get_scenario_state()
    pattern_cid = state.get("pattern_cid")
    input_cid = state.get("last_cid")
    assert pattern_cid, "No pattern CID stored."
    assert input_cid, "No input CID stored."

    request_path = f"/awk/{pattern_cid}/{input_cid}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step('When I request the sed server with expression "<expression>" and the stored CID')
def when_request_sed_with_expression(expression: str) -> None:
    """Request the sed server with an expression and stored CID."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    # URL-encode the expression
    encoded_expression = quote(expression, safe="")
    request_path = f"/sed/{encoded_expression}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step('When I request the grep server with pattern "<pattern>" and the stored CID')
def when_request_grep_with_pattern(pattern: str) -> None:
    """Request the grep server with a pattern and stored CID."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    # URL-encode the pattern
    encoded_pattern = quote(pattern, safe="")
    request_path = f"/grep/{encoded_pattern}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step('When I request the jq server with filter "<jq_filter>" and the stored CID')
def when_request_jq_with_filter(jq_filter: str) -> None:
    """Request the jq server with a filter and stored CID."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    # URL-encode the filter
    encoded_filter = quote(jq_filter, safe="")
    request_path = f"/jq/{encoded_filter}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step("When I request the resource /<path>/{stored CID}")
def when_request_path_with_stored_cid(path: str) -> None:
    """Request a path with the stored CID appended."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    # Replace {stored CID} placeholder in path if present
    normalized_path = path.replace("{stored CID}", cid_value)
    request_path = f"/{normalized_path}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


# Generic request step for wrapper tests

@step("When I request the resource /awk-wrapper/awk/{print $1}/{stored CID}")
def when_request_awk_wrapper() -> None:
    """Request awk-wrapper with awk path parameter chain."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    encoded_pattern = quote("{print $1}", safe="")
    request_path = f"/awk-wrapper/awk/{encoded_pattern}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step("When I request the resource /sed-wrapper/sed/s%2Fbar%2Fbaz%2F/{stored CID}")
def when_request_sed_wrapper() -> None:
    """Request sed-wrapper with sed path parameter chain."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    request_path = f"/sed-wrapper/sed/s%2Fbar%2Fbaz%2F/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step("When I request the resource /grep-wrapper/grep/apple/{stored CID}")
def when_request_grep_wrapper() -> None:
    """Request grep-wrapper with grep path parameter chain."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    request_path = f"/grep-wrapper/grep/apple/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step("When I request the resource /jq-wrapper/jq/.key/{stored CID}")
def when_request_jq_wrapper() -> None:
    """Request jq-wrapper with jq path parameter chain."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored."

    encoded_filter = quote(".key", safe="")
    request_path = f"/jq-wrapper/jq/{encoded_filter}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step("When I request the resource /simple-bash/input-source")
def when_request_simple_bash() -> None:
    """Request simple-bash server with input-source."""
    client = get_shared_client()
    state = get_scenario_state()
    response = client.get("/simple-bash/input-source")
    state["response"] = response


# Assertion steps

@step("And the CID content should not contain \"<expected>\"")
def and_cid_content_should_not_contain(expected: str) -> None:
    """Assert the CID content does not include the expected substring."""
    state = get_scenario_state()
    location = state.get("redirect_location")
    assert location, "No redirect location recorded."

    content = _resolve_cid_content(location)
    assert content is not None, f"Could not resolve CID content for {location}"
    assert expected not in content, (
        f"Expected CID content to NOT include '{expected}' but got '{content}'"
    )
