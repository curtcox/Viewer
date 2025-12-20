import os
import unittest
from typing import cast

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SESSION_SECRET", "test-secret-key")

from app import app, db
from db_access import (
    EntityInteractionRequest,
    get_recent_entity_interactions,
    record_entity_interaction,
)


class TestEntityInteractions(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_record_entity_interaction_persists(self):
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type="server",
                entity_name="example",
                action="save",
                message="initial setup",
                content='print("hello world")',
            )
        )

        interactions = get_recent_entity_interactions("server", "example")
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0].message, "initial setup")
        self.assertEqual(interactions[0].content, 'print("hello world")')

    def test_api_records_and_returns_updated_history(self):
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type="server",
                entity_name="example",
                action="save",
                message="initial setup",
                content='print("hello world")',
            )
        )

        payload = {
            "entity_type": "server",
            "entity_name": "example",
            "action": "ai",
            "message": "trim trailing spaces",
            "content": 'print("hello world")\n'.strip(),
        }

        response = self.client.post("/api/interactions", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("interactions", data)
        self.assertGreaterEqual(len(data["interactions"]), 2)
        latest = data["interactions"][0]
        self.assertEqual(latest["action"], "ai")
        self.assertEqual(latest["message"], "trim trailing spaces")

    def test_api_requires_entity_details(self):
        response = self.client.post("/api/interactions", json={"content": "value"})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_record_entity_interaction_rejects_invalid_payload(self):
        with self.assertRaises(AttributeError):
            record_entity_interaction(cast(EntityInteractionRequest, object()))

    def test_interaction_history_includes_timestamp_url(self):
        """Verify that interaction history includes timestamp_url for URL generation."""
        record_entity_interaction(
            EntityInteractionRequest(
                entity_type="server",
                entity_name="example",
                action="save",
                message="initial setup",
                content='print("hello world")',
            )
        )

        payload = {
            "entity_type": "server",
            "entity_name": "example",
            "action": "save",
            "message": "update",
            "content": 'print("updated")',
        }

        response = self.client.post("/api/interactions", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("interactions", data)
        self.assertGreaterEqual(len(data["interactions"]), 1)

        # Check that each interaction has timestamp_url and timestamp_url_end fields
        for interaction in data["interactions"]:
            self.assertIn("timestamp_url", interaction)
            self.assertIn("timestamp_url_end", interaction)
            # If timestamp_url is not empty, it should be in the correct format
            if interaction["timestamp_url"]:
                # Format should be YYYY/MM/DD HH:MM:SS
                import re

                pattern = r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$"
                self.assertIsNotNone(
                    re.match(pattern, interaction["timestamp_url"]),
                    f"timestamp_url '{interaction['timestamp_url']}' does not match expected format",
                )
                self.assertIsNotNone(
                    re.match(pattern, interaction["timestamp_url_end"]),
                    f"timestamp_url_end '{interaction['timestamp_url_end']}' does not match expected format",
                )
                # Verify that timestamp_url_end is one second after timestamp_url
                from history_filters import parse_history_timestamp

                start_dt = parse_history_timestamp(interaction["timestamp_url"])
                end_dt = parse_history_timestamp(interaction["timestamp_url_end"])
                self.assertIsNotNone(start_dt)
                self.assertIsNotNone(end_dt)
                diff = (end_dt - start_dt).total_seconds()
                self.assertEqual(
                    diff,
                    1.0,
                    f"timestamp_url_end should be 1 second after timestamp_url, but difference is {diff} seconds",
                )


if __name__ == "__main__":
    unittest.main()
