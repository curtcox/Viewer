import pytest

from cid import CID
from cid_presenter import (
    cid_full_url,
    cid_path,
    extract_cid_from_path,
    format_cid,
    format_cid_short,
    is_probable_cid_path,
    render_cid_link,
)


CID_SAMPLE = CID.from_bytes(b"cid-presenter-sample")
CID_SAMPLE_STR = CID_SAMPLE.value
CID_SAMPLE_SHORT = CID_SAMPLE_STR[:10]


@pytest.mark.parametrize("value", [None, "", "   ", "/ "])
def test_render_cid_link_empty_values(value):
    rendered = render_cid_link(value)
    assert str(rendered) == ""


def test_render_cid_link_includes_expected_elements():
    cid = CID_SAMPLE_STR
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


def test_render_cid_link_accepts_cid_object():
    cid_obj = CID.from_bytes(b"cid-presenter-object")
    cid_str = cid_obj.value

    # Rendering with CID object should match rendering with plain string
    rendered_from_str = str(render_cid_link(cid_str))
    rendered_from_obj = str(render_cid_link(cid_obj))

    assert rendered_from_obj == rendered_from_str


def test_render_cid_link_strips_leading_slash():
    cid = f"/{CID_SAMPLE_SHORT}"
    rendered = str(render_cid_link(cid))

    assert f'href="/{CID_SAMPLE_SHORT}.txt"' in rendered
    assert f'>#{CID_SAMPLE_SHORT[:9]}...<' in rendered


def test_format_helpers_accept_cid_object():
    cid_obj = CID.from_bytes(b"cid-presenter-format")
    cid_str = cid_obj.value

    assert format_cid(cid_obj) == cid_str
    assert format_cid_short(cid_obj) == f"{cid_str[:6]}..."

    # Path helpers should also work with CID objects
    assert cid_path(cid_obj) == f"/{cid_str}"
    assert cid_path(cid_obj, "txt") == f"/{cid_str}.txt"

    base = "https://example.com/"
    assert cid_full_url(base, cid_obj, "txt") == f"https://example.com/{cid_str}.txt"


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("/" , None),
        ("/alpha/beta", None),
        (f"/{CID_SAMPLE_STR}.txt", CID_SAMPLE_STR),
        (CID_SAMPLE_STR, CID_SAMPLE_STR),
        (f"/{CID_SAMPLE_STR}?download=1", CID_SAMPLE_STR),
    ],
)
def test_extract_cid_from_path(value, expected):
    assert extract_cid_from_path(value) == expected


def test_is_probable_cid_path_filters_non_cid_targets():
    assert is_probable_cid_path(f"/{CID_SAMPLE_SHORT}")
    assert not is_probable_cid_path("/servers/example")
    assert not is_probable_cid_path("/demo/path")
