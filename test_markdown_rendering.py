"""Unit tests that verify Markdown features render to the expected HTML."""

from __future__ import annotations

import textwrap

from cid_utils import _render_markdown_document


def _render_fragment(markdown_text: str) -> str:
    """Render Markdown text and return the HTML fragment inside the main tag."""

    normalized = textwrap.dedent(markdown_text).strip() + "\n"
    html_document = _render_markdown_document(normalized)

    marker = '<main class="markdown-body">'
    start = html_document.index(marker)
    fragment_with_tag = html_document[start:].split("</main>", 1)[0]
    fragment = fragment_with_tag.split('>', 1)[1]
    return fragment.strip()


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


class TestGithubStyleLinks:
    def test_relative_link_renders_with_normalized_path(self):
        fragment = _render_fragment("Navigate to [[About]] for details.")

        assert '<a href="/about/">About</a>' in fragment

    def test_relative_link_with_custom_label_uses_pipe_syntax(self):
        fragment = _render_fragment("Refer to [[Guides/Getting Started|the quickstart guide]].")

        assert '<a href="/guides/getting-started/">the quickstart guide</a>' in fragment

    def test_relative_link_with_anchor_slugifies_target_heading(self):
        fragment = _render_fragment("See [[Guides/Getting Started#Deep Dive|the deep dive section]].")

        assert '<a href="/guides/getting-started/#deep-dive">the deep dive section</a>' in fragment

    def test_relative_anchor_only_link_targets_heading_on_same_page(self):
        fragment = _render_fragment("Jump to [[#Usage Notes]] for details.")

        assert '<a href="#usage-notes">#Usage Notes</a>' in fragment

    def test_relative_link_to_markdown_file_preserves_extension(self):
        fragment = _render_fragment("Read [[Docs/API.md|API reference]].")

        assert '<a href="/docs/api.md">API reference</a>' in fragment

    def test_multiple_relative_links_convert_independently(self):
        fragment = _render_fragment("See [[About]] alongside [[Guides/Overview|the overview]].")

        assert '<a href="/about/">About</a>' in fragment
        assert '<a href="/guides/overview/">the overview</a>' in fragment

    def test_invalid_relative_link_is_left_unchanged(self):
        fragment = _render_fragment("Avoid [[   |blank]] targets.")

        assert '[[   |blank]]' in fragment

