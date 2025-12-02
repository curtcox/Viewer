"""Behavior for executing server literals defined by CID path segments."""

from types import SimpleNamespace
import textwrap

import pytest
from flask import Response

import server_execution
from app import app
from server_execution import code_execution, server_lookup


@pytest.fixture(autouse=True)
def patch_server_literal_environment(monkeypatch):
    """Stub out database-backed functions for server literal execution tests."""

    monkeypatch.setattr(code_execution, "_load_user_context", lambda: {"variables": {}, "secrets": {}, "servers": {}})
    monkeypatch.setattr(code_execution, "get_server_by_name", lambda name: None)
    monkeypatch.setattr(code_execution, "find_matching_alias", lambda path: None)
    monkeypatch.setattr(code_execution, "get_servers", lambda: [])
    monkeypatch.setattr(code_execution, "get_secrets", lambda: [])
    monkeypatch.setattr(code_execution, "get_variables", lambda: [])
    monkeypatch.setattr(code_execution, "create_cid_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(server_lookup, "get_server_by_name", lambda name: None)

    from server_execution import invocation_tracking

    monkeypatch.setattr(invocation_tracking, "create_server_invocation_record", lambda *args, **kwargs: None)

    def simple_success(output, content_type, server_name):  # pylint: disable=unused-argument
        return Response(output, mimetype=content_type or "text/html")

    monkeypatch.setattr(code_execution, "_handle_successful_execution", simple_success)


@pytest.fixture()
def cid_registry(monkeypatch):
    registry: dict[str, bytes] = {}

    def fake_get_cid_by_path(path):
        payload = registry.get(path)
        if payload is None:
            return None
        return SimpleNamespace(file_data=payload)

    monkeypatch.setattr(code_execution, "get_cid_by_path", fake_get_cid_by_path)
    return registry


def test_try_server_execution_runs_python_literal(cid_registry):
    python_cid = "pycid123"
    cid_registry[f"/{python_cid}"] = b"""\
def main():
    return {"output": "python-literal", "content_type": "text/plain"}
"""

    with app.test_request_context(f"/{python_cid}.py/trailing-segment"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/trailing-segment"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True) == "python-literal"


def test_try_server_execution_runs_bash_literal(cid_registry):
    bash_cid = "bashcid1"
    cid_registry[f"/{bash_cid}"] = b"echo bash-literal"

    with app.test_request_context(f"/{bash_cid}.sh/extra"):
        response = server_execution.try_server_execution(f"/{bash_cid}.sh/extra")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash-literal"


def test_chaining_python_output_to_bash_literal(cid_registry):
    bash_cid = "bashchain"
    python_cid = "pychain"

    cid_registry[f"/{bash_cid}"] = textwrap.dedent(
        """
        python -c 'import json,sys; data=json.load(sys.stdin); print(f"bash:{data.get(\"input\",\"\")}" )'
        """
    ).encode("utf-8")
    cid_registry[f"/{python_cid}"] = b"""\
def main():
    return {"output": "python-output", "content_type": "text/plain"}
"""

    with app.test_request_context(f"/{bash_cid}.sh/{python_cid}.py/next"):
        response = server_execution.try_server_execution(
            f"/{bash_cid}.sh/{python_cid}.py/next"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash:python-output"


def test_chaining_bash_output_to_python_literal(cid_registry):
    bash_cid = "bashpayload"
    python_cid = "pypayload"

    cid_registry[f"/{bash_cid}"] = b"echo bash-to-python"
    cid_registry[f"/{python_cid}"] = b"""\
def main(payload):
    return {"output": f"python:{payload}", "content_type": "text/plain"}
"""

    with app.test_request_context(f"/{python_cid}.py/{bash_cid}.sh/final"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{bash_cid}.sh/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "python:bash-to-python"
