# CIDS Archive Format

The CIDS archive format is a simple, plain text format for mapping file paths to Content-addressed IDs.

## Format Specification

### Basic Structure

A CIDS archive is a plain text file where each line contains:
```
<path> <CID>
```

Example:
```
readme.md AAAAABC123xyz.md
docs/api.html AAAAABC456abc.html
images/logo.png AAAAABC789def.png
```

### Rules

1. **One path per line** - Each line represents one file
2. **Whitespace separator** - Path and CID separated by space(s)
3. **No duplicates** - Duplicate paths are validation errors
4. **Empty lines allowed** - Blank lines are ignored
5. **Leading slashes optional** - Paths are normalized (leading `/` removed)

### MIME Type Extensions

CIDs can include file extensions to specify the MIME type:

| Extension | MIME Type | Example |
|-----------|-----------|---------|
| `.txt` | `text/plain` | `CID123.txt` |
| `.html` | `text/html` | `CID456.html` |
| `.md` | `text/markdown` | `CID789.md` |
| `.json` | `application/json` | `CIDabc.json` |
| `.jpg` | `image/jpeg` | `CIDdef.jpg` |
| `.png` | `image/png` | `CIDghi.png` |

For more information about CIDs and the CIDS server, visit [256t.org on GitHub](https://github.com/curtcox/256t.org).

---

[← Back to Index](../index.md) | [Previous: What are CIDs?](what-are-cids.md) | [Next: Deduplication →](deduplication.md)
