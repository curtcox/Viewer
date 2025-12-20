from unittest.mock import patch

import pytest

from alias_definition import format_primary_alias_line
from database import db
from db_access import update_alias_cid_reference, update_cid_references
from models import Alias, Server

pytestmark = pytest.mark.integration


def test_update_cid_references_refreshes_alias_and_server_state(integration_app):
    old_cid = "legacycid1234567890"
    new_cid = "replacementcid0987654321"

    with integration_app.app_context():
        definition_text = format_primary_alias_line(
            "literal",
            "/latest",
            f"/{old_cid}?download=1",
            alias_name="latest",
        )
        definition_text = f"{definition_text}\n# legacy pointer {old_cid}"
        alias = Alias(
            name="latest",
            definition=definition_text,
        )
        server = Server(
            name="docs",
            definition=(f"def main(request):\n    return '{old_cid}'\n"),
            definition_cid=old_cid,
        )
        db.session.add_all([alias, server])
        db.session.commit()

        with (
            patch("cid_utils.save_server_definition_as_cid") as mock_save,
            patch("cid_utils.store_server_definitions_cid") as mock_store,
        ):
            mock_save.side_effect = lambda definition: "test-integration-cid"
            mock_store.side_effect = lambda: "bundle"

            result = update_cid_references(old_cid, new_cid)

        assert result == {"aliases": 1, "servers": 1}

        refreshed_alias = db.session.get(Alias, alias.id)
        refreshed_server = db.session.get(Server, server.id)

        assert refreshed_alias is not None
        assert refreshed_server is not None

        assert refreshed_alias.target_path == f"/{new_cid}?download=1"
        assert new_cid in (refreshed_alias.definition or "")
        assert old_cid not in (refreshed_alias.definition or "")

        assert new_cid in (refreshed_server.definition or "")
        assert old_cid not in (refreshed_server.definition or "")
        assert refreshed_server.definition_cid == "test-integration-cid"

        mock_save.assert_called_once()
        mock_store.assert_called_once()


def test_update_alias_cid_reference_updates_existing_alias(integration_app):
    with integration_app.app_context():
        definition_text = format_primary_alias_line(
            "regex",
            "/custom",
            "/legacycid?download=1",
            ignore_case=True,
            alias_name="integration-release",
        )
        definition_text = f"{definition_text}\n# replace legacycid"
        alias = Alias(
            name="integration-release",
            definition=definition_text,
        )
        db.session.add(alias)
        db.session.commit()

        result = update_alias_cid_reference(
            "legacycid",
            "integration-latest",
            "integration-release",
        )

        assert result == {"created": False, "updated": 1}

        refreshed = db.session.get(Alias, alias.id)
        assert refreshed is not None
        assert refreshed.target_path == "/integration-latest?download=1"
        assert "integration-latest" in (refreshed.definition or "")
        assert "legacycid" not in (refreshed.definition or "")
        assert refreshed.match_type == "literal"
        assert refreshed.match_pattern == "/integration-release"
        assert refreshed.ignore_case is True


def test_update_alias_cid_reference_creates_alias_when_missing(integration_app):
    with integration_app.app_context():
        result = update_alias_cid_reference(
            "missing", "integration-fresh", "integration-new"
        )

        assert result == {"created": True, "updated": 1}

        created = Alias.query.filter_by(name="integration-new").first()
        assert created is not None
        assert created.target_path == "/integration-fresh"
        assert created.definition.startswith("integration-new -> /integration-fresh")
