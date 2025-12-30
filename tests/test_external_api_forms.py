"""Tests for HTML form generation helpers."""

from server_utils.external_api import FormField, generate_form


def test_generate_basic_form_includes_fields_and_examples() -> None:
    fields = [
        FormField(name="api_key", label="API Key", required=True, placeholder="abc"),
        FormField(
            name="message",
            label="Message",
            field_type="textarea",
            default="hello",
            help_text="Enter the message text.",
        ),
        FormField(
            name="channel",
            label="Channel",
            field_type="select",
            options=["general", "random"],
            default="random",
        ),
    ]

    result = generate_form(
        server_name="slack",
        title="Slack Message",
        description="Send a message to Slack.",
        fields=fields,
        examples=[{"title": "Post", "description": "Basic post", "request": "{...}"}],
        documentation_url="https://api.slack.com",
    )

    html = result["output"]
    assert "Slack Message" in html
    assert "Send a message" in html
    assert "input type=\"text\"" in html
    assert "textarea" in html
    assert "select" in html
    assert "<option value=\"random\" selected>" in html
    assert "Examples" in html
    assert "View API Documentation" in html


def test_generate_form_defaults_endpoint_to_server_name() -> None:
    result = generate_form(
        server_name="example",
        title="Example",
        description="Desc",
        fields=[],
    )

    assert "action=\"/example\"" in result["output"]
