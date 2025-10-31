"""Integration tests for content negotiation across documented endpoints."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Dict

import pytest

from alias_definition import format_primary_alias_line
from database import db
from identity import ensure_default_user
from models import Alias, Secret, Server, Variable


@pytest.fixture()
def sample_entities(client) -> Dict[str, str]:
    with client.application.app_context():
        user = ensure_default_user()
        alias_definition = format_primary_alias_line(
            "literal", "/json-alias", "/json-target", alias_name="json-alias"
        )
        alias = Alias(
            name="json-alias",
            definition=alias_definition,
            user_id=user.id,
            enabled=True,
        )
        server = Server(
            name="json-server",
            definition="def main(query):\n    return query",
            user_id=user.id,
            enabled=True,
        )
        variable = Variable(
            name="json-variable",
            definition="value",
            user_id=user.id,
            enabled=True,
        )
        secret = Secret(
            name="json-secret",
            definition="secret-value",
            user_id=user.id,
            enabled=True,
        )
        db.session.add_all([alias, server, variable, secret])
        db.session.commit()
    return {
        "alias": "json-alias",
        "server": "json-server",
        "variable": "json-variable",
        "secret": "json-secret",
    }


@pytest.mark.integration
def test_aliases_endpoint_supports_json_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/aliases.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert isinstance(payload, list)
    matching = [entry for entry in payload if entry["name"] == sample_entities["alias"]]
    assert matching, "Expected alias record to be included"
    record = matching[0]
    assert record["match_pattern"] == "/json-alias"
    assert record["target_path"] == "/json-target"


@pytest.mark.integration
def test_alias_detail_endpoint_returns_record(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/aliases/{sample_entities['alias']}.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert payload["name"] == sample_entities["alias"]
    assert payload["match_type"] == "literal"


@pytest.mark.integration
def test_aliases_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/aliases.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    items = document.findall("item")
    assert items, "Expected alias records in XML payload"
    assert any(item.findtext("name") == sample_entities["alias"] for item in items)


@pytest.mark.integration
def test_alias_detail_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/aliases/{sample_entities['alias']}.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    assert document.findtext("name") == sample_entities["alias"]
    assert document.findtext("match_type") == "literal"


@pytest.mark.integration
def test_aliases_endpoint_honors_plain_text_accept_header(client, login_default_user) -> None:
    login_default_user()
    response = client.get("/aliases", headers={"Accept": "text/plain"})

    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    body = response.get_data(as_text=True)
    assert "Aliases" in body


@pytest.mark.integration
def test_interactions_endpoint_supports_xml_extension(client, login_default_user) -> None:
    login_default_user()
    payload = {
        "entity_type": "server",
        "entity_name": "example-server",
        "action": "ai",
        "message": "Trigger negotiation test",
        "content": "print('hello world')",
    }

    response = client.post("/api/interactions.xml", data=json.dumps(payload), content_type="application/json")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    body = response.get_data(as_text=True)
    assert "<response>" in body
    assert "Trigger negotiation test" in body


@pytest.mark.integration
def test_servers_endpoint_supports_json_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/servers.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert isinstance(payload, list)
    assert any(entry["name"] == sample_entities["server"] for entry in payload)


@pytest.mark.integration
def test_server_detail_endpoint_returns_record(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/servers/{sample_entities['server']}.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert payload["name"] == sample_entities["server"]
    assert payload["definition"].startswith("def main")


@pytest.mark.integration
def test_servers_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/servers.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    items = document.findall("item")
    assert any(item.findtext("name") == sample_entities["server"] for item in items)


@pytest.mark.integration
def test_server_detail_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/servers/{sample_entities['server']}.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    assert document.findtext("name") == sample_entities["server"]
    definition = document.findtext("definition")
    assert definition is not None and definition.startswith("def main")


@pytest.mark.integration
def test_variables_endpoint_supports_json_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/variables.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert isinstance(payload, list)
    assert any(entry["name"] == sample_entities["variable"] for entry in payload)


@pytest.mark.integration
def test_variable_detail_endpoint_returns_record(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/variables/{sample_entities['variable']}.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert payload["name"] == sample_entities["variable"]
    assert payload["definition"] == "value"


@pytest.mark.integration
def test_variables_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/variables.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    items = document.findall("item")
    assert any(item.findtext("name") == sample_entities["variable"] for item in items)


@pytest.mark.integration
def test_variable_detail_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/variables/{sample_entities['variable']}.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    assert document.findtext("name") == sample_entities["variable"]
    assert document.findtext("definition") == "value"


@pytest.mark.integration
def test_secrets_endpoint_supports_json_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/secrets.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert isinstance(payload, list)
    assert any(entry["name"] == sample_entities["secret"] for entry in payload)


@pytest.mark.integration
def test_secret_detail_endpoint_returns_record(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/secrets/{sample_entities['secret']}.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    payload = response.get_json()
    assert payload["name"] == sample_entities["secret"]
    assert payload["definition"] == "secret-value"


@pytest.mark.integration
def test_secrets_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get("/secrets.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    items = document.findall("item")
    assert any(item.findtext("name") == sample_entities["secret"] for item in items)


@pytest.mark.integration
def test_secret_detail_endpoint_supports_xml_extension(client, login_default_user, sample_entities) -> None:
    login_default_user()
    response = client.get(f"/secrets/{sample_entities['secret']}.xml")

    assert response.status_code == 200
    assert response.mimetype == "application/xml"

    document = ET.fromstring(response.get_data(as_text=True))
    assert document.findtext("name") == sample_entities["secret"]
    assert document.findtext("definition") == "secret-value"
