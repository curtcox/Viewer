"""Property-based database equivalence tests for in-memory vs disk modes."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from database import db
from models import CID, Server
from tests.property.strategies import binary_cid_data, server_records


@pytest.mark.db_equivalence
class TestPropertyBasedEquivalence:
    """Property-based checks that memory and disk databases stay equivalent."""

    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(record=server_records)
    def test_server_roundtrip_equivalence(self, memory_db_app, disk_db_app, record):
        results = {}

        for label, app in (("memory", memory_db_app), ("disk", disk_db_app)):
            with app.app_context():
                Server.query.delete()
                db.session.commit()

                server = Server(**record)
                db.session.add(server)
                db.session.commit()

                retrieved = Server.query.filter_by(name=record["name"]).first()
                results[label] = (
                    retrieved.name,
                    retrieved.definition,
                    retrieved.enabled,
                )

        assert results["memory"] == results["disk"]

    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(blob=binary_cid_data)
    def test_cid_binary_storage_equivalence(self, memory_db_app, disk_db_app, blob):
        target_path = "/cid/hypothesis"
        stored_bytes = {}

        for label, app in (("memory", memory_db_app), ("disk", disk_db_app)):
            with app.app_context():
                CID.query.delete()
                db.session.commit()

                cid = CID(path=target_path, file_data=blob)
                db.session.add(cid)
                db.session.commit()

                stored = CID.query.filter_by(path=target_path).first()
                stored_bytes[label] = stored.file_data

        assert stored_bytes["memory"] == stored_bytes["disk"] == blob
