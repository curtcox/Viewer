"""Heuristics for determining server implementation languages."""

import re


def detect_server_language(definition: str | None) -> str:
    """Return the probable implementation language for a server definition.

    The heuristics prefer explicit signals (like shebang lines) and fall back
    to Python when no strong Bash indicators are present.
    """

    if not definition:
        return "python"

    text = str(definition)
    stripped = text.lstrip()
    first_line = stripped.splitlines()[0].lower() if stripped else ""

    if first_line.startswith("#!"):
        if "python" in first_line:
            return "python"
        if "bash" in first_line or first_line.endswith("/sh") or "/sh " in first_line:
            return "bash"
        if "clojure" in first_line or "bb" in first_line or "babashka" in first_line:
            return "clojure"

    python_markers = (
        r"^\s*def\s+\w+\s*\(",
        r"^\s*import\s+\w+",
        r"^\s*from\s+\w+\s+import",
    )
    if any(re.search(pattern, text, re.MULTILINE) for pattern in python_markers):
        return "python"

    clojure_markers = (
        r"\(ns\b",
        r"\(defn\s+main",
        r"\(println\b",
    )
    if any(re.search(pattern, text, re.MULTILINE) for pattern in clojure_markers):
        return "clojure"

    bash_markers = (
        r"^\s*set\s+-[a-zA-Z]*[EeUuOoFfPp][a-zA-Z]*",
        r"^\s*echo\b",
        r"^\s*function\s+\w+\s*\{",
        r"\bthen\b",
        r"\bfi\b",
    )
    if any(re.search(pattern, text, re.MULTILINE) for pattern in bash_markers):
        return "bash"

    return "python"


__all__ = ["detect_server_language"]
