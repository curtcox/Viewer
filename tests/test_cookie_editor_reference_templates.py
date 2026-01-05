"""Unit tests covering cookie editor reference template wiring."""

from __future__ import annotations

import json
from pathlib import Path

from cid import CID

REPO_ROOT = Path(__file__).parent.parent
REF_TEMPLATES = REPO_ROOT / "reference/templates"
UPLOADS = REF_TEMPLATES / "uploads" / "contents"

COOKIE_EDITOR_HTML_CID = CID.from_bytes(
    (UPLOADS / "cookie_editor.html").read_bytes()
).value
COOKIE_EDITOR_CSS_CID = CID.from_bytes(
    (UPLOADS / "cookie_editor.css").read_bytes()
).value
COOKIE_EDITOR_JS_CID = CID.from_bytes((UPLOADS / "cookie_editor.js").read_bytes()).value
COOKIE_EDITOR_ICON_CID = CID.from_bytes(
    (UPLOADS / "cookie_editor_icon.svg").read_bytes()
).value


def test_cookie_alias_points_to_cookie_cid():
    """The cookies alias should target the generated cookie editor HTML CID."""

    alias_path = REF_TEMPLATES / "aliases" / "cookies.txt"
    content = alias_path.read_text().strip()

    assert content.startswith("cookies -> /")
    assert content.endswith(".html")
    assert COOKIE_EDITOR_HTML_CID in content


def test_cookie_assets_registered_in_sources():
    """Templates and boot sources should reference all cookie editor assets."""

    templates_source = json.loads((REF_TEMPLATES / "templates.source.json").read_text())

    uploads = templates_source["uploads"]
    assert (
        uploads["cookie-editor"]["content_cid"]
        == "reference/templates/uploads/contents/cookie_editor.html"
    )
    assert (
        uploads["cookie-editor-style"]["content_cid"]
        == "reference/templates/uploads/contents/cookie_editor.css"
    )
    assert (
        uploads["cookie-editor-script"]["content_cid"]
        == "reference/templates/uploads/contents/cookie_editor.js"
    )
    assert (
        uploads["cookie-editor-icon"]["content_cid"]
        == "reference/templates/uploads/contents/cookie_editor_icon.svg"
    )

    alias_templates = templates_source["aliases"]
    assert (
        alias_templates["cookie-editor"]["definition_cid"]
        == "reference/templates/aliases/cookies.txt"
    )

    cookie_boot_alias = {
        alias["name"]: alias["definition_cid"]
        for alias in json.loads(
            (REF_TEMPLATES / "default.boot.source.json").read_text()
        )["aliases"]
    }
    readonly_cookie_alias = {
        alias["name"]: alias["definition_cid"]
        for alias in json.loads(
            (REF_TEMPLATES / "readonly.boot.source.json").read_text()
        )["aliases"]
    }

    expected_definition = "reference/templates/aliases/cookies.txt"
    assert cookie_boot_alias["cookies"] == expected_definition
    assert readonly_cookie_alias["cookies"] == expected_definition

    html_content = (UPLOADS / "cookie_editor.html").read_text()
    assert (
        COOKIE_EDITOR_HTML_CID not in html_content
    )  # self-reference is handled via alias file
    assert COOKIE_EDITOR_CSS_CID in html_content
    assert COOKIE_EDITOR_JS_CID in html_content
    assert COOKIE_EDITOR_ICON_CID in html_content
