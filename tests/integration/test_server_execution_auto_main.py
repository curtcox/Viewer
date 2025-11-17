"""Integration coverage for auto-main server execution with nested inputs."""

from __future__ import annotations

import textwrap
from urllib.parse import urlsplit

import pytest

from database import db
from models import Alias, CID, Server


pytestmark = pytest.mark.integration


def _store_server(app, name: str, definition: str) -> None:
    """Persist a server definition for the default integration user."""

    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        db.session.add(
            Server(name=name, definition=normalized)
        )
        db.session.commit()


def _store_alias(app, name: str, definition: str) -> None:
    """Persist an alias definition for the default integration user."""

    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        db.session.add(
            Alias(name=name, definition=normalized)
        )
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
            record = CID.query.filter_by(path=candidate).first()
            if record is not None:
                break

        assert record is not None, f"CID record not found for {raw_path!r}"
        return record.file_data.decode("utf-8")


def test_nested_server_chain_executes_in_order(
    client, integration_app
):
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


def test_nested_alias_provides_remaining_parameter(
    client, integration_app
):
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


def test_nested_cid_contents_feed_server_input(
    client, integration_app
):
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
        db.session.add(
            CID(path=f"/{cid_value}", file_data=b"cid-payload")
        )
        db.session.commit()

    response = client.get(f"/outer/{cid_value}")
    assert response.status_code in {302, 303}

    payload = _resolve_cid_payload(integration_app, response.headers["Location"])
    assert payload == "cid-payload"


def test_query_and_nested_server_parameters_combine(
    client, integration_app
):
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
