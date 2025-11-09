from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import server_execution
from app import app
from cid_utils import MermaidRenderLocation, _render_markdown_document
from server_templates.definitions import auto_main_markdown
from text_function_runner import run_text_function


def test_auto_main_markdown_main_normalizes_input(monkeypatch):
    captured = {}

    def fake_renderer(text):
        captured["text"] = text
        return "<html></html>"

    monkeypatch.setattr(auto_main_markdown, "_render_markdown_document", fake_renderer)

    result = auto_main_markdown.main(markdown="## Heading")

    assert result["content_type"] == "text/html"
    assert result["output"] == "<html></html>"
    assert captured["text"] == "## Heading\n"


def test_auto_main_markdown_supports_mermaid_and_formdown():
    svg_bytes = b"<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>"
    markdown = """
    # Release planning

    ```mermaid
    graph TD
        A --> B
    ```

    ```formdown
    @email: [email required]
    @submit: [submit label="Notify me"]
    ```
    """.strip()

    with (
        patch("content_rendering._mermaid_renderer._fetch_svg", return_value=svg_bytes),
        patch(
            "content_rendering._mermaid_renderer._store_svg",
            return_value=MermaidRenderLocation(is_cid=True, value="diagramcid123"),
        ),
    ):
        result = auto_main_markdown.main(markdown=markdown)

    assert result["content_type"] == "text/html"
    assert "mermaid-diagram" in result["output"]
    assert "/diagramcid123.svg" in result["output"]
    assert "<div class=\"formdown-document\"" in result["output"]
    assert "Notify me" in result["output"]


@pytest.fixture
def patched_server_execution(monkeypatch):
    """Provide a predictable environment for server execution tests."""
    from server_execution import code_execution, variable_resolution
    import identity

    # After decomposition, current_user is only in variable_resolution
    mock_user = SimpleNamespace(id="user-123")
    monkeypatch.setattr(identity, "current_user", mock_user)
    monkeypatch.setattr(variable_resolution, "current_user", mock_user)

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

    monkeypatch.setattr(code_execution, "_handle_successful_execution", fake_success)


def test_auto_main_markdown_runs_through_text_function_runner():
    definition = """
from server_templates.definitions import auto_main_markdown

return auto_main_markdown.main(markdown=markdown)
""".strip()

    result = run_text_function(definition, {"markdown": "Hello from text runner"})

    assert result["content_type"] == "text/html"
    assert "Hello from text runner" in result["output"]
    assert "<main class=\"markdown-body\"" in result["output"]


def test_auto_main_markdown_executes_via_server_execution(patched_server_execution):
    definition = Path("server_templates/definitions/auto_main_markdown.py").read_text(encoding='utf-8')

    with app.test_request_context("/markdown", json={"markdown": "Hello from server execution"}):
        result = server_execution.execute_server_code_from_definition(
            definition, "markdown-renderer"
        )

    assert result["server_name"] == "markdown-renderer"
    assert result["content_type"] == "text/html"
    assert "Hello from server execution" in result["output"]
    assert "<main class=\"markdown-body\"" in result["output"]


def test_auto_main_markdown_matches_markdown_showcase_template():
    repo_root = Path(__file__).resolve().parent.parent
    markdown_sample = (
        repo_root / "upload_templates" / "contents" / "markdown_showcase.md"
    ).read_text(encoding="utf-8")

    expected_html = _render_markdown_document(markdown_sample)
    rendered = auto_main_markdown.main(markdown=markdown_sample)

    assert rendered["content_type"] == "text/html"
    assert rendered["output"] == expected_html


def test_auto_main_markdown_matches_formdown_showcase_template():
    repo_root = Path(__file__).resolve().parent.parent
    formdown_sample = (
        repo_root / "upload_templates" / "contents" / "formdown_showcase.formdown"
    ).read_text(encoding="utf-8")

    expected_html = _render_markdown_document(formdown_sample)
    rendered = auto_main_markdown.main(markdown=formdown_sample)

    assert rendered["content_type"] == "text/html"
    assert rendered["output"] == expected_html
    assert "<div class=\"formdown-document\"" in rendered["output"]
