import pytest

from cid_presenter import extract_cid_from_path, is_probable_cid_path, render_cid_link


@pytest.mark.parametrize("value", [None, "", "   ", "/ "])
def test_render_cid_link_empty_values(value):
    rendered = render_cid_link(value)
    assert str(rendered) == ""


def test_render_cid_link_includes_expected_elements():
    cid = "bafybeigdyrztgv7vdy3niece7krvlshk7qe5b6mr4uxk5qf7f4q23yyeuq"
    rendered = str(render_cid_link(cid))

    assert '<span class="cid-display dropdown">' in rendered
    assert f'href="/{cid}.txt"' in rendered
    assert f'title="{cid}"' in rendered
    assert f">#{cid[:9]}...<" in rendered
    assert 'class="dropdown-item cid-copy-action"' in rendered
    assert f'data-copy-path="/{cid}.txt"' in rendered
    assert f'href="/{cid}.txt"' in rendered
    assert f'href="/{cid}.md"' in rendered
    assert f'href="/{cid}.html"' in rendered
    assert f'href="/{cid}.json"' in rendered
    assert f'href="/{cid}.png"' in rendered
    assert f'href="/{cid}.jpg"' in rendered
    assert f'href="/{cid}.qr"' in rendered
    assert f'href="/edit/{cid}"' in rendered
    assert f'href="/meta/{cid}"' in rendered
    assert 'class="btn btn-sm btn-outline-secondary cid-menu-btn dropdown-toggle"' in rendered
    assert 'data-bs-boundary="viewport"' in rendered
    assert 'data-bs-offset="0,8"' in rendered
    assert 'class="dropdown-menu dropdown-menu-end"' in rendered


def test_render_cid_link_strips_leading_slash():
    cid = "/bafybeigdyr"
    rendered = str(render_cid_link(cid))

    assert 'href="/bafybeigdyr.txt"' in rendered
    assert '>#bafybeigd...<' in rendered


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("/" , None),
        ("/alpha/beta", None),
        ("/bafybeigdyr.txt", "bafybeigdyr"),
        ("bafybeigdyr", "bafybeigdyr"),
        ("/bafybeigdyr?download=1", "bafybeigdyr"),
    ],
)
def test_extract_cid_from_path(value, expected):
    assert extract_cid_from_path(value) == expected


def test_is_probable_cid_path_filters_non_cid_targets():
    assert is_probable_cid_path("/bafybeigdyr")
    assert not is_probable_cid_path("/servers/example")
    assert not is_probable_cid_path("/demo/path")
