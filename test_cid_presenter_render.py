import pytest

from cid_presenter import render_cid_link


@pytest.mark.parametrize("value", [None, "", "   ", "/ "])
def test_render_cid_link_empty_values(value):
    rendered = render_cid_link(value)
    assert str(rendered) == ""


def test_render_cid_link_includes_expected_elements():
    cid = "bafybeigdyrztgv7vdy3niece7krvlshk7qe5b6mr4uxk5qf7f4q23yyeuq"
    rendered = str(render_cid_link(cid))

    assert '<span class="cid-display dropdown">' in rendered
    assert f'href="/{cid}"' in rendered
    assert f'title="{cid}"' in rendered
    assert f">#{cid[:9]}...<" in rendered
    assert 'class="dropdown-item cid-copy-action"' in rendered
    assert f'data-copy-path="/{cid}"' in rendered
    assert f'href="/{cid}.txt"' in rendered
    assert f'href="/{cid}.md"' in rendered
    assert f'href="/{cid}.html"' in rendered
    assert f'href="/{cid}.json"' in rendered
    assert f'href="/{cid}.png"' in rendered
    assert f'href="/{cid}.jpg"' in rendered
    assert f'href="/edit/{cid}"' in rendered
    assert f'href="/meta/{cid}"' in rendered
    assert 'class="btn btn-sm btn-outline-secondary cid-menu-btn dropdown-toggle"' in rendered
    assert 'data-bs-boundary="viewport"' in rendered
    assert 'data-bs-offset="0,8"' in rendered
    assert 'class="dropdown-menu dropdown-menu-end"' in rendered


def test_render_cid_link_strips_leading_slash():
    cid = "/bafybeigdyr"
    rendered = str(render_cid_link(cid))

    assert 'href="/bafybeigdyr"' in rendered
    assert '>#bafybeigd...<' in rendered
