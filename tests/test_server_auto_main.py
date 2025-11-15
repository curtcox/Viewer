"""Tests for auto_main functionality in server execution."""
# pylint: disable=no-name-in-module  # False positive: server_execution submodules available via lazy loading

from pathlib import Path
from types import SimpleNamespace

import pytest

import server_execution
import reference_templates.servers as server_templates
from app import app
from reference_templates.servers import get_server_templates


@pytest.fixture(autouse=True)
def patch_execution_environment(monkeypatch):
    from server_execution import code_execution

    monkeypatch.setattr(
        code_execution,
        "_load_user_context",
        lambda: {"variables": {}, "secrets": {}, "servers": {}},
    )

    def fake_success(output, content_type, server_name):
        return {
            "output": output,
            "content_type": content_type,
            "server_name": server_name,
        }

    # Patch where _handle_successful_execution is used, not where it's defined
    monkeypatch.setattr(code_execution, "_handle_successful_execution", fake_success)


def test_auto_main_uses_query_parameters_over_other_sources():
    definition = """
 def main(name, greeting="Hello"):
     return {"output": f"{greeting}, {name}", "content_type": "text/plain"}
 """

    with app.test_request_context(
        "/welcome?name=Query&greeting=Hi",
        json={"name": "Body", "greeting": "Body"},
        headers={"Name": "Header"},
    ):
        result = server_execution.execute_server_code_from_definition(definition, "welcome")

    assert result["output"] == "Hi, Query"
    assert result["content_type"] == "text/plain"
    assert result["server_name"] == "welcome"


def test_auto_main_reads_request_body_when_query_missing():
    definition = """
 def main(topic):
     return {"output": topic, "content_type": "text/plain"}
 """

    with app.test_request_context("/topic", json={"topic": "Body topic"}):
        result = server_execution.execute_server_code_from_definition(definition, "topic")

    assert result["output"] == "Body topic"


def test_auto_main_prefers_body_over_headers():
    definition = """
 def main(token):
     return {"output": token, "content_type": "text/plain"}
 """

    with app.test_request_context(
        "/body", json={"token": "from-body"}, headers={"Token": "from-header"}
    ):
        result = server_execution.execute_server_code_from_definition(definition, "body")

    assert result["output"] == "from-body"


def test_auto_main_reads_headers_when_query_and_body_missing():
    definition = """
 def main(user_agent):
     return {"output": user_agent, "content_type": "text/plain"}
 """

    with app.test_request_context("/ua", headers={"User-Agent": "HeaderUA"}):
        result = server_execution.execute_server_code_from_definition(definition, "ua")

    assert result["output"] == "HeaderUA"


def test_auto_main_error_page_includes_debug_details():
    definition = """
 def main(name):
     raise RuntimeError(f"failure for {name}")
 """

    with app.test_request_context("/boom?name=Auto"):
        response = server_execution.execute_server_code_from_definition(definition, "boom")

    assert response.status_code == 500

    html = response.get_data(as_text=True)

    assert "failure for Auto" in html
    assert "Traceback" in html


def test_auto_main_matches_hyphenated_headers():
    definition = """
 def main(x_custom_token):
     return {"output": x_custom_token, "content_type": "text/plain"}
 """

    with app.test_request_context("/token", headers={"X-Custom-Token": "header-value"}):
        result = server_execution.execute_server_code_from_definition(definition, "token")

    assert result["output"] == "header-value"


def test_auto_main_missing_required_parameter_returns_detailed_error():
    definition = """
 def main(required_value):
     return {"output": required_value}
 """

    with app.test_request_context("/missing"):
        response = server_execution.execute_server_code_from_definition(definition, "missing")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Missing required parameters for main()"
    assert payload["missing_parameters"][0]["name"] == "required_value"
    assert payload["available_keys"]["query_string"] == []
    assert payload["available_keys"]["request_body"] == []
    assert isinstance(payload["available_keys"]["headers"], list)
    assert payload["available_keys"]["context_variables"] == []
    assert payload["available_keys"]["context_secrets"] == []


def test_auto_main_falls_back_to_context_variables(monkeypatch):
    definition = """
 def main(name):
     return {"output": name, "content_type": "text/plain"}
 """

    monkeypatch.setattr(
        server_execution.code_execution,
        "_load_user_context",
        lambda: {"variables": {"name": "Variable Name"}, "secrets": {}, "servers": {}},
    )

    with app.test_request_context("/variable"):
        result = server_execution.execute_server_code_from_definition(definition, "variable")

    assert result["output"] == "Variable Name"
    assert result["content_type"] == "text/plain"


def test_auto_main_uses_secrets_when_variables_missing(monkeypatch):
    definition = """
 def main(token):
     return {"output": token, "content_type": "text/plain"}
 """

    monkeypatch.setattr(
        server_execution.code_execution,
        "_load_user_context",
        lambda: {"variables": {}, "secrets": {"token": "secret-token"}, "servers": {}},
    )

    with app.test_request_context("/secret"):
        result = server_execution.execute_server_code_from_definition(definition, "secret")

    assert result["output"] == "secret-token"
    assert result["content_type"] == "text/plain"


def test_auto_main_honors_optional_defaults():
    definition = """
 def main(name="World"):
     return {"output": name, "content_type": "text/plain"}
 """

    with app.test_request_context("/optional"):
        result = server_execution.execute_server_code_from_definition(definition, "optional")

    assert result["output"] == "World"


def test_auto_main_supports_keyword_only_parameters():
    definition = """
 def main(*, token):
     return {"output": token, "content_type": "text/plain"}
 """

    with app.test_request_context("/kwonly", json={"token": "kw"}):
        result = server_execution.execute_server_code_from_definition(definition, "kwonly")

    assert result["output"] == "kw"


def test_auto_main_uses_nested_server_response(monkeypatch):
    outer_definition = """
 def main(message):
     return {"output": message.upper(), "content_type": "text/plain"}
 """

    inner_definition = """
 def main():
     return {"output": "nested", "content_type": "text/plain"}
 """

    servers = {
        "outer": SimpleNamespace(definition=outer_definition),
        "inner": SimpleNamespace(definition=inner_definition),
    }

    from server_execution import code_execution
    monkeypatch.setattr(
        code_execution,
        "get_server_by_name",
        lambda user_id, name: servers.get(name),
    )

    with app.test_request_context("/outer/inner"):
        result = server_execution.execute_server_code_from_definition(
            outer_definition, "outer"
        )

    assert result["output"] == "NESTED"
    assert result["content_type"] == "text/plain"


def test_auto_main_accepts_alias_result_for_remaining_parameter(monkeypatch):
    outer_definition = """
 def main(payload):
     return {"output": payload, "content_type": "text/plain"}
 """

    inner_definition = """
 def main():
     return {"output": "from-alias", "content_type": "text/plain"}
 """

    servers = {
        "outer": SimpleNamespace(definition=outer_definition),
        "inner": SimpleNamespace(definition=inner_definition),
    }

    from server_execution import code_execution
    monkeypatch.setattr(
        code_execution,
        "get_server_by_name",
        lambda user_id, name: servers.get(name),
    )

    def fake_find_matching_alias(path):
        if path == "/alias-to-inner":
            return SimpleNamespace(route=SimpleNamespace(target_path="/inner"))
        return None

    # Patch find_matching_alias where it's used (in code_execution)
    monkeypatch.setattr(code_execution, "find_matching_alias", fake_find_matching_alias)

    with app.test_request_context("/outer/alias-to-inner"):
        result = server_execution.execute_server_code_from_definition(
            outer_definition, "outer"
        )

    assert result["output"] == "from-alias"
    assert result["content_type"] == "text/plain"


def test_auto_main_reads_cid_content_for_remaining_parameter(monkeypatch):
    outer_definition = """
 def main(body):
     return {"output": body, "content_type": "text/plain"}
 """

    cid_value = "bafyexamplecid"
    cid_bytes = b"payload-from-cid"

    from server_execution import code_execution
    monkeypatch.setattr(
        code_execution,
        "get_server_by_name",
        lambda user_id, name: None,
    )

    monkeypatch.setattr(
        code_execution,
        "get_cid_by_path",
        lambda path: SimpleNamespace(file_data=cid_bytes) if path == f"/{cid_value}" else None,
    )

    # Patch find_matching_alias where it's used (in code_execution)
    monkeypatch.setattr(code_execution, "find_matching_alias", lambda path: None)

    with app.test_request_context(f"/outer/{cid_value}"):
        result = server_execution.execute_server_code_from_definition(
            outer_definition, "outer"
        )

    assert result["output"] == "payload-from-cid"


def test_auto_main_handles_mixed_sources_with_single_remaining_parameter(monkeypatch):
    outer_definition = """
 def main(prefix, message):
     return {"output": f"{prefix}:{message}", "content_type": "text/plain"}
 """

    inner_definition = """
 def main():
     return {"output": "value", "content_type": "text/plain"}
 """

    servers = {
        "outer": SimpleNamespace(definition=outer_definition),
        "inner": SimpleNamespace(definition=inner_definition),
    }

    from server_execution import code_execution
    monkeypatch.setattr(
        code_execution,
        "get_server_by_name",
        lambda user_id, name: servers.get(name),
    )

    with app.test_request_context("/outer/inner?prefix=start"):
        result = server_execution.execute_server_code_from_definition(
            outer_definition, "outer"
        )

    assert result["output"] == "start:value"


def test_auto_main_multiple_missing_parameters_render_error_page(monkeypatch):
    outer_definition = """
 def main(first, second):
     return {"output": f"{first}:{second}", "content_type": "text/plain"}
 """

    from server_execution import code_execution
    monkeypatch.setattr(
        code_execution,
        "get_server_by_name",
        lambda user_id, name: None,
    )

    monkeypatch.setattr(server_execution, "find_matching_alias", lambda path: None)

    from server_execution import request_parsing
    monkeypatch.setattr(
        request_parsing,
        "render_template",
        lambda template_name, **context: "\n".join(
            [
                "Missing parameters",
                *context["missing_parameters"],
                "Supplied parameters",
                *context["supplied_parameters"],
            ]
        ),
    )

    with app.test_request_context("/outer/inner"):
        response = server_execution.execute_server_code_from_definition(
            outer_definition, "outer"
        )

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "Missing parameters" in body
    assert "first" in body
    assert "second" in body
    assert "Supplied parameters" in body


def test_auto_main_allows_request_context_parameter():
    definition = """
 def main(request):
     return {"output": request["path"], "content_type": "text/plain"}
 """

    with app.test_request_context("/context?value=1"):
        result = server_execution.execute_server_code_from_definition(definition, "context")

    assert result["output"] == "/context"


def test_auto_main_skips_when_explicit_return_present():
    definition = """
 def main(name):
     return {"output": f"auto {name}"}

 return {"output": "manual", "content_type": "text/plain"}
 """

    with app.test_request_context("/manual?name=Query"):
        result = server_execution.execute_server_code_from_definition(definition, "manual")

    assert result["output"] == "manual"


def test_auto_main_rejects_unsupported_signatures():
    definition = """
 def main(name, *args):
     return {"output": name}
 """

    with app.test_request_context("/unsupported?name=value"):
        response = server_execution.execute_server_code_from_definition(definition, "unsupported")

    assert response.status_code == 400
    payload = response.get_json()
    assert "Unsupported main() signature" in payload["error"]
    assert any("*args" in reason for reason in payload["reasons"])


def test_helper_function_routes_map_parameters():
    definition = """
 from html import escape

 def render_row(label, value):
     if value in (None, ""):
         return ""
     return f"<p><strong>{escape(str(label))}:</strong> {escape(str(value))}</p>"

 def main(name):
     return {"output": f"Hello, {name}", "content_type": "text/plain"}
 """

    with app.test_request_context("/greet/render_row?label=Name&value=Alice"):
        result = server_execution.execute_server_function_from_definition(
            definition, "greet", "render_row"
        )

    assert result["output"] == "<p><strong>Name:</strong> Alice</p>"
    assert result["content_type"] == "text/html"
    assert result["server_name"] == "greet"


def test_helper_function_missing_parameter_returns_error():
    definition = """
 def helper(required_value):
     return {"output": required_value, "content_type": "text/plain"}
 """

    with app.test_request_context("/helper/missing"):
        response = server_execution.execute_server_function_from_definition(
            definition, "helper", "helper"
        )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Missing required parameters for helper()"
    assert payload["missing_parameters"][0]["name"] == "required_value"


def test_try_server_execution_handles_helper_routes(monkeypatch):
    definition = """
 def helper(label):
     return {"output": label, "content_type": "text/plain"}
 """

    server = SimpleNamespace(definition=definition)

    from server_execution import server_lookup
    monkeypatch.setattr(
        server_lookup,
        "get_server_by_name",
        lambda user_id, name: server if name == "widget" else None,
    )

    with app.test_request_context("/widget/helper?label=Value"):
        result = server_execution.try_server_execution("/widget/helper")

    assert result["output"] == "Value"
    assert result["server_name"] == "widget"


def test_try_server_execution_returns_none_for_unknown_helper(monkeypatch):
    definition = """
 def main():
     return {"output": "ok", "content_type": "text/plain"}
 """

    server = SimpleNamespace(definition=definition)

    from server_execution import server_lookup
    monkeypatch.setattr(
        server_lookup,
        "get_server_by_name",
        lambda user_id, name: server if name == "widget" else None,
    )

    with app.test_request_context("/widget/unknown"):
        result = server_execution.try_server_execution("/widget/unknown")

    assert result is None


def test_server_templates_strip_internal_ruff_controls():
    templates = get_server_templates()
    assert templates, "At least one server template should be registered"

    for template in templates:
        definition = template.get("definition", "")
        assert "# ruff" not in definition

    auto_templates = [template for template in templates if template["id"] == "auto-main"]
    assert auto_templates, "auto-main template should be registered"
    definition = auto_templates[0]["definition"]
    assert "def main(" in definition
    assert "Automatic main() mapping" in definition


def test_server_templates_include_suggested_name_field():
    templates = get_server_templates()
    assert templates, "At least one server template should be registered"

    base_dir = Path(server_templates.__file__).parent
    template_dir = base_dir / "templates"
    available_template_stems = {path.stem for path in template_dir.glob("*.json")}
    assert available_template_stems, "Expected server template files to exist"

    for template in templates:
        suggested_name = template.get("suggested_name")
        assert suggested_name, f"Template {template.get('id')} should expose a suggested_name"
        assert (
            suggested_name in available_template_stems
        ), f"suggested_name {suggested_name} should match a template file"


def test_server_template_sources_retain_ruff_controls():
    base_dir = Path(server_templates.__file__).parent
    definitions_dir = base_dir / "definitions"
    definition_files = sorted(definitions_dir.glob("*.py"))

    assert definition_files, "Server template definition files should exist"

    for definition_path in definition_files:
        content = definition_path.read_text(encoding="utf-8")
        assert any(line.lstrip().startswith("# ruff") for line in content.splitlines()), (
            f"Expected {definition_path.name} to keep ruff control comments"
        )
