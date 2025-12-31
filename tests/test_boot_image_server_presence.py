import json
from pathlib import Path

import pytest

from cid_core import extract_literal_content, is_literal_cid, is_normalized_cid
from common_commands import COMMON_COMMANDS, group_commands_for_readonly


PROJECT_ROOT = Path(__file__).parent.parent
REFERENCE_TEMPLATES = PROJECT_ROOT / "reference_templates"
CIDS_DIR = PROJECT_ROOT / "cids"


NON_COMMAND_SERVER_DEFINITIONS = {
    "ai_stub": "ai_stub.py",
    "anthropic_claude": "anthropic_claude.py",
    "airtable": "airtable.py",
    "asana": "asana.py",
    "auto_main": "auto_main.py",
    "markdown": "markdown.py",
    "jsonplaceholder": "jsonplaceholder.py",
    "shell": "shell.py",
    "glom": "glom.py",
    "gmail": "gmail.py",
    "hrx": "hrx.py",
    "gateway": "gateway.py",
    "mcp": "mcp.py",
    "io": "io.py",
    "files": "files.py",
    "cid_links": "cid_links.py",
    "google_gemini": "google_gemini.py",
    "google_sheets": "google_sheets.py",
    "github": "github.py",
    "hubspot": "hubspot.py",
    "jinja": "jinja_renderer.py",
    "mailchimp": "mailchimp.py",
    "nvidia_nim": "nvidia_nim.py",
    "notion": "notion.py",
    "openai_chat": "openai_chat.py",
    "openrouter": "openrouter.py",
    "proxy": "proxy.py",
    "qr": "qr.py",
    "pygments": "pygments.py",
    "urleditor": "urleditor.py",
    "reflect": "reflect.py",
    "ai_editor": "ai_editor.py",
    "ai_assist": "ai_assist.py",
    "slack": "slack.py",
    "stripe": "stripe.py",
    "zendesk": "zendesk.py",
    "zoom": "zoom.py",
}


def _expected_default_servers() -> dict[str, str]:
    expected: dict[str, str] = {}
    for name, filename in NON_COMMAND_SERVER_DEFINITIONS.items():
        expected[name] = f"reference_templates/servers/definitions/{filename}"
    for command in COMMON_COMMANDS:
        expected[command.name] = f"reference_templates/servers/definitions/{command.name}.sh"
    return expected


def _expected_readonly_servers() -> dict[str, str]:
    expected: dict[str, str] = {}
    for name, filename in NON_COMMAND_SERVER_DEFINITIONS.items():
        if name == "shell":
            continue
        expected[name] = f"reference_templates/servers/definitions/{filename}"
    for command in group_commands_for_readonly(COMMON_COMMANDS):
        expected[command.name] = f"reference_templates/servers/definitions/{command.name}.sh"
    return expected


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _servers_mapping_from_source(data: dict) -> dict[str, str]:
    servers = data.get("servers")
    if not isinstance(servers, list):
        raise AssertionError("Expected 'servers' to be a list")
    mapping: dict[str, str] = {}
    for entry in servers:
        name = entry.get("name")
        definition = entry.get("definition_cid")
        if not isinstance(name, str) or not isinstance(definition, str):
            raise AssertionError("Server entry missing name/definition_cid")
        if name in mapping:
            raise AssertionError(f"Duplicate server entry: {name}")
        mapping[name] = definition
    return mapping


def _assert_all_server_definitions_are_reference_paths(payload: dict) -> None:
    servers = _servers_mapping_from_source(payload)
    for name, definition in servers.items():
        assert isinstance(definition, str)
        assert definition.startswith("reference_templates/")
        assert "/servers/definitions/" in definition
        assert definition.endswith((".py", ".sh"))
        assert "\\" not in definition
        assert ".." not in definition
        assert name.strip() == name


def _assert_all_server_definitions_are_cids(payload: dict) -> None:
    servers = _servers_mapping_from_source(payload)
    for definition in servers.values():
        assert isinstance(definition, str)
        assert not definition.startswith("reference_templates/")
        assert is_normalized_cid(definition)


def _load_generated_boot_payload_from_cid_file(cid_file: Path) -> dict:
    cid = cid_file.read_text(encoding="utf-8").strip()
    if not cid:
        raise AssertionError(f"Empty CID file: {cid_file}")

    if is_literal_cid(cid):
        content = extract_literal_content(cid)
        if content is None:
            raise AssertionError(f"Could not extract literal CID content: {cid}")
        raw = content
    else:
        raw = (CIDS_DIR / cid).read_bytes()

    return json.loads(raw.decode("utf-8"))


def _assert_expected_servers_in_source(source_file: str, expected: dict[str, str]) -> None:
    data = _load_json(REFERENCE_TEMPLATES / source_file)
    actual = _servers_mapping_from_source(data)

    assert set(actual.keys()) == set(expected.keys())
    for name, expected_path in expected.items():
        assert actual[name] == expected_path


def _assert_expected_servers_in_generated(cid_file: str, expected: dict[str, str]) -> None:
    payload = _load_generated_boot_payload_from_cid_file(REFERENCE_TEMPLATES / cid_file)
    actual = _servers_mapping_from_source(payload)

    assert set(actual.keys()) == set(expected.keys())

    for definition in actual.values():
        assert isinstance(definition, str)
        assert not definition.startswith("reference_templates/")


@pytest.mark.parametrize(
    "source_file, expected",
    [
        ("default.boot.source.json", _expected_default_servers()),
        ("readonly.boot.source.json", _expected_readonly_servers()),
    ],
)
def test_boot_source_files_contain_expected_servers(source_file, expected):
    _assert_expected_servers_in_source(source_file, expected)


@pytest.mark.parametrize(
    "cid_file, expected",
    [
        ("default.boot.cid", _expected_default_servers()),
        ("readonly.boot.cid", _expected_readonly_servers()),
    ],
)
def test_boot_cids_contain_expected_servers(cid_file, expected):
    _assert_expected_servers_in_generated(cid_file, expected)


@pytest.mark.parametrize(
    "source_file",
    [
        "boot.source.json",
        "minimal.boot.source.json",
        "default.boot.source.json",
        "readonly.boot.source.json",
    ],
)
def test_boot_source_files_use_reference_template_paths_for_server_definitions(source_file):
    payload = _load_json(REFERENCE_TEMPLATES / source_file)
    _assert_all_server_definitions_are_reference_paths(payload)


@pytest.mark.parametrize(
    "boot_file",
    [
        "boot.json",
        "minimal.boot.json",
        "default.boot.json",
        "readonly.boot.json",
    ],
)
def test_generated_boot_json_files_use_cids_for_server_definitions(boot_file):
    payload = _load_json(REFERENCE_TEMPLATES / boot_file)
    _assert_all_server_definitions_are_cids(payload)
