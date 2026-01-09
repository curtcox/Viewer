"""Property tests for Formdown rendering helpers."""

from hypothesis import given, strategies as st

from formdown_renderer import (
    BOOLEAN_ATTRIBUTES,
    Paragraph,
    _generate_field_id,
    _render_attribute,
    _render_paragraph,
    render_formdown_html,
)


@given(st.lists(st.text(min_size=0, max_size=50), min_size=1, max_size=50))
def test_generate_field_id_produces_unique_ids(names):
    existing_counts = {}
    ids = [_generate_field_id(name, existing_counts) for name in names]
    assert len(ids) == len(set(ids))


@given(st.sampled_from(sorted(BOOLEAN_ATTRIBUTES)), st.text(min_size=0, max_size=10))
def test_render_attribute_boolean_only_emits_when_truthy(name, value):
    rendered = _render_attribute(name, value)
    flag = (value or "").strip().lower()
    should_render = flag in {"", "1", "true", "yes", name}
    assert (rendered != "") == should_render


@given(
    st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\x00\r\n\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029",
        ),
        min_size=0,
        max_size=200,
    )
)
def test_render_formdown_html_escapes_paragraph_text(text):
    if not text.strip():
        return
    if text.strip().startswith("@"):  # could be parsed as a form field
        return
    if text.strip().startswith("#"):  # could be parsed as a heading
        return
    if text.strip() == "---":
        return

    html_output = render_formdown_html(text)
    paragraph_html = _render_paragraph(Paragraph(text=text.strip()))
    assert paragraph_html in html_output


@given(
    st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\x00\r",
        ),
        min_size=0,
        max_size=200,
    )
)
def test_render_attribute_escapes_non_boolean_values(value):
    rendered = _render_attribute("data-value", value)
    assert "data-value=\"" in rendered
    assert "\"" in rendered
    assert "<" not in rendered
