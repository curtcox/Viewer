from link_presenter import (
    alias_full_url,
    alias_path,
    render_alias_link,
    render_server_link,
    render_url_link,
    server_full_url,
    server_path,
)


def test_alias_path_normalizes_input():
    assert alias_path(" demo ") == "/demo"
    assert alias_path("/demo") == "/demo"
    assert alias_path(None) is None


def test_server_path_normalizes_input():
    assert server_path(" main ") == "/servers/main"
    assert server_path("/servers/main") == "/servers/main"
    assert server_path("") is None


def test_alias_full_url_prefers_base_url():
    assert (
        alias_full_url("https://example.com/", "hello") == "https://example.com/hello"
    )
    assert alias_full_url("https://example.com", "hello") == "https://example.com/hello"
    assert alias_full_url("", "hello") == "/hello"


def test_server_full_url_prefers_base_url():
    assert (
        server_full_url("https://example.com/", "alpha")
        == "https://example.com/servers/alpha"
    )
    assert server_full_url(None, "alpha") == "/servers/alpha"


def test_render_alias_link_relative_path():
    html = str(render_alias_link("alpha", code=True))
    assert '<a href="/alpha"' in html
    assert ">/alpha<" in html


def test_render_alias_link_full_url():
    html = str(render_alias_link("alpha", base_url="https://example.com/", code=True))
    assert 'href="https://example.com/alpha"' in html
    assert ">https://example.com/alpha<" in html


def test_render_server_link_relative_path():
    html = str(render_server_link("beta", code=True))
    assert '<a href="/servers/beta"' in html
    assert ">/servers/beta<" in html


def test_render_url_link_supports_custom_label_and_class():
    html = str(render_url_link("/demo", label="Demo", class_name="badge"))
    assert '<a href="/demo" class="badge">' in html
    assert ">Demo<" in html


def test_render_functions_return_empty_markup_for_missing_values():
    assert str(render_alias_link(None)) == ""
    assert str(render_server_link(None)) == ""
    assert str(render_url_link(None)) == ""
