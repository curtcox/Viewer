import textwrap
from types import SimpleNamespace

import pytest
from flask import Response

import db_access
import server_execution
from app import app
from server_execution import code_execution, invocation_tracking, server_lookup


@pytest.fixture(autouse=True)
def clojure_environment(monkeypatch):
    cid_registry: dict[str, bytes] = {}
    servers: dict[str, SimpleNamespace] = {}
    clojure_runs: list[dict[str, str | None]] = []

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
    monkeypatch.setattr(invocation_tracking, "create_server_invocation_record", noop_record)
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

    def simple_success(output, content_type, server_name):  # pylint: disable=unused-argument
        return Response(output, mimetype=content_type or "text/html")

    monkeypatch.setattr(code_execution, "_handle_successful_execution", simple_success)

    def fake_run_clojure(code, server_name, chained_input=None):  # pylint: disable=unused-argument
        payload = chained_input if chained_input is not None else "from-clojure"
        clojure_runs.append(
            {
                "code": code,
                "server_name": server_name,
                "chained_input": chained_input,
                "payload": payload,
            }
        )
        return f"clj:{payload}".encode(), 200, b""

    def fake_run_bash(code, server_name, chained_input=None):  # pylint: disable=unused-argument
        if chained_input is not None:
            payload = chained_input
        else:
            stripped = (code or "").strip()
            payload = stripped.split()[-1] if stripped else ""
        return f"bash:{payload}".encode(), 200, b""

    monkeypatch.setattr(code_execution, "_run_clojure_script", fake_run_clojure)
    monkeypatch.setattr(code_execution, "_run_bash_script", fake_run_bash)

    return SimpleNamespace(
        cid_registry=cid_registry, servers=servers, clojure_runs=clojure_runs
    )


def _store_python_server(cid_registry: dict[str, bytes], name: str, body: str):
    cid_registry[f"/{name}"] = textwrap.dedent(body).encode("utf-8")


def _store_clojure_server(cid_registry: dict[str, bytes], name: str, body: str = "(defn main [])"):
    normalized = name.lstrip("/")
    if normalized.endswith(".clj"):
        normalized = normalized.rsplit(".", 1)[0]
    cid_registry[f"/{normalized}"] = body.encode("utf-8")


def test_clojure_literal_chains_into_python_literal(clojure_environment):
    python_cid = "py-clj-left"
    clojure_cid = "clj-source"

    _store_python_server(
        clojure_environment.cid_registry,
        python_cid,
        """
        def main(payload):
            return {"output": f"py:{payload}", "content_type": "text/plain"}
        """,
    )
    _store_clojure_server(clojure_environment.cid_registry, f"{clojure_cid}.clj")

    with app.test_request_context(f"/{python_cid}.py/{clojure_cid}.clj/result"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{clojure_cid}.clj/result"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "py:clj:from-clojure"


def test_clojure_literal_chains_into_bash_literal(clojure_environment):
    bash_cid = "bash-left"
    clojure_cid = "clj-right"

    clojure_environment.cid_registry[f"/{bash_cid}"] = b"echo placeholder"
    _store_clojure_server(clojure_environment.cid_registry, f"{clojure_cid}.clj")

    with app.test_request_context(f"/{bash_cid}.sh/{clojure_cid}.clj/final"):
        response = server_execution.try_server_execution(
            f"/{bash_cid}.sh/{clojure_cid}.clj/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash:clj:from-clojure"


def test_clojure_literal_chains_into_clojure_literal(clojure_environment):
    left_cid = "clj-left"
    right_cid = "clj-right"

    _store_clojure_server(clojure_environment.cid_registry, f"{left_cid}.clj")
    _store_clojure_server(clojure_environment.cid_registry, f"{right_cid}.clj")

    with app.test_request_context(f"/{left_cid}.clj/{right_cid}.clj/final"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.clj/{right_cid}.clj/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:clj:from-clojure"


def test_clojure_server_consumes_single_segment_cid_input(clojure_environment):
    clojure_cid = "clj-consume"
    bash_cid = "bash-yield"

    _store_clojure_server(clojure_environment.cid_registry, f"{clojure_cid}.clj")
    clojure_environment.cid_registry[f"/{bash_cid}"] = b"echo chained-bash"

    with app.test_request_context(f"/{clojure_cid}.clj/{bash_cid}.sh"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/{bash_cid}.sh"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:bash:chained-bash"


def test_clojure_server_consumes_single_segment_python_input(clojure_environment):
    clojure_cid = "clj-consume"
    python_cid = "py-yield"

    _store_clojure_server(clojure_environment.cid_registry, f"{clojure_cid}.clj")
    _store_python_server(
        clojure_environment.cid_registry,
        python_cid,
        """
        def main():
            return {"output": "python-into-clj", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/{clojure_cid}.clj/{python_cid}.py"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/{python_cid}.py"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:python-into-clj"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "python-into-clj"


def test_named_clojure_server_receives_python_input(clojure_environment):
    clojure_environment.servers["clj-server"] = SimpleNamespace(
        name="clj-server", definition="(defn main [payload])"
    )
    python_cid = "py-input"

    _store_python_server(
        clojure_environment.cid_registry,
        python_cid,
        """
        def main():
            return {"output": "python->clj", "content_type": "text/plain"}
        """,
    )

    with app.test_request_context(f"/clj-server/{python_cid}.py/final"):
        response = server_execution.try_server_execution(f"/clj-server/{python_cid}.py/final")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:python->clj"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "python->clj"


def test_clojure_server_receives_bash_input(clojure_environment):
    clj_cid = "clj-target"
    bash_cid = "bash-source"

    _store_clojure_server(clojure_environment.cid_registry, f"{clj_cid}.clj")
    clojure_environment.cid_registry[f"/{bash_cid}"] = b"echo bash-into-clj"

    with app.test_request_context(f"/{clj_cid}.clj/{bash_cid}.sh/run"):
        response = server_execution.try_server_execution(
            f"/{clj_cid}.clj/{bash_cid}.sh/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:bash:bash-into-clj"


def test_clojure_server_receives_clojure_input(clojure_environment):
    left_cid = "clj-left"
    right_cid = "clj-right"

    _store_clojure_server(clojure_environment.cid_registry, f"{left_cid}.clj")
    _store_clojure_server(clojure_environment.cid_registry, f"{right_cid}.clj")

    with app.test_request_context(f"/{left_cid}.clj/{right_cid}.clj/run"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.clj/{right_cid}.clj/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:clj:from-clojure"


def test_clojure_literal_without_extension_executes(clojure_environment):
    clojure_cid = "rawclj"
    _store_clojure_server(
        clojure_environment.cid_registry,
        clojure_cid,
        "(defn main [] (println \"noext\"))",
    )

    with app.test_request_context(f"/{clojure_cid}/next"):
        response = server_execution.try_server_execution(f"/{clojure_cid}/next")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:from-clojure"


def test_clojure_literal_with_extension_executes(clojure_environment):
    clojure_cid = "extclj"
    _store_clojure_server(
        clojure_environment.cid_registry,
        f"{clojure_cid}.clj",
        "(defn main [] (println \"ext\"))",
    )

    with app.test_request_context(f"/{clojure_cid}.clj/final"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:from-clojure"
