# ruff: noqa: F821, F706
"""Server that adds hyperlinks to CIDs found in text.

Accepts text as input and replaces CID references with clickable links.
For HTML content, uses anchor tags.
For literal CIDs (embedded content < 94 chars), uses data URLs.
"""

import re
from typing import Any, Optional

from cid_core import (
    CID_CHARACTER_CLASS,
    CID_LENGTH,
    CID_MIN_LENGTH,
    is_normalized_cid,
)

# Pattern to find potential CIDs in text
CID_PATTERN = re.compile(rf"\b([{CID_CHARACTER_CLASS}]{{{CID_MIN_LENGTH},{CID_LENGTH}}})\b")

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


def _replace_cid_html(text: str, cid: str, match_start: int) -> Optional[str]:
    """Generate HTML anchor replacement for a CID."""
    if _is_cid_in_link(text, cid, match_start):
        return None  # Don't replace, already in a link

    if not is_normalized_cid(cid):
        return None

    # Only link CIDs that match the canonical encoding produced by this app.
    # In practice, generated CIDs always have a length-prefix encoding that starts
    # with 'A' (high bits of the 48-bit length are zero for realistic content sizes).
    if not cid.startswith("A"):
        return None

    # Use relative path for hash-based CIDs
    return f'<a href="cid_links/{cid}.txt">{cid}</a>'


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


def main(text: Any = "", *, context=None):
    """Add hyperlinks to CID references found in the input text.

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

    # Convert newlines to HTML line breaks
    text = text.replace("\n", "<br>")

    output = '<html>' + _process_html(text) + '</html>'
    content_type = "text/html"

    return {
        "output": output,
        "content_type": content_type,
    }
