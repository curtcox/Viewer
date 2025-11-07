"""Content rendering functionality for Markdown, Mermaid, and Formdown.

This module handles rendering of various content formats into HTML,
including GitHub-style Markdown, Mermaid diagrams, and Formdown forms.
"""

import base64
import html
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests
from sqlalchemy.exc import SQLAlchemyError

try:
    import markdown  # type: ignore
    _markdown_available = True
    _markdown_import_error = None
except ModuleNotFoundError as exc:  # pragma: no cover
    markdown = None  # type: ignore[assignment]
    _markdown_available = False
    _markdown_import_error = exc

from cid_core import generate_cid, base64url_encode
from cid_presenter import cid_path, format_cid
from cid_storage import ensure_cid_exists, get_cid_content
from formdown_renderer import render_formdown_html


# ============================================================================
# RENDERING CONFIGURATION
# ============================================================================

# Markdown extensions to use
MARKDOWN_EXTENSIONS = [
    'extra',
    'admonition',
    'sane_lists',
]

# Patterns to detect markdown content
MARKDOWN_INDICATOR_PATTERNS = [
    re.compile(r'(^|\n)#{1,6}\s+\S'),  # Headers
    re.compile(r'(^|\n)(?:\*|-|\+)\s+\S'),  # Bullet lists
    re.compile(r'(^|\n)\d+\.\s+\S'),  # Numbered lists
    re.compile(r'(^|\n)>\s+\S'),  # Blockquotes
    re.compile(r'```'),  # Code blocks
    re.compile(r'\[[^\]]+\]\([^\)]+\)'),  # Links
    re.compile(r'!\[[^\]]*\]\([^\)]+\)'),  # Images
    re.compile(r'(^|\n)[^\n]+\n[=-]{3,}\s*(\n|$)'),  # Setext headers
]

# Patterns for inline formatting
INLINE_BOLD_PATTERN = re.compile(r'\*\*(?=\S)(.+?)(?<=\S)\*\*')
INLINE_ITALIC_PATTERN = re.compile(r'(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)')
INLINE_CODE_PATTERN = re.compile(r'`[^`\n]+`')

# GitHub-style relative link patterns
GITHUB_RELATIVE_LINK_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")
GITHUB_RELATIVE_LINK_PATH_SANITIZER = re.compile(r"[^A-Za-z0-9._/\-]+")
GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER = re.compile(r"[^a-z0-9\-]+")

# Formdown and Mermaid fence patterns
FORMDOWN_FENCE_RE = re.compile(r"(^|\n)[ \t]*```formdown\s*\n(.*?)```", re.DOTALL)
MERMAID_FENCE_RE = re.compile(r"(^|\n)([ \t]*)```mermaid\s*\n(.*?)```", re.DOTALL)


# ============================================================================
# TEXT DECODING AND MARKDOWN DETECTION
# ============================================================================

def decode_text_safely(data: bytes) -> Optional[str]:
    """Decode bytes as UTF-8 if possible, returning None on failure.

    Args:
        data: Bytes to decode

    Returns:
        Decoded string or None if decoding fails

    Example:
        >>> decode_text_safely(b"hello")
        'hello'
        >>> decode_text_safely(b"\\xff\\xfe")  # Invalid UTF-8
        None
    """
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return None


def count_bullet_lines(lines: list[str]) -> int:
    """Count lines that start with bullet list markers.

    Args:
        lines: List of text lines

    Returns:
        Number of lines starting with bullet markers

    Example:
        >>> count_bullet_lines(['- item', '* thing', 'normal'])
        2
    """
    return sum(1 for line in lines if line.lstrip().startswith(('- ', '* ', '+ ')))


def looks_like_markdown(text: str) -> bool:
    """Heuristically determine whether text is likely Markdown content.

    Uses multiple indicators including headers, lists, links, and formatting
    to make an educated guess about whether the text is Markdown.

    Args:
        text: Text content to analyze

    Returns:
        True if text appears to be Markdown

    Example:
        >>> looks_like_markdown("# Title\\n\\nSome text")
        True
        >>> looks_like_markdown("Plain text")
        False
    """
    if not text or not text.strip():
        return False

    # Binary data is not markdown
    if '\x00' in text:
        return False

    # Count structural indicators
    indicator_hits = sum(
        1 for pattern in MARKDOWN_INDICATOR_PATTERNS if pattern.search(text)
    )

    # Count inline formatting
    inline_format_score = sum(
        1
        for pattern in (INLINE_BOLD_PATTERN, INLINE_ITALIC_PATTERN, INLINE_CODE_PATTERN)
        if pattern.search(text)
    )

    # Two or more indicators suggests markdown
    if indicator_hits + inline_format_score >= 2:
        return True

    lines = text.strip().splitlines()
    if not lines:
        return False

    # Single ATX header at start
    if lines[0].startswith('# '):
        return True

    # Setext header (underlined)
    if len(lines) > 1 and set(lines[1].strip()) in ({'='}, {'-'}):
        return True

    # Multiple bullet points
    if count_bullet_lines(lines) >= 2:
        return True

    return False


def extract_markdown_title(text: str) -> str:
    """Extract the first header from Markdown text as a title.

    Args:
        text: Markdown text

    Returns:
        Title string (defaults to 'Document' if no header found)

    Example:
        >>> extract_markdown_title("# My Title\\n\\nContent")
        'My Title'
        >>> extract_markdown_title("No headers here")
        'Document'
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            return stripped.lstrip('#').strip() or 'Document'
    return 'Document'


# ============================================================================
# GITHUB-STYLE LINK CONVERSION
# ============================================================================

def normalize_github_relative_link_target(raw_target: str) -> Optional[str]:
    """Normalize GitHub-style relative link targets.

    Converts wiki-style links like [[Page Name]] or [[path#anchor]] into
    normalized paths suitable for use in Markdown links.

    Args:
        raw_target: Raw link target (may include |label syntax)

    Returns:
        Normalized path/anchor or None if invalid

    Example:
        >>> normalize_github_relative_link_target("Some Page")
        '/some-page'
        >>> normalize_github_relative_link_target("Page#section")
        '/page#section'
    """
    if not raw_target:
        return None

    target = raw_target.strip()
    if not target:
        return None

    # Handle pipe syntax: [[target|label]] - use only target
    primary = target.split('|', 1)[0].strip()
    if not primary:
        return None

    # Split into page and anchor parts
    page_part, _, anchor_part = primary.partition('#')

    normalized_path = ""
    if page_part:
        preserve_trailing_slash = page_part.rstrip().endswith('/')
        # Replace spaces with hyphens
        prepared = re.sub(r"\s+", "-", page_part.strip())
        # Remove invalid characters
        cleaned = GITHUB_RELATIVE_LINK_PATH_SANITIZER.sub('', prepared)
        segments = [segment for segment in cleaned.split('/') if segment]
        if segments:
            normalized_segments = [segment.lower() for segment in segments]
            normalized_path = '/' + '/'.join(normalized_segments)
            if preserve_trailing_slash:
                normalized_path += '/'

    anchor_fragment = ""
    if anchor_part:
        anchor_slug = anchor_part.strip().lower()
        anchor_slug = re.sub(r"\s+", '-', anchor_slug)
        anchor_slug = GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER.sub('', anchor_slug)
        anchor_slug = anchor_slug.strip('-')
        if anchor_slug:
            anchor_fragment = f'#{anchor_slug}'

    if normalized_path and anchor_fragment:
        return f'{normalized_path}{anchor_fragment}'
    if normalized_path:
        return normalized_path
    if anchor_fragment:
        return anchor_fragment
    return None


def convert_github_relative_links(text: str) -> str:
    """Rewrite GitHub-style [[link]] syntax to standard Markdown links.

    Args:
        text: Markdown text with [[...]] links

    Returns:
        Text with links converted to [text](url) format

    Example:
        >>> convert_github_relative_links("See [[Other Page]]")
        'See [Other Page](/other-page)'
        >>> convert_github_relative_links("[[Page|Custom Label]]")
        'See [Custom Label](/page)'
    """
    def replacement(match: re.Match[str]) -> str:
        inner = match.group(1)
        if not inner:
            return match.group(0)

        label, target = inner, inner
        if '|' in inner:
            target, label = (part.strip() for part in inner.split('|', 1))
        else:
            label = inner.strip()
            target = label

        normalized_target = normalize_github_relative_link_target(target)
        display_text = label.strip() or target.strip()
        if not normalized_target or not display_text:
            return match.group(0)

        return f"[{display_text}]({normalized_target})"

    return GITHUB_RELATIVE_LINK_PATTERN.sub(replacement, text)


# ============================================================================
# MERMAID DIAGRAM RENDERING
# ============================================================================

class MermaidRenderingError(RuntimeError):
    """Raised when a Mermaid diagram cannot be rendered."""


@dataclass
class MermaidRenderLocation:
    """Represents where a rendered Mermaid diagram is stored."""

    is_cid: bool
    value: str

    def img_src(self) -> str:
        """Get the image source URL for this location.

        Returns:
            URL or path to the image
        """
        if self.is_cid:
            path = cid_path(self.value, "svg") or f"/{self.value}.svg"
            return path
        return self.value


class MermaidRenderer:
    """Render Mermaid diagrams through mermaid.ink and store them as CIDs."""

    API_ENDPOINT = "https://mermaid.ink/svg"
    REMOTE_SVG_BASE = "https://mermaid.ink/svg/"
    REQUEST_TIMEOUT_SECONDS = 20

    def __init__(self) -> None:
        """Initialize the renderer with a session and cache."""
        self._session = requests.Session()
        self._cache: Dict[str, MermaidRenderLocation] = {}

    def render_html(self, source: str, user_id: Optional[str] = None) -> str:
        """Render Mermaid diagram source to HTML figure element.

        Args:
            source: Mermaid diagram source code
            user_id: Optional user ID for CID storage

        Returns:
            HTML figure element with the rendered diagram

        Raises:
            MermaidRenderingError: If rendering fails
        """
        normalized = (source or "").strip()
        if not normalized:
            raise MermaidRenderingError("Mermaid diagram was empty")

        cached = self._cache.get(normalized)
        if cached is not None:
            return self._build_html(cached, normalized)

        location: Optional[MermaidRenderLocation]
        try:
            svg_bytes = self._fetch_svg(normalized)
        except (requests.RequestException, ValueError, OSError, RuntimeError):
            # Fall back to remote rendering on network, processing, or runtime errors
            location = self._remote_location(normalized)
        else:
            if not svg_bytes:
                raise MermaidRenderingError("Mermaid renderer returned no data")

            location = self._store_svg(svg_bytes, user_id)
            if location is None:
                # Fall back to data URL
                data_url = self._build_data_url(svg_bytes)
                location = MermaidRenderLocation(is_cid=False, value=data_url)

        if location is None:
            raise MermaidRenderingError("Mermaid renderer failed to produce an image")

        self._cache[normalized] = location
        return self._build_html(location, normalized)

    def _fetch_svg(self, source: str) -> bytes:
        """Fetch SVG from mermaid.ink API.

        Args:
            source: Mermaid diagram source

        Returns:
            SVG content as bytes

        Raises:
            requests.RequestException: If fetch fails
        """
        response = self._session.post(
            self.API_ENDPOINT,
            data=source.encode("utf-8"),
            timeout=self.REQUEST_TIMEOUT_SECONDS,
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()
        return response.content

    def _store_svg(self, svg_bytes: bytes, user_id: Optional[str]) -> Optional[MermaidRenderLocation]:
        """Store SVG as a CID.

        Args:
            svg_bytes: SVG content
            user_id: User ID for ownership

        Returns:
            Location object or None if storage fails
        """
        try:
            cid_value = format_cid(generate_cid(svg_bytes))
            path = cid_path(cid_value)

            # Check if already exists
            if path and get_cid_content(path):
                return MermaidRenderLocation(is_cid=True, value=cid_value)

            # Create new CID record
            ensure_cid_exists(cid_value, svg_bytes, user_id)
            return MermaidRenderLocation(is_cid=True, value=cid_value)
        except (ValueError, OSError, AttributeError, SQLAlchemyError):
            # Fall back gracefully if CID storage fails (database or filesystem errors)
            return None

    @staticmethod
    def _build_data_url(svg_bytes: bytes) -> str:
        """Build a data URL from SVG bytes.

        Args:
            svg_bytes: SVG content

        Returns:
            Data URL string
        """
        encoded = base64.b64encode(svg_bytes).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

    @staticmethod
    def _encode_source(source: str) -> str:
        """Encode Mermaid source for URL embedding.

        Args:
            source: Mermaid diagram source

        Returns:
            Base64url-encoded source
        """
        return base64url_encode(source.encode("utf-8"))

    @classmethod
    def _remote_location(cls, source: str) -> Optional[MermaidRenderLocation]:
        """Build a remote URL for mermaid.ink rendering.

        Args:
            source: Mermaid diagram source

        Returns:
            Location pointing to remote mermaid.ink URL
        """
        encoded = cls._encode_source(source)
        remote_url = f"{cls.REMOTE_SVG_BASE}{encoded}"
        return MermaidRenderLocation(is_cid=False, value=remote_url)

    @classmethod
    def _build_html(cls, location: MermaidRenderLocation, source: str) -> str:
        """Build HTML figure element for the diagram.

        Args:
            location: Where the diagram is stored
            source: Original Mermaid source (for data attribute)

        Returns:
            HTML figure element
        """
        escaped_src = html.escape(location.img_src(), quote=True)
        encoded_diagram = cls._encode_source(source)
        return (
            f'<figure class="mermaid-diagram" data-mermaid-source="{encoded_diagram}">\n'
            f'  <img src="{escaped_src}" alt="Mermaid diagram" loading="lazy" decoding="async">\n'
            f"</figure>\n"
        )


# Global renderer instance
_mermaid_renderer = MermaidRenderer()


def replace_mermaid_fences(text: str) -> Tuple[str, bool]:
    """Replace ```mermaid fences with rendered diagram figures.

    Args:
        text: Markdown text with mermaid code blocks

    Returns:
        Tuple of (converted_text, found_any)
    """
    found = False

    def replacement(match: re.Match[str]) -> str:
        nonlocal found
        prefix = match.group(1)
        indent = match.group(2)
        diagram_source = (match.group(3) or "").rstrip("\n")
        try:
            figure_html = _mermaid_renderer.render_html(diagram_source)
        except (MermaidRenderingError, Exception):  # pylint: disable=broad-exception-caught
            # Keep original fence if any rendering error occurs (defensive fallback)
            return match.group(0)
        found = True
        return f"{prefix}{indent}{figure_html}"

    replaced = MERMAID_FENCE_RE.sub(replacement, text)
    return replaced, found


# ============================================================================
# FORMDOWN RENDERING
# ============================================================================

def replace_formdown_fences(text: str) -> Tuple[str, bool]:
    """Replace ```formdown fences with rendered HTML forms.

    Args:
        text: Markdown text with formdown code blocks

    Returns:
        Tuple of (converted_text, found_any)
    """
    found = False

    def replacement(match: re.Match[str]) -> str:
        nonlocal found
        found = True
        prefix = match.group(1)
        inner = match.group(2).rstrip("\n")
        html_form = render_formdown_html(inner)
        if prefix:
            return f"{prefix}{html_form}"
        return html_form

    converted = FORMDOWN_FENCE_RE.sub(replacement, text)
    return converted, found


# ============================================================================
# MARKDOWN DOCUMENT RENDERING
# ============================================================================

def render_markdown_document(text: str) -> str:
    """Render Markdown text to a standalone HTML document.

    Converts GitHub-style links, renders Mermaid diagrams and Formdown forms,
    then converts Markdown to HTML and wraps in a complete HTML document with styling.

    Args:
        text: Markdown source text

    Returns:
        Complete HTML document

    Raises:
        RuntimeError: If markdown module is not available

    Example:
        >>> html = render_markdown_document("# Title\\n\\nContent")
        >>> "<!DOCTYPE html>" in html
        True
    """
    if not _markdown_available or markdown is None:
        raise RuntimeError(
            "Missing optional dependency 'Markdown'. Run './install' or "
            "'pip install -r requirements.txt' before rendering Markdown documents."
        ) from _markdown_import_error

    # Convert special syntaxes
    converted = convert_github_relative_links(text)
    converted, _ = replace_mermaid_fences(converted)
    converted, _ = replace_formdown_fences(converted)

    # Render markdown
    body = markdown.markdown(
        converted,
        extensions=MARKDOWN_EXTENSIONS,
        output_format='html5'
    )

    title = extract_markdown_title(text)

    # Build complete HTML document
    return _build_html_document(title, body)


def _build_html_document(title: str, body: str) -> str:
    """Build a complete HTML document with styling.

    Args:
        title: Document title
        body: Rendered HTML body content

    Returns:
        Complete HTML document
    """
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        f"  <title>{title}</title>\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "  <style>\n"
        + _get_document_styles() +
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <main class=\"markdown-body\">\n"
        f"  {body}\n"
        "  </main>\n"
        "</body>\n"
        "</html>\n"
    )


def _get_document_styles() -> str:
    """Get CSS styles for rendered documents.

    Returns:
        CSS style string
    """
    return """    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin: 0;
      padding: 2rem;
      background: #f7f7f8;
      color: #111827;
    }
    .markdown-body {
      max-width: none;
      width: 100%;
      margin: 0;
      background: #fff;
      padding: 2rem 3rem;
      border-radius: 12px;
      box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
    }
    pre {
      background: #0f172a;
      color: #f8fafc;
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
    }
    code {
      background: rgba(15, 23, 42, 0.08);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      font-size: 0.95em;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 1.5rem 0;
    }
    th, td {
      border: 1px solid #e2e8f0;
      padding: 0.6rem 0.75rem;
      text-align: left;
    }
    blockquote {
      border-left: 4px solid #3b82f6;
      padding-left: 1rem;
      color: #1f2937;
      background: rgba(59, 130, 246, 0.08);
    }
    .admonition {
      border-left: 4px solid #7c3aed;
      background: rgba(124, 58, 237, 0.08);
      padding: 1rem 1.25rem;
      border-radius: 8px;
      margin: 1.5rem 0;
    }
    .admonition-title {
      font-weight: 600;
      margin-bottom: 0.5rem;
    }
    img, iframe {
      max-width: 100%;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.12);
    }
    .mermaid-diagram {
      margin: 2rem 0;
      text-align: center;
    }
    .mermaid-diagram img {
      display: inline-block;
    }
    .formdown-document {
      margin: 2rem 0;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }
    .formdown-form {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      padding: 1.5rem;
      border: 1px solid rgba(148, 163, 184, 0.35);
      border-radius: 12px;
      background: #f8fafc;
    }
    .formdown-field {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .formdown-field--choices {
      gap: 0.75rem;
    }
    .formdown-heading {
      font-weight: 600;
      color: #0f172a;
    }
    .formdown-heading--form {
      margin-bottom: 0;
    }
    .formdown-paragraph {
      color: #475569;
    }
    .formdown-paragraph--form {
      margin: 0;
    }
    .formdown-label {
      font-weight: 600;
      color: #0f172a;
    }
    .formdown-input {
      display: block;
      width: 100%;
      padding: 0.5rem 0.75rem;
      border-radius: 8px;
      border: 1px solid rgba(148, 163, 184, 0.5);
      font-size: 1rem;
      color: #0f172a;
      background: #fff;
    }
    .formdown-input:focus {
      outline: 2px solid #3b82f6;
      outline-offset: 1px;
    }
    .formdown-options {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
    }
    .formdown-options--vertical {
      flex-direction: column;
    }
    .formdown-option {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: 500;
      color: #0f172a;
    }
    .formdown-option-label {
      display: inline-block;
    }
    .formdown-help {
      font-size: 0.875rem;
      color: #64748b;
    }
    .formdown-separator {
      border: none;
      border-top: 1px solid rgba(148, 163, 184, 0.35);
      margin: 0;
    }
    .formdown-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      border-radius: 8px;
      padding: 0.5rem 1.25rem;
      font-weight: 600;
      cursor: pointer;
      border: none;
    }
    .formdown-button--submit {
      background: #2563eb;
      color: #f8fafc;
    }
    .formdown-button--reset {
      background: #e2e8f0;
      color: #0f172a;
    }
"""
