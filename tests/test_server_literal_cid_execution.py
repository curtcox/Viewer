"""Behavior for executing server literals defined by CID path segments."""

from flask import Response

from cid_core import generate_cid
import server_execution
from app import app


def test_try_server_execution_runs_python_literal():
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
    assert response.status_code == 302

    client = app.test_client()
    final_response = client.get(response.location, follow_redirects=True)
    assert final_response.get_data(as_text=True) == "python-literal"


def test_try_server_execution_runs_bash_literal():
    bash_literal = "#!/bin/bash\necho bash-literal\n"
    bash_cid = generate_cid(bash_literal.encode("utf-8"))

    with app.test_request_context(f"/{bash_cid}.sh/extra"):
        response = server_execution.try_server_execution(f"/{bash_cid}.sh/extra")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "bash-literal"


def test_chaining_python_output_to_bash_literal():
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


def test_chaining_bash_output_to_python_literal():
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
    assert response.status_code == 302

    client = app.test_client()
    final_response = client.get(response.location, follow_redirects=True)
    assert final_response.get_data(as_text=True).strip() == "python:bash-to-python"


def test_python_literal_receives_path_parameter_from_chained_literal():
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
    assert response.status_code == 302

    client = app.test_client()
    final_response = client.get(response.location, follow_redirects=True)
    assert final_response.get_data(as_text=True).strip() == "param:alex"


def test_literal_chain_streams_nested_output_to_leftmost_server():
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


def test_literal_chain_ignores_mime_wrapper_between_servers():
    """Ensure literal servers forward only the nested output value when chaining."""

    grep_cid = "AAAAAAAJZ3JlcCBzaG9l"
    payload_cid = "AAAAAAAicmVkYmlyZApibGFja2JpcmQKZnJlZGJpcmQKZ3Vtc2hvZQ"

    with app.test_request_context(f"/{grep_cid}/{payload_cid}"):
        response = server_execution.try_server_execution(f"/{grep_cid}/{payload_cid}")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "gumshoe"


def test_chained_literal_cids_return_grep_match():
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


def test_literal_cids_default_to_literal_when_not_last():
    """Non-terminal CIDs should be treated as literal servers and chained."""

    grep_shoe = "AAAAAAAJZ3JlcCBzaG9l"
    payload_cid = "AAAAAAAicmVkYmlyZApibGFja2JpcmQKZnJlZGJpcmQKZ3Vtc2hvZQ"

    with app.test_request_context(f"/{grep_shoe}/{payload_cid}"):
        response = server_execution.try_server_execution(f"/{grep_shoe}/{payload_cid}")

    assert isinstance(response, Response)
    assert response.get_data(as_text=True).strip() == "gumshoe"
