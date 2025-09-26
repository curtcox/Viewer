"""Unit tests that verify Markdown features render to the expected HTML."""

from __future__ import annotations

import re
import textwrap

from pathlib import Path

from cid_utils import _FORMDOWN_SCRIPT_URL, _render_markdown_document


def _render_fragment(markdown_text: str) -> str:
    """Render Markdown text and return the HTML fragment inside the main tag."""

    normalized = textwrap.dedent(markdown_text).strip() + "\n"
    html_document = _render_markdown_document(normalized)

    marker = '<main class="markdown-body">'
    start = html_document.index(marker)
    fragment_with_tag = html_document[start:].split("</main>", 1)[0]
    fragment = fragment_with_tag.split('>', 1)[1]
    return fragment.strip()


def _render_formdown_form(markdown_text: str) -> tuple[str, str]:
    """Render markdown and return the HTML fragment plus formdown DSL body."""

    fragment = _render_fragment(markdown_text)
    container_match = re.search(
        r"<div[^>]*data-formdown[^>]*>(?P<body>.*?)</div>",
        fragment,
        re.DOTALL,
    )
    assert container_match is not None, "Expected a data-formdown container in the output"
    script_match = re.search(
        r"<script[^>]+type=\"text/formdown\"[^>]*>(?P<body>.*?)</script>",
        container_match.group("body"),
        re.DOTALL,
    )
    assert script_match is not None, "Expected a text/formdown script inside the container"
    script_body = textwrap.dedent(script_match.group("body")).strip()
    return fragment, script_body


class TestHeadingsAndEmphasis:
    def test_heading_levels_render_to_semantic_html(self):
        fragment = _render_fragment(
            """
            # Markdown Showcase

            ## Headings & Emphasis
            """
        )

        assert "<h1>Markdown Showcase</h1>" in fragment
        assert "<h2>Headings &amp; Emphasis</h2>" in fragment
        assert fragment.index("<h1>") < fragment.index("<h2>")

    def test_inline_emphasis_renders_to_strong_and_em_tags(self):
        fragment = _render_fragment("- **Bold** and *italic* text")

        assert "<strong>Bold</strong>" in fragment
        assert "<em>italic</em>" in fragment


class TestListsAndBlockquotes:
    def test_tip_blockquote_renders_with_strong_label(self):
        fragment = _render_fragment(
            """
            > **Tip:** Use Markdown to quickly share runbooks.
            """
        )

        assert "<blockquote>" in fragment
        assert "<strong>Tip:</strong>" in fragment

    def test_checklist_items_render_as_list_items(self):
        fragment = _render_fragment(
            """
            - Nested lists for checklists
              - [ ] Capture requirements
              - [x] Render Markdown beautifully
            """
        )

        assert fragment.count("<li>") == 3
        assert "[ ] Capture requirements" in fragment
        assert "[x] Render Markdown beautifully" in fragment


class TestCodeBlocksAndAdmonitions:
    def test_python_fenced_block_preserves_language_class(self):
        fragment = _render_fragment(
            """
            ```python
            print("Rendered at", datetime.now().isoformat())
            ```
            """
        )

        assert '<pre><code class="language-python">' in fragment
        assert "print(&quot;Rendered at&quot;, datetime.now().isoformat())" in fragment

    def test_admonition_renders_with_title_and_body(self):
        fragment = _render_fragment(
            '!!! note "Reusable components"\n    Wrap snippets in callouts.'
        )

        assert 'class="admonition note"' in fragment
        assert '<p class="admonition-title">Reusable components</p>' in fragment
        assert '<p>Wrap snippets in callouts.</p>' in fragment


class TestDataRepresentations:
    def test_tables_render_with_header_and_body_sections(self):
        fragment = _render_fragment(
            """
            | Feature | Syntax example |
            | ------- | -------------- |
            | Headings | `## Section title` |
            """
        )

        assert "<table>" in fragment
        assert "<thead>" in fragment and "<tbody>" in fragment
        assert "<th>Feature</th>" in fragment
        assert "<td><code>## Section title</code></td>" in fragment

    def test_definition_lists_render_with_dt_and_dd(self):
        fragment = _render_fragment(
            """
            Term
            : Details stay aligned thanks to the definition list extension.
            """
        )

        assert "<dl>" in fragment
        assert "<dt>Term</dt>" in fragment
        assert "<dd>Details stay aligned thanks to the definition list extension.</dd>" in fragment


class TestImagesAndEmbeds:
    def test_images_render_with_alt_and_title_attributes(self):
        fragment = _render_fragment(
            """
            ![Flow diagram placeholder](https://placehold.co/960x360 "Embed screenshots or generated charts")
            """
        )

        assert '<img alt="Flow diagram placeholder"' in fragment
        assert 'src="https://placehold.co/960x360"' in fragment
        assert 'title="Embed screenshots or generated charts"' in fragment

    def test_mermaid_fenced_block_identifies_language(self):
        fragment = _render_fragment(
            """
            ```mermaid
            sequenceDiagram
                participant User
            ```
            """
        )

        assert '<pre><code class="language-mermaid">' in fragment
        assert "sequenceDiagram" in fragment
        assert "participant User" in fragment


class TestFormIdeasAndDividers:
    def test_form_sketch_preserves_literal_characters_in_code_block(self):
        fragment = _render_fragment(
            """
            ```
            :::form id="feature-request"
            [name] (text, required)
            [priority] (select: low | medium | high)
            ```
            """
        )

        assert '<pre><code>' in fragment
        assert ':::form id=&quot;feature-request&quot;' in fragment
        assert '[priority] (select: low | medium | high)' in fragment
    def test_horizontal_rule_renders_between_sections(self):
        fragment = _render_fragment(
            """
            First section

            ---

            Second section
            """
        )

        assert fragment.count("<p>") == 2
        assert "<hr>" in fragment
        assert fragment.index("First section") < fragment.index("<hr>") < fragment.index("Second section")


class TestFormdownEmbeds:
    def test_formdown_code_fence_renders_form_markup(self):
        markdown_text = textwrap.dedent(
            """
            ```formdown
            Signup to our club!

            [[
            --Your name--
            T___firstName
            #placeholder|First name
            {r m5 M40}

            T___lastName
            #placeholder|Last name
            {r m5 M40}
            ]]

            --Email address--
            @___email
            {r}

            (submit|Sign up!)
            ```
            """
        ).strip()

        fragment, script_body = _render_formdown_form(markdown_text)
        html_document = _render_markdown_document(markdown_text)

        assert "data-formdown" in fragment
        assert "<script type=\"text/formdown\"" in fragment
        assert "<formdown-ui" not in fragment
        assert "Signup to our club!" in script_body
        assert "[[" in script_body
        assert "T___firstName" in script_body
        assert "<pre" not in fragment
        assert _FORMDOWN_SCRIPT_URL in html_document

    def test_formdown_group_block_is_preserved(self):
        _, script_body = _render_formdown_form(
            """
            ```formdown
            [[
            --Group heading--
            T___firstName
            ]]
            ```
            """
        )

        assert script_body.startswith("[[\n--Group heading--")
        assert script_body.endswith("]]"), script_body

    def test_formdown_placeholder_directive_is_preserved(self):
        _, script_body = _render_formdown_form(
            """
            ```formdown
            T___firstName
            #placeholder|First name
            ```
            """
        )

        assert "#placeholder|First name" in script_body

    def test_formdown_helper_directive_is_preserved(self):
        _, script_body = _render_formdown_form(
            """
            ```formdown
            T___firstName
            #helper|Share as it appears on your ID.
            ```
            """
        )

        assert "#helper|Share as it appears on your ID." in script_body

    def test_formdown_required_and_length_constraints_are_preserved(self):
        _, script_body = _render_formdown_form(
            """
            ```formdown
            T___firstName
            {r m2 M40}
            ```
            """
        )

        assert "{r m2 M40}" in script_body

    def test_formdown_upload_field_is_preserved(self):
        _, script_body = _render_formdown_form(
            """
            ```formdown
            U___supportingFile
            #helper|Optional upload, max 15 MB.
            {M15}
            ```
            """
        )

        assert "U___supportingFile" in script_body
        assert "#helper|Optional upload, max 15 MB." in script_body
        assert "{M15}" in script_body

    def test_formdown_submit_action_is_preserved(self):
        _, script_body = _render_formdown_form(
            """
            ```formdown
            (submit|Send request)
            ```
            """
        )

        assert "(submit|Send request)" in script_body

    def test_formdown_markup_injects_loader_script(self):
        html_document = _render_markdown_document(
            "<div data-formdown data-form=\"support-request\"></div>"
        )

        assert _FORMDOWN_SCRIPT_URL in html_document
        assert html_document.index('</main>') < html_document.index(_FORMDOWN_SCRIPT_URL)

    def test_formdown_script_tag_injects_loader_script(self):
        html_document = _render_markdown_document(
            "<script type=\"text/formdown\">Demo</script>"
        )

        assert _FORMDOWN_SCRIPT_URL in html_document

    def test_unrelated_markdown_does_not_include_formdown_script(self):
        html_document = _render_markdown_document(
            """
            # Release notes

            Welcome to the changelog.
            """
        )

        assert _FORMDOWN_SCRIPT_URL not in html_document

    def test_formdown_showcase_template_uses_formdown_code_fence(self):
        template_path = Path("upload_templates/contents/formdown_showcase.md")
        markdown_text = template_path.read_text(encoding="utf-8")

        assert "```formdown" in markdown_text

    def test_formdown_showcase_template_renders_with_formdown_markup(self):
        template_path = Path("upload_templates/contents/formdown_showcase.md")
        markdown_text = template_path.read_text(encoding="utf-8")

        html_document = _render_markdown_document(markdown_text)

        assert _FORMDOWN_SCRIPT_URL in html_document
        assert "data-formdown" in html_document
        assert "<formdown-ui" not in html_document
        assert "Share a support request" in html_document
        assert "U___supportingFile" in html_document
        assert "<pre" not in html_document
        assert "formdown.net" in html_document


class TestGithubStyleLinks:
    def test_relative_link_renders_with_normalized_path(self):
        fragment = _render_fragment("Navigate to [[About]] for details.")

        assert '<a href="/about">About</a>' in fragment

    def test_relative_link_with_custom_label_uses_pipe_syntax(self):
        fragment = _render_fragment("Refer to [[Guides/Getting Started|the quickstart guide]].")

        assert '<a href="/guides/getting-started">the quickstart guide</a>' in fragment

    def test_relative_link_with_anchor_slugifies_target_heading(self):
        fragment = _render_fragment("See [[Guides/Getting Started#Deep Dive|the deep dive section]].")

        assert '<a href="/guides/getting-started#deep-dive">the deep dive section</a>' in fragment

    def test_relative_anchor_only_link_targets_heading_on_same_page(self):
        fragment = _render_fragment("Jump to [[#Usage Notes]] for details.")

        assert '<a href="#usage-notes">#Usage Notes</a>' in fragment

    def test_relative_link_to_markdown_file_preserves_extension(self):
        fragment = _render_fragment("Read [[Docs/API.md|API reference]].")

        assert '<a href="/docs/api.md">API reference</a>' in fragment

    def test_multiple_relative_links_convert_independently(self):
        fragment = _render_fragment("See [[About]] alongside [[Guides/Overview|the overview]].")

        assert '<a href="/about">About</a>' in fragment
        assert '<a href="/guides/overview">the overview</a>' in fragment

    def test_relative_link_with_lowercase_name_preserves_label(self):
        fragment = _render_fragment("Check out [[echo]] next.")

        assert '<a href="/echo">echo</a>' in fragment

    def test_relative_link_with_explicit_trailing_slash_is_preserved(self):
        fragment = _render_fragment("Browse [[Guides/Deep Dive/|the deep dive index]].")

        assert '<a href="/guides/deep-dive/">the deep dive index</a>' in fragment

    def test_invalid_relative_link_is_left_unchanged(self):
        fragment = _render_fragment("Avoid [[   |blank]] targets.")

        assert '[[   |blank]]' in fragment

