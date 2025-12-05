"""Behavior for executing server literals defined by CID path segments."""

import textwrap

import pytest
from flask import Response

from cid_core import generate_cid
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
    monkeypatch.setattr(code_execution, "get_cid_by_path", lambda path: None)
    monkeypatch.setattr(server_lookup, "get_server_by_name", lambda name: None)

    from server_execution import invocation_tracking

    monkeypatch.setattr(invocation_tracking, "create_server_invocation_record", lambda *args, **kwargs: None)

    def simple_success(output, content_type, server_name):  # pylint: disable=unused-argument
        return Response(output, mimetype=content_type or "text/html")

    monkeypatch.setattr(code_execution, "_handle_successful_execution", simple_success)

def test_try_server_execution_runs_python_literal(monkeypatch):
    python_literal = """\
def main():
    return {'output':'python-literal'}
"""
    python_cid = generate_cid(python_literal.encode("utf-8"))

    with app.test_request_context(f"/{python_cid}.py/trailing-segment"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/trailing-segment"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True) == "python-literal"


def test_try_server_execution_runs_bash_literal(monkeypatch):
    bash_literal = "#!/bin/bash\necho bash-literal\n"
    bash_cid = generate_cid(bash_literal.encode("utf-8"))

    with app.test_request_context(f"/{bash_cid}.sh/extra"):
        response = server_execution.try_server_execution(f"/{bash_cid}.sh/extra")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash-literal"


def test_chaining_python_output_to_bash_literal(monkeypatch):
    bash_literal = "#!/bin/bash\nread data\necho bash:$data\n"
    bash_cid = generate_cid(bash_literal.encode("utf-8"))

    python_literal = """\
def main():
    return {'output': 'python-output'}
"""
    python_cid = generate_cid(python_literal.encode("utf-8"))

    with app.test_request_context(f"/{bash_cid}.sh/{python_cid}.py/next"):
        response = server_execution.try_server_execution(
            f"/{bash_cid}.sh/{python_cid}.py/next"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash:python-output"


def test_chaining_bash_output_to_python_literal(monkeypatch):
    bash_literal = "#!/bin/bash\necho bash-to-python\n"
    bash_cid = generate_cid(bash_literal.encode("utf-8"))

    python_literal = """\
def main(payload):
    return {'output': f'python:{payload}'}
"""
    python_cid = generate_cid(python_literal.encode("utf-8"))

    with app.test_request_context(f"/{python_cid}.py/{bash_cid}.sh/final"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{bash_cid}.sh/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "python:bash-to-python"


def test_python_literal_receives_path_parameter_from_chained_literal(monkeypatch):
    python_literal = """\
def main(name):
    return {'output': f'param:{name}'}
"""
    python_cid = generate_cid(python_literal.encode("utf-8"))

    bash_cid = generate_cid(b"#!/bin/bash\necho alex\n")

    with app.test_request_context(f"/{python_cid}.py/{bash_cid}.sh/final"):
        response = server_execution.try_server_execution(
            f"/{python_cid}.py/{bash_cid}.sh/final"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "param:alex"


def test_literal_chain_streams_nested_output_to_leftmost_server(monkeypatch):
    """Chained literal CIDs should stream only output into the left server."""

    grep_cid = "AAAAAAAJZ3JlcCBzaG9l"
    echo_cid = "AAAAAAAdZWNobyAiMSBmdW4gXG4yIHNob2VcbjMgdHJlZSI"
    empty_cid = "AAAAAAAA"

    with app.test_request_context(f"/{grep_cid}/{echo_cid}/{empty_cid}"):
        response = server_execution.try_server_execution(
            f"/{grep_cid}/{echo_cid}/{empty_cid}"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "2 shoe"


def test_literal_chain_ignores_mime_wrapper_between_servers(monkeypatch):
    """Ensure literal servers forward only the nested output value when chaining."""

    grep_cid = "AAAAAAAJZ3JlcCBzaG9l"
    payload_cid = "AAAAAAAicmVkYmlyZApibGFja2JpcmQKZnJlZGJpcmQKZ3Vtc2hvZQ"

    with app.test_request_context(f"/{grep_cid}/{payload_cid}"):
        response = server_execution.try_server_execution(f"/{grep_cid}/{payload_cid}")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "gumshoe"


def test_chained_literal_cids_return_grep_match(monkeypatch):
    """Chaining literal CIDs should mirror bash piping semantics for grep/echo."""

    grep_shoe = "AAAAAAAJZ3JlcCBzaG9l"
    echo_numbers = "AAAAAAAdZWNobyAiMSBmdW4gXG4yIHNob2VcbjMgdHJlZSI"
    empty_literal = "AAAAAAAA"

    with app.test_request_context(f"/{grep_shoe}/{echo_numbers}/{empty_literal}"):
        response = server_execution.try_server_execution(
            f"/{grep_shoe}/{echo_numbers}/{empty_literal}"
        )

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "2 shoe"


def test_literal_cids_default_to_literal_when_not_last(monkeypatch):
    """Non-terminal CIDs should be treated as literal servers and chained."""

    grep_shoe = "AAAAAAAJZ3JlcCBzaG9l"
    payload_cid = "AAAAAAAicmVkYmlyZApibGFja2JpcmQKZnJlZGJpcmQKZ3Vtc2hvZQ"

    with app.test_request_context(f"/{grep_shoe}/{payload_cid}"):
        response = server_execution.try_server_execution(f"/{grep_shoe}/{payload_cid}")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "gumshoe"
