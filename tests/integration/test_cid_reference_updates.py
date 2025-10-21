import pytest
from unittest.mock import patch

from database import db
from db_access import update_cid_references
from models import Alias, Server


pytestmark = pytest.mark.integration


def test_update_cid_references_refreshes_alias_and_server_state(integration_app):
    old_cid = "legacycid1234567890"
    new_cid = "replacementcid0987654321"

    with integration_app.app_context():
        alias = Alias(
            name="latest",
            target_path=f"/{old_cid}?download=1",
            user_id="default-user",
            match_type="literal",
            match_pattern="/latest",
            ignore_case=False,
            definition=(
                f"latest -> /{old_cid}?download=1\n"
                f"# legacy pointer {old_cid}"
            ),
        )
        server = Server(
            name="docs",
            definition=(
                "def main(request):\n"
                f"    return '{old_cid}'\n"
            ),
            definition_cid=old_cid,
            user_id="default-user",
        )
        db.session.add_all([alias, server])
        db.session.commit()

        with patch("cid_utils.save_server_definition_as_cid") as mock_save, patch(
            "cid_utils.store_server_definitions_cid"
        ) as mock_store:
            mock_save.side_effect = lambda definition, user_id: f"{user_id}-integration-cid"
            mock_store.side_effect = lambda user_id: f"bundle-{user_id}"

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
        assert refreshed_server.definition_cid == "default-user-integration-cid"

        mock_save.assert_called_once()
        mock_store.assert_called_once_with("default-user")
