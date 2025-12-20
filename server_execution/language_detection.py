"""Heuristics for determining server implementation languages."""

import re

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
        if (
            "deno" in first_line
            or "ts-node" in first_line
            or "typescript" in first_line
        ):
            return "typescript"
        if "clojurescript" in first_line or "nbb" in first_line:
            return "clojurescript"
        if "clojure" in first_line or "bb" in first_line or "babashka" in first_line:
            return "clojure"

    clojurescript_markers = (
        r"\bcljs\.core\b",
        r"\(ns\s+[\w\.\-]*cljs",
        r"#\?\s*:\s*cljs",
        r"\bclojurescript\b",
    )
    if any(
        re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        for pattern in clojurescript_markers
    ):
        return "clojurescript"

    typescript_markers = (
        r"\bDeno\.",
        r"\bfrom\s+\"https?://deno\.land",
        r"\bexport\s+async\s+function\s+main\b",
        r"\bexport\s+function\s+main\b",
        r"\basync\s+function\s+main\b",
    )
    if any(
        re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        for pattern in typescript_markers
    ):
        return "typescript"

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

    tokens = re.findall(r"[A-Za-z0-9_./-]+|\$\(|\|\||&&|>>|[|><;$(){}\[\]]", text)
    if tokens:
        shell_token_count = sum(
            1 for token in tokens if token.lower() in COMMON_SHELL_TOKENS
        )
        if shell_token_count >= len(tokens) / 2:
            return "bash"

    return "python"


__all__ = ["detect_server_language"]
