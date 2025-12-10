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

### Step-by-step: finding chunk citations

Follow this recipe when you need to locate the output behind a chunk citation such as `【d05d1b†L1-L6】`:

1. **Scan recent tool output** for the chunk hash. Tool responses expose a `chunk_id` label next to the rendered output—search for the six-character token (e.g., `d05d1b`). If your terminal supports filtering, use a search (e.g., `/d05d1b` in `less`) to jump straight to the right block.
2. **Match the exact chunk** by comparing the hash and line numbers. The cited line range (here `L1-L6`) refers to the numbered lines in that chunked output block. Verify the chunk heading still shows the same `chunk_id` to avoid confusing it with similarly prefixed IDs.
3. **Open the chunk details**. If your tooling folds long outputs, expand the chunk so you can see all lines. When output is paginated across multiple chunks, note where the chunk begins so the `L1` anchor is unambiguous.
4. **Validate context**. Confirm the surrounding lines still represent the scenario being cited (e.g., the test run or command invocation). If the chunk shows multiple commands in one response, ensure you are looking at the right sub-block. Re-read the prompt or command header if present to confirm you are in the expected output section.
5. **Cross-reference adjacent chunks** if necessary. When multiple sequential chunks share the same context (such as a long test run), check earlier or later chunk IDs to gather full context before relying on the citation. Long commands often spill into several chunks; trace the sequence by timestamp or output ordering.
6. **Capture the line numbers**. Once located, jot down the exact `L` range you need so you can transcribe the citation accurately into your document without re-opening the log.

### Chunk lifecycles and durability

- **Creation**: Each command invocation in the tool pipeline emits output in one or more discrete chunks. Every chunk receives a SHA-256-derived `chunk_id` at creation time based solely on its text content.
- **Stability**: Within a session, the same chunk text always yields the same ID; editing or re-running commands that change output content produces new hashes, so citations remain tied to the captured evidence, not the command name.
- **Ordering**: Chunks are ordered chronologically per tool response. When reconstructing long outputs, rely on this sequence plus the `L` ranges to stitch adjacent chunks together.
- **Retention**: Chunk identifiers remain valid as long as the associated session logs are available. If logs are truncated or a new session is started, the same commands will produce fresh chunk IDs because the hashing input (captured text) may change with timestamps or environment details.
- **Portability**: Citations should point to chunks recorded in shared or persisted logs when possible. For ephemeral sessions, copy the relevant chunk text into reviewable artifacts (e.g., PR descriptions) so the citation remains auditable after the session ends.

## Recommended contexts

- Use citations in TODOs, plan documents, and PR summaries to ground statements in observed failures (as seen in `/todo/fix_gauge_specs.md`).
- Include citations in test plans and debugging notes to capture the exact log lines that motivated the next steps.
- When summarizing terminal runs in commit messages or status updates, cite the command chunks so reviewers can cross-check the logs.

Keeping citations consistent makes it easier for collaborators to trace every assertion back to verifiable evidence.
