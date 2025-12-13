"""Tests for the cid_links server that adds hyperlinks to CIDs in text."""

import pytest

import server_execution
from app import app
from cid_core import generate_cid


@pytest.fixture(autouse=True)
def patch_execution_environment(monkeypatch):
    from server_execution import code_execution

    monkeypatch.setattr(
        code_execution,
        "_load_user_context",
        lambda: {"variables": {}, "secrets": {}, "servers": {}},
    )

    def fake_success(output, content_type, server_name, *, external_calls=None):
        return {
            "output": output,
            "content_type": content_type,
            "server_name": server_name,
        }

    monkeypatch.setattr(code_execution, "_handle_successful_execution", fake_success)


# ============================================================================
# HTML DETECTION TESTS
# ============================================================================


def _get_cid_links_definition():
    """Load the cid_links server definition."""
    from pathlib import Path

    definition_path = Path(
        "reference_templates/servers/definitions/cid_links.py"
    )
    return definition_path.read_text()


def test_cid_links_detects_html_doctype():
    """HTML detection works for DOCTYPE declarations."""
    definition = _get_cid_links_definition()
    html_content = "<!DOCTYPE html><html><body>Hello</body></html>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["content_type"] == "text/html"


def test_cid_links_detects_html_tags():
    """HTML detection works for common HTML tags."""
    definition = _get_cid_links_definition()
    html_content = "<div><p>Hello world</p></div>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["content_type"] == "text/html"


def test_cid_links_detects_plain_text():
    """Non-HTML text is treated as plain text (markdown)."""
    definition = _get_cid_links_definition()
    plain_content = "This is just plain text with no HTML tags."

    with app.test_request_context("/cid_links", json={"text": plain_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["content_type"] == "text/plain"


def test_cid_links_detects_markdown():
    """Markdown content is treated as plain text."""
    definition = _get_cid_links_definition()
    md_content = "# Heading\n\nSome **bold** and *italic* text."

    with app.test_request_context("/cid_links", json={"text": md_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["content_type"] == "text/plain"


# ============================================================================
# HTML CID REPLACEMENT TESTS
# ============================================================================


def test_cid_links_replaces_cid_in_html():
    """CIDs in HTML are replaced with anchor tags."""
    definition = _get_cid_links_definition()
    # Use a valid hash-based CID (94 chars)
    test_cid = generate_cid(b"x" * 100)  # Generates a hash-based CID
    html_content = f"<p>See document {test_cid} for details.</p>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    expected_link = f'<a href="{test_cid}.txt">{test_cid}</a>'
    assert expected_link in result["output"]


def test_cid_links_does_not_replace_cid_in_href():
    """CIDs that are already link targets are not double-linked."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"y" * 100)
    html_content = f'<p>See <a href="{test_cid}.txt">this document</a>.</p>'

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Should not have nested anchor tags
    assert '<a href="<a' not in result["output"]
    # Original link should be preserved
    assert f'href="{test_cid}.txt"' in result["output"]


def test_cid_links_does_not_replace_cid_in_anchor_text_with_matching_href():
    """CIDs used as anchor text with matching href are not replaced."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"z" * 100)
    html_content = f'<p><a href="{test_cid}.txt">{test_cid}</a></p>'

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Count anchor tags - should still be just one
    assert result["output"].count("<a ") == 1
    assert result["output"].count("</a>") == 1


def test_cid_links_replaces_multiple_cids_in_html():
    """Multiple CIDs in HTML are all replaced."""
    definition = _get_cid_links_definition()
    cid1 = generate_cid(b"content1" * 20)
    cid2 = generate_cid(b"content2" * 20)
    html_content = f"<div><p>First: {cid1}</p><p>Second: {cid2}</p></div>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert f'<a href="{cid1}.txt">{cid1}</a>' in result["output"]
    assert f'<a href="{cid2}.txt">{cid2}</a>' in result["output"]


# ============================================================================
# LITERAL CID DATA URL TESTS
# ============================================================================


def test_cid_links_uses_data_url_for_literal_cid_in_html():
    """Literal CIDs with embedded content use data URLs in HTML."""
    definition = _get_cid_links_definition()
    # Create a literal CID with embedded content
    literal_cid = generate_cid(b"hello")  # "AAAABWhlbGxv"
    html_content = f"<p>Embedded: {literal_cid}</p>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Should use data URL, not relative path
    assert "data:text/plain;base64," in result["output"]
    assert f'href="{literal_cid}.txt"' not in result["output"]


def test_cid_links_uses_data_url_for_literal_cid_in_markdown():
    """Literal CIDs with embedded content use data URLs in Markdown."""
    definition = _get_cid_links_definition()
    literal_cid = generate_cid(b"test")
    md_content = f"Check this: {literal_cid}"

    with app.test_request_context("/cid_links", json={"text": md_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Should use data URL in markdown format
    assert f"[{literal_cid}](data:text/plain;base64," in result["output"]


def test_cid_links_empty_literal_cid():
    """Empty literal CID is handled correctly."""
    definition = _get_cid_links_definition()
    empty_cid = generate_cid(b"")  # "AAAAAAAA"
    html_content = f"<p>Empty: {empty_cid}</p>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Should have a data URL link
    assert f">{empty_cid}</a>" in result["output"]
    assert "data:" in result["output"]


# ============================================================================
# MARKDOWN CID REPLACEMENT TESTS
# ============================================================================


def test_cid_links_replaces_cid_in_markdown():
    """CIDs in Markdown are replaced with markdown links."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"markdown test" * 10)
    md_content = f"See {test_cid} for more info."

    with app.test_request_context("/cid_links", json={"text": md_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    expected_link = f"[{test_cid}]({test_cid}.txt)"
    assert expected_link in result["output"]


def test_cid_links_does_not_replace_cid_in_existing_markdown_link():
    """CIDs already in markdown links are not replaced."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"linked content" * 10)
    md_content = f"See [{test_cid}]({test_cid}.txt) here."

    with app.test_request_context("/cid_links", json={"text": md_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Should not have nested brackets
    assert "[[" not in result["output"]
    # Original link format should be preserved or similar
    assert f"[{test_cid}]" in result["output"]


def test_cid_links_replaces_multiple_cids_in_markdown():
    """Multiple CIDs in Markdown are all replaced."""
    definition = _get_cid_links_definition()
    cid1 = generate_cid(b"first content" * 10)
    cid2 = generate_cid(b"second content" * 10)
    md_content = f"First {cid1} and second {cid2}."

    with app.test_request_context("/cid_links", json={"text": md_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert f"[{cid1}]({cid1}.txt)" in result["output"]
    assert f"[{cid2}]({cid2}.txt)" in result["output"]


# ============================================================================
# EDGE CASES
# ============================================================================


def test_cid_links_handles_empty_input():
    """Empty input returns empty output."""
    definition = _get_cid_links_definition()

    with app.test_request_context("/cid_links", json={"text": ""}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["output"] == ""
    assert result["content_type"] == "text/plain"


def test_cid_links_handles_no_cids():
    """Text without CIDs is returned unchanged."""
    definition = _get_cid_links_definition()
    content = "This is text without any content identifiers."

    with app.test_request_context("/cid_links", json={"text": content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["output"] == content


def test_cid_links_handles_bytes_input():
    """Bytes input is handled correctly."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"bytes test" * 10)
    # Note: bytes input would come through query param or body as string

    with app.test_request_context(f"/cid_links?text=Check+{test_cid}"):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert test_cid in result["output"]


def test_cid_links_preserves_surrounding_text():
    """Surrounding text is preserved when replacing CIDs."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"preserve test" * 10)
    content = f"Before {test_cid} after"

    with app.test_request_context("/cid_links", json={"text": content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["output"].startswith("Before ")
    assert result["output"].endswith(" after")


def test_cid_links_invalid_cid_pattern_not_linked():
    """Strings that look like CIDs but are invalid are not linked."""
    definition = _get_cid_links_definition()
    # A string with CID-like characters but invalid structure
    fake_cid = "ZZZZZZZZ" + "A" * 86  # Invalid - doesn't parse

    content = f"Fake: {fake_cid}"

    with app.test_request_context("/cid_links", json={"text": content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    # Should not create a link for invalid CID
    assert "<a " not in result["output"] or fake_cid not in result["output"]


def test_cid_links_with_cid_at_start_of_text():
    """CID at the very start of text is handled."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"start test" * 10)
    content = f"{test_cid} is at the start"

    with app.test_request_context("/cid_links", json={"text": content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert f"[{test_cid}]({test_cid}.txt)" in result["output"]


def test_cid_links_with_cid_at_end_of_text():
    """CID at the very end of text is handled."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"end test" * 10)
    content = f"Ends with {test_cid}"

    with app.test_request_context("/cid_links", json={"text": content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert f"[{test_cid}]({test_cid}.txt)" in result["output"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_cid_links_server_definition_is_valid():
    """The cid_links server definition file is syntactically valid Python."""
    definition = _get_cid_links_definition()
    # Should not raise
    compile(definition, "cid_links.py", "exec")


def test_cid_links_with_html_body_tag():
    """HTML with body tag is correctly detected and processed."""
    definition = _get_cid_links_definition()
    test_cid = generate_cid(b"body tag test" * 10)
    html_content = f"<body><h1>Title</h1><p>{test_cid}</p></body>"

    with app.test_request_context("/cid_links", json={"text": html_content}):
        result = server_execution.execute_server_code_from_definition(
            definition, "cid_links"
        )

    assert result["content_type"] == "text/html"
    assert f'<a href="{test_cid}.txt">{test_cid}</a>' in result["output"]
