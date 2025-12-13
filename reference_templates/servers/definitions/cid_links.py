# ruff: noqa: F821, F706
"""Server that adds hyperlinks to CIDs found in text.

Accepts text as input and replaces CID references with clickable links.
For HTML content, uses anchor tags. For Markdown, uses markdown link syntax.
For literal CIDs (embedded content < 94 chars), uses data URLs.
"""

import base64
import re
from typing import Any, Optional

from cid_core import (
    CID_CHARACTER_CLASS,
    CID_LENGTH,
    CID_MIN_LENGTH,
    extract_literal_content,
    is_literal_cid,
    is_normalized_cid,
)

# Pattern to find potential CIDs in text
CID_PATTERN = re.compile(rf"\b([{CID_CHARACTER_CLASS}]{{{CID_MIN_LENGTH},{CID_LENGTH}}})\b")


def _is_html(text: str) -> bool:
    """Detect if text is HTML using simple heuristics.

    Returns True if the text appears to be HTML based on:
    - Contains common HTML tags like <html>, <body>, <div>, <p>, <a>, etc.
    - Contains DOCTYPE declaration
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    # Check for DOCTYPE
    if text_lower.startswith("<!doctype"):
        return True

    # Check for common HTML tags
    html_tag_pattern = re.compile(
        r"<\s*(html|head|body|div|span|p|a|img|table|ul|ol|li|"
        r"h[1-6]|form|input|button|script|style|link|meta|br|hr)\b",
        re.IGNORECASE,
    )
    if html_tag_pattern.search(text):
        return True

    # Check for self-closing tags or any tag with attributes
    if re.search(r"<[a-zA-Z][^>]*>", text):
        return True

    return False


def _is_cid_in_link(text: str, cid: str, match_start: int) -> bool:
    """Check if a CID at the given position is already a link target in HTML.

    Looks backwards from the match position to see if this CID is inside an href attribute.
    """
    # Look at the text before this CID to see if we're in an href
    prefix = text[max(0, match_start - 200) : match_start]

    # Check if we're inside an href attribute (e.g., href="/CID" or href="CID")
    # Look for href=" followed by optional path chars, but no closing quote before our position
    href_pattern = re.compile(r'href\s*=\s*["\'][^"\']*$', re.IGNORECASE)
    if href_pattern.search(prefix):
        return True

    # Check if the CID is the text content of an anchor tag that links to it
    # e.g., <a href="/CID.txt">CID</a>
    # Look for pattern: <a href="/CID anything">...CID
    anchor_pattern = re.compile(
        rf'<a\s+[^>]*href\s*=\s*["\'][^"\']*{re.escape(cid[:20])}[^"\']*["\'][^>]*>[^<]*$',
        re.IGNORECASE,
    )
    if anchor_pattern.search(prefix):
        return True

    return False


def _get_data_url(content: bytes) -> str:
    """Create a data URL for the given content."""
    # Try to decode as UTF-8 text
    try:
        content.decode("utf-8")
        # Use text/plain for valid UTF-8
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:text/plain;base64,{encoded}"
    except UnicodeDecodeError:
        # Use application/octet-stream for binary
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:application/octet-stream;base64,{encoded}"


def _replace_cid_html(text: str, cid: str, match_start: int) -> Optional[str]:
    """Generate HTML anchor replacement for a CID."""
    if _is_cid_in_link(text, cid, match_start):
        return None  # Don't replace, already in a link

    if not is_normalized_cid(cid):
        return None

    # Check if this is a literal CID with embedded content
    if is_literal_cid(cid):
        content = extract_literal_content(cid)
        if content is not None:
            data_url = _get_data_url(content)
            return f'<a href="{data_url}">{cid}</a>'

    # Use server path for hash-based CIDs
    return f'<a href="/{cid}.txt">{cid}</a>'


def _replace_cid_markdown(cid: str) -> Optional[str]:
    """Generate Markdown link replacement for a CID."""
    if not is_normalized_cid(cid):
        return None

    # Check if this is a literal CID with embedded content
    if is_literal_cid(cid):
        content = extract_literal_content(cid)
        if content is not None:
            data_url = _get_data_url(content)
            return f"[{cid}]({data_url})"

    # Use server path for hash-based CIDs
    return f"[{cid}](/{cid}.txt)"


def _process_html(text: str) -> str:
    """Process HTML text, adding links to CIDs."""
    result = []
    last_end = 0

    for match in CID_PATTERN.finditer(text):
        cid = match.group(1)
        start = match.start(1)

        replacement = _replace_cid_html(text, cid, start)
        if replacement is not None:
            result.append(text[last_end:start])
            result.append(replacement)
            last_end = match.end(1)

    result.append(text[last_end:])
    return "".join(result)


def _process_markdown(text: str) -> str:
    """Process Markdown text, adding links to CIDs."""
    result = []
    last_end = 0

    for match in CID_PATTERN.finditer(text):
        cid = match.group(1)
        start = match.start(1)

        # Check if already in a markdown link: [text](url) or [text][ref]
        # Look at surrounding context
        prefix = text[max(0, start - 100) : start]
        suffix = text[match.end(1) : match.end(1) + 100]

        # Skip if inside markdown link text [...] or link URL (...)
        # Pattern: we're after a [ and before a ]
        if re.search(r"\[[^\]]*$", prefix) and re.search(r"^[^\[]*\]", suffix):
            continue  # Inside link text
        # Pattern: we're after a ( from a link and before )
        if re.search(r"\]\([^)]*$", prefix) and re.search(r"^[^(]*\)", suffix):
            continue  # Inside link URL

        replacement = _replace_cid_markdown(cid)
        if replacement is not None:
            result.append(text[last_end:start])
            result.append(replacement)
            last_end = match.end(1)

    result.append(text[last_end:])
    return "".join(result)


def main(text: Any = "", *, context=None):
    """Add hyperlinks to CID references found in the input text.

    Automatically detects whether the text is HTML or Markdown based on
    content heuristics. For HTML, CIDs are wrapped in anchor tags.
    For Markdown, CIDs become markdown links.

    For literal CIDs (those with embedded content, less than 94 characters),
    data URLs are used instead of server paths.

    Args:
        text: The input text containing CID references to link.
        context: Optional context (unused but accepted for compatibility).

    Returns:
        Dict with 'output' containing the processed text and 'content_type'.
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    else:
        text = str(text or "")

    if not text.strip():
        return {
            "output": text,
            "content_type": "text/plain",
        }

    is_html = _is_html(text)

    if is_html:
        output = _process_html(text)
        content_type = "text/html"
    else:
        output = _process_markdown(text)
        content_type = "text/plain"

    return {
        "output": output,
        "content_type": content_type,
    }
