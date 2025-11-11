"""Text highlighting utilities for search results."""

from typing import List
from markupsafe import escape


# Default context length for snippets
DEFAULT_CONTEXT_CHARS: int = 60


class TextHighlighter:
    """Provides highlighting functionality for search queries."""

    @staticmethod
    def has_match(text: str | None, query_lower: str) -> bool:
        """Return True when the search term appears in the supplied text."""
        if not text or not query_lower:
            return False
        return query_lower in text.lower()

    @staticmethod
    def highlight_full(text: str | None, query_lower: str) -> str:
        """Return the supplied text with all matches wrapped in <mark> tags."""
        if not text:
            return ""
        if not query_lower:
            return str(escape(text))

        lower_text = text.lower()
        query_length = len(query_lower)
        if query_length == 0:
            return str(escape(text))

        result_parts: List[str] = []
        cursor = 0

        while True:
            match_index = lower_text.find(query_lower, cursor)
            if match_index == -1:
                remaining = text[cursor:]
                if remaining:
                    result_parts.append(str(escape(remaining)))
                break

            if match_index > cursor:
                result_parts.append(str(escape(text[cursor:match_index])))

            matched_text = text[match_index: match_index + query_length]
            result_parts.append(f"<mark>{escape(matched_text)}</mark>")
            cursor = match_index + query_length

        return "".join(result_parts)

    @staticmethod
    def highlight_snippet(
        text: str | None,
        query_lower: str,
        *,
        context: int = DEFAULT_CONTEXT_CHARS
    ) -> str:
        """Return a snippet of text around the first match with highlighting."""
        if not text or not query_lower:
            return ""

        lower_text = text.lower()
        match_index = lower_text.find(query_lower)
        if match_index == -1:
            return ""

        query_length = len(query_lower)
        start = max(match_index - context, 0)
        end = min(match_index + query_length + context, len(text))

        snippet = text[start:end]
        highlighted = TextHighlighter.highlight_full(snippet, query_lower)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{highlighted}{suffix}"


__all__ = ["TextHighlighter", "DEFAULT_CONTEXT_CHARS"]
