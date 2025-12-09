import html
import json
import re

import pytest


class TestAiEditorIntegration:
    """Integration tests for the AI request editor server."""

    @pytest.fixture(autouse=True)
    def setup_ai_editor_server(self, memory_db_app):
        with memory_db_app.app_context():
            from pathlib import Path
            from models import Server
            from database import db

            ai_editor_path = (
                Path(__file__).parent.parent.parent
                / "reference_templates"
                / "servers"
                / "definitions"
                / "ai_editor.py"
            )
            with open(ai_editor_path, "r", encoding="utf-8") as handle:
                definition = handle.read()
            if not Server.query.filter_by(name="ai_editor").first():
                server = Server(name="ai_editor", definition=definition, enabled=True)
                db.session.add(server)
                db.session.commit()

    def test_ai_editor_server_is_available(self, memory_client):
        response = memory_client.get("/servers")
        assert response.status_code == 200
        assert "ai_editor" in response.get_data(as_text=True)

    def test_ai_editor_renders_tabs(self, memory_client):
        response = memory_client.get("/ai_editor", follow_redirects=False)
        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        body = memory_client.get(location).get_data(as_text=True)
        assert "AI request editor" in body
        for label in ["request_text", "original_text", "target_label", "context_data", "form_summary"]:
            assert label in body

    def test_ai_editor_populates_from_payload(self, memory_client):
        payload = {
            "request_text": "Edit me",
            "original_text": "Original value",
            "context_data": {"area": "test"},
            "form_summary": {"field": "example"},
            "target_label": "sample",
        }
        response = memory_client.post(
            "/ai_editor",
            data={"payload": json.dumps(payload), "target_endpoint": "/ai"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        body = memory_client.get(location).get_data(as_text=True)
        assert "Edit me" in body
        assert "Original value" in body
        assert "\"area\": \"test\"" in body

    def test_ai_editor_contains_navigation_and_info_menu(self, memory_client):
        response = memory_client.get("/ai_editor", follow_redirects=False)
        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        body = memory_client.get(location).get_data(as_text=True)
        assert "/search" in body
        assert "Server Events" in body

    def test_initial_payload_matches_submitted_request(self, memory_client):
        payload = {
            "request_text": "Round trip",
            "context_data": {"section": "alpha"},
            "form_summary": {},
        }
        response = memory_client.post(
            "/ai_editor",
            data={"payload": json.dumps(payload)},
            follow_redirects=False,
        )
        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        body = memory_client.get(location).get_data(as_text=True)
        match = re.search(r"data-initial-payload=[\"']([^\"']*)[\"']", body)
        assert match
        stored = json.loads(html.unescape(match.group(1)))
        assert stored["request_text"] == payload["request_text"]
        assert stored["context_data"] == payload["context_data"]

    def test_ai_editor_escapes_payload_attribute(self, memory_client):
        payload = {"request_text": "Bob's draft"}
        response = memory_client.post(
            "/ai_editor",
            json=payload,
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        body = memory_client.get(location).get_data(as_text=True)

        assert "Bob&#x27;s draft" in body

        match = re.search(r"data-initial-payload=[\"']([^\"']*)[\"']", body)
        assert match
        stored = json.loads(html.unescape(match.group(1)))
        assert stored["request_text"] == payload["request_text"]

    def test_ai_editor_returns_error_for_invalid_json_payload(self, memory_client):
        response = memory_client.post("/ai_editor", json="bad payload", follow_redirects=False)

        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        error_page = memory_client.get(location)
        assert "JSON object payload" in error_page.get_data(as_text=True)

    def test_ai_editor_returns_error_for_invalid_form_payload(self, memory_client):
        response = memory_client.post(
            "/ai_editor", data={"payload": "[1, 2, 3]"}, follow_redirects=False
        )

        assert response.status_code == 302
        location = response.headers.get("Location")
        assert location
        error_page = memory_client.get(location)
        assert "'payload' form field" in error_page.get_data(as_text=True)
