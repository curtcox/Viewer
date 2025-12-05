"""Comprehensive unit tests for server_execution.py functions."""

import json
import subprocess
import types
import unittest
from unittest.mock import patch

from flask import Flask

# pylint: disable=no-name-in-module  # False positive: names available via lazy loading in __getattr__
from server_execution import (
    FunctionDetails,
    MissingParameterError,
    _analyze_server_definition_for_function,
    _auto_main_accepts_additional_path,
    _build_missing_parameter_response,
    _build_multi_parameter_error_page,
    _build_unsupported_signature_response,
    _clone_request_context_kwargs,
    _extract_chained_output,
    _extract_request_body_values,
    _normalize_execution_result,
    _parse_function_details,
    _remaining_path_segments,
    _resolve_function_parameters,
    _split_path_segments,
    analyze_server_definition,
    build_request_args,
    describe_function_parameters,
    describe_main_function_parameters,
    detect_server_language,
    is_potential_server_path,
    is_potential_versioned_server_path,
    model_as_dict,
    request_details,
)
from server_execution.code_execution import _run_bash_script


class TestSplitPathSegments(unittest.TestCase):
    """Test _split_path_segments function."""

    def test_splits_valid_path(self):
        assert _split_path_segments("/foo/bar/baz") == ["foo", "bar", "baz"]

    def test_handles_empty_path(self):
        assert _split_path_segments("") == []
        assert _split_path_segments(None) == []

    def test_filters_empty_segments(self):
        assert _split_path_segments("/foo//bar/") == ["foo", "bar"]

    def test_handles_single_segment(self):
        assert _split_path_segments("/single") == ["single"]


class TestNormalizeExecutionResult(unittest.TestCase):
    """Test _normalize_execution_result function."""

    def test_extracts_dict_with_output_and_content_type(self):
        result = {"output": "hello", "content_type": "text/plain"}
        output, content_type = _normalize_execution_result(result)
        assert output == "hello"
        assert content_type == "text/plain"

    def test_handles_dict_without_keys(self):
        result = {"other": "value"}
        output, content_type = _normalize_execution_result(result)
        assert output == ""
        assert content_type == "text/html"

    def test_handles_tuple_result(self):
        result = ("content", "text/xml")
        output, content_type = _normalize_execution_result(result)
        assert output == "content"
        assert content_type == "text/xml"

    def test_handles_string_result(self):
        result = "plain text"
        output, content_type = _normalize_execution_result(result)
        assert output == "plain text"
        assert content_type == "text/html"


class TestExtractChainedOutput(unittest.TestCase):
    """Test _extract_chained_output helper."""

    def test_extracts_from_dict(self):
        assert _extract_chained_output({"output": "value", "content_type": "text/plain"}) == "value"

    def test_extracts_from_json_string(self):
        payload = json.dumps({"output": "json-value", "content_type": "text/plain"})
        assert _extract_chained_output(payload) == "json-value"

    def test_passthrough_for_non_json_string(self):
        assert _extract_chained_output("raw-text") == "raw-text"


class TestParseFunctionDetails(unittest.TestCase):
    """Test _parse_function_details function."""

    def test_parses_simple_function(self):
        import ast

        code = "def func(a, b, c=1): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        details = _parse_function_details(func_node)

        assert details.parameter_order == ["a", "b", "c"]
        assert details.required_parameters == ["a", "b"]
        assert details.optional_parameters == ["c"]
        assert not details.unsupported_reasons

    def test_parses_keyword_only_params(self):
        import ast

        code = "def func(a, *, b, c=1): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        details = _parse_function_details(func_node)

        assert details.parameter_order == ["a", "b", "c"]
        assert details.required_parameters == ["a", "b"]
        assert details.optional_parameters == ["c"]

    def test_detects_vararg(self):
        import ast

        code = "def func(a, *args): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        details = _parse_function_details(func_node)

        assert "var positional parameters (*args) are not supported" in details.unsupported_reasons

    def test_detects_kwarg(self):
        import ast

        code = "def func(a, **kwargs): pass"
        tree = ast.parse(code)
        func_node = tree.body[0]
        details = _parse_function_details(func_node)

        assert "arbitrary keyword parameters (**kwargs) are not supported" in details.unsupported_reasons


class TestAnalyzeServerDefinitionForFunction(unittest.TestCase):
    """Test _analyze_server_definition_for_function function."""

    def test_finds_function_in_definition(self):
        code = """
def main(a, b):
    return a + b
"""
        details = _analyze_server_definition_for_function(code, "main")
        assert details is not None
        assert details.parameter_order == ["a", "b"]
        assert details.required_parameters == ["a", "b"]

    def test_returns_none_for_missing_function(self):
        code = """
def other():
    pass
"""
        details = _analyze_server_definition_for_function(code, "main")
        assert details is None

    def test_returns_none_for_syntax_error(self):
        code = "def main( invalid syntax"
        details = _analyze_server_definition_for_function(code, "main")
        assert details is None

    def test_returns_none_for_outer_return(self):
        code = """
def main():
    pass
return "value"
"""
        details = _analyze_server_definition_for_function(code, "main")
        assert details is None


class TestDescribeFunctionParameters(unittest.TestCase):
    """Test describe_function_parameters and describe_main_function_parameters."""

    def test_describes_simple_function(self):
        code = """
def example(a, b, c=1):
    pass
"""
        result = describe_function_parameters(code, "example")
        assert result is not None
        assert len(result["parameters"]) == 3
        assert result["required_parameters"] == ["a", "b"]
        assert result["optional_parameters"] == ["c"]

    def test_returns_none_for_unsupported_signature(self):
        code = """
def example(*args):
    pass
"""
        result = describe_function_parameters(code, "example")
        assert result is None

    def test_describe_main_function_parameters(self):
        code = """
def main(x, y=2):
    pass
"""
        result = describe_main_function_parameters(code)
        assert result is not None
        assert result["required_parameters"] == ["x"]
        assert result["optional_parameters"] == ["y"]


class TestAnalyzeServerDefinition(unittest.TestCase):
    """Test analyze_server_definition function."""

    def test_analyzes_valid_definition_with_main(self):
        code = """
def main(a, b=1):
    return "result"
"""
        result = analyze_server_definition(code)
        assert result["is_valid"] is True
        assert result["has_main"] is True
        assert result["auto_main"] is True
        assert result["mode"] == "main"
        assert len(result["parameters"]) == 2

    def test_handles_syntax_error(self):
        code = "def main( invalid"
        result = analyze_server_definition(code)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert result["errors"][0]["message"]

    def test_handles_no_main_function(self):
        code = """
def other():
    pass
"""
        result = analyze_server_definition(code)
        assert result["is_valid"] is True
        assert result["has_main"] is False
        assert result["auto_main"] is False

    def test_detects_unsupported_main_signature(self):
        code = """
def main(*args):
    pass
"""
        result = analyze_server_definition(code)
        assert result["has_main"] is True
        assert result["auto_main"] is False
        assert len(result["auto_main_errors"]) > 0

    def test_detects_language_for_python_and_bash(self):
        assert detect_server_language("def main():\n    return 'ok'\n") == "python"
        assert (
            detect_server_language("#!/usr/bin/env bash\necho 'ok'\n")
            == "bash"
        )
        assert (
            detect_server_language("#!/usr/bin/env bb\n(println \"ok\")\n")
            == "clojure"
        )
        assert (
            detect_server_language(
                "(ns cljs.demo (:require [cljs.core :as c]))\n(defn main [] (println \"hi\"))"
            )
            == "clojurescript"
        )
        assert (
            detect_server_language(
                "#!/usr/bin/env -S deno run --quiet\nexport async function main() {}"
            )
            == "typescript"
        )

    def test_typescript_imports_do_not_match_python(self):
        deno_script = (
            "import { serve } from \"https://deno.land/std/http/server.ts\"\n"
            "export async function main() {\n"
            "  await serve(() => new Response('ok'));\n"
            "}"
        )

        assert detect_server_language(deno_script) == "typescript"

    def test_analyze_reports_language(self):
        result = analyze_server_definition("#!/bin/bash\necho hi\n")
        assert result["language"] == "bash"


class TestExtractRequestBodyValues(unittest.TestCase):
    """Test _extract_request_body_values function."""

    def test_extracts_json_payload(self):
        app = Flask(__name__)
        with app.test_request_context(
            "/test", method="POST", json={"key": "value"}
        ):
            result = _extract_request_body_values()
        assert result == {"key": "value"}

    def test_extracts_form_data(self):
        app = Flask(__name__)
        with app.test_request_context(
            "/test", method="POST", data={"field": "data"}
        ):
            result = _extract_request_body_values()
        assert result == {"field": "data"}

    def test_handles_empty_request(self):
        app = Flask(__name__)
        with app.test_request_context("/test"):
            result = _extract_request_body_values()
        assert not result


class TestResolveRequestParameters(unittest.TestCase):
    """Test _resolve_function_parameters function."""

    def test_resolves_from_query_string(self):
        app = Flask(__name__)
        details = FunctionDetails(
            parameter_order=["a", "b"],
            required_parameters=["a", "b"],
            optional_parameters=[],
            unsupported_reasons=[],
        )

        with app.test_request_context("/test?a=1&b=2"):
            result = _resolve_function_parameters(details, {})

        assert result == {"a": "1", "b": "2"}

    def test_resolves_from_base_args(self):
        details = FunctionDetails(
            parameter_order=["a"],
            required_parameters=["a"],
            optional_parameters=[],
            unsupported_reasons=[],
        )

        app = Flask(__name__)
        with app.test_request_context("/test"):
            result = _resolve_function_parameters(details, {"a": "value"})

        assert result == {"a": "value"}

    def test_resolves_from_context_variables(self):
        details = FunctionDetails(
            parameter_order=["a"],
            required_parameters=["a"],
            optional_parameters=[],
            unsupported_reasons=[],
        )

        app = Flask(__name__)
        with app.test_request_context("/test"):
            result = _resolve_function_parameters(
                details, {"context": {"variables": {"a": "var-value"}}}
            )

        assert result == {"a": "var-value"}

    def test_raises_missing_parameter_error(self):
        details = FunctionDetails(
            parameter_order=["a", "b"],
            required_parameters=["a", "b"],
            optional_parameters=[],
            unsupported_reasons=[],
        )

        app = Flask(__name__)
        with app.test_request_context("/test?a=1"):
            with self.assertRaises(MissingParameterError) as ctx:
                _resolve_function_parameters(details, {})

        assert "b" in ctx.exception.missing

    def test_allows_partial_resolution(self):
        details = FunctionDetails(
            parameter_order=["a", "b"],
            required_parameters=["a", "b"],
            optional_parameters=[],
            unsupported_reasons=[],
        )

        app = Flask(__name__)
        with app.test_request_context("/test?a=1"):
            resolved, missing, _ = _resolve_function_parameters(
                details, {}, allow_partial=True
            )

        assert resolved == {"a": "1"}
        assert "b" in missing


class TestBuildMissingParameterResponse(unittest.TestCase):
    """Test _build_missing_parameter_response function."""

    def test_builds_json_response(self):
        app = Flask(__name__)
        with app.app_context():
            error = MissingParameterError(["param1", "param2"], {"query_string": []})
            response = _build_missing_parameter_response("main", error)

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "missing_parameters" in data
            assert len(data["missing_parameters"]) == 2


class TestBuildMultiParameterErrorPage(unittest.TestCase):
    """Test _build_multi_parameter_error_page function."""

    def test_builds_html_error_page(self):
        app = Flask(__name__)
        app.config["TESTING"] = True

        with app.test_request_context("/test?a=1"):
            with patch("server_execution.request_parsing.render_template") as mock_render:
                mock_render.return_value = "<html>error</html>"
                response = _build_multi_parameter_error_page(
                    "server",
                    "main",
                    ["param1", "param2"],
                    ["a"],
                    {"query_string": ["a"]},
                )

        assert response.status_code == 400
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"


class TestBuildUnsupportedSignatureResponse(unittest.TestCase):
    """Test _build_unsupported_signature_response function."""

    def test_builds_json_error_response(self):
        app = Flask(__name__)
        with app.app_context():
            details = FunctionDetails(
                parameter_order=[],
                required_parameters=[],
                optional_parameters=[],
                unsupported_reasons=["*args not supported"],
            )
            response = _build_unsupported_signature_response("main", details)

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "reasons" in data


class TestModelAsDict(unittest.TestCase):
    """Test model_as_dict function."""

    def test_converts_models_to_dict(self):
        obj1 = types.SimpleNamespace(name="server1", definition="code1", enabled=True)
        obj2 = types.SimpleNamespace(name="server2", definition="code2", enabled=True)
        result = model_as_dict([obj1, obj2])

        assert result == {"server1": "code1", "server2": "code2"}

    def test_filters_disabled_models(self):
        obj1 = types.SimpleNamespace(name="server1", definition="code1", enabled=True)
        obj2 = types.SimpleNamespace(name="server2", definition="code2", enabled=False)
        result = model_as_dict([obj1, obj2])

        assert result == {"server1": "code1"}

    def test_handles_empty_list(self):
        result = model_as_dict([])
        assert not result

    def test_handles_none(self):
        result = model_as_dict(None)
        assert not result


class TestRequestDetails(unittest.TestCase):
    """Test request_details function."""

    def test_collects_request_details(self):
        app = Flask(__name__)
        with app.test_request_context(
            "/test?key=value",
            method="POST",
            data=json.dumps({"request_text": "Update"}),
            content_type="application/json",
            headers={"User-Agent": "TestAgent", "Cookie": "session=xyz"},
        ):
            result = request_details()

        assert result["path"] == "/test"
        assert result["query_string"] == "key=value"
        assert result["method"] == "POST"
        assert "User-Agent" in result["headers"]
        assert "Cookie" not in result["headers"]
        assert result["json"] == {"request_text": "Update"}
        assert "Update" in (result["body"] or "")


class TestBuildRequestArgs(unittest.TestCase):
    """Test build_request_args function."""

    def test_builds_request_args(self):
        app = Flask(__name__)

        with patch("server_execution.code_execution.get_variables", return_value=[]):
            with patch("server_execution.code_execution.get_secrets", return_value=[]):
                with patch("server_execution.code_execution.get_servers", return_value=[]):
                    with app.test_request_context("/test"):
                        result = build_request_args()

        assert "request" in result
        assert "context" in result
        assert result["request"]["path"] == "/test"
        assert "variables" in result["context"]
        assert "secrets" in result["context"]
        assert "servers" in result["context"]


class TestRemainingPathSegments(unittest.TestCase):
    """Test _remaining_path_segments function."""

    def test_returns_remaining_segments(self):
        app = Flask(__name__)
        with app.test_request_context("/server/func/extra"):
            result = _remaining_path_segments("server")

        assert result == ["func", "extra"]

    def test_returns_empty_for_exact_match(self):
        app = Flask(__name__)
        with app.test_request_context("/server"):
            result = _remaining_path_segments("server")

        assert result == []

    def test_returns_empty_for_non_matching_name(self):
        app = Flask(__name__)
        with app.test_request_context("/other/path"):
            result = _remaining_path_segments("server")

        assert result == []


class TestAutoMainAcceptsAdditionalPath(unittest.TestCase):
    """Test _auto_main_accepts_additional_path function."""

    def test_returns_true_for_parameterized_main(self):
        server = types.SimpleNamespace(
            definition="""
def main(a):
    pass
"""
        )
        result = _auto_main_accepts_additional_path(server)
        assert result is True

    def test_returns_false_for_no_parameters(self):
        server = types.SimpleNamespace(
            definition="""
def main():
    pass
"""
        )
        result = _auto_main_accepts_additional_path(server)
        assert result is False

    def test_returns_false_for_no_main(self):
        server = types.SimpleNamespace(definition="print('hello')")
        result = _auto_main_accepts_additional_path(server)
        assert result is False


class TestCloneRequestContextKwargs(unittest.TestCase):
    """Test _clone_request_context_kwargs function."""

    def test_clones_get_request_context(self):
        app = Flask(__name__)
        with app.test_request_context("/test?key=value", method="GET"):
            result = _clone_request_context_kwargs("/new-path")

        assert result["path"] == "/new-path"
        assert result["method"] == "GET"
        assert result["query_string"] == "key=value"

    def test_clones_post_request_with_json(self):
        app = Flask(__name__)
        with app.test_request_context(
            "/test", method="POST", json={"key": "value"}
        ):
            result = _clone_request_context_kwargs("/new-path")

        assert result["method"] == "POST"
        assert result["json"] == {"key": "value"}

    def test_excludes_cookie_headers(self):
        app = Flask(__name__)
        with app.test_request_context(
            "/test", headers={"Cookie": "session=xyz", "User-Agent": "Test"}
        ):
            result = _clone_request_context_kwargs("/new-path")

        assert "headers" in result
        header_keys = [k for k, v in result["headers"]]
        assert "Cookie" not in header_keys
        assert "User-Agent" in header_keys

    def test_uses_defaults_without_request_context(self):
        result = _clone_request_context_kwargs("/path")
        assert result["method"] == "GET"
        assert result["query_string"] == ""


class TestIsPotentialVersionedServerPath(unittest.TestCase):
    """Test is_potential_versioned_server_path function."""

    def test_matches_two_segment_path(self):
        result = is_potential_versioned_server_path("/server/bafy123", [])
        assert result is True

    def test_matches_three_segment_path(self):
        result = is_potential_versioned_server_path("/server/bafy123/func", [])
        assert result is True

    def test_rejects_single_segment(self):
        result = is_potential_versioned_server_path("/server", [])
        assert result is False

    def test_rejects_existing_route(self):
        result = is_potential_versioned_server_path("/server/bafy123", ["/server"])
        assert result is False

    def test_rejects_invalid_path(self):
        result = is_potential_versioned_server_path("", [])
        assert result is False


class TestIsPotentialServerPath(unittest.TestCase):
    """Test is_potential_server_path function."""

    def test_accepts_valid_server_path(self):
        result = is_potential_server_path("/server", [])
        assert result is True

    def test_rejects_existing_route(self):
        result = is_potential_server_path("/server", ["/server"])
        assert result is False

    def test_rejects_path_with_existing_prefix(self):
        result = is_potential_server_path("/static/file", ["/static"])
        assert result is False

    def test_rejects_empty_path(self):
        result = is_potential_server_path("", [])
        assert result is False


class TestMissingParameterError(unittest.TestCase):
    """Test MissingParameterError exception."""

    def test_stores_missing_parameters(self):
        error = MissingParameterError(["a", "b"], {"query": []})
        assert error.missing == ["a", "b"]
        assert error.available == {"query": []}

    def test_formats_error_message(self):
        error = MissingParameterError(["param1", "param2"], {})
        assert "param1" in str(error)
        assert "param2" in str(error)


def test_run_bash_script_times_out(monkeypatch):
    removed_paths: list[str] = []

    def fake_run(cmd, input=None, capture_output=None, check=None, timeout=None):  # noqa: A002  # pylint: disable=redefined-builtin
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr("server_execution.code_execution.subprocess.run", fake_run)
    monkeypatch.setattr(
        "server_execution.code_execution.os.remove",
        removed_paths.append,
    )

    def empty_request_args():
        return {}

    monkeypatch.setattr("server_execution.code_execution.build_request_args", empty_request_args)

    app = Flask(__name__)
    with app.test_request_context("/bash-server"):
        stdout, status_code, stderr = _run_bash_script("#!/usr/bin/env bash\n", "bash-server")

    assert status_code == 504
    assert b"timed out" in stdout
    assert stderr == b""
    assert removed_paths


if __name__ == "__main__":
    unittest.main()
