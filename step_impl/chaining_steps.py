"""Step implementations for server command chaining specs."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from getgauge.python import step

from cid_utils import generate_cid
from database import db
from models import CID, Server
from step_impl.shared_app import get_shared_app, get_shared_client
from step_impl.shared_state import get_scenario_state


def _store_server(name: str, definition: str) -> None:
    """Persist a server definition."""
    app = get_shared_app()
    normalized = textwrap.dedent(definition).strip() + "\n"
    with app.app_context():
        existing = Server.query.filter_by(name=name).first()
        if existing:
            existing.definition = normalized
        else:
            db.session.add(Server(name=name, definition=normalized, enabled=True))
        db.session.commit()


def _store_cid(content: bytes) -> str:
    """Store content as a CID and return the CID value."""
    app = get_shared_app()
    cid_value = generate_cid(content)

    with app.app_context():
        existing = CID.query.filter_by(path=f"/{cid_value}").first()
        if not existing:
            db.session.add(CID(path=f"/{cid_value}", file_data=content))
            db.session.commit()

    return cid_value


def _resolve_cid_content(location: str) -> Optional[str]:
    """Retrieve CID content from a redirect location."""
    app = get_shared_app()
    raw_path = urlsplit(location).path or location

    candidates = [raw_path]
    if "." in raw_path:
        candidates.append(raw_path.split(".", 1)[0])

    with app.app_context():
        for candidate in candidates:
            record = CID.query.filter_by(path=candidate).first()
            if record is not None:
                return record.file_data.decode("utf-8")

    return None


def _save_language_cid(
    language: str, code: str, *, keys: list[str], extension: str | None
) -> str:
    """Persist a CID containing source code for the requested language."""

    cid_value = _store_cid(code.encode("utf-8"))
    state = get_scenario_state()
    for key in keys:
        state[key] = cid_value
        if extension:
            state[f"{key}_path"] = f"{cid_value}.{extension}"

    state["last_cid"] = cid_value

    return cid_value


@step(['Given a server named "<server_name>" that echoes its input with prefix "<prefix>"',
       'And a server named "<server_name>" that echoes its input with prefix "<prefix>"'])
def given_echo_server(server_name: str, prefix: str) -> None:
    """Create a server that echoes input with a prefix."""
    definition = f'''
def main(input_data):
    return {{"output": f"{prefix}{{input_data}}", "content_type": "text/plain"}}
'''
    _store_server(server_name, definition)


@step(['Given a server named "<server_name>" that returns "<value>"',
       'And a server named "<server_name>" that returns "<value>"'])
def given_simple_server(server_name: str, value: str) -> None:
    """Create a server that returns a fixed value."""
    definition = f'''
def main():
    return {{"output": "{value}", "content_type": "text/plain"}}
'''
    _store_server(server_name, definition)


@step('And a CID containing "<content>"')
def and_cid_containing(content: str) -> None:
    """Store a CID with the given content."""
    state = get_scenario_state()
    cid_value = _store_cid(content.encode("utf-8"))
    state["last_cid"] = cid_value


@step("When I request the processor server with the stored CID")
def when_request_processor_cid() -> None:
    """Request the chained processor/CID resource."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored. Call 'And a CID containing' first."

    client = get_shared_client()
    response = client.get(f"/processor/{cid_value}")
    state["response"] = response


@step("When I request the chained resource /second/first")
def when_request_second_first() -> None:
    """Request the chained second/first resource."""
    client = get_shared_client()
    state = get_scenario_state()
    response = client.get("/second/first")
    state["response"] = response


@step("When I request the level2/level1 servers with the stored CID")
def when_request_level2_level1_cid() -> None:
    """Request the three-level chained resource."""
    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored. Call 'And a CID containing' first."

    client = get_shared_client()
    response = client.get(f"/level2/level1/{cid_value}")
    state["response"] = response


@step("Then the response should redirect to a CID")
def then_response_redirects() -> None:
    """Assert the response is a redirect to a CID."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    assert response.status_code in {302, 303}, (
        f"Expected redirect status but got {response.status_code}"
    )
    location = response.headers.get("Location")
    assert location, "Redirect response missing Location header"
    state["redirect_location"] = location


@step('And the CID content should be "<expected_content>"')
def and_cid_content_should_be(expected_content: str) -> None:
    """Assert the CID content matches the expected value."""
    state = get_scenario_state()
    location = state.get("redirect_location")
    assert location, "No redirect location recorded."

    content = _resolve_cid_content(location)
    assert content is not None, f"Could not resolve CID content for {location}"
    assert content == expected_content, (
        f"Expected CID content '{expected_content}' but got '{content}'"
    )


@step('Given the default server "<server_name>" is available')
def given_default_server_available(server_name: str) -> None:
    """Load a default server definition from reference templates."""

    definition_path = (
        Path("reference_templates") / "servers" / "definitions" / f"{server_name}.py"
    )
    assert definition_path.exists(), f"Default server {server_name} not found"

    _store_server(server_name, definition_path.read_text(encoding="utf-8"))


@step('And a wrapping server named "<server_name>" that wraps payload with "<prefix>"')
def and_wrapping_server(server_name: str, prefix: str) -> None:
    """Create a wrapper server that prefixes chained payloads."""

    definition = f'''
def main(payload):
    return {{"output": f"{prefix}{{payload}}", "content_type": "text/plain"}}
'''
    _store_server(server_name, definition)


@step('When I request the resource /<path_prefix>/{stored CID}')
def when_request_resource_with_cid(path_prefix: str) -> None:
    """Request a chained resource using the stored CID."""

    state = get_scenario_state()
    cid_value = state.get("last_cid")
    assert cid_value, "No CID stored. Call 'And a CID containing' first."

    normalized = path_prefix.strip("/")
    request_path = f"/{normalized}/{cid_value}"

    client = get_shared_client()
    response = client.get(request_path)
    state["response"] = response


@step([
    'Then the CID content should contain "<expected_content>"',
    'And the CID content should contain "<expected_content>"',
])
def then_cid_content_contains(expected_content: str) -> None:
    """Assert the CID content includes the expected substring."""

    state = get_scenario_state()
    location = state.get("redirect_location")
    assert location, "No redirect location recorded."

    content = _resolve_cid_content(location)
    assert content is not None, f"Could not resolve CID content for {location}"
    assert expected_content in content, (
        f"Expected CID content to include '{expected_content}' but got '{content}'"
    )


@step('Given a CID containing python server code that returns "<output>"')
def given_python_cid_literal(output: str) -> None:
    """Store a Python CID literal server that returns a constant output."""

    definition = f'''def main(payload=None):
    return {{"output": "{output}", "content_type": "text/plain"}}
'''
    _save_language_cid(
        "python", textwrap.dedent(definition).strip() + "\n", keys=["python server CID"], extension="py"
    )


@step('Given a CID containing bash server code that echoes "<output>"')
def given_bash_cid_literal(output: str) -> None:
    """Store a Bash CID literal server that echoes a value."""

    script = f"""#!/bin/bash
echo "{output}"
"""
    _save_language_cid("bash", script, keys=["bash server CID"], extension="sh")


@step([
    'Given a python CID literal server that returns "<output>"',
    'And a python CID literal server that returns "<output>"',
])
def python_literal_server(output: str) -> None:
    """Persist a Python CID server for chaining checks."""

    definition = f'''def main(payload=None):
    return {{"output": "{output}", "content_type": "text/plain"}}
'''
    _save_language_cid(
        "python", textwrap.dedent(definition).strip() + "\n", keys=["python server CID"], extension="py"
    )


@step([
    'Given a python CID literal server that prefixes its payload with "<prefix>"',
    'And a python CID literal server that prefixes its payload with "<prefix>"',
])
def python_literal_prefix(prefix: str) -> None:
    """Persist a Python CID server that prefixes chained payloads."""

    definition = f'''def main(payload=None):
    payload = "" if payload is None else payload
    return {{"output": f"{prefix}{{payload}}", "content_type": "text/plain"}}
'''
    _save_language_cid(
        "python", textwrap.dedent(definition).strip() + "\n", keys=["python server CID"], extension="py"
    )


@step([
    'Given a python CID literal server that wraps its payload with "<prefix>"',
    'And a python CID literal server that wraps its payload with "<prefix>"',
])
def python_literal_wrap(prefix: str) -> None:
    """Persist a Python CID server that wraps chained payloads."""

    definition = f'''def main(payload=None):
    payload = "" if payload is None else payload
    return {{"output": f"{prefix}{{payload}}", "content_type": "text/plain"}}
'''
    _save_language_cid(
        "python", textwrap.dedent(definition).strip() + "\n", keys=["python server CID"], extension="py"
    )


@step([
    'Given a bash CID literal server that prefixes input with "<prefix>"',
    'And a bash CID literal server that prefixes input with "<prefix>"',
    'Given a bash CID literal server that prefixes its payload with "<prefix>"',
    'And a bash CID literal server that prefixes its payload with "<prefix>"',
])
def bash_literal_prefix(prefix: str) -> None:
    """Persist a Bash CID server that prefixes its input payload."""

    script = f"""#!/bin/bash
read input_payload
echo "{prefix}${{input_payload}}"
"""
    _save_language_cid("bash", script, keys=["bash server CID"], extension="sh")


@step([
    'Given a bash CID literal server that echoes "<output>"',
    'And a bash CID literal server that echoes "<output>"',
])
def bash_literal_echo(output: str) -> None:
    """Persist a Bash CID server that echoes a constant string."""

    script = f"""#!/bin/bash
echo "{output}"
"""
    _save_language_cid("bash", script, keys=["bash server CID"], extension="sh")


@step([
    'Given a clojure CID literal server that emits "<output>"',
    'And a clojure CID literal server that emits "<output>"',
])
def clojure_literal_emit(output: str) -> None:
    """Persist a Clojure CID server with stubbed output."""

    script = f""";; OUTPUT: {output}
(ns cid.literal)
(defn -main [] (println "{output}"))
"""
    _save_language_cid(
        "clojure", script, keys=["clojure server CID", "right clojure server CID"], extension="clj"
    )


@step([
    'Given a clojure CID literal server that prefixes its payload with "<prefix>"',
    'And a clojure CID literal server that prefixes its payload with "<prefix>"',
])
def clojure_literal_prefix(prefix: str) -> None:
    """Persist a Clojure CID server that prefixes chained payloads."""

    script = f""";; OUTPUT: {prefix}$PAYLOAD
(ns cid.literal)
(defn -main [] (let [payload (slurp *in*)] (println (str "{prefix}" payload))))
"""
    _save_language_cid(
        "clojure", script, keys=["clojure server CID", "left clojure server CID"], extension="clj"
    )


@step('Given a clojure CID literal server stored without an extension that emits "<output>"')
def clojure_literal_no_extension(output: str) -> None:
    """Persist a Clojure CID server without a file extension."""

    script = f""";; OUTPUT: {output}
(defn -main [] (println "{output}"))
"""
    _save_language_cid("clojure", script, keys=["clojure CID"], extension=None)


@step([
    'Given a clojurescript CID literal server that emits "<output>"',
    'And a clojurescript CID literal server that emits "<output>"',
])
def clojurescript_literal_emit(output: str) -> None:
    """Persist a ClojureScript CID server with stubbed output."""

    script = f""";; OUTPUT: {output}
(ns cid.literal)
(defn -main [] (println "{output}"))
"""
    _save_language_cid(
        "clojurescript",
        script,
        keys=["clojurescript server CID", "right clojurescript server CID"],
        extension="cljs",
    )


@step([
    'Given a clojurescript CID literal server that prefixes its payload with "<prefix>"',
    'And a clojurescript CID literal server that prefixes its payload with "<prefix>"',
])
def clojurescript_literal_prefix(prefix: str) -> None:
    """Persist a ClojureScript CID server that prefixes chained payloads."""

    script = f""";; OUTPUT: {prefix}$PAYLOAD
(ns cid.literal)
(defn -main [] (let [payload (slurp *in*)] (println (str "{prefix}" payload))))
"""
    _save_language_cid(
        "clojurescript",
        script,
        keys=["clojurescript server CID", "left clojurescript server CID"],
        extension="cljs",
    )


@step('Given a clojurescript CID literal server stored without an extension that emits "<output>"')
def clojurescript_literal_no_extension(output: str) -> None:
    """Persist a ClojureScript CID server without a file extension."""

    script = f""";; OUTPUT: {output}
(defn -main [] (println "{output}"))
"""
    _save_language_cid("clojurescript", script, keys=["clojurescript CID"], extension=None)


@step([
    'Given a TypeScript CID literal server that emits "<output>"',
    'And a TypeScript CID literal server that emits "<output>"',
])
def typescript_literal_emit(output: str) -> None:
    """Persist a TypeScript CID server with stubbed output."""

    script = f"""// OUTPUT: {output}
export default function main(payload) {{
  console.log("{output}");
}}
"""
    _save_language_cid(
        "typescript", script, keys=["typescript server CID", "right typescript server CID"], extension="ts"
    )


@step([
    'Given a TypeScript CID literal server that prefixes its payload with "<prefix>"',
    'And a TypeScript CID literal server that prefixes its payload with "<prefix>"',
])
def typescript_literal_prefix(prefix: str) -> None:
    """Persist a TypeScript CID server that prefixes payloads."""

    script = f"""// OUTPUT: {prefix}$PAYLOAD
export default function main(payload) {{
  const input = payload ?? new TextDecoder().decode(Deno.stdin.readSync(1024) ?? new Uint8Array());
  console.log(`{prefix}${{input}}`);
}}
"""
    _save_language_cid(
        "typescript", script, keys=["typescript server CID", "left typescript server CID"], extension="ts"
    )


@step('Given a TypeScript CID literal server stored without an extension that emits "<output>"')
def typescript_literal_no_extension(output: str) -> None:
    """Persist a TypeScript CID server without a file extension."""

    script = f"""// OUTPUT: {output}
export default function main() {{
  console.log("{output}");
}}
"""
    _save_language_cid("typescript", script, keys=["typescript CID"], extension=None)


@step('Given a TypeScript CID literal server stored with a .ts extension that emits "<output>"')
def typescript_literal_with_extension(output: str) -> None:
    """Persist a TypeScript CID server with an explicit .ts extension."""

    script = f"""// OUTPUT: {output}
export default function main() {{
  console.log("{output}");
}}
"""
    _save_language_cid("typescript", script, keys=["typescript CID"], extension="ts")


@step(
    'Given a server named "<server_name>" defined in /servers that prefixes its payload with "<prefix>"'
)
def given_named_prefixed_server(server_name: str, prefix: str) -> None:
    """Create a named server that prefixes payload with the provided prefix."""

    definition = f"""// OUTPUT: {prefix}$PAYLOAD
export default function main(payload) {{
  const input = payload ?? new TextDecoder().decode(Deno.stdin.readSync(1024) ?? new Uint8Array());
  return {{"output": `{prefix}${{input}}`, "content_type": "text/plain"}};
}}
"""
    _store_server(server_name, definition)


def _substitute_placeholders(path: str) -> str:
    """Replace CID placeholders in a path with actual stored CID values."""
    state = get_scenario_state()
    result = path

    # Replace all {key} placeholders with values from state
    for key, value in state.items():
        if not isinstance(value, str):
            continue
        placeholder = f"{{{key}}}"
        result = result.replace(placeholder, value)

    return result


def _request_path_and_store_response(path: str) -> None:
    """Make a GET request to the path and store the response in scenario state."""
    client = get_shared_client()
    state = get_scenario_state()

    # Substitute placeholders with actual CID values
    resolved_path = _substitute_placeholders(path)

    response = client.get(resolved_path)
    state["response"] = response


@step('When I request the resource /{stored CID}.py/<suffix>')
def when_request_python_cid_literal(suffix: str) -> None:
    """Request a Python CID literal server with a suffix."""
    state = get_scenario_state()
    cid_value = state.get("last_cid") or state.get("python server CID")
    assert cid_value, "No Python CID stored."

    _request_path_and_store_response(f"/{cid_value}.py/{suffix}")


@step('When I request the resource /{stored CID}.sh/<suffix>')
def when_request_bash_cid_literal(suffix: str) -> None:
    """Request a Bash CID literal server with a suffix."""
    state = get_scenario_state()
    cid_value = state.get("last_cid") or state.get("bash server CID")
    assert cid_value, "No Bash CID stored."

    _request_path_and_store_response(f"/{cid_value}.sh/{suffix}")


@step('When I request the resource /{bash server CID}.sh/{python server CID}.py/<suffix>')
def when_request_bash_then_python(suffix: str) -> None:
    """Request bash CID chained into python CID."""
    state = get_scenario_state()
    bash_cid = state.get("bash server CID")
    python_cid = state.get("python server CID")
    assert bash_cid, "No Bash CID stored."
    assert python_cid, "No Python CID stored."

    _request_path_and_store_response(f"/{bash_cid}.sh/{python_cid}.py/{suffix}")


@step('When I request the resource /{python server CID}.py/{bash server CID}.sh/<suffix>')
def when_request_python_then_bash(suffix: str) -> None:
    """Request python CID chained into bash CID."""
    state = get_scenario_state()
    python_cid = state.get("python server CID")
    bash_cid = state.get("bash server CID")
    assert python_cid, "No Python CID stored."
    assert bash_cid, "No Bash CID stored."

    _request_path_and_store_response(f"/{python_cid}.py/{bash_cid}.sh/{suffix}")


@step('When I request the resource /{python server CID}.py/{clojure server CID}.clj/<suffix>')
def when_request_python_then_clojure(suffix: str) -> None:
    """Request python CID chained into clojure CID."""
    state = get_scenario_state()
    python_cid = state.get("python server CID")
    clojure_cid = state.get("clojure server CID")
    assert python_cid, "No Python CID stored."
    assert clojure_cid, "No Clojure CID stored."

    _request_path_and_store_response(f"/{python_cid}.py/{clojure_cid}.clj/{suffix}")


@step('When I request the resource /{bash server CID}.sh/{clojure server CID}.clj/<suffix>')
def when_request_bash_then_clojure(suffix: str) -> None:
    """Request bash CID chained into clojure CID."""
    state = get_scenario_state()
    bash_cid = state.get("bash server CID")
    clojure_cid = state.get("clojure server CID")
    assert bash_cid, "No Bash CID stored."
    assert clojure_cid, "No Clojure CID stored."

    _request_path_and_store_response(f"/{bash_cid}.sh/{clojure_cid}.clj/{suffix}")


@step('When I request the resource /{clojure server CID}.clj/{bash server CID}.sh')
def when_request_clojure_then_bash() -> None:
    """Request clojure CID chained into bash CID."""
    state = get_scenario_state()
    clojure_cid = state.get("clojure server CID") or state.get("left clojure server CID")
    bash_cid = state.get("bash server CID")
    assert clojure_cid, "No Clojure CID stored."
    assert bash_cid, "No Bash CID stored."

    _request_path_and_store_response(f"/{clojure_cid}.clj/{bash_cid}.sh")


@step('When I request the resource /{clojure server CID}.clj/{python server CID}.py')
def when_request_clojure_then_python() -> None:
    """Request clojure CID chained into python CID."""
    state = get_scenario_state()
    clojure_cid = state.get("clojure server CID") or state.get("left clojure server CID")
    python_cid = state.get("python server CID")
    assert clojure_cid, "No Clojure CID stored."
    assert python_cid, "No Python CID stored."

    _request_path_and_store_response(f"/{clojure_cid}.clj/{python_cid}.py")


@step('When I request the resource /{left clojure server CID}.clj/{right clojure server CID}.clj')
def when_request_clojure_chain() -> None:
    """Request left clojure CID chained into right clojure CID."""
    state = get_scenario_state()
    left_cid = state.get("left clojure server CID")
    right_cid = state.get("right clojure server CID")
    assert left_cid, "No left Clojure CID stored."
    assert right_cid, "No right Clojure CID stored."

    _request_path_and_store_response(f"/{left_cid}.clj/{right_cid}.clj")


@step('When I request the resource /{clojure CID}/<suffix>')
def when_request_clojure_no_ext(suffix: str) -> None:
    """Request a clojure CID without extension."""
    state = get_scenario_state()
    cid_value = state.get("clojure CID")
    assert cid_value, "No Clojure CID stored."

    _request_path_and_store_response(f"/{cid_value}/{suffix}")


@step('When I request the resource /{python server CID}.py/{clojurescript server CID}.cljs/<suffix>')
def when_request_python_then_clojurescript(suffix: str) -> None:
    """Request python CID chained into clojurescript CID."""
    state = get_scenario_state()
    python_cid = state.get("python server CID")
    cljs_cid = state.get("clojurescript server CID")
    assert python_cid, "No Python CID stored."
    assert cljs_cid, "No ClojureScript CID stored."

    _request_path_and_store_response(f"/{python_cid}.py/{cljs_cid}.cljs/{suffix}")


@step('When I request the resource /{bash server CID}.sh/{clojurescript server CID}.cljs/<suffix>')
def when_request_bash_then_clojurescript(suffix: str) -> None:
    """Request bash CID chained into clojurescript CID."""
    state = get_scenario_state()
    bash_cid = state.get("bash server CID")
    cljs_cid = state.get("clojurescript server CID")
    assert bash_cid, "No Bash CID stored."
    assert cljs_cid, "No ClojureScript CID stored."

    _request_path_and_store_response(f"/{bash_cid}.sh/{cljs_cid}.cljs/{suffix}")


@step('When I request the resource /{left clojurescript server CID}.cljs/{right clojurescript server CID}.cljs')
def when_request_clojurescript_chain() -> None:
    """Request left clojurescript CID chained into right clojurescript CID."""
    state = get_scenario_state()
    left_cid = state.get("left clojurescript server CID")
    right_cid = state.get("right clojurescript server CID")
    assert left_cid, "No left ClojureScript CID stored."
    assert right_cid, "No right ClojureScript CID stored."

    _request_path_and_store_response(f"/{left_cid}.cljs/{right_cid}.cljs")


@step('When I request the resource /{clojurescript server CID}.cljs/{python server CID}.py')
def when_request_clojurescript_then_python() -> None:
    """Request clojurescript CID chained into python CID."""
    state = get_scenario_state()
    cljs_cid = state.get("clojurescript server CID") or state.get("left clojurescript server CID")
    python_cid = state.get("python server CID")
    assert cljs_cid, "No ClojureScript CID stored."
    assert python_cid, "No Python CID stored."

    _request_path_and_store_response(f"/{cljs_cid}.cljs/{python_cid}.py")


@step('When I request the resource /{clojurescript server CID}.cljs/{bash server CID}.sh')
def when_request_clojurescript_then_bash() -> None:
    """Request clojurescript CID chained into bash CID."""
    state = get_scenario_state()
    cljs_cid = state.get("clojurescript server CID") or state.get("left clojurescript server CID")
    bash_cid = state.get("bash server CID")
    assert cljs_cid, "No ClojureScript CID stored."
    assert bash_cid, "No Bash CID stored."

    _request_path_and_store_response(f"/{cljs_cid}.cljs/{bash_cid}.sh")


@step('When I request the resource /cljs-chain/{python server CID}.py/<suffix>')
def when_request_cljs_chain_python(suffix: str) -> None:
    """Request named cljs-chain server with python CID input."""
    state = get_scenario_state()
    python_cid = state.get("python server CID")
    assert python_cid, "No Python CID stored."

    _request_path_and_store_response(f"/cljs-chain/{python_cid}.py/{suffix}")


@step('When I request the resource /{clojurescript CID}/<suffix>')
def when_request_clojurescript_no_ext(suffix: str) -> None:
    """Request a clojurescript CID without extension."""
    state = get_scenario_state()
    cid_value = state.get("clojurescript CID")
    assert cid_value, "No ClojureScript CID stored."

    _request_path_and_store_response(f"/{cid_value}/{suffix}")


@step('When I request the resource /{python server CID}.py/{typescript server CID}.ts/<suffix>')
def when_request_python_then_typescript(suffix: str) -> None:
    """Request python CID chained into typescript CID."""
    state = get_scenario_state()
    python_cid = state.get("python server CID")
    ts_cid = state.get("typescript server CID")
    assert python_cid, "No Python CID stored."
    assert ts_cid, "No TypeScript CID stored."

    _request_path_and_store_response(f"/{python_cid}.py/{ts_cid}.ts/{suffix}")


@step('When I request the resource /{bash server CID}.sh/{typescript server CID}.ts/<suffix>')
def when_request_bash_then_typescript(suffix: str) -> None:
    """Request bash CID chained into typescript CID."""
    state = get_scenario_state()
    bash_cid = state.get("bash server CID")
    ts_cid = state.get("typescript server CID")
    assert bash_cid, "No Bash CID stored."
    assert ts_cid, "No TypeScript CID stored."

    _request_path_and_store_response(f"/{bash_cid}.sh/{ts_cid}.ts/{suffix}")


@step('When I request the resource /{left typescript server CID}.ts/{right typescript server CID}.ts')
def when_request_typescript_chain() -> None:
    """Request left typescript CID chained into right typescript CID."""
    state = get_scenario_state()
    left_cid = state.get("left typescript server CID")
    right_cid = state.get("right typescript server CID")
    assert left_cid, "No left TypeScript CID stored."
    assert right_cid, "No right TypeScript CID stored."

    _request_path_and_store_response(f"/{left_cid}.ts/{right_cid}.ts")


@step('When I request the resource /{typescript server CID}.ts/{python server CID}.py')
def when_request_typescript_then_python() -> None:
    """Request typescript CID chained into python CID."""
    state = get_scenario_state()
    ts_cid = state.get("typescript server CID") or state.get("left typescript server CID")
    python_cid = state.get("python server CID")
    assert ts_cid, "No TypeScript CID stored."
    assert python_cid, "No Python CID stored."

    _request_path_and_store_response(f"/{ts_cid}.ts/{python_cid}.py")


@step('When I request the resource /{typescript server CID}.ts/{bash server CID}.sh')
def when_request_typescript_then_bash() -> None:
    """Request typescript CID chained into bash CID."""
    state = get_scenario_state()
    ts_cid = state.get("typescript server CID") or state.get("left typescript server CID")
    bash_cid = state.get("bash server CID")
    assert ts_cid, "No TypeScript CID stored."
    assert bash_cid, "No Bash CID stored."

    _request_path_and_store_response(f"/{ts_cid}.ts/{bash_cid}.sh")


@step('When I request the resource /ts-chain/{python server CID}.py/<suffix>')
def when_request_ts_chain_python(suffix: str) -> None:
    """Request named ts-chain server with python CID input."""
    state = get_scenario_state()
    python_cid = state.get("python server CID")
    assert python_cid, "No Python CID stored."

    _request_path_and_store_response(f"/ts-chain/{python_cid}.py/{suffix}")


@step('When I request the resource /{typescript CID}/<suffix>')
def when_request_typescript_no_ext(suffix: str) -> None:
    """Request a typescript CID without extension."""
    state = get_scenario_state()
    cid_value = state.get("typescript CID")
    assert cid_value, "No TypeScript CID stored."

    _request_path_and_store_response(f"/{cid_value}/{suffix}")


@step('When I request the resource /{typescript CID}.ts/<suffix>')
def when_request_typescript_with_ext(suffix: str) -> None:
    """Request a typescript CID with .ts extension."""
    state = get_scenario_state()
    cid_value = state.get("typescript CID")
    assert cid_value, "No TypeScript CID stored."

    _request_path_and_store_response(f"/{cid_value}.ts/{suffix}")


@step('Given a python CID literal server that wraps its payload with "<prefix>"')
def python_literal_wraps_payload(prefix: str) -> None:
    """Persist a Python CID server that wraps its input payload."""

    definition = f'''def main(payload=None):
    return {{"output": "{prefix}" + str(payload or ""), "content_type": "text/plain"}}
'''
    _save_language_cid(
        "python", textwrap.dedent(definition).strip() + "\n", keys=["python server CID"], extension="py"
    )


@step('Given a python CID literal server that prefixes its payload with "<prefix>"')
def python_literal_prefix_payload(prefix: str) -> None:
    """Persist a Python CID server that prefixes its input payload."""

    definition = f'''def main(payload=None):
    return {{"output": "{prefix}" + str(payload or ""), "content_type": "text/plain"}}
'''
    _save_language_cid(
        "python", textwrap.dedent(definition).strip() + "\n", keys=["python server CID"], extension="py"
    )


@step('Given a bash CID literal server that prefixes its payload with "<prefix>"')
def bash_literal_prefixes_payload(prefix: str) -> None:
    """Persist a Bash CID server that prefixes its payload."""

    script = f"""#!/bin/bash
read input_payload
echo "{prefix}${{input_payload}}"
"""
    _save_language_cid("bash", script, keys=["bash server CID"], extension="sh")


# Response assertion steps for server command chaining
@step('Then the response should contain "literal-bash"')
def then_response_contains_literal_bash() -> None:
    """Assert response contains literal-bash."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "literal-bash" in body, "Expected 'literal-bash' in response body"


@step('Then the response should contain "bash:py-literal"')
def then_response_contains_bash_py_literal() -> None:
    """Assert response contains bash:py-literal."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "bash:py-literal" in body, "Expected 'bash:py-literal' in response body"


@step('Then the response should contain "bash:clj->bash"')
def then_response_contains_bash_clj_bash() -> None:
    """Assert response contains bash:clj->bash."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "bash:clj->bash" in body, "Expected 'bash:clj->bash' in response body"


@step('Then the response should contain "clj:bash->clj"')
def then_response_contains_clj_bash_clj() -> None:
    """Assert response contains clj:bash->clj."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "clj:bash->clj" in body, "Expected 'clj:bash->clj' in response body"


@step('Then the response should contain "clj:py->clj"')
def then_response_contains_clj_py_clj() -> None:
    """Assert response contains clj:py->clj."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "clj:py->clj" in body, "Expected 'clj:py->clj' in response body"


@step('Then the response should contain "clj:clj-right"')
def then_response_contains_clj_clj_right() -> None:
    """Assert response contains clj:clj-right."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "clj:clj-right" in body, "Expected 'clj:clj-right' in response body"


@step('Then the response should contain "clj-noext"')
def then_response_contains_clj_noext() -> None:
    """Assert response contains clj-noext."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "clj-noext" in body, "Expected 'clj-noext' in response body"


@step('Then the response should contain "bash:cljs->bash"')
def then_response_contains_bash_cljs_bash() -> None:
    """Assert response contains bash:cljs->bash."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "bash:cljs->bash" in body, "Expected 'bash:cljs->bash' in response body"


@step('Then the response should contain "cljs:cljs-right"')
def then_response_contains_cljs_cljs_right() -> None:
    """Assert response contains cljs:cljs-right."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "cljs:cljs-right" in body, "Expected 'cljs:cljs-right' in response body"


@step('Then the response should contain "cljs:py->cljs"')
def then_response_contains_cljs_py_cljs() -> None:
    """Assert response contains cljs:py->cljs."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "cljs:py->cljs" in body, "Expected 'cljs:py->cljs' in response body"


@step('Then the response should contain "cljs:bash->cljs"')
def then_response_contains_cljs_bash_cljs() -> None:
    """Assert response contains cljs:bash->cljs."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "cljs:bash->cljs" in body, "Expected 'cljs:bash->cljs' in response body"


@step('Then the response should contain "cljs:named->cljs"')
def then_response_contains_cljs_named_cljs() -> None:
    """Assert response contains cljs:named->cljs."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "cljs:named->cljs" in body, "Expected 'cljs:named->cljs' in response body"


@step('Then the response should contain "cljs-noext"')
def then_response_contains_cljs_noext() -> None:
    """Assert response contains cljs-noext."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "cljs-noext" in body, "Expected 'cljs-noext' in response body"


@step('Then the response should contain "bash:ts->bash"')
def then_response_contains_bash_ts_bash() -> None:
    """Assert response contains bash:ts->bash."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "bash:ts->bash" in body, "Expected 'bash:ts->bash' in response body"


@step('Then the response should contain "ts:ts-right"')
def then_response_contains_ts_ts_right() -> None:
    """Assert response contains ts:ts-right."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "ts:ts-right" in body, "Expected 'ts:ts-right' in response body"


@step('Then the response should contain "ts:py->ts"')
def then_response_contains_ts_py_ts() -> None:
    """Assert response contains ts:py->ts."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "ts:py->ts" in body, "Expected 'ts:py->ts' in response body"


@step('Then the response should contain "ts:bash->ts"')
def then_response_contains_ts_bash_ts() -> None:
    """Assert response contains ts:bash->ts."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "ts:bash->ts" in body, "Expected 'ts:bash->ts' in response body"


@step('Then the response should contain "ts:named->ts"')
def then_response_contains_ts_named_ts() -> None:
    """Assert response contains ts:named->ts."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "ts:named->ts" in body, "Expected 'ts:named->ts' in response body"


@step('Then the response should contain "ts-noext"')
def then_response_contains_ts_noext() -> None:
    """Assert response contains ts-noext."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "ts-noext" in body, "Expected 'ts-noext' in response body"


@step('Then the response should contain "ts-ext"')
def then_response_contains_ts_ext() -> None:
    """Assert response contains ts-ext."""
    state = get_scenario_state()
    response = state.get("response")
    assert response is not None, "No response recorded."
    body = response.get_data(as_text=True)
    assert "ts-ext" in body, "Expected 'ts-ext' in response body"
