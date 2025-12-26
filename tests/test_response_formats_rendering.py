"""Unit tests for response payload rendering utilities."""

from response_formats import render_payload


def test_render_payload_text_sequence_names():
    payload = [{"name": "alpha"}, {"name": "bravo"}]

    body, mimetype = render_payload(payload, "txt")

    assert body == "alpha\nbravo"
    assert mimetype == "text/plain"


def test_render_payload_markdown_mapping():
    payload = {"name": "charlie", "definition": "value"}

    body, mimetype = render_payload(payload, "md")

    assert "- **name**: charlie" in body
    assert "- **definition**: value" in body
    assert mimetype == "text/markdown"
