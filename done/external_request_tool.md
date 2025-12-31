# Refactor Compression Logic Out of Individual Servers

## Problem Statement

The file `reference_templates/servers/definitions/jsonplaceholder.py` contains ~40 lines of code (lines 27-65) dedicated to handling compressed HTTP responses (gzip, deflate, brotli). This logic:

1. **Duplicates code** - Any server that contacts an external API and needs to access `response.content` directly must implement the same decompression logic
2. **Inflates simple proxies** - For jsonplaceholder.py, this compression handling constituted ~25% of the file's code
3. **Is error-prone** - `proxy.py` was missing this logic entirely, making it vulnerable to returning corrupted binary data when upstream servers send compressed responses
4. **Is inconsistent** - Some servers handle compression, others don't, with no clear pattern

### Current State

| Server | Uses | Compression Handling | Status |
|--------|------|---------------------|--------|
| `jsonplaceholder.py` | `requests` directly | ✅ Via `auto_decode_response()` | Refactored to shared helper |
| `proxy.py` | `requests` directly | ✅ Via `auto_decode_response()` | Fixed |
| `gateway.py` | `requests` directly | N/A (internal only) | OK |
| 43 servers | `ExternalApiClient` | Relies on `.json()` | OK (auto-decompressed) |

---

## Proposed Solution

### Add `content_decoder.py` to `server_utils/external_api/`

Create a new utility module that centralizes content decompression logic. This module will:

1. Provide a `decode_content()` function that handles gzip, deflate, and brotli decompression
2. Provide an `auto_decode_response()` function that extracts content from a `requests.Response` and decodes it
3. Be easily importable by any server that needs to access raw response content

### File: `server_utils/external_api/content_decoder.py`

```python
"""Content decoder for HTTP responses with compressed content.

This module centralizes the logic for decompressing HTTP response bodies
that may be gzip, deflate, or brotli encoded. Use this when accessing
response.content directly instead of response.json() or response.text.
"""

import gzip
import zlib
from typing import Optional, Union


def decode_content(
    content: Union[bytes, bytearray, str],
    content_encoding: Optional[str],
) -> bytes:
    """
    Decode HTTP response content based on Content-Encoding header.

    Args:
        content: Raw response body (bytes, bytearray, or string)
        content_encoding: Value of Content-Encoding header (may be comma-separated)

    Returns:
        Decoded bytes

    Raises:
        ValueError: If brotli encoding is used but brotli library is not installed
        zlib.error: If deflate decompression fails
        gzip.BadGzipFile: If gzip decompression fails
    """
    # Normalize content to bytes
    if not isinstance(content, (bytes, bytearray)):
        return str(content).encode("utf-8")

    body = bytes(content)

    # No encoding means content is already decoded
    if not content_encoding:
        return body

    # Parse encoding header (may be comma-separated for stacked encodings)
    encodings = [
        encoding.strip().lower()
        for encoding in str(content_encoding).split(",")
        if encoding and str(encoding).strip()
    ]

    if not encodings:
        return body

    # Process encodings in reverse order (last applied = first to remove)
    for encoding in reversed(encodings):
        if encoding in {"identity", "none"}:
            continue

        if encoding == "gzip":
            body = gzip.decompress(body)
            continue

        if encoding == "deflate":
            try:
                body = zlib.decompress(body)
            except zlib.error:
                # Try raw deflate (no zlib header)
                body = zlib.decompress(body, -zlib.MAX_WBITS)
            continue

        if encoding == "br":
            try:
                import brotli  # type: ignore
            except ImportError as exc:
                raise ValueError(
                    "Response was brotli-compressed (Content-Encoding: br), "
                    "but the brotli library is not installed. "
                    "Install it with: pip install brotli"
                ) from exc
            body = brotli.decompress(body)
            continue

        # Unknown encoding - leave content as-is
        # (could also raise an error, but this is more permissive)

    return body


def auto_decode_response(response) -> bytes:
    """
    Extract and decode content from a requests.Response object.

    This is a convenience function that combines extracting the response
    content and Content-Encoding header, then calling decode_content().

    Args:
        response: A requests.Response object

    Returns:
        Decoded response body as bytes
    """
    content = response.content
    content_encoding = response.headers.get("Content-Encoding")
    return decode_content(content, content_encoding)
```

### Update `server_utils/external_api/__init__.py`

Export the new functions:

```python
from .content_decoder import decode_content, auto_decode_response
```

---

## Migration Plan

### Phase 1: Add the Utility Module

1. Create `server_utils/external_api/content_decoder.py`
2. Add exports to `server_utils/external_api/__init__.py`
3. Add unit tests in `tests/test_external_api_content_decoder.py`
4. Verify all existing tests still pass

### Phase 2: Simplify jsonplaceholder.py

Replace the 40-line `_decode_content` function with an import:

**Before (lines 17-18, 27-65, 147):**
```python
import gzip
import zlib

def _decode_content(content: bytes, content_encoding: str | None) -> bytes:
    # ... 38 lines of decompression logic ...

# In _proxy_request:
output = _decode_content(response.content, content_encoding)
```

**After:**
```python
from server_utils.external_api import auto_decode_response

# In _proxy_request:
output = auto_decode_response(response)
```

**Net reduction:** ~35 lines of code

### Phase 3: Fix proxy.py

Add the missing decompression logic:

**Before (line 119):**
```python
return {"output": response.content, "content_type": content_type}
```

**After:**
```python
from server_utils.external_api import auto_decode_response

# In _proxy_request:
output = auto_decode_response(response)
return {"output": output, "content_type": content_type}
```

### Phase 4: Optionally Extend ExternalApiClient

For servers that use `ExternalApiClient` and need decoded content, add a convenience method:

```python
# In ExternalApiClient class:
def get_decoded_content(self, response: Response) -> bytes:
    """Return response content, automatically decompressing if needed."""
    from .content_decoder import auto_decode_response
    return auto_decode_response(response)
```

---

## Checklist of Servers to Modify

### Must Fix (Bug)

- [x] **`proxy.py`** - Uses `auto_decode_response()` to handle compressed responses
  - Location: `reference_templates/servers/definitions/proxy.py`
  - Fix: Import and use `auto_decode_response()`

### Should Refactor (Remove Duplication)

- [x] **`jsonplaceholder.py`** - Uses `auto_decode_response()` (shared helper)
  - Location: `reference_templates/servers/definitions/jsonplaceholder.py`
  - Fix: Replace custom decompression logic with `auto_decode_response(response)`

### No Changes Needed (Safe)

These servers use `.json()` or `.text` which are auto-decompressed by requests:

- `ai_assist.py`
- `anthropic_claude.py`
- `google_gemini.py`
- `nvidia_nim.py`
- `openai_chat.py`
- `openrouter.py`
- `gateway.py` (internal only, doesn't contact external servers)

### No Changes Needed (ExternalApiClient Users)

These 43 servers use `ExternalApiClient` and access `.json()`:

- `airtable.py`
- `asana.py`
- `basecamp.py`
- `calendly.py`
- `clickup.py`
- `close_crm.py`
- `confluence.py`
- `discord.py`
- `dynamics365.py`
- `github.py`
- `google_ads.py`
- `google_analytics.py`
- `google_calendar.py`
- `google_contacts.py`
- `google_docs.py`
- `google_drive.py`
- `google_forms.py`
- `google_sheets.py`
- `gmail.py`
- `hubspot.py`
- `insightly.py`
- `jira.py`
- `mailchimp.py`
- `microsoft_excel.py`
- `microsoft_outlook.py`
- `microsoft_teams.py`
- `monday.py`
- `notion.py`
- `onedrive.py`
- `pipedrive.py`
- `salesforce.py`
- `slack.py`
- `smartsheet.py`
- `stripe.py`
- `todoist.py`
- `trello.py`
- `twilio.py`
- `whatsapp.py`
- `telegram.py`
- `youtube.py`
- `zendesk.py`
- `zoho_crm.py`

---

## Test Plan

### Unit Tests for `content_decoder.py`

| Test | Description |
|------|-------------|
| `test_decode_uncompressed_content` | Pass-through for no encoding |
| `test_decode_identity_encoding` | Pass-through for `identity` encoding |
| `test_decode_gzip_content` | Decompress gzip-encoded bytes |
| `test_decode_deflate_content` | Decompress deflate-encoded bytes |
| `test_decode_deflate_raw_content` | Decompress raw deflate (no zlib header) |
| `test_decode_brotli_content` | Decompress brotli-encoded bytes (with brotli installed) |
| `test_decode_brotli_not_installed` | Raise ValueError when brotli not available |
| `test_decode_multiple_encodings` | Handle comma-separated encodings (e.g., `gzip, deflate`) |
| `test_decode_string_content` | Handle string input (encode to UTF-8) |
| `test_auto_decode_response` | End-to-end with mock Response object |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_jsonplaceholder_decompresses_gzip` | Already exists in `tests/test_gateway_server.py` |
| `test_proxy_decompresses_gzip` | New test needed after fix |
| `test_proxy_decompresses_deflate` | New test needed after fix |

---

## Alternative Approaches Considered

### 1. Request `Accept-Encoding: identity`

jsonplaceholder.py already does this (line 129), but it's not foolproof:
- Some servers ignore the header
- Some proxies/CDNs may still compress
- Doesn't help for APIs that only serve compressed content

**Verdict:** Good defensive measure, but doesn't eliminate the need for decompression.

### 2. Let requests handle it automatically

The `requests` library automatically decompresses for `.json()`, `.text`, and `.content` in most cases. However:
- When accessing `.content`, requests does NOT decompress by default if the response is binary
- Some edge cases around Transfer-Encoding vs Content-Encoding
- Relying on implicit behavior is fragile

**Verdict:** Works for JSON APIs, but not for binary content proxies.

### 3. Use a wrapper Response class

Wrap `requests.Response` in a custom class that always returns decoded content.

**Verdict:** More invasive change, harder to adopt incrementally.

---

## Benefits of Proposed Solution

1. **Single source of truth** - Compression logic lives in one place
2. **Minimal changes** - Only 2 servers need modification
3. **Backward compatible** - Existing code continues to work
4. **Incremental adoption** - Servers can migrate one at a time
5. **Testable** - Isolated utility function is easy to test
6. **Fixes a bug** - proxy.py will actually work with compressed responses

---

## Timeline

No time estimates provided per guidelines. Implementation order:

1. Create `content_decoder.py` and tests
2. Fix `proxy.py` (bug fix - highest priority)
3. Refactor `jsonplaceholder.py` (code cleanup)
4. Optionally extend `ExternalApiClient`
