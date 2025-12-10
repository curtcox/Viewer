# Chunk anatomy walkthrough

This note dissects a single chunk end-to-end: how it was created, how its identifier was derived, and how to inspect the raw bytes with a hex dump.

## Selected chunk

- **Chunk text** (randomly chosen synthetic sample):
  ```
  chunk anatomy demo
  chunk source: synthetic sample from documentation walkthrough
  note: random chunk captured for anatomy reference
  ```
- **Chunk ID**: `27575c` (first six hex chars of the SHA-256 digest of the UTF-8 chunk text)
- **Creation command**:
  ```bash
  python - <<'PY'
  import hashlib, textwrap
  chunk_text = textwrap.dedent("""
  chunk anatomy demo
  chunk source: synthetic sample from documentation walkthrough
  note: random chunk captured for anatomy reference
  """).lstrip('\n')
  print(chunk_text)
  print('chunk_id', hashlib.sha256(chunk_text.encode()).hexdigest()[:6])
  PY
  ```

## Annotated hex dump

The bytes below come from the chunk text encoded as UTF-8. Offsets are in hexadecimal, followed by byte values and their printable ASCII representation.

```
00000000  63 68 75 6e 6b 20 61 6e 61 74 6f 6d 79 20 64 65  |chunk anatomy de|
00000010  6d 6f 0a 63 68 75 6e 6b 20 73 6f 75 72 63 65 3a  |mo.chunk source:|
00000020  20 73 79 6e 74 68 65 74 69 63 20 73 61 6d 70 6c  | synthetic sampl|
00000030  65 20 66 72 6f 6d 20 64 6f 63 75 6d 65 6e 74 61  |e from documenta|
00000040  74 69 6f 6e 20 77 61 6c 6b 74 68 72 6f 75 67 68  |tion walkthrough|
00000050  0a 6e 6f 74 65 3a 20 72 61 6e 64 6f 6d 20 63 68  |.note: random ch|
00000060  75 6e 6b 20 63 61 70 74 75 72 65 64 20 66 6f 72  |unk captured for|
00000070  20 61 6e 61 74 6f 6d 79 20 72 65 66 65 72 65 6e  | anatomy referen|
00000080  63 65 0a                                         |ce.|
```

To validate the chunk ID, hash the same text and truncate the digest:

```python
import hashlib
chunk_text = """chunk anatomy demo
chunk source: synthetic sample from documentation walkthrough
note: random chunk captured for anatomy reference
"""
print(hashlib.sha256(chunk_text.encode()).hexdigest()[:6])  # 27575c
```

## Tools for chunk manipulation

- **Hashing**: `hashlib.sha256` in Python cleanly reproduces the chunk ID calculation shown above. For shell pipelines, `sha256sum` offers the same digest, after which you can take the first six hex characters.
- **Hex dumps**: If `xxd` or `hexdump` is unavailable, a short Python loop (as used to generate the dump above) can render offsets, bytes, and ASCII side-by-side. When available, tools like `xxd -g1` or `hexdump -C` provide the same view.
- **Text normalization**: Use `textwrap.dedent` or `strip` helpers to avoid unintentional indentation or trailing spaces that would change the hash. Always confirm that the bytes used for hashing match the bytes shown in the hex dump.
- **Persistence and reuse**: Store the exact chunk text alongside its ID to make regeneration straightforward. A tracked file such as `chunk_sample.txt` or a snippet in documentation keeps the evidence stable across sessions.

These steps show every stage of a chunk’s lifecycle—from text to digest to byte-level inspection—so you can manipulate or verify chunks confidently.
