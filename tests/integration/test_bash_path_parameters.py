"""Integration tests for bash path parameter support ($1).

These tests verify the end-to-end behavior of bash servers that use
path parameters through $1, including the new awk, sed, grep, and jq servers.
"""

from __future__ import annotations

import textwrap
from urllib.parse import urlsplit

import pytest

from cid_utils import generate_cid
from database import db
from db_access import get_cid_by_path
from models import CID, Server


pytestmark = pytest.mark.integration

JQ_SERVER_DEFINITION = """#!/bin/bash
set -e
tmp=$(mktemp -t jq-server.XXXXXX)
trap 'rm -f "$tmp"' EXIT
cat > "$tmp"
jq --unbuffered "$1" "$tmp"
"""


def _store_server(app, name: str, definition: str) -> None:
    """Persist a server definition."""
    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        existing = Server.query.filter_by(name=name).first()
        if existing:
            existing.definition = normalized
        else:
            db.session.add(Server(name=name, definition=normalized, enabled=True))
        db.session.commit()


def _store_cid(app, content: bytes) -> str:
    """Store content as a CID and return the CID value."""
    cid_value = generate_cid(content)
    with app.app_context():
        existing = CID.query.filter_by(path=f"/{cid_value}").first()
        if not existing:
            db.session.add(CID(path=f"/{cid_value}", file_data=content))
            db.session.commit()
    return cid_value


def _resolve_cid_payload(app, location: str) -> str:
    """Return the stored CID payload for the redirect location."""
    raw_path = urlsplit(location).path or location
    candidates = [raw_path]
    if "." in raw_path:
        candidates.append(raw_path.split(".", 1)[0])

    with app.app_context():
        record = None
        for candidate in candidates:
            record = get_cid_by_path(candidate)
            if record is not None:
                break

        if record is None:
            return None
        return record.file_data.decode("utf-8")


def _extract_response_body(app, response) -> str:
    """Return the response payload, following CID redirects when necessary."""
    if response.status_code in {302, 303}:
        location = response.headers.get("Location")
        assert location, "Redirect response missing Location header"
        return _resolve_cid_payload(app, location)
    return response.get_data(as_text=True)


# Tests for awk server

def test_awk_server_accepts_pattern_from_path(client, integration_app):
    """Awk server should accept pattern from path segment and input from chained server."""
    _store_server(
        integration_app,
        "awk",
        """#!/bin/bash
awk "$1"
""",
    )

    _store_server(
        integration_app,
        "echo_data",
        """
def main():
    return {"output": "hello world\\nfoo bar\\nhello again", "content_type": "text/plain"}
""",
    )

    response = client.get("/awk/{print $1}/echo_data")
    body = _extract_response_body(integration_app, response)

    assert "hello" in body
    assert "foo" in body


def test_awk_server_with_cid_input(client, integration_app):
    """Awk server should accept CID as input source."""
    _store_server(
        integration_app,
        "awk",
        """#!/bin/bash
awk "$1"
""",
    )

    cid = _store_cid(integration_app, b"line1 value1\nline2 value2\nline3 value3")

    response = client.get(f"/awk/{{print $2}}/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "value1" in body
    assert "value2" in body
    assert "value3" in body


def test_awk_server_provides_input_to_left(client, integration_app):
    """Awk server output should chain to the server on its left."""
    _store_server(
        integration_app,
        "awk",
        """#!/bin/bash
awk "$1"
""",
    )

    _store_server(
        integration_app,
        "wrapper",
        """
def main(payload):
    return {"output": f"wrapped:{payload}", "content_type": "text/plain"}
""",
    )

    cid = _store_cid(integration_app, b"hello world")

    response = client.get(f"/wrapper/awk/{{print $1}}/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "wrapped:hello" in body


# Tests for sed server

def test_sed_server_accepts_expression_from_path(client, integration_app):
    """Sed server should accept expression from path segment."""
    _store_server(
        integration_app,
        "sed",
        """#!/bin/bash
sed "$1"
""",
    )

    _store_server(
        integration_app,
        "echo_text",
        """
def main():
    return {"output": "hello world", "content_type": "text/plain"}
""",
    )

    response = client.get("/sed/s%2Fworld%2Funiverse%2F/echo_text")  # URL-encoded s/world/universe/
    body = _extract_response_body(integration_app, response)

    assert "hello universe" in body


def test_sed_server_with_cid_input(client, integration_app):
    """Sed server should accept CID as input source."""
    _store_server(
        integration_app,
        "sed",
        """#!/bin/bash
sed "$1"
""",
    )

    cid = _store_cid(integration_app, b"foo bar baz")

    response = client.get(f"/sed/s%2Fbar%2FREPLACED%2F/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "foo REPLACED baz" in body


def test_sed_server_provides_input_to_left(client, integration_app):
    """Sed server output should chain to the server on its left."""
    _store_server(
        integration_app,
        "sed",
        """#!/bin/bash
sed "$1"
""",
    )

    _store_server(
        integration_app,
        "prefix",
        """
def main(payload):
    return {"output": f"PREFIX:{payload}", "content_type": "text/plain"}
""",
    )

    cid = _store_cid(integration_app, b"original text")

    response = client.get(f"/prefix/sed/s%2Foriginal%2Fmodified%2F/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "PREFIX:modified text" in body


# Tests for grep server

def test_grep_server_accepts_pattern_from_path(client, integration_app):
    """Grep server should accept pattern from path segment."""
    _store_server(
        integration_app,
        "grep",
        """#!/bin/bash
grep -E "$1" || true
""",
    )

    _store_server(
        integration_app,
        "multiline",
        """
def main():
    return {"output": "apple\\nbanana\\napricot\\ncherry", "content_type": "text/plain"}
""",
    )

    response = client.get("/grep/^a/multiline")
    body = _extract_response_body(integration_app, response)

    assert "apple" in body
    assert "apricot" in body
    assert "banana" not in body
    assert "cherry" not in body


def test_grep_server_with_cid_input(client, integration_app):
    """Grep server should accept CID as input source."""
    _store_server(
        integration_app,
        "grep",
        """#!/bin/bash
grep -E "$1" || true
""",
    )

    cid = _store_cid(integration_app, b"error: something failed\ninfo: all good\nerror: another issue")

    response = client.get(f"/grep/error/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "error: something failed" in body
    assert "error: another issue" in body
    assert "info: all good" not in body


def test_grep_server_provides_input_to_left(client, integration_app):
    """Grep server output should chain to the server on its left."""
    _store_server(
        integration_app,
        "grep",
        """#!/bin/bash
grep -E "$1" || true
""",
    )

    _store_server(
        integration_app,
        "count_lines",
        """
def main(payload):
    lines = payload.strip().split("\\n") if payload else []
    return {"output": f"count:{len(lines)}", "content_type": "text/plain"}
""",
    )

    cid = _store_cid(integration_app, b"match1\nno\nmatch2\nno\nmatch3")

    response = client.get(f"/count_lines/grep/match/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "count:3" in body


# Tests for jq server

def test_jq_server_accepts_filter_from_path(client, integration_app):
    """Jq server should accept filter from path segment."""
    _store_server(
        integration_app,
        "jq",
        JQ_SERVER_DEFINITION,
    )

    _store_server(
        integration_app,
        "json_data",
        """
import json
def main():
    data = json.dumps({"name": "test", "value": 42})
    return {"output": data, "content_type": "application/json"}
""",
    )

    response = client.get("/jq/.name/json_data")
    body = _extract_response_body(integration_app, response)

    assert '"test"' in body


def test_jq_server_with_cid_input(client, integration_app):
    """Jq server should accept CID as input source."""
    _store_server(
        integration_app,
        "jq",
        JQ_SERVER_DEFINITION,
    )

    cid = _store_cid(integration_app, b'{"items": [1, 2, 3], "total": 6}')

    response = client.get(f"/jq/.total/{cid}")
    body = _extract_response_body(integration_app, response)

    assert "6" in body


def test_jq_server_provides_input_to_left(client, integration_app):
    """Jq server output should chain to the server on its left."""
    _store_server(
        integration_app,
        "jq",
        JQ_SERVER_DEFINITION,
    )

    _store_server(
        integration_app,
        "format_output",
        """
def main(payload):
    return {"output": f"Result: {payload.strip()}", "content_type": "text/plain"}
""",
    )

    cid = _store_cid(integration_app, b'{"key": "secret-value"}')

    response = client.get(f"/format_output/jq/.key/{cid}")
    body = _extract_response_body(integration_app, response)

    assert 'Result: "secret-value"' in body


# Tests for CID pattern resolution

def test_path_parameter_resolves_cid_content(client, integration_app):
    """When path parameter is a CID, its contents should be used as $1."""
    _store_server(
        integration_app,
        "echo_arg",
        """#!/bin/bash
echo "Argument: $1"
""",
    )

    # Store a CID containing the pattern to use
    pattern_cid = _store_cid(integration_app, b"{print $1}")

    _store_server(
        integration_app,
        "data_source",
        """
def main():
    return {"output": "word1 word2 word3", "content_type": "text/plain"}
""",
    )

    response = client.get(f"/echo_arg/{pattern_cid}/data_source")
    body = _extract_response_body(integration_app, response)

    # The CID content should be passed as $1
    assert "Argument: {print $1}" in body


def test_awk_with_cid_pattern(client, integration_app):
    """Awk server should use CID contents as the pattern."""
    _store_server(
        integration_app,
        "awk",
        """#!/bin/bash
awk "$1"
""",
    )

    # Store a CID containing the awk pattern
    pattern_cid = _store_cid(integration_app, b"{print $2}")

    # Store a CID containing input data
    data_cid = _store_cid(integration_app, b"a1 b1 c1\na2 b2 c2")

    response = client.get(f"/awk/{pattern_cid}/{data_cid}")
    body = _extract_response_body(integration_app, response)

    assert "b1" in body
    assert "b2" in body


# Test standard bash server without $1 still works

def test_standard_bash_server_unchanged(client, integration_app):
    """Bash servers without $1 should continue to work as before."""
    _store_server(
        integration_app,
        "simple_bash",
        """#!/bin/bash
echo "Simple bash server"
cat
""",
    )

    _store_server(
        integration_app,
        "input_server",
        """
def main():
    return {"output": "input data", "content_type": "text/plain"}
""",
    )

    response = client.get("/simple_bash/input_server")
    body = _extract_response_body(integration_app, response)

    assert "Simple bash server" in body
    assert "input data" in body
