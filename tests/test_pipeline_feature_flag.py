import os

from flask import Response

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import app  # noqa: E402  # pylint: disable=wrong-import-position
from server_execution import code_execution  # noqa: E402  # pylint: disable=wrong-import-position


def test_evaluate_nested_path_uses_pipeline(monkeypatch):
    """Nested evaluation routes through the pipeline compatibility layer."""
    import server_execution.pipeline_compat as pipeline_compat

    calls = {}

    def fake_evaluate(path, visited=None):
        calls["path"] = path
        calls["visited"] = visited
        return "pipeline-result"

    monkeypatch.setattr(
        pipeline_compat, "evaluate_nested_path_to_value_v2", fake_evaluate
    )

    result = code_execution._evaluate_nested_path_to_value("/s1/s2", {"visited"})

    assert result == "pipeline-result"
    assert calls["path"] == "/s1/s2"
    assert calls["visited"] == {"visited"}


def test_resolve_chained_input_uses_pipeline(monkeypatch):
    """Chained input resolution honors the pipeline compatibility layer."""
    import server_execution.pipeline_compat as pipeline_compat

    def fake_resolver(path, visited=None):
        return f"resolved:{path}", None

    monkeypatch.setattr(
        pipeline_compat, "resolve_chained_input_from_path_v2", fake_resolver
    )

    chained_input, response = code_execution._resolve_chained_input_from_path(
        "/a/b", set()
    )

    assert chained_input == "resolved:/a/b"
    assert response is None


def test_not_found_returns_pipeline_debug_response(monkeypatch):
    """404 handler returns pipeline debug output when requested."""
    from routes import error_handlers

    fake_response = Response("debug", mimetype="text/plain")
    monkeypatch.setattr(
        error_handlers, "should_return_debug_response", lambda req: True
    )
    monkeypatch.setattr(error_handlers, "is_pipeline_request", lambda path: True)
    monkeypatch.setattr(
        error_handlers,
        "execute_pipeline",
        lambda path, debug=False: {"path": path, "debug": debug},
    )

    def fake_formatter(result, extension=None):
        assert result["debug"] is True
        assert extension == "txt"
        return fake_response

    monkeypatch.setattr(error_handlers, "format_debug_response", fake_formatter)

    with app.test_request_context("/pipe/path.txt?debug=true"):
        response = error_handlers.not_found_error(Exception("notfound"))

    assert response is fake_response
