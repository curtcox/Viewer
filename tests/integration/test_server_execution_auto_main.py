"""Integration coverage for auto-main server execution with nested inputs."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests

from database import db
from cid_presenter import cid_path
from cid_utils import _render_markdown_document
from db_access import get_cid_by_path
from models import Alias, CID, Secret, Server, ServerInvocation


pytestmark = pytest.mark.integration


def _store_server(app, name: str, definition: str) -> None:
    """Persist a server definition for the default integration user."""

    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        db.session.add(Server(name=name, definition=normalized))
        db.session.commit()


def _store_alias(app, name: str, definition: str) -> None:
    """Persist an alias definition for the default integration user."""

    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        db.session.add(Alias(name=name, definition=normalized))
        db.session.commit()


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

        assert record is not None, f"CID record not found for {raw_path!r}"
        return record.file_data.decode("utf-8")


def _extract_response_body(app, response) -> str:
    """Return the response payload, following CID redirects when necessary."""

    if response.status_code in {302, 303}:
        location = response.headers.get("Location")
        assert location, "Redirect response missing Location header"
        return _resolve_cid_payload(app, location)
    return response.get_data(as_text=True)


def test_nested_server_chain_executes_in_order(client, integration_app):
    """Multiple nested servers should resolve sequentially for auto-main input."""

    _store_server(
        integration_app,
        "inner",
        """
        def main():
            return {"output": "inner", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "middle",
        """
        def main(payload):
            return {"output": f"{payload}-middle", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "outer",
        """
        def main(payload):
            return {"output": f"{payload}-outer", "content_type": "text/plain"}
        """,
    )

    response = client.get("/outer/middle/inner")
    assert response.status_code in {302, 303}
    assert response.headers["Location"]

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "inner-middle-outer"


def test_nested_alias_provides_remaining_parameter(client, integration_app):
    """Alias targets should execute and feed their output into auto-main servers."""

    _store_server(
        integration_app,
        "inner",
        """
        def main():
            return {"output": "alias-value", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "outer",
        """
        def main(payload):
            return {"output": payload, "content_type": "text/plain"}
        """,
    )

    _store_alias(
        integration_app,
        "alias-nest",
        """
        alias-nest -> /inner
        """,
    )

    response = client.get("/outer/alias-nest")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "alias-value"


def test_nested_cid_contents_feed_server_input(client, integration_app):
    """CID path segments should supply their decoded contents to auto-main servers."""

    _store_server(
        integration_app,
        "outer",
        """
        def main(payload):
            return {"output": payload, "content_type": "text/plain"}
        """,
    )

    cid_value = "bafytestcidvalue"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"cid-payload"))
        db.session.commit()

    response = client.get(f"/outer/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "cid-payload"


def test_query_and_nested_server_parameters_combine(client, integration_app):
    """Auto-main should merge standard request parameters with nested server results."""

    _store_server(
        integration_app,
        "inner",
        """
        def main():
            return {"output": "value", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "outer",
        """
        def main(prefix, payload):
            return {"output": f"{prefix}:{payload}", "content_type": "text/plain"}
        """,
    )

    response = client.get("/outer/inner?prefix=start")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "start:value"


# =============================================================================
# Server Command Chaining Integration Tests
# =============================================================================
# These tests verify the command chaining functionality as described in the issue:
# - /s/CID translates into s.main(contents(CID))
# - /s2/s1 translates into s2.main(s1.main())
# - /s2/s1/CID translates into s2.main(s1.main(contents(CID)))


def test_chaining_server_with_cid_content(client, integration_app):
    """Integration test for /s/CID: s.main(contents(CID))."""

    _store_server(
        integration_app,
        "processor",
        """
        def main(data):
            return {"output": f"processed:{data}", "content_type": "text/plain"}
        """,
    )

    cid_value = "bafyintegrationcid"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"raw-input"))
        db.session.commit()

    response = client.get(f"/processor/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "processed:raw-input"


def test_chaining_two_servers(client, integration_app):
    """Integration test for /s2/s1: s2.main(s1.main())."""

    _store_server(
        integration_app,
        "first",
        """
        def main():
            return {"output": "first-output", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "second",
        """
        def main(data):
            return {"output": f"second({data})", "content_type": "text/plain"}
        """,
    )

    response = client.get("/second/first")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "second(first-output)"


def test_chaining_three_level_deep(client, integration_app):
    """Integration test for /s3/s2/s1/CID: s3.main(s2.main(s1.main(contents(CID))))."""

    _store_server(
        integration_app,
        "level1",
        """
        def main(input_val):
            return {"output": f"L1({input_val})", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "level2",
        """
        def main(input_val):
            return {"output": f"L2({input_val})", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "level3",
        """
        def main(input_val):
            return {"output": f"L3({input_val})", "content_type": "text/plain"}
        """,
    )

    cid_value = "bafydeepchaining"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"base"))
        db.session.commit()

    response = client.get(f"/level3/level2/level1/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "L3(L2(L1(base)))"


def test_chaining_server_with_alias_to_server(client, integration_app):
    """Integration test for /s2/alias: s2.main(alias->s1.main())."""

    _store_server(
        integration_app,
        "target_srv",
        """
        def main():
            return {"output": "via-alias", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "caller",
        """
        def main(data):
            return {"output": f"caller({data})", "content_type": "text/plain"}
        """,
    )

    _store_alias(
        integration_app,
        "shortcut",
        """
        shortcut -> /target_srv
        """,
    )

    response = client.get("/caller/shortcut")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "caller(via-alias)"


def test_bash_server_respects_exit_code_and_input(client, integration_app):
    """Bash servers should stream stdin JSON and map exit codes to HTTP codes."""

    _store_server(
        integration_app,
        "bash-echo",
        """#!/usr/bin/env bash
cat
exit 201
""",
    )

    response = client.post("/bash-echo", data="body-text")

    assert response.status_code == 201
    payload = json.loads(response.get_data(as_text=True))
    assert payload["input"] == "body-text"


def test_bash_exit_code_outside_range_maps_to_500(client, integration_app):
    """Exit codes outside HTTP range should be normalised."""

    _store_server(
        integration_app,
        "bash-error",
        """#!/bin/bash
echo "oops"
exit 42
""",
    )

    response = client.get("/bash-error")
    assert response.status_code == 500
    assert "oops" in response.get_data(as_text=True)


def test_chaining_across_bash_and_python_servers(client, integration_app):
    """Bash and Python servers should participate in the same pipeline."""

    _store_server(
        integration_app,
        "bash-leaf",
        """#!/usr/bin/env bash
printf "leaf"
""",
    )

    _store_server(
        integration_app,
        "python-middle",
        """
        def main(payload):
            return {"output": f"{payload}-py", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "bash-outer",
        """#!/usr/bin/env bash
cat
""",
    )

    response = client.get("/bash-outer/python-middle/bash-leaf")
    assert response.status_code in {200, 302, 303}

    body = _extract_response_body(integration_app, response)
    assert body.strip() == "leaf-py"


def test_bash_servers_chain_directly(client, integration_app):
    """Nested bash servers should still feed stdout into upstream stdin."""

    _store_server(
        integration_app,
        "bash-inner",
        """#!/usr/bin/env bash
printf "inner"
""",
    )

    _store_server(
        integration_app,
        "bash-outer",
        """#!/usr/bin/env bash
cat
""",
    )

    response = client.get("/bash-outer/bash-inner")
    assert response.status_code in {200, 302, 303}

    body = _extract_response_body(integration_app, response)
    assert body.strip() == "inner"


def test_bash_server_chains_with_identifier_paths(client, integration_app):
    """Identifier-only path segments should still allow chaining into bash servers."""

    _store_server(
        integration_app,
        "pythoninner",
        """
        def main():
            return {"output": "inner", "content_type": "text/plain"}
        """,
    )

    _store_server(
        integration_app,
        "bashouter",
        """#!/usr/bin/env bash
cat
""",
    )

    response = client.get("/bashouter/pythoninner")
    assert response.status_code in {200, 302, 303}

    body = _extract_response_body(integration_app, response)
    assert body.strip() == "inner"


def test_default_markdown_consumes_cid_path_segment(client, integration_app):
    """Markdown server should render CID content supplied via chained path."""

    markdown_definition = Path(
        "reference_templates/servers/definitions/markdown.py"
    ).read_text(encoding="utf-8")
    _store_server(integration_app, "markdown", markdown_definition)

    cid_value = "bafydefaultmarkdown"
    markdown_text = b"## Path Heading"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=markdown_text))
        db.session.commit()

    response = client.get(f"/markdown/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert "Path Heading" in payload
    assert "markdown-body" in payload


def test_default_markdown_renders_showcase_via_cid(client, integration_app):
    """The markdown server should render the showcase markdown file from a CID."""

    markdown_definition = Path(
        "reference_templates/servers/definitions/markdown.py"
    ).read_text(encoding="utf-8")
    markdown_sample = Path(
        "reference_templates/uploads/contents/markdown_showcase.md"
    ).read_text(encoding="utf-8")
    expected_html = _render_markdown_document(markdown_sample)

    _store_server(integration_app, "markdown", markdown_definition)

    cid_value = "bafymarkdownshowcase"
    with integration_app.app_context():
        db.session.add(
            CID(path=f"/{cid_value}", file_data=markdown_sample.encode("utf-8"))
        )
        db.session.commit()

    response = client.get(f"/markdown/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == expected_html
    assert "<h1>Markdown Showcase</h1>" in payload
    assert "Use Markdown to quickly share runbooks" in payload
    assert "language-python" in payload and "Rendered at" in payload
    assert "admonition note" in payload and "Reusable components" in payload
    assert "<table>" in payload and "<td>Headings</td>" in payload
    assert "<dl>" in payload and "Details stay aligned" in payload
    assert "Flow diagram placeholder" in payload
    assert "mermaid-diagram" in payload
    assert "feature-request" in payload
    assert "Need a quick start? Duplicate this file" in payload


def test_default_markdown_renders_showcase_via_cid_with_extension(
    client, integration_app
):
    """Markdown server should resolve CID payloads even when an extension is present."""

    markdown_definition = Path(
        "reference_templates/servers/definitions/markdown.py"
    ).read_text(encoding="utf-8")
    markdown_sample = Path(
        "reference_templates/uploads/contents/markdown_showcase.md"
    ).read_text(encoding="utf-8")
    expected_html = _render_markdown_document(markdown_sample)

    _store_server(integration_app, "markdown", markdown_definition)

    cid_value = "bafymarkdownshowcaseext"
    with integration_app.app_context():
        db.session.add(
            CID(path=f"/{cid_value}", file_data=markdown_sample.encode("utf-8"))
        )
        db.session.commit()

    response = client.get(f"/markdown/{cid_value}.txt")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == expected_html
    assert "<h1>Markdown Showcase</h1>" in payload
    assert "Use Markdown to quickly share runbooks" in payload
    assert "language-python" in payload and "Rendered at" in payload
    assert "admonition note" in payload and "Reusable components" in payload
    assert "<table>" in payload and "<td>Headings</td>" in payload
    assert "<dl>" in payload and "Details stay aligned" in payload
    assert "Flow diagram placeholder" in payload
    assert "mermaid-diagram" in payload
    assert "feature-request" in payload
    assert "Need a quick start? Duplicate this file" in payload


def test_default_markdown_output_chains_left(client, integration_app):
    """Markdown output should feed into the next server on the left."""

    markdown_definition = Path(
        "reference_templates/servers/definitions/markdown.py"
    ).read_text(encoding="utf-8")
    _store_server(integration_app, "markdown", markdown_definition)

    _store_server(
        integration_app,
        "consumer",
        """
        def main(payload):
            return {"output": f"wrapped::{payload}", "content_type": "text/plain"}
        """,
    )

    cid_value = "bafydefaultmarkdownchain"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"# Outer Chain"))
        db.session.commit()

    response = client.get(f"/consumer/markdown/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload.startswith("wrapped::")
    assert "Outer Chain" in payload


def test_default_shell_consumes_cid_path_segment(client, integration_app):
    """Shell server should receive input from chained CID content."""

    shell_definition = Path(
        "reference_templates/servers/definitions/shell.py"
    ).read_text(encoding="utf-8")
    _store_server(integration_app, "shell", shell_definition)

    cid_value = "bafydefaultshell"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"echo chained"))
        db.session.commit()

    response = client.get(f"/shell/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert "echo chained" in payload
    assert "exit" in payload


def test_default_shell_output_chains_left(client, integration_app):
    """Shell output should feed into the next chained server."""

    shell_definition = Path(
        "reference_templates/servers/definitions/shell.py"
    ).read_text(encoding="utf-8")
    _store_server(integration_app, "shell", shell_definition)

    _store_server(
        integration_app,
        "collector",
        """
        def main(payload):
            return {"output": f"collected>>{payload}", "content_type": "text/plain"}
        """,
    )

    cid_value = "bafydefaultshellchain"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"echo chain"))
        db.session.commit()

    response = client.get(f"/collector/shell/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload.startswith("collected>>")
    assert "echo chain" in payload


def test_default_ai_stub_consumes_cid_path_segment(client, integration_app):
    """ai_stub should treat chained CID content as request_text input."""

    ai_stub_definition = Path(
        "reference_templates/servers/definitions/ai_stub.py"
    ).read_text(encoding="utf-8")
    _store_server(integration_app, "ai_stub", ai_stub_definition)

    cid_value = "bafydefaultaistub"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"do something"))
        db.session.commit()

    response = client.get(f"/ai_stub/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    parsed = json.loads(payload)
    assert parsed["updated_text"].endswith("do something")
    assert "message" in parsed


def test_default_ai_stub_output_chains_left(client, integration_app):
    """ai_stub output should flow into the next chained server."""

    ai_stub_definition = Path(
        "reference_templates/servers/definitions/ai_stub.py"
    ).read_text(encoding="utf-8")
    _store_server(integration_app, "ai_stub", ai_stub_definition)

    _store_server(
        integration_app,
        "wrapper",
        """
        def main(payload):
            return {"output": f"[[{payload}]]", "content_type": "text/plain"}
        """,
    )

    cid_value = "bafydefaultaistubchain"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{cid_value}", file_data=b"adjust text"))
        db.session.commit()

    response = client.get(f"/wrapper/ai_stub/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload.startswith("[[") and payload.endswith("]]")
    assert "adjust text" in payload


def test_literal_python_cid_executes_as_server(client, integration_app):
    """Non-terminal CID path segments should execute python definitions."""

    python_cid = "literalpythonint"
    with integration_app.app_context():
        db.session.add(
            CID(
                path=f"/{python_cid}",
                file_data=textwrap.dedent(
                    """
                    def main():
                        return {"output": "integration-python", "content_type": "text/plain"}
                    """
                ).encode("utf-8"),
            )
        )
        db.session.commit()

    response = client.get(f"/{python_cid}.py/trailing-segment")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "integration-python"


def test_literal_bash_cid_executes_as_server(client, integration_app):
    """Bash CID literals should run when used in non-terminal path positions."""

    bash_cid = "literalbashint"
    with integration_app.app_context():
        db.session.add(CID(path=f"/{bash_cid}", file_data=b"echo integration-bash"))
        db.session.commit()

    response = client.get(f"/{bash_cid}.sh/extra")
    assert response.status_code == 200
    assert (
        _extract_response_body(integration_app, response).strip() == "integration-bash"
    )


def test_literal_python_receives_path_parameter(client, integration_app):
    """Python literal CID should receive parameters from chained path literals."""

    python_cid = "literalpyparam"
    bash_cid = "literalbashparam"
    with integration_app.app_context():
        db.session.add_all(
            [
                CID(
                    path=f"/{python_cid}",
                    file_data=textwrap.dedent(
                        """
                        def main(name):
                            return {"output": f"param::{name}", "content_type": "text/plain"}
                        """
                    ).encode("utf-8"),
                ),
                CID(path=f"/{bash_cid}", file_data=b"echo morgan"),
            ]
        )
        db.session.commit()

    response = client.get(f"/{python_cid}.py/{bash_cid}.sh/next")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload.strip() == "param::morgan"


def test_literal_python_chains_into_bash(client, integration_app):
    """Python literal output should feed into bash literal input."""

    bash_cid = "literalbashchain"
    python_cid = "literalpychain"
    with integration_app.app_context():
        db.session.add_all(
            [
                CID(
                    path=f"/{bash_cid}",
                    file_data=textwrap.dedent(
                        """
                        input=$(cat)
                        echo "bash:$input"
                        """
                    ).encode("utf-8"),
                ),
                CID(
                    path=f"/{python_cid}",
                    file_data=textwrap.dedent(
                        """
                        def main():
                            return {"output": "py-chain", "content_type": "text/plain"}
                        """
                    ).encode("utf-8"),
                ),
            ]
        )
        db.session.commit()

    response = client.get(f"/{bash_cid}.sh/{python_cid}.py/final")
    assert response.status_code == 200
    assert _extract_response_body(integration_app, response).strip() == "bash:py-chain"


def test_literal_bash_chains_into_python(client, integration_app):
    """Bash literal output should supply input for python literal servers."""

    bash_cid = "literalbashpayload"
    python_cid = "literalpypayload"
    with integration_app.app_context():
        db.session.add_all(
            [
                CID(path=f"/{bash_cid}", file_data=b"echo bash-into-python"),
                CID(
                    path=f"/{python_cid}",
                    file_data=textwrap.dedent(
                        """
                        def main(payload):
                            return {"output": f"py::{payload}", "content_type": "text/plain"}
                        """
                    ).encode("utf-8"),
                ),
            ]
        )
        db.session.commit()

    response = client.get(f"/{python_cid}.py/{bash_cid}.sh/next")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload.strip() == "py::bash-into-python"


def test_python_server_captures_external_calls(client, integration_app, monkeypatch):
    secret_value = "secret-token"

    with integration_app.app_context():
        db.session.add(Secret(name="API_KEY", definition=secret_value))
        db.session.commit()

    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = f"result {secret_value}".encode("utf-8")
        response.headers = {"Authorization": f"Bearer {secret_value}"}
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    _store_server(
        integration_app,
        "http_capture",
        """
import requests


def main(request, context):
    headers = {"Authorization": f"Bearer {context['secrets']['API_KEY']}"}
    requests.get("https://example.com/data", headers=headers, params={"token": context['secrets']['API_KEY']})
    return {"output": "ok", "content_type": "text/plain"}
        """,
    )

    response = client.get("/http_capture")
    assert response.status_code in {302, 303}

    with integration_app.app_context():
        invocation = (
            ServerInvocation.query.filter_by(server_name="http_capture")
            .order_by(ServerInvocation.invoked_at.desc())
            .first()
        )

        assert invocation is not None
        assert invocation.external_calls_cid is not None

        record = CID.query.filter_by(
            path=cid_path(invocation.external_calls_cid)
        ).first()
        assert record is not None

        calls = json.loads(record.file_data)
        assert calls
        entry = calls[0]
        assert entry["request"]["headers"]["Authorization"] == "Bearer <secret:API_KEY>"
        assert entry["response"]["body"] == "result <secret:API_KEY>"
        assert entry["request"]["params"]["token"] == "<secret:API_KEY>"


def test_python_server_captures_external_calls_on_error(
    client, integration_app, monkeypatch
):
    secret_value = "secret-token"

    with integration_app.app_context():
        db.session.add(Secret(name="API_KEY", definition=secret_value))
        db.session.commit()

    def fake_request(self, method, url, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 200
        response._content = f"result {secret_value}".encode("utf-8")
        response.headers = {"Authorization": f"Bearer {secret_value}"}
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", fake_request, raising=False)

    _store_server(
        integration_app,
        "http_capture_error",
        """
import requests


def main(request, context):
    headers = {"Authorization": f"Bearer {context['secrets']['API_KEY']}"}
    requests.get("https://example.com/data", headers=headers, params={"token": context['secrets']['API_KEY']})
    raise RuntimeError("boom")
        """,
    )

    response = client.get("/http_capture_error")
    assert response.status_code == 500

    with integration_app.app_context():
        invocation = (
            ServerInvocation.query.filter_by(server_name="http_capture_error")
            .order_by(ServerInvocation.invoked_at.desc())
            .first()
        )

        assert invocation is not None
        assert invocation.external_calls_cid is not None

        record = CID.query.filter_by(
            path=cid_path(invocation.external_calls_cid)
        ).first()
        assert record is not None

        calls = json.loads(record.file_data)
        assert calls
        entry = calls[0]
        assert entry["request"]["headers"]["Authorization"] == "Bearer <secret:API_KEY>"
        assert entry["response"]["body"] == "result <secret:API_KEY>"
        assert entry["request"]["params"]["token"] == "<secret:API_KEY>"
