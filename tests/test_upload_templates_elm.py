from upload_templates import get_upload_templates


def test_elm_template_is_available():
    templates = {template["id"]: template for template in get_upload_templates()}

    assert "hello-world-elm" in templates
    elm_template = templates["hello-world-elm"]

    assert elm_template["suggested_filename"] == "hello.elm"
    assert "Elm" in elm_template["name"]
    assert "Hello!" in elm_template["content"]
