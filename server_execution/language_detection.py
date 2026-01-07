"""Heuristics for determining server implementation languages."""

from __future__ import annotations

import re
from dataclasses import dataclass

COMMON_SHELL_TOKENS = {
    # Frequently used Unix utilities
    "awk",
    "cat",
    "cd",
    "chmod",
    "chown",
    "cp",
    "curl",
    "cut",
    "diff",
    "echo",
    "env",
    "find",
    "grep",
    "gunzip",
    "gzip",
    "head",
    "ls",
    "mkdir",
    "mv",
    "pwd",
    "rm",
    "rsync",
    "scp",
    "sed",
    "sort",
    "sudo",
    "tail",
    "tar",
    "touch",
    "tr",
    "uniq",
    "wc",
    "wget",
    "xargs",
    # Punctuation and operators common in shell pipelines
    "|",
    "||",
    "&&",
    ">",
    ">>",
    "<",
    ";",
    "$",
    "$(",
}


@dataclass
class LanguageDetector:
    """Detector for a specific language with priority-based matching."""

    language: str
    priority: int
    patterns: tuple[re.Pattern, ...]

    def matches(self, text: str) -> bool:
        """Check if any pattern matches the text."""
        return any(pattern.search(text) for pattern in self.patterns)


# Pre-compiled regex patterns for efficient matching
_DETECTORS = [
    LanguageDetector(
        "bash",
        100,
        (re.compile(r"^\s*@bash_command\b", re.MULTILINE),),
    ),
    LanguageDetector(
        "clojurescript",
        90,
        (
            re.compile(r"\bcljs\.core\b", re.IGNORECASE | re.MULTILINE),
            re.compile(r"\(ns\s+[\w\.\-]*cljs", re.IGNORECASE | re.MULTILINE),
            re.compile(r"#\?\s*:\s*cljs", re.IGNORECASE | re.MULTILINE),
            re.compile(r"\bclojurescript\b", re.IGNORECASE | re.MULTILINE),
        ),
    ),
    LanguageDetector(
        "typescript",
        80,
        (
            re.compile(r"\bDeno\.", re.IGNORECASE | re.MULTILINE),
            re.compile(r"\bfrom\s+\"https?://deno\.land", re.IGNORECASE | re.MULTILINE),
            re.compile(r"\bexport\s+async\s+function\s+main\b", re.IGNORECASE | re.MULTILINE),
            re.compile(r"\bexport\s+function\s+main\b", re.IGNORECASE | re.MULTILINE),
            re.compile(r"\basync\s+function\s+main\b", re.IGNORECASE | re.MULTILINE),
        ),
    ),
    LanguageDetector(
        "python",
        70,
        (
            re.compile(r"^\s*def\s+\w+\s*\(", re.MULTILINE),
            re.compile(r"^\s*import\s+\w+", re.MULTILINE),
            re.compile(r"^\s*from\s+\w+\s+import", re.MULTILINE),
        ),
    ),
    LanguageDetector(
        "clojure",
        60,
        (
            re.compile(r"\(ns\b", re.MULTILINE),
            re.compile(r"\(defn\s+main", re.MULTILINE),
            re.compile(r"\(println\b", re.MULTILINE),
        ),
    ),
    LanguageDetector(
        "bash",
        50,
        (
            re.compile(r"^\s*set\s+-[a-zA-Z]*[EeUuOoFfPp][a-zA-Z]*", re.MULTILINE),
            re.compile(r"^\s*echo\b", re.MULTILINE),
            re.compile(r"^\s*function\s+\w+\s*\{", re.MULTILINE),
            re.compile(r"\bthen\b", re.MULTILINE),
            re.compile(r"\bfi\b", re.MULTILINE),
        ),
    ),
]


def _detect_from_shebang(first_line: str) -> str | None:
    """Detect language from shebang line."""
    if not first_line.startswith("#!"):
        return None

    shebang_map = {
        "python": ["python"],
        "bash": ["bash", "/sh", "sh "],
        "typescript": ["deno", "ts-node", "typescript"],
        "clojurescript": ["clojurescript", "nbb"],
        "clojure": ["clojure", "bb", "babashka"],
    }

    for language, markers in shebang_map.items():
        if any(marker in first_line for marker in markers):
            return language

    return None


def _detect_from_shell_tokens(text: str) -> str | None:
    """Detect bash based on shell token frequency."""
    tokens = re.findall(r"[A-Za-z0-9_./-]+|\$\(|\|\||&&|>>|[|><;$(){}\[\]]", text)
    if not tokens:
        return None

    shell_token_count = sum(
        1 for token in tokens if token.lower() in COMMON_SHELL_TOKENS
    )
    if shell_token_count >= len(tokens) / 2:
        return "bash"

    return None


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

    # Check for @bash_command marker (highest priority)
    if first_line.startswith("@bash_command"):
        return "bash"

    # Check shebang line
    if first_line.startswith("#!"):
        language = _detect_from_shebang(first_line)
        if language:
            return language

    # Check language-specific patterns in priority order
    for detector in _DETECTORS:
        if detector.matches(text):
            return detector.language

    # Check shell token frequency as final heuristic
    shell_language = _detect_from_shell_tokens(text)
    if shell_language:
        return shell_language

    return "python"


__all__ = ["detect_server_language"]
