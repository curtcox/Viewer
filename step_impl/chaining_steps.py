"""Step implementations for server command chaining specs."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from getgauge.python import step

from cid_presenter import format_cid
from cid_utils import generate_cid
from database import db
from models import CID, Server
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state


def _store_server(name: str, definition: str) -> None:
    """Persist a server definition."""
    app = get_shared_app()
    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        existing = Server.query.filter_by(name=name).first()
        if existing:
            existing.definition = normalized
        else:
            db.session.add(Server(name=name, definition=normalized, enabled=True))
        db.session.commit()


def _store_cid(content: bytes) -> str:
    """Store content as a CID and return the CID value."""
    app = get_shared_app()
    cid_value = format_cid(generate_cid(content))

    with app.app_context():
        existing = CID.query.filter_by(path=f"/{cid_value}").first()
        if not existing:
            db.session.add(CID(path=f"/{cid_value}", file_data=content))
            db.session.commit()

    return cid_value


def _resolve_cid_content(location: str) -> Optional[str]:
    """Retrieve CID content from a redirect location."""
    app = get_shared_app()
    raw_path = urlsplit(location).path or location

    candidates = [raw_path]
    if "." in raw_path:
        candidates.append(raw_path.split(".", 1)[0])

    with app.app_context():
        for candidate in candidates:
            record = CID.query.filter_by(path=candidate).first()
            if record is not None:
                return record.file_data.decode("utf-8")

    return None


@step(['Given a server named "<server_name>" that echoes its input with prefix "<prefix>"',
       'And a server named "<server_name>" that echoes its input with prefix "<prefix>"'])
def given_echo_server(server_name: str, prefix: str) -> None:
    """Create a server that echoes input with a prefix."""
    definition = f'''
def main(input_data):
    return {{"output": f"{prefix}{{input_data}}", "content_type": "text/plain"}}
'''
    _store_server(server_name, definition)


@step(['Given a server named "<server_name>" that returns "<value>"',
       'And a server named "<server_name>" that returns "<value>"'])
def given_simple_server(server_name: str, value: str) -> None:
    """Create a server that returns a fixed value."""
    definition = f'''
def main():
    return {{"output": "{value}", "content_type": "text/plain"}}
'''
    _store_server(server_name, definition)


@step('And a CID containing "<content>"')
def and_cid_containing(content: str) -> None:
    """Store a CID with the given content."""
    state = get_scenario_state()
    cid_value = _store_cid(content.encode("utf-8"))
    state["last_cid"] = cid_value


@step("When I request the processor server with the stored CID")
def when_request_processor_cid() -> None:
    """Request the chained processor/CID resource."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored. Call 'And a CID containing' first."

    client = get_shared_client()
    response = client.get(f"/processor/{cid_value}")
    state["response"] = response


@step("When I request the chained resource /second/first")
def when_request_second_first() -> None:
    """Request the chained second/first resource."""
    client = get_shared_client()
    state = get_scenario_state()
    response = client.get("/second/first")
    state["response"] = response


@step("When I request the level2/level1 servers with the stored CID")
def when_request_level2_level1_cid() -> None:
    """Request the three-level chained resource."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored. Call 'And a CID containing' first."

    client = get_shared_client()
    response = client.get(f"/level2/level1/{cid_value}")
    state["response"] = response


@step("Then the response should redirect to a CID")
def then_response_redirects() -> None:
    """Assert the response is a redirect to a CID."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    assert response.status_code in {302, 303}, (
        f"Expected redirect status but got {response.status_code}"
    )
    location = response.headers.get("Location")
    assert location, "Redirect response missing Location header"
    state["redirect_location"] = location


@step('And the CID content should be "<expected_content>"')
def and_cid_content_should_be(expected_content: str) -> None:
    """Assert the CID content matches the expected value."""
    state = get_scenario_state()
    location = state.get("redirect_location")
    assert location, "No redirect location recorded."

    content = _resolve_cid_content(location)
    assert content is not None, f"Could not resolve CID content for {location}"
    assert content == expected_content, (
        f"Expected CID content '{expected_content}' but got '{content}'"
    )


@step('Given the default server "<server_name>" is available')
def given_default_server_available(server_name: str) -> None:
    """Load a default server definition from reference templates."""

    definition_path = (
        Path("reference_templates") / "servers" / "definitions" / f"{server_name}.py"
    )
    assert definition_path.exists(), f"Default server {server_name} not found"

    _store_server(server_name, definition_path.read_text(encoding="utf-8"))


@step('And a wrapping server named "<server_name>" that wraps payload with "<prefix>"')
def and_wrapping_server(server_name: str, prefix: str) -> None:
    """Create a wrapper server that prefixes chained payloads."""

    definition = f'''
def main(payload):
    return {{"output": f"{prefix}{{payload}}", "content_type": "text/plain"}}
'''
    _store_server(server_name, definition)


@step('When I request the resource /<path_prefix>/{stored CID}')
def when_request_resource_with_cid(path_prefix: str) -> None:
    """Request a chained resource using the stored CID."""

    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored. Call 'And a CID containing' first."

    normalized = path_prefix.strip("/")
    request_path = f"/{normalized}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step('Then the CID content should contain "<expected_content>"')
def then_cid_content_contains(expected_content: str) -> None:
    """Assert the CID content includes the expected substring."""

    state = get_scenario_state()
    location = state.get("redirect_location")
    assert location, "No redirect location recorded."

    content = _resolve_cid_content(location)
    assert content is not None, f"Could not resolve CID content for {location}"
    assert expected_content in content, (
        f"Expected CID content to include '{expected_content}' but got '{content}'"
    )
