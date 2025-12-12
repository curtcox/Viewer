import textwrap
from types import SimpleNamespace

import pytest
from flask import Response

from cid_core import generate_cid
import db_access
import server_execution
from app import app
from server_execution import code_execution, invocation_tracking, server_lookup


_CID_PAYLOADS: dict[str, bytes] = {}


@pytest.fixture(autouse=True)
def clojure_environment(monkeypatch):
    servers: dict[str, SimpleNamespace] = {}
    clojure_runs: list[dict[str, str | None]] = []
    _CID_PAYLOADS.clear()

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
    monkeypatch.setattr(server_lookup, "get_server_by_name", servers.get)
    monkeypatch.setattr(code_execution, "get_server_by_name", servers.get)
    monkeypatch.setattr(db_access, "get_server_by_name", servers.get)
    monkeypatch.setattr(db_access, "get_servers", return_servers)

    def fake_get_cid_by_path(path):
        normalized = path if path.startswith("/") else f"/{path}"
        payload = _CID_PAYLOADS.get(normalized)
        if payload is None:
            return None
        return SimpleNamespace(file_data=payload)

    monkeypatch.setattr(code_execution, "get_cid_by_path", fake_get_cid_by_path)
    monkeypatch.setattr(db_access, "get_cid_by_path", fake_get_cid_by_path)

    def simple_success(
        output, content_type, server_name, *, external_calls=None
    ):  # pylint: disable=unused-argument
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

    return SimpleNamespace(servers=servers, clojure_runs=clojure_runs)


def _literal_cid(source: str) -> str:
    normalized = textwrap.dedent(source)
    payload = normalized.encode("utf-8")
    cid_value = generate_cid(payload)
    _CID_PAYLOADS[f"/{cid_value}"] = payload
    return cid_value


def _python_literal(body: str) -> str:
    return _literal_cid(body)


def _clojure_literal(body: str = "(defn main [])") -> str:
    return _literal_cid(body)


def _bash_literal(body: str) -> str:
    return _literal_cid(body)


def test_clojure_literal_chains_into_python_literal(clojure_environment):
    python_cid = _python_literal(
        "def main(payload):\n return {'output':'py:'+payload}"
    )
    clojure_cid = _clojure_literal()

    with app.test_request_context(f"/{python_cid}.py/{clojure_cid}.clj/result"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{clojure_cid}.clj/result"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "py:clj:from-clojure"


def test_clojure_literal_chains_into_bash_literal(clojure_environment):
    bash_cid = _bash_literal("#!/bin/bash\necho placeholder\n")
    clojure_cid = _clojure_literal()

    with app.test_request_context(f"/{bash_cid}.sh/{clojure_cid}.clj/final"):
        response = server_execution.try_server_execution(
            f"/{bash_cid}.sh/{clojure_cid}.clj/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash:clj:from-clojure"


def test_clojure_literal_chains_into_clojure_literal(clojure_environment):
    left_cid = _clojure_literal("(defn main [] (println \"left\"))")
    right_cid = _clojure_literal("(defn main [] (println \"right\"))")

    with app.test_request_context(f"/{left_cid}.clj/{right_cid}.clj/final"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.clj/{right_cid}.clj/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:clj:from-clojure"


def test_clojure_server_consumes_single_segment_cid_input(clojure_environment):
    clojure_cid = _clojure_literal()
    bash_cid = _bash_literal("#!/bin/bash\necho chained-bash\n")

    with app.test_request_context(f"/{clojure_cid}.clj/{bash_cid}.sh"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/{bash_cid}.sh"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:bash:chained-bash"


def test_clojure_server_consumes_single_segment_python_input(clojure_environment):
    clojure_cid = _clojure_literal()
    python_cid = _python_literal(
        "def main():\n return {'output':'python-into-clj'}"
    )
    with app.test_request_context(f"/{clojure_cid}.clj/{python_cid}.py"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/{python_cid}.py"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:python-into-clj"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "python-into-clj"


def test_clojure_server_does_not_execute_terminal_literal_without_extension(clojure_environment):
    """Single-segment literals lacking an extension should remain raw."""

    clojure_cid = _clojure_literal()
    literal_payload = _literal_cid("raw-literal")

    with app.test_request_context(f"/{clojure_cid}.clj/{literal_payload}"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/{literal_payload}"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:raw-literal"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "raw-literal"


def test_clojure_server_executes_terminal_literal_with_clj_extension(clojure_environment):
    """Single-segment literals should execute when extension matches a language."""

    clojure_cid = _clojure_literal()
    literal_payload = _clojure_literal("(defn main [] (println \"from-literal\"))")

    with app.test_request_context(f"/{clojure_cid}.clj/{literal_payload}.clj"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/{literal_payload}.clj"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:clj:from-clojure"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "clj:from-clojure"


def test_named_clojure_server_receives_python_input(clojure_environment):
    clojure_environment.servers["clj-server"] = SimpleNamespace(
        name="clj-server", definition="(defn main [payload])"
    )
    python_cid = _python_literal(
        "def main():\n return {'output':'python->clj'}"
    )

    with app.test_request_context(f"/clj-server/{python_cid}.py/final"):
        response = server_execution.try_server_execution(f"/clj-server/{python_cid}.py/final")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:python->clj"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "python->clj"


def test_named_clojure_server_executes_terminal_python_literal(clojure_environment):
    clojure_environment.servers["clj-server"] = SimpleNamespace(
        name="clj-server", definition="(defn main [payload])"
    )
    python_cid = _python_literal(
        "def main():\n return {'output':'terminal-python'}"
    )

    with app.test_request_context(f"/clj-server/{python_cid}.py"):
        response = server_execution.try_server_execution(f"/clj-server/{python_cid}.py")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:terminal-python"
    assert clojure_environment.clojure_runs[-1]["chained_input"] == "terminal-python"


def test_clojure_server_receives_bash_input(clojure_environment):
    clj_cid = _clojure_literal()
    bash_cid = _bash_literal("#!/bin/bash\necho bash-into-clj\n")

    with app.test_request_context(f"/{clj_cid}.clj/{bash_cid}.sh/run"):
        response = server_execution.try_server_execution(
            f"/{clj_cid}.clj/{bash_cid}.sh/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:bash:bash-into-clj"


def test_clojure_server_receives_clojure_input(clojure_environment):
    left_cid = _clojure_literal("(defn main [] (println \"left\"))")
    right_cid = _clojure_literal("(defn main [] (println \"right\"))")

    with app.test_request_context(f"/{left_cid}.clj/{right_cid}.clj/run"):
        response = server_execution.try_server_execution(
            f"/{left_cid}.clj/{right_cid}.clj/run"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:clj:from-clojure"


def test_clojure_literal_without_extension_executes(clojure_environment):
    clojure_cid = _clojure_literal('(defn main [] (println "noext"))')

    with app.test_request_context(f"/{clojure_cid}/next"):
        response = server_execution.try_server_execution(f"/{clojure_cid}/next")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:from-clojure"


def test_clojure_literal_with_extension_executes(clojure_environment):
    clojure_cid = _clojure_literal('(defn main [] (println "ext"))')

    with app.test_request_context(f"/{clojure_cid}.clj/final"):
        response = server_execution.try_server_execution(
            f"/{clojure_cid}.clj/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "clj:from-clojure"
