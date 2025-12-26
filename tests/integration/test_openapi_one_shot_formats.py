"""Integration tests for one-shot responses across media types."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cid_utils import generate_cid
from encryption import encrypt_secret_value

pytestmark = pytest.mark.integration

DATASET = {
    "aliases": {
        "name": "cli-alias",
        "definition": "/cli-alias -> /target",
        "enabled": True,
    },
    "servers": {
        "name": "cli-server",
        "definition": 'def main():\n    return "ok"',
        "enabled": True,
    },
    "variables": {"name": "cli-variable", "definition": "value", "enabled": True},
    "secrets": {"name": "cli-secret", "definition": "hidden", "enabled": True},
}

FORMAT_EXTENSIONS = {
    "html": "",
    "txt": ".txt",
    "csv": ".csv",
    "json": ".json",
    "xml": ".xml",
    "md": ".md",
}


@pytest.fixture(scope="module")
def boot_image_fixture(tmp_path_factory):
    """Create a shared boot image with all entity types."""

    cli_root = Path(__file__).parent.parent.parent
    cids_dir = tmp_path_factory.mktemp("cids")
    secret_key = "integration-secret-key"

    created_files: list[Path] = []

    def _store_payload(payload: object) -> str:
        content = json.dumps(payload, indent=2).encode("utf-8")
        cid = generate_cid(content)
        cid_path = cids_dir / cid
        cid_path.write_bytes(content)
        created_files.append(cid_path)
        return cid

    alias_cid = _store_payload([DATASET["aliases"]])
    server_cid = _store_payload([DATASET["servers"]])
    variable_cid = _store_payload([DATASET["variables"]])
    secret_ciphertext = encrypt_secret_value(
        DATASET["secrets"]["definition"], secret_key
    )
    secret_payload = [
        {
            "name": DATASET["secrets"]["name"],
            "ciphertext": secret_ciphertext,
            "enabled": True,
        }
    ]
    secret_cid = _store_payload(secret_payload)

    boot_payload = {
        "version": 6,
        "aliases": alias_cid,
        "servers": server_cid,
        "variables": variable_cid,
        "secrets": secret_cid,
    }
    boot_cid = _store_payload(boot_payload)

    yield {
        "boot_cid": boot_cid,
        "cli_root": cli_root,
        "cids_dir": cids_dir,
        "secret_key": secret_key,
    }

    for path in created_files:
        path.unlink(missing_ok=True)


def _parse_output(raw_output: str) -> tuple[int, str]:
    status_code = None
    lines = raw_output.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Status:"):
            status_code = int(line.split(":", 1)[1].strip())
            body = "\n".join(lines[index + 1 :])
            return status_code, body
    raise AssertionError(f"Missing status line in output: {raw_output}")


def _run_one_shot(
    path: str, boot_cid: str, cli_root: Path, cids_dir: Path, secret_key: str
) -> tuple[int, str]:
    env = os.environ.copy()
    env.pop("TESTING", None)
    env.setdefault("SESSION_SECRET", "integration-secret")
    env["BOOT_SECRET_KEY"] = secret_key
    env["CID_DIRECTORY"] = str(cids_dir)
    env["TESTING"] = "1"

    result = subprocess.run(
        [sys.executable, "main.py", "--in-memory-db", path, boot_cid],
        cwd=cli_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )

    return _parse_output(result.stdout)


def _build_path(resource: str, scope: str, extension: str) -> str:
    if scope == "list":
        base = f"/{resource}"
    else:
        base = f"/{resource}/{DATASET[resource]['name']}"
    return f"{base}{extension}"


def _assert_body(resource: str, fmt: str, scope: str, body: str) -> None:
    name = DATASET[resource]["name"]

    if fmt == "html":
        assert "<html" in body.lower()
        assert name in body
    elif fmt == "json":
        parsed = json.loads(body)
        if scope == "list":
            assert any(entry.get("name") == name for entry in parsed)
        else:
            assert parsed.get("name") == name
    elif fmt == "csv":
        lines = [line for line in body.splitlines() if line]
        assert lines, "CSV response should not be empty"
        assert "name" in lines[0]
        assert any(name in line for line in lines[1:])
    elif fmt == "xml":
        assert f"<name>{name}</name>" in body
    elif fmt == "txt":
        if scope == "list":
            assert body.strip() == name
        else:
            assert f"name: {name}" in body
            assert "definition:" in body
    elif fmt == "md":
        if scope == "list":
            assert f"- {name}" in body
        else:
            assert f"**name**: {name}" in body
    else:
        raise AssertionError(f"Unhandled format: {fmt}")


@pytest.mark.parametrize("resource", ["aliases", "servers", "variables", "secrets"])
@pytest.mark.parametrize("fmt", list(FORMAT_EXTENSIONS.keys()))
@pytest.mark.parametrize("scope", ["list", "detail"])
def test_one_shot_media_outputs(resource: str, fmt: str, scope: str, boot_image_fixture):
    extension = FORMAT_EXTENSIONS[fmt]
    path = _build_path(resource, scope, extension)

    status, body = _run_one_shot(
        path,
        boot_image_fixture["boot_cid"],
        boot_image_fixture["cli_root"],
        boot_image_fixture["cids_dir"],
        boot_image_fixture["secret_key"],
    )

    assert status == 200
    _assert_body(resource, fmt, scope, body)
