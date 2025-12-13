import textwrap
from types import SimpleNamespace

import pytest
from flask import Response

import db_access
import server_execution
from app import app
from server_execution import code_execution, server_lookup


@pytest.fixture(autouse=True)
def clojurescript_environment(monkeypatch):
    cid_registry: dict[str, bytes] = {}
    servers: dict[str, SimpleNamespace] = {}
    clojurescript_runs: list[dict[str, str | None]] = []

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

    def fake_run_clojurescript(
        code, server_name, chained_input=None
    ):  # pylint: disable=unused-argument
        payload = chained_input if chained_input is not None else "from-cljs"
        clojurescript_runs.append(
            {
                "code": code,
                "server_name": server_name,
                "chained_input": chained_input,
                "payload": payload,
            }
        )
        return f"cljs:{payload}".encode(), 200, b""

    def fake_run_bash(code, server_name, chained_input=None):  # pylint: disable=unused-argument
        if chained_input is not None:
            payload = chained_input
        else:
            stripped = (code or "").strip()
            payload = stripped.split()[-1] if stripped else ""
        return f"bash:{payload}".encode(), 200, b""

    monkeypatch.setattr(code_execution, "_run_clojurescript_script", fake_run_clojurescript)
    monkeypatch.setattr(code_execution, "_run_bash_script", fake_run_bash)

    return SimpleNamespace(
        cid_registry=cid_registry,
        servers=servers,
        clojurescript_runs=clojurescript_runs,
    )


def _store_python_server(cid_registry: dict[str, bytes], name: str, body: str):
    cid_registry[f"/{name}"] = textwrap.dedent(body).encode("utf-8")


def _store_clojurescript_server(
    cid_registry: dict[str, bytes], name: str, body: str = "(ns cljs.user)\n(defn main [])"
):
    normalized = name.lstrip("/")
    if normalized.endswith(".cljs"):
        normalized = normalized.rsplit(".", 1)[0]
    cid_registry[f"/{normalized}"] = body.encode("utf-8")


def test_clojurescript_literal_chains_into_python_literal(clojurescript_environment):
    python_cid = "py-cljs-left"
    cljs_cid = "cljs-source"

    _store_python_server(
        clojurescript_environment.cid_registry,
        python_cid,
        """
        def main(payload):
            return {"output": f"py:{payload}", "content_type": "text/plain"}
        """,
    )
    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{cljs_cid}.cljs"
    )

    with app.test_request_context(f"/{python_cid}.py/{cljs_cid}.cljs/result"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{cljs_cid}.cljs/result"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "py:cljs:from-cljs"


def test_clojurescript_literal_chains_into_bash_literal(clojurescript_environment):
    bash_cid = "bash-left"
    cljs_cid = "cljs-right"

    clojurescript_environment.cid_registry[f"/{bash_cid}"] = b"echo placeholder"
    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{cljs_cid}.cljs"
    )

    with app.test_request_context(f"/{bash_cid}.sh/{cljs_cid}.cljs/final"):
        response = server_execution.try_server_execution(
            f"/{bash_cid}.sh/{cljs_cid}.cljs/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash:cljs:from-cljs"


def test_clojurescript_literal_chains_into_clojurescript_literal(clojurescript_environment):
    left_cid = "cljs-left"
    right_cid = "cljs-right"

    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{left_cid}.cljs"
    )
    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{right_cid}.cljs"
    )

    with app.test_request_context(f"/{left_cid}.cljs/{right_cid}.cljs/final"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.cljs/{right_cid}.cljs/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:cljs:from-cljs"


def test_clojurescript_server_consumes_python_input(clojurescript_environment):
    cljs_cid = "cljs-consume"
    python_cid = "py-yield"

    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{cljs_cid}.cljs"
    )
    _store_python_server(
        clojurescript_environment.cid_registry,
        python_cid,
        """
        def main():
            return {"output": "python-into-cljs", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/{cljs_cid}.cljs/{python_cid}.py"):
        response = server_execution.try_server_execution(
            f"/{cljs_cid}.cljs/{python_cid}.py"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:python-into-cljs"
    assert (
        clojurescript_environment.clojurescript_runs[-1]["chained_input"]
        == "python-into-cljs"
    )


def test_clojurescript_server_consumes_bash_input(clojurescript_environment):
    cljs_cid = "cljs-target"
    bash_cid = "bash-source"

    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{cljs_cid}.cljs"
    )
    clojurescript_environment.cid_registry[f"/{bash_cid}"] = b"echo bash-into-cljs"

    with app.test_request_context(f"/{cljs_cid}.cljs/{bash_cid}.sh/run"):
        response = server_execution.try_server_execution(
            f"/{cljs_cid}.cljs/{bash_cid}.sh/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:bash:bash-into-cljs"


def test_clojurescript_server_consumes_clojurescript_input(
    clojurescript_environment,
):
    left_cid = "cljs-left"
    right_cid = "cljs-right"

    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{left_cid}.cljs"
    )
    _store_clojurescript_server(
        clojurescript_environment.cid_registry, f"{right_cid}.cljs"
    )

    with app.test_request_context(f"/{left_cid}.cljs/{right_cid}.cljs/run"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.cljs/{right_cid}.cljs/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:cljs:from-cljs"


def test_named_clojurescript_server_receives_python_input(clojurescript_environment):
    clojurescript_environment.servers["cljs-server"] = SimpleNamespace(
        name="cljs-server",
        definition="(ns cljs.server) (defn main [payload])",
    )
    python_cid = "py-input"

    _store_python_server(
        clojurescript_environment.cid_registry,
        python_cid,
        """
        def main():
            return {"output": "python->cljs", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/cljs-server/{python_cid}.py/final"):
        response = server_execution.try_server_execution(
            f"/cljs-server/{python_cid}.py/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:python->cljs"
    assert (
        clojurescript_environment.clojurescript_runs[-1]["chained_input"]
        == "python->cljs"
    )


def test_clojurescript_literal_without_extension_executes(clojurescript_environment):
    cljs_cid = "rawcljs"
    _store_clojurescript_server(
        clojurescript_environment.cid_registry,
        cljs_cid,
        "(ns cljs.noext) (defn main [] (println \"noext\"))",
    )

    with app.test_request_context(f"/{cljs_cid}/next"):
        response = server_execution.try_server_execution(f"/{cljs_cid}/next")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:from-cljs"


def test_clojurescript_literal_with_extension_executes(clojurescript_environment):
    cljs_cid = "extcljs"
    _store_clojurescript_server(
        clojurescript_environment.cid_registry,
        f"{cljs_cid}.cljs",
        "(ns cljs.ext) (defn main [] (println \"ext\"))",
    )

    with app.test_request_context(f"/{cljs_cid}.cljs/final"):
        response = server_execution.try_server_execution(
            f"/{cljs_cid}.cljs/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "cljs:from-cljs"
