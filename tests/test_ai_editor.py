"""Unit tests for the AI request editor server."""

import html
import json
import re
from pathlib import Path


def load_ai_editor_module():
    """Load the ai_editor server module via exec."""

    ai_editor_path = (
        Path(__file__).parent.parent
        / "reference_templates"
        / "servers"
        / "definitions"
        / "ai_editor.py"
    )
    namespace: dict = {}
    with open(ai_editor_path, "r", encoding="utf-8") as handle:
        exec(handle.read(), namespace)
    return namespace


class DummyRequest:
    """Lightweight stand-in for Flask's request object."""

    def __init__(self, *, path="/ai_editor", form=None, json_payload=None):
        self.path = path
        self.form = form or {}
        self._json_payload = json_payload

    def get_json(self, silent=False):  # pylint: disable=unused-argument
        return self._json_payload


class TestAiEditorBasics:
    """Basic behaviour checks for the AI editor server."""

    def setup_method(self):
        self.module = load_ai_editor_module()

    def test_main_exists_and_returns_html(self):
        result = self.module["main"]()

        assert result["content_type"] == "text/html"
        assert "AI request editor" in result["output"]
        assert "/search" in result["output"]

    def test_rejects_chained_input(self):
        result = self.module["main"](input_data="upstream")

        assert result["status"] == 400
        assert "cannot be used in a server chain" in result["output"]

    def test_meta_links_present(self):
        result = self.module["main"]()

        assert "Server Events" in result["output"]
        assert "/server_events?start=" in result["output"]


class TestAiEditorPayloadHandling:
    """Payload extraction and embedding behaviour."""

    def setup_method(self):
        self.module = load_ai_editor_module()

    def test_embeds_payload_from_json_request(self):
        payload = {
            "request_text": "Update copy",
            "original_text": "Original text",
            "context_data": {"region": "eu"},
            "form_summary": {"field": "value"},
            "target_label": "description",
            "target_endpoint": "/ai",
        }
        request = DummyRequest(json_payload=payload)

        result = self.module["main"](request=request)

        match = re.search(r"data-initial-payload=[\"']([^\"']*)[\"']", result["output"])
        assert match, "Initial payload attribute should be present"
        stored_payload = json.loads(html.unescape(match.group(1)))
        assert stored_payload["context_data"] == payload["context_data"]
        assert stored_payload["form_summary"] == payload["form_summary"]
        assert stored_payload["request_text"] == payload["request_text"]

    def test_defaults_target_endpoint_to_ai(self):
        result = self.module["main"]()

        assert "Target: /ai" in result["output"]

    def test_rejects_non_object_json_payload(self):
        request = DummyRequest(json_payload="not a dict")

        result = self.module["main"](request=request)

        assert result["status"] == 400
        assert "JSON object payload" in result["output"]

    def test_rejects_invalid_form_payload(self):
        form = {"payload": "[1, 2, 3]"}
        request = DummyRequest(form=form)

        result = self.module["main"](request=request)

        assert result["status"] == 400
        assert "payload" in result["output"]

    def test_parses_context_strings_as_json(self):
        form = {
            "context_data": '{"foo": "bar"}',
            "form_summary": "{}",
            "request_text": "Hello",
        }
        request = DummyRequest(form=form)

        result = self.module["main"](request=request)

        match = re.search(r"data-initial-payload=[\"']([^\"']*)[\"']", result["output"])
        stored_payload = json.loads(html.unescape(match.group(1)))
        assert stored_payload["context_data"] == {"foo": "bar"}
        assert stored_payload["form_summary"] == {}

    def test_payload_attribute_escapes_quotes(self):
        payload = {"request_text": "Bob's draft"}
        request = DummyRequest(json_payload=payload)

        result = self.module["main"](request=request)

        assert "Bob&#x27;s draft" in result["output"]

        match = re.search(r"data-initial-payload=[\"']([^\"']*)[\"']", result["output"])
        assert match
        stored_payload = json.loads(html.unescape(match.group(1)))
        assert stored_payload["request_text"] == payload["request_text"]
