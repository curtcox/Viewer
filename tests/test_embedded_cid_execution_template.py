"""Tests for the embedded CID execution upload template."""

from __future__ import annotations

from pathlib import Path

from cid_core import is_literal_cid

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = (
    REPO_ROOT
    / "reference/templates"
    / "uploads"
    / "contents"
    / "embedded_cid_execution.formdown"
)

EXPECTED_LITERAL_CIDS = {
    "ls": "AAAAAAARIyEvYmluL3NoCmxzIC1sYWg",
    "grep": "AAAAAAAiIyEvYmluL3NoCmdyZXAgLW4gLS1jb2xvcj1uZXZlciAnJw",
    "sed": "AAAAAAAYIyEvYmluL3NoCnNlZCAtbiAnMSwyMHAn",
    "awk": "AAAAAAAaIyEvYmluL3NoCmF3ayAne3ByaW50IE5GfSc",
    "curl": "AAAAAAASIyEvYmluL3NoCmN1cmwgLXNT",
    "head": "AAAAAAATIyEvYmluL3NoCmhlYWQgLW4gNQ",
    "tail": "AAAAAAATIyEvYmluL3NoCnRhaWwgLW4gNQ",
    "jq": "AAAAAAAWIyEvdXNyL2Jpbi9lbnYganEgLXIgLg",
}


def test_embedded_cid_template_contains_literals_and_examples():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "Executable URL path elements" in content or "executable URL" in content

    for name, cid in EXPECTED_LITERAL_CIDS.items():
        assert is_literal_cid(cid), f"Expected {name} CID to be literal"
        assert cid in content, f"CID for {name} should appear in the template"
        assert f"/{cid}" in content, (
            f"CID for {name} should be embedded as a path element"
        )

    assert ".sh" in content
    assert ".jq" in content


def test_embedded_cid_template_forms_chain_commands():
    content = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert (
        "/AAAAAAARIyEvYmluL3NoCmxzIC1sYWg.sh/AAAAAAAiIyEvYmluL3NoCmdyZXAgLW4gLS1jb2xvcj1uZXZlciAnJw.sh/AAAAAAATIyEvYmluL3NoCmhlYWQgLW4gNQ.sh"
        in content
    )
    assert (
        "/AAAAAAASIyEvYmluL3NoCmN1cmwgLXNT.sh/https://api.example.com/data.json/AAAAAAAWIyEvdXNyL2Jpbi9lbnYganEgLXIgLg.jq"
        in content
    )

    for cid in (EXPECTED_LITERAL_CIDS["sed"], EXPECTED_LITERAL_CIDS["tail"]):
        assert f"{cid}.sh" in content
