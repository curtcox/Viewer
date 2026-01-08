# Potential Hypothesis Tests

This document tracked opportunities for property-based testing using Hypothesis throughout the codebase. **Most high-priority items have now been implemented.**

## Summary

### ✅ Completed (6/9 high-priority modules, 59 tests total)

The following high-priority modules now have comprehensive hypothesis property tests:

1. **HRX Parser** - `tests/property/test_hrx_parser_properties.py` (6 tests)
2. **MIME Utils** - `tests/property/test_mime_utils_properties.py` (9 tests)
3. **CLI Arguments** - `tests/property/test_cli_args_properties.py` (10 tests)
4. **CID Core** - `tests/property/test_cid_core_properties.py` (13 tests)
5. **Authorization** - `tests/property/test_authorization_properties.py` (9 tests)
6. **History Filters** - `tests/property/test_history_filters_properties.py` (12 tests)

### Remaining Opportunities

The following modules remain as opportunities for future hypothesis tests:

- **Formdown Renderer** (`formdown_renderer.py`) - descriptor parsing, HTML safety, field ID uniqueness
- **Entity References** (`entity_references.py`) - extraction idempotence, path normalization, deduplication
- **Link Presenter** (`link_presenter.py`) - path normalization, URL combination, server paths

## Already Covered

The following modules already had hypothesis tests before this work:
- `tests/property/test_cid_properties.py` - CID encoding/parsing round-trips
- `tests/property/test_alias_matching_properties.py` - Alias pattern normalization
- `tests/property/test_serialization_properties.py` - Model serialization
- `tests/property/test_encryption_properties.py` - Encryption/decryption and tampering detection
- `tests/property/test_response_format_properties.py` - XML/CSV format conversions
- `tests/property/test_db_equivalence_property.py` - In-memory vs disk database equivalence
- `tests/property/test_serve_cid_content_properties.py` - Content serving properties

---

## High Priority Opportunities

### 1. HRX Parser (`hrx_parser.py`) ✅ DONE

**Status**: Implemented in `tests/property/test_hrx_parser_properties.py`

**Test: HRX parse-serialize idempotence**
- **What it tests**: Parsing an HRX archive and reconstructing it should preserve file paths and content
- **Why**: HRX is a custom format with complex parsing logic (boundaries, directories, files). Property-based testing would ensure the parser handles edge cases like:
  - Different boundary lengths (variable `=` count)
  - Empty files
  - Files with boundary-like content
  - Unicode in filenames and content
  - Trailing/leading whitespace
- **Property**: For any valid HRX archive string, parsing it should extract all files, and the extracted files should match the original content

**Test: HRX boundary independence**
- **What it tests**: The same file structure should parse identically regardless of boundary length
- **Why**: The HRX format allows variable-length boundaries (`<=>`, `<===>`, etc.). The parser should handle all valid boundary lengths consistently
- **Property**: Generating an archive with N equals vs M equals should produce equivalent file structures

**Test: HRX path safety**
- **What it tests**: Invalid paths (path traversal attempts, absolute paths, etc.) should be handled safely
- **Why**: Security - ensure the parser doesn't allow directory traversal attacks
- **Property**: No parsed file path should contain ".." or start with "/" in a way that escapes the archive root

---

### 2. MIME Utils (`mime_utils.py`) ✅ DONE

**Status**: Implemented in `tests/property/test_mime_utils_properties.py`

**Test: Extension-MIME round-trip consistency**
- **What it tests**: For any known MIME type, converting to extension and back should be stable
- **Why**: Ensures bidirectional mapping is consistent. While not all extensions round-trip (e.g., "jpg"/"jpeg" both map to "image/jpeg"), the mapping should be stable
- **Property**: `get_extension_from_mime_type(mime) → ext` then checking `get_mime_type_from_extension(ext) == mime`

**Test: Filename extraction from CID paths**
- **What it tests**: `extract_filename_from_cid_path()` should handle various path formats
- **Why**: This function has specific parsing logic for CID paths with extensions. Property testing can verify:
  - Paths with multiple dots (e.g., `/CID.my.file.tar.gz`)
  - Single extension paths (should return None)
  - Invalid paths
  - Edge cases like empty components
- **Property**: For any valid CID path with 3+ components, extraction should succeed and preserve the filename portion correctly

**Test: MIME type consistency with parameters**
- **What it tests**: `get_extension_from_mime_type()` should ignore charset and other parameters
- **Why**: MIME types often include parameters like `charset=utf-8`. The function should handle these consistently
- **Property**: For any MIME type string with/without parameters, the extracted extension should be the same (e.g., "text/plain" and "text/plain; charset=utf-8" → "txt")

---

### 3. Formdown Renderer (`formdown_renderer.py`)

**Test: Descriptor parsing round-trip**
- **What it tests**: Parsing formdown descriptors and reconstructing them should preserve attributes
- **Why**: The descriptor parsing uses `shlex.split()` and custom escaping. Property testing would ensure:
  - Attributes with quotes, newlines, backslashes are correctly escaped/unescaped
  - Boolean attributes are handled correctly
  - Edge cases with empty values
- **Property**: For any valid descriptor, parsing attributes and the control type should extract values that match the original intent

**Test: HTML output safety**
- **What it tests**: Rendered HTML should always be properly escaped
- **Why**: Security - prevent XSS attacks from user-supplied form content
- **Property**: For any field definition with arbitrary text in labels, values, or help text, the rendered HTML should not contain unescaped `<`, `>`, `"`, or `'` characters outside of HTML tags

**Test: Form field ID uniqueness**
- **What it tests**: Generated field IDs should be unique within a form
- **Why**: HTML requires unique IDs for proper form behavior and accessibility
- **Property**: For any formdown document, all generated field IDs should be unique

**Test: Attribute rendering consistency**
- **What it tests**: Boolean attributes vs value attributes render correctly
- **Why**: HTML has special handling for boolean attributes (e.g., `required` vs `value="foo"`)
- **Property**: Boolean attributes should render as standalone words or not at all; non-boolean attributes should always have `key="value"` format

---

### 4. Entity References (`entity_references.py`)

**Test: Reference extraction idempotence**
- **What it tests**: Extracting references from text multiple times should yield the same results
- **Why**: The extraction logic uses regex and database lookups. Should be deterministic
- **Property**: `extract_references_from_text(text)` called twice should return identical results

**Test: Path normalization safety**
- **What it tests**: `_normalize_local_path()` should reject URLs with schemes or hosts
- **Why**: Security - prevent SSRF attacks or unintended external references
- **Property**: For any string with a URL scheme (http://, https://, ftp://, etc.), normalization should return None

**Test: Reference deduplication**
- **What it tests**: `_dedupe()` should remove duplicates while preserving order
- **Why**: Multiple mentions of the same entity should appear only once in results
- **Property**: For any list of references with duplicates, deduping should produce a subset with unique values in first-seen order

**Test: Extension stripping consistency**
- **What it tests**: `_strip_extension()` should handle paths with multiple extensions correctly
- **Why**: Handles complex cases like `.tar.gz` files
- **Property**: Stripping extensions should only remove from the last path segment, not from directory names

---

### 5. Link Presenter (`link_presenter.py`)

**Test: Path normalization idempotence**
- **What it tests**: Normalizing a path twice should yield the same result
- **Why**: Path normalization should be stable
- **Property**: `_normalize_segment(value)` and `_normalize_url(value)` should be idempotent

**Test: URL combination associativity**
- **What it tests**: Combining base URLs with paths should handle trailing/leading slashes consistently
- **Why**: Avoid double slashes or missing slashes in combined URLs
- **Property**: For any base URL and path, `_combine_base_url(base, path)` should produce a valid URL without `//` (except after protocol)

**Test: Server path normalization**
- **What it tests**: `server_path()` should handle paths that already start with "servers/"
- **Why**: Ensures consistent path generation regardless of input format
- **Property**: `server_path("foo")` and `server_path("servers/foo")` should produce the same result

---

### 6. History Filters (`history_filters.py`) ✅ DONE

**Status**: Implemented in `tests/property/test_history_filters_properties.py`

**Test: Timestamp round-trip**
- **What it tests**: Formatting a datetime and parsing it back should yield the original value (modulo timezone)
- **Why**: Ensures timestamp format is lossless for valid dates
- **Property**: For any timezone-aware datetime, `parse_history_timestamp(format_history_timestamp(dt))` should equal the original datetime in UTC

**Test: Timezone normalization**
- **What it tests**: All timestamps should be normalized to UTC
- **Why**: Consistency across different timezone inputs
- **Property**: For any datetime with any timezone, formatting should produce a UTC timestamp

**Test: Date range parsing robustness**
- **What it tests**: `parse_date_range()` should handle invalid inputs gracefully
- **Why**: User input can be malformed
- **Property**: For any pair of strings (valid or invalid), parsing should never raise an exception and should set validity flags correctly

**Test: Date range filter consistency**
- **What it tests**: The `filters` property should round-trip through query parameters
- **Why**: URL parameters need to preserve the date range for navigation
- **Property**: For any valid date range, the filter dict should contain values that can be parsed back to the same dates

---

### 7. CLI Arguments (`cli_args.py`) ✅ DONE

**Status**: Implemented in `tests/property/test_cli_args_properties.py`

**Test: Memory size parsing**
- **What it tests**: `parse_memory_size()` should handle various formats correctly
- **Why**: Users can input memory sizes in many formats (1G, 512M, 100K, 1024, etc.)
- **Property**: For any valid size string, parsing should produce a positive integer, and the result should be within expected bounds for the unit
  - Test: "1K" = 1024, "1M" = 1024^2, "1G" = 1024^3
  - Test: Parsing "1024" == parsing "1K"

**Test: Memory size format variations**
- **What it tests**: Different formatting variations should parse to the same value
- **Why**: Users might write "1G", "1 G", "1GB", "1g", etc.
- **Property**: For equivalent sizes, parsing should yield the same byte count regardless of spacing or 'B' suffix

**Test: Memory size parsing invalid inputs**
- **What it tests**: Invalid inputs should raise ValueError consistently
- **Why**: Error handling should be predictable
- **Property**: For any string that doesn't match the expected format, `parse_memory_size()` should raise ValueError (not return None or a garbage value)

---

### 8. CID Core (`cid_core.py`) ✅ DONE

**Status**: Implemented in `tests/property/test_cid_core_properties.py`

**Test: Base64url encode/decode round-trip**
- **What it tests**: Encoding bytes and decoding back should yield original data
- **Why**: Base64url is used throughout CID handling
- **Property**: For any byte string, `base64url_decode(base64url_encode(data)) == data`

**Test: CID component normalization**
- **What it tests**: `normalize_component()` should strip whitespace and leading slashes consistently
- **Why**: User input needs normalization
- **Property**: For any string, normalizing multiple times should yield the same result (idempotence)

**Test: CID validation pattern consistency**
- **What it tests**: The various regex patterns should have consistent validation
- **Why**: Multiple patterns exist for different purposes (normalized, reference, strict, path capture)
- **Property**: If a string matches `CID_STRICT_PATTERN`, it should also match `CID_REFERENCE_PATTERN` and `CID_NORMALIZED_PATTERN`

**Test: CID length encoding**
- **What it tests**: `encode_cid_length()` should handle the full range of valid content lengths
- **Why**: CIDs can represent content from 0 to `MAX_CONTENT_LENGTH`
- **Property**: For any length in the valid range, encoding should produce an 8-character base64url string, and the result should be decodable back to the original length

---

### 9. Authorization (`authorization.py`) ✅ DONE

**Status**: Implemented in `tests/property/test_authorization_properties.py`

**Test: AuthorizationResult validation**
- **What it tests**: Creating an `AuthorizationResult` with `allowed=False` should require status_code and message
- **Why**: The class has validation logic to ensure rejected requests have proper error info
- **Property**: For any AuthorizationResult where `allowed=False`, attempting to create it without status_code or message should raise ValueError

**Test: Status code validation**
- **What it tests**: Only 401 and 403 should be valid status codes for denied requests
- **Why**: HTTP semantics - 401 = authentication required, 403 = forbidden
- **Property**: For any status code outside {401, 403}, creating a denied AuthorizationResult should raise ValueError

---

## Medium Priority Opportunities

### 10. Content Rendering (via `content_rendering.py`)

**Test: Markdown detection**
- **What it tests**: `looks_like_markdown()` should consistently identify markdown content
- **Why**: Uses heuristics based on patterns. Property testing can verify:
  - Files with markdown extensions are detected
  - Content with markdown indicators is detected
  - Plain text doesn't trigger false positives
- **Property**: For any text containing multiple markdown indicators (headings, bullets, code blocks), detection should return True

**Test: GitHub relative link conversion**
- **What it tests**: Converting GitHub-style relative links should handle edge cases
- **Why**: Complex regex-based transformation
- **Property**: For any markdown with relative links, conversion should produce valid links without breaking the markdown structure

---

### 11. Alias Routing (`alias_routing.py`)

Would need to read this file to identify specific properties, but likely opportunities around:
- Route matching consistency
- Pattern compilation
- Path normalization during routing

---

### 12. Template Manager (if exists)

Based on the test file `test_template_manager.py`, there may be opportunities around:
- Template variable substitution
- Template parsing and rendering
- Default value handling

---

## Lower Priority / Nice to Have

### 13. Analytics (`analytics.py`)

Event tracking and data recording might benefit from property tests around:
- Event data serialization
- Timestamp consistency
- Data validation

### 14. Database Operations (`db_access/`)

Beyond the existing DB equivalence tests:
- CRUD operation consistency
- Query parameter handling
- Transaction rollback behavior

### 15. Import/Export Helpers

Based on `test_import_export_helpers.py`:
- JSON serialization/deserialization
- Data validation during import
- Error handling for malformed input

---

## General Testing Strategies

### Invariants to Test Across Modules

1. **Idempotence**: Operations that should produce the same result when called multiple times
   - Normalization functions
   - Parsing functions
   - Formatting functions

2. **Round-trips**: Operations with inverses should round-trip correctly
   - Encode/decode
   - Serialize/deserialize
   - Format/parse

3. **Input validation**: Functions should handle invalid input gracefully
   - Return None/empty for invalid input (where appropriate)
   - Raise specific exceptions (not generic ones)
   - Never return garbage values

4. **Security properties**: Functions processing user input should be safe
   - No XSS vulnerabilities (proper escaping)
   - No path traversal (proper path normalization)
   - No SSRF (rejecting external URLs where inappropriate)

5. **Consistency**: Related functions should agree
   - Multiple validators should agree on validity
   - Multiple parsers for the same format should agree
   - Forward and reverse mappings should be consistent

---

## Implementation Notes

When implementing these tests:

1. **Start with simple properties**: Begin with round-trip and idempotence tests
2. **Use appropriate strategies**:
   - Use `st.text()` with appropriate alphabets for string inputs
   - Use `st.binary()` for byte content
   - Use `st.integers()` with appropriate bounds for numeric inputs
   - Use `st.datetimes()` with timezone constraints
3. **Add examples**: Use `@example()` decorator for known edge cases
4. **Set reasonable limits**: Use `max_examples` appropriately (25-100 for most tests)
5. **Handle preconditions**: Use `assume()` to filter invalid inputs rather than handling in the test
6. **Test one property at a time**: Don't combine multiple properties in one test

---

## Notes on Existing Tests

The existing property tests provide good examples:
- `test_cid_properties.py` shows how to use custom strategies for domain-specific data
- `test_encryption_properties.py` demonstrates mutation testing (tamper detection)
- `test_response_format_properties.py` shows recursive strategies for nested data
- `test_db_equivalence_property.py` demonstrates fixtures with Hypothesis

Use these as templates when writing new property tests.
