import json
import textwrap
from types import SimpleNamespace

import pytest
from flask import Response

import db_access
import server_execution
from app import app
from server_execution import code_execution, server_lookup


@pytest.fixture(autouse=True)
def typescript_environment(monkeypatch):
    cid_registry: dict[str, bytes] = {}
    servers: dict[str, SimpleNamespace] = {}
    typescript_runs: list[dict[str, str | None]] = []

    def return_empty_context():
        return {"variables": {}, "secrets": {}, "servers": {}}

    def return_none(*_, **__):
        return None

    def return_empty_list(*_, **__):
        return []

    def return_servers():
        return list(servers.values())

    def noop_record(*_, **__):
        return None

    def noop_create_cid(*_, **__):
        return None

    monkeypatch.setattr(code_execution, "_load_user_context", return_empty_context)
    monkeypatch.setattr(code_execution, "find_matching_alias", return_none)
    monkeypatch.setattr(code_execution, "get_servers", return_servers)
    monkeypatch.setattr(code_execution, "get_secrets", return_empty_list)
    monkeypatch.setattr(code_execution, "get_variables", return_empty_list)
    monkeypatch.setattr(db_access, "get_secrets", return_empty_list)
    monkeypatch.setattr(db_access, "get_variables", return_empty_list)
    monkeypatch.setattr(
        server_execution.invocation_tracking,
        "create_server_invocation_record",
        noop_record,
    )
    monkeypatch.setattr(code_execution, "create_cid_record", noop_create_cid)

    def fake_get_cid_by_path(path):
        payload = cid_registry.get(path)
        if payload is None:
            return None
        return SimpleNamespace(file_data=payload)

    monkeypatch.setattr(code_execution, "get_cid_by_path", fake_get_cid_by_path)
    monkeypatch.setattr(server_lookup, "get_server_by_name", servers.get)
    monkeypatch.setattr(code_execution, "get_server_by_name", servers.get)
    monkeypatch.setattr(db_access, "get_server_by_name", servers.get)
    monkeypatch.setattr(db_access, "get_servers", return_servers)

    def simple_success(
        output, content_type, server_name, *, external_calls=None
    ):  # pylint: disable=unused-argument
        return Response(output, mimetype=content_type or "text/html")

    monkeypatch.setattr(code_execution, "_handle_successful_execution", simple_success)

    def fake_run_typescript(code, server_name, chained_input=None):  # pylint: disable=unused-argument
        payload = chained_input if chained_input is not None else "from-ts"
        typescript_runs.append(
            {
                "code": code,
                "server_name": server_name,
                "chained_input": chained_input,
                "payload": payload,
            }
        )
        return f"ts:{payload}".encode(), 200, b""

    def fake_run_bash(
        code, server_name, chained_input=None, *, script_args=None
    ):  # pylint: disable=unused-argument
        if chained_input is not None:
            payload = chained_input
        else:
            stripped = (code or "").strip()
            payload = stripped.split()[-1] if stripped else ""
        return f"bash:{payload}".encode(), 200, b""

    monkeypatch.setattr(code_execution, "_run_typescript_script", fake_run_typescript)
    monkeypatch.setattr(code_execution, "_run_bash_script", fake_run_bash)

    return SimpleNamespace(
        cid_registry=cid_registry,
        servers=servers,
        typescript_runs=typescript_runs,
    )


def _store_python_server(cid_registry: dict[str, bytes], name: str, body: str):
    cid_registry[f"/{name}"] = textwrap.dedent(body).encode("utf-8")


def _store_typescript_server(
    cid_registry: dict[str, bytes], name: str, body: str = "export function main() {}"
):
    normalized = name.lstrip("/")
    if normalized.endswith(".ts"):
        normalized = normalized.rsplit(".", 1)[0]
    cid_registry[f"/{normalized}"] = body.encode("utf-8")


def test_typescript_literal_chains_into_python_literal(typescript_environment):
    python_cid = "py-ts-left"
    ts_cid = "ts-source"

    _store_python_server(
        typescript_environment.cid_registry,
        python_cid,
        """
        def main(payload):
            return {"output": f"py:{payload}", "content_type": "text/plain"}
        """,
    )
    _store_typescript_server(
        typescript_environment.cid_registry, f"{ts_cid}.ts"
    )

    with app.test_request_context(f"/{python_cid}.py/{ts_cid}.ts/result"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{ts_cid}.ts/result"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "py:ts:from-ts"


def test_typescript_literal_chains_into_bash_literal(typescript_environment):
    bash_cid = "bash-left"
    ts_cid = "ts-right"

    typescript_environment.cid_registry[f"/{bash_cid}"] = b"echo placeholder"
    _store_typescript_server(
        typescript_environment.cid_registry, f"{ts_cid}.ts"
    )

    with app.test_request_context(f"/{bash_cid}.sh/{ts_cid}.ts/final"):
        response = server_execution.try_server_execution(
            f"/{bash_cid}.sh/{ts_cid}.ts/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash:ts:from-ts"


def test_typescript_literal_chains_into_typescript_literal(typescript_environment):
    left_cid = "ts-left"
    right_cid = "ts-right"

    _store_typescript_server(
        typescript_environment.cid_registry, f"{left_cid}.ts"
    )
    _store_typescript_server(
        typescript_environment.cid_registry, f"{right_cid}.ts"
    )

    with app.test_request_context(f"/{left_cid}.ts/{right_cid}.ts/final"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.ts/{right_cid}.ts/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:ts:from-ts"


def test_typescript_server_consumes_python_input(typescript_environment):
    ts_cid = "ts-consume"
    python_cid = "py-yield"

    _store_typescript_server(
        typescript_environment.cid_registry, f"{ts_cid}.ts"
    )
    _store_python_server(
        typescript_environment.cid_registry,
        python_cid,
        """
        def main():
            return {"output": "python-into-ts", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/{ts_cid}.ts/{python_cid}.py"):
        response = server_execution.try_server_execution(
            f"/{ts_cid}.ts/{python_cid}.py"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:python-into-ts"
    assert (
        typescript_environment.typescript_runs[-1]["chained_input"]
        == "python-into-ts"
    )


def test_typescript_server_consumes_bash_input(typescript_environment):
    ts_cid = "ts-target"
    bash_cid = "bash-source"

    _store_typescript_server(
        typescript_environment.cid_registry, f"{ts_cid}.ts"
    )
    typescript_environment.cid_registry[f"/{bash_cid}"] = b"echo bash-into-ts"

    with app.test_request_context(f"/{ts_cid}.ts/{bash_cid}.sh/run"):
        response = server_execution.try_server_execution(
            f"/{ts_cid}.ts/{bash_cid}.sh/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:bash:bash-into-ts"


def test_typescript_server_consumes_typescript_input(typescript_environment):
    left_cid = "ts-left"
    right_cid = "ts-right"

    _store_typescript_server(
        typescript_environment.cid_registry, f"{left_cid}.ts"
    )
    _store_typescript_server(
        typescript_environment.cid_registry, f"{right_cid}.ts"
    )

    with app.test_request_context(f"/{left_cid}.ts/{right_cid}.ts/run"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.ts/{right_cid}.ts/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:ts:from-ts"


def test_named_typescript_server_receives_python_input(typescript_environment):
    typescript_environment.servers["ts-server"] = SimpleNamespace(
        name="ts-server",
        definition="export function main(payload?: string) { return payload; }",
    )
    python_cid = "py-input"

    _store_python_server(
        typescript_environment.cid_registry,
        python_cid,
        """
        def main():
            return {"output": "python->ts", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/ts-server/{python_cid}.py/final"):
        response = server_execution.try_server_execution(
            f"/ts-server/{python_cid}.py/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:python->ts"
    assert (
        typescript_environment.typescript_runs[-1]["chained_input"]
        == "python->ts"
    )


def test_python_literal_extracts_output_from_typescript_json(
    typescript_environment, monkeypatch
):
    ts_cid = "ts-json"
    python_cid = "py-target"

    def fake_run_typescript(code, server_name, chained_input=None):  # pylint: disable=unused-argument
        payload = json.dumps(
            {"output": "ts-json-output", "content_type": "application/json"}
        ).encode("utf-8")
        return payload, 200, b""

    monkeypatch.setattr(code_execution, "_run_typescript_script", fake_run_typescript)

    _store_typescript_server(typescript_environment.cid_registry, f"{ts_cid}.ts")
    _store_python_server(
        typescript_environment.cid_registry,
        python_cid,
        """
        def main(payload):
            return {"output": f"py::{payload}", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/{python_cid}.py/{ts_cid}.ts/final"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{ts_cid}.ts/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "py::ts-json-output"


def test_typescript_literal_without_extension_executes(typescript_environment):
    ts_cid = "rawtssrc"
    _store_typescript_server(
        typescript_environment.cid_registry,
        ts_cid,
        "export async function main() { await Promise.resolve(); }",
    )

    with app.test_request_context(f"/{ts_cid}/tail"):
        response = server_execution.try_server_execution(f"/{ts_cid}/tail")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:from-ts"


def test_typescript_literal_with_extension_executes(typescript_environment):
    ts_cid = "exttssrc"
    _store_typescript_server(
        typescript_environment.cid_registry,
        f"{ts_cid}.ts",
        "export function main() { console.log('ext'); }",
    )

    with app.test_request_context(f"/{ts_cid}.ts/final"):
        response = server_execution.try_server_execution(
            f"/{ts_cid}.ts/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "ts:from-ts"
