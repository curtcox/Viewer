# File citation format

This project uses inline citation brackets to anchor claims to reproducible evidence from files or terminal output. The same format appears in `/todo/fix_gauge_specs.md`, and this document fully specifies how to create, resolve, and apply those citations.

## Formats at a glance

There are two citation shapes:

- **File citations** reference static repository paths: `【F:relative/path.ext†L10-L25】`.
- **Command/terminal citations** reference captured command output chunks: `【abc123†L1-L7】`.

Each citation wraps the identifier in fullwidth brackets `【…】`, uses a dagger `†` to introduce the line range, and ends with `L<start>-L<end>` (or a single line `L5`).

## Scope and usage rules

- Use **file citations** when pointing to lines in tracked files. The path is relative to the repo root and prefixed with `F:` to distinguish it from chunk IDs.
- Use **command citations** when the evidence comes from terminal output returned by the developer tooling. The identifier is the chunk hash recorded alongside the output.
- Multiple citations can be chained back-to-back when a statement relies on several sources (see `/todo/fix_gauge_specs.md` for examples such as `【c4cad4†L1-L5】【d05d1b†L1-L6】`).
- Citations must come after the sentence they support.

## Chunk hashing algorithm

Command outputs are stored as discrete chunks. Each chunk is hashed with **SHA-256** over the raw UTF-8 text of the chunk. The system then takes the **first six hexadecimal characters** of that digest to form the chunk identifier (e.g., `c4cad4`). This short hash is collision-resistant for typical session volumes while staying concise enough for inline citations.

```
chunk_id = sha256(chunk_text.encode("utf-8")).hexdigest()[:6]
```

Because the hash is derived from the chunk text, any change to the output content produces a new `chunk_id`, ensuring citations are stable only for unmodified logs.

## Creating citations programmatically

The following Python snippets demonstrate how to build citations that match the format in `/todo/fix_gauge_specs.md`.

### File citations

```python
from pathlib import Path

def file_citation(path: str, start_line: int, end_line: int | None = None) -> str:
    rel_path = Path(path).as_posix()
    line_part = f"L{start_line}" if end_line is None else f"L{start_line}-L{end_line}"
    return f"【F:{rel_path}†{line_part}】"

# Example
print(file_citation("todo/fix_gauge_specs.md", 5, 6))
# -> 【F:todo/fix_gauge_specs.md†L5-L6】
```

### Command citations

```python
import hashlib

def chunk_hash(chunk_text: str) -> str:
    return hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:6]

def command_citation(chunk_text: str, start_line: int, end_line: int | None = None) -> str:
    chunk_id = chunk_hash(chunk_text)
    line_part = f"L{start_line}" if end_line is None else f"L{start_line}-L{end_line}"
    return f"【{chunk_id}†{line_part}】"

# Example
sample_output = """1: test started\n2: test passed\n"""
citation = command_citation(sample_output, 1, 2)
print(citation)
# -> 【5e408e†L1-L2】 (chunk ID will vary with content)
```

## Resolving citations

To resolve a citation:

1. **Identify the type**: citations starting with `F:` are file-based; otherwise they are command chunks.
2. **Locate the source**:
   - For file citations, open the referenced file and navigate to the specified line range.
   - For chunk citations, find the command output chunk with the matching six-character hash in your session logs (tool responses include a `chunk_id` field you can match against).
3. **Verify the content** at the stated lines before relying on the cited claim.

## Recommended contexts

- Use citations in TODOs, plan documents, and PR summaries to ground statements in observed failures (as seen in `/todo/fix_gauge_specs.md`).
- Include citations in test plans and debugging notes to capture the exact log lines that motivated the next steps.
- When summarizing terminal runs in commit messages or status updates, cite the command chunks so reviewers can cross-check the logs.

Keeping citations consistent makes it easier for collaborators to trace every assertion back to verifiable evidence.
