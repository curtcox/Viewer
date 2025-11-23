# One-Shot Run Test Proposals

This document outlines proposed tests to verify the one-shot run functionality provides equivalent responses to HTTP requests.

## Overview

One-shot run mode allows the application to be invoked from the command line with a URL parameter, returning the same response as if the request came via HTTP. This mode is useful for:
- Testing endpoints without running a server
- Scripting and automation
- CI/CD pipelines
- Verifying identical behavior between HTTP and CLI

## Test Categories

### 1. Entity Endpoints

#### 1.1 Aliases Equivalence
**Test:** Verify `/aliases.json` returns identical content via HTTP and CLI
- **Why:** Aliases are core entities that should be queryable consistently
- **What to check:** JSON structure, alias names, definitions, enabled status
- **CLI command:** `python main.py /aliases.json`

#### 1.2 Variables Equivalence
**Test:** Verify `/variables.json` returns identical content via HTTP and CLI
- **Why:** Variables store configuration that must be accessible via both methods
- **What to check:** Variable names, values, metadata
- **CLI command:** `python main.py /variables.json`

#### 1.3 Secrets Endpoint Equivalence
**Test:** Verify `/secrets.json` returns same response (likely restricted) via HTTP and CLI
- **Why:** Security-sensitive endpoints should behave identically
- **What to check:** Same authentication/authorization behavior
- **CLI command:** `python main.py /secrets.json`

### 2. Content Negotiation

#### 2.1 JSON Format Equivalence
**Test:** Verify requesting `/servers.json` returns JSON via both HTTP and CLI
- **Why:** Content negotiation should work consistently
- **What to check:** Content-Type header behavior, JSON parsing
- **CLI command:** `python main.py /servers.json`

#### 2.2 HTML Format Equivalence
**Test:** Verify requesting `/servers` (no extension) returns HTML via both methods
- **Why:** Default content type should be consistent
- **What to check:** HTML structure, status code
- **CLI command:** `python main.py /servers`

#### 2.3 Plain Text Format Equivalence
**Test:** Verify requesting CID content as `.txt` returns same text via HTTP and CLI
- **Why:** Text rendering should be identical
- **What to check:** Plain text content, encoding
- **CLI command:** `python main.py /{cid}.txt`

### 3. CID Content Access

#### 3.1 Direct CID Access Equivalence
**Test:** Verify accessing a CID path `/{cid}` returns identical content
- **Why:** CIDs are the foundation of the content system
- **What to check:** Binary content, content-type detection
- **CLI command:** `python main.py /AAAABP7x8...`

#### 3.2 CID With Different Extensions
**Test:** Verify same CID with different extensions (`.json`, `.txt`, `.html`) returns appropriate format
- **Why:** Format conversion should be consistent
- **What to check:** Response format matches extension
- **CLI commands:**
  - `python main.py /{cid}.json`
  - `python main.py /{cid}.txt`
  - `python main.py /{cid}.html`

### 4. Query Parameters and Filtering

#### 4.1 Filtered Server List
**Test:** Verify `/servers.json?enabled=true` filters results identically
- **Why:** Query parameter handling must be consistent
- **What to check:** Filtered results match between methods
- **CLI command:** `python main.py "/servers.json?enabled=true"`

#### 4.2 Search Parameters
**Test:** Verify search functionality works identically via HTTP and CLI
- **Why:** Search is a key feature that needs consistency
- **What to check:** Search results, pagination
- **CLI command:** `python main.py "/search?q=test"`

### 5. Error Handling

#### 5.1 404 Consistency
**Test:** Verify 404 responses are identical for non-existent paths
- **Why:** Error pages should provide same information
- **What to check:** Status code, error message, HTML structure
- **CLI command:** `python main.py /this-does-not-exist`

#### 5.2 Invalid CID Format Error
**Test:** Verify requesting invalid CID format returns same error
- **Why:** Validation errors should be consistent
- **What to check:** Status code, error message
- **CLI command:** `python main.py /invalid-cid-format-!!!`

#### 5.3 Method Not Allowed
**Test:** Verify that CLI GET-only limitation matches HTTP GET restrictions
- **Why:** HTTP method restrictions should be clear
- **What to check:** Error handling for POST-only endpoints accessed via CLI
- **CLI command:** `python main.py /some-post-only-endpoint`

### 6. Integration with Boot CIDs

#### 6.1 Boot CID Data Availability
**Test:** Verify data imported from boot CID is immediately available in one-shot mode
- **Why:** Boot CIDs should load data before processing request
- **What to check:** Imported entities appear in response
- **CLI command:** `python main.py /servers.json {boot_cid}`

#### 6.2 Boot CID Override
**Test:** Verify boot CID data overrides existing data consistently
- **Why:** Data precedence rules should be the same
- **What to check:** Boot CID data takes precedence
- **CLI command:** Test with conflicting boot CID

### 7. Special Endpoints

#### 7.1 OpenAPI Spec Equivalence
**Test:** Verify `/openapi.json` returns identical OpenAPI specification
- **Why:** API documentation should be consistent
- **What to check:** Complete OpenAPI schema matches
- **CLI command:** `python main.py /openapi.json`

#### 7.2 Health Check Endpoint
**Test:** Verify health check endpoints work identically
- **Why:** Health checks are critical for monitoring
- **What to check:** Status and diagnostic information
- **CLI command:** `python main.py /health` (if such endpoint exists)

### 8. Performance and Edge Cases

#### 8.1 Large Response Handling
**Test:** Verify large responses (>1MB) are handled identically
- **Why:** Large responses can reveal buffering differences
- **What to check:** Complete content delivery, no truncation
- **CLI command:** `python main.py /{large_cid}`

#### 8.2 Binary Content
**Test:** Verify binary content (images, PDFs) is delivered correctly via CLI
- **Why:** Binary data encoding can differ between methods
- **What to check:** Binary output is identical to HTTP
- **CLI command:** `python main.py /{binary_cid}`

#### 8.3 Concurrent One-Shot Invocations
**Test:** Verify multiple one-shot invocations can run concurrently without conflicts
- **Why:** CLI should support parallel execution for automation
- **What to check:** No database locking issues, correct results
- **CLI command:** Run multiple `python main.py /path` in parallel

### 9. Content Headers and Metadata

#### 9.1 Content-Type Header Consistency
**Test:** Verify Content-Type headers are reported correctly in one-shot mode
- **Why:** Content type detection should be identical
- **What to check:** Status output includes correct content type
- **CLI command:** Check output of `python main.py /some.json`

#### 9.2 Cache Headers
**Test:** Verify caching headers (if any) are documented in CLI output
- **Why:** Caching behavior should be transparent
- **What to check:** Cache-related headers in status output
- **CLI command:** `python main.py /{cacheable_cid}`

### 10. Documentation and Help

#### 10.1 Help Text Completeness
**Test:** Verify `--help` fully documents one-shot mode
- **Why:** Users need clear documentation
- **What to check:** One-shot mode described, examples provided
- **CLI command:** `python main.py --help`

#### 10.2 Example Commands Work
**Test:** Verify all example commands in help text actually work
- **Why:** Documentation examples must be accurate
- **What to check:** Each example executes successfully
- **CLI commands:** Test each example from help

### 11. Exit Codes

#### 11.1 Success Exit Code
**Test:** Verify exit code 0 for successful 2xx responses
- **Why:** Exit codes are important for scripting
- **What to check:** `echo $?` returns 0 after successful request
- **CLI command:** `python main.py / && echo $?`

#### 11.2 Error Exit Code
**Test:** Verify exit code 1 for 4xx/5xx responses
- **Why:** Errors should be detectable in scripts
- **What to check:** `echo $?` returns 1 after error
- **CLI command:** `python main.py /404 || echo $?`

### 12. UTF-8 and International Content

#### 12.1 Unicode Content Equivalence
**Test:** Verify content with unicode characters renders identically
- **Why:** International content must be handled correctly
- **What to check:** Unicode characters preserved in both methods
- **CLI command:** `python main.py /{unicode_cid}`

#### 12.2 Special Characters in URLs
**Test:** Verify URL-encoded special characters work in one-shot mode
- **Why:** URL encoding should be handled consistently
- **What to check:** Special characters properly decoded
- **CLI command:** `python main.py "/search?q=test%20query"`

## Implementation Priority

**High Priority:**
1. Basic entity endpoints (aliases, variables, servers) - Core functionality
2. CID content access - Foundation of the system
3. Error handling (404, validation) - User experience
4. Boot CID integration - Key feature interaction

**Medium Priority:**
5. Content negotiation - Multiple format support
6. Query parameters - Advanced filtering
7. Exit codes - Scripting support
8. Special endpoints (OpenAPI) - API documentation

**Low Priority:**
9. Performance edge cases - Edge case coverage
10. Binary content - Less common use case
11. Content headers - Advanced features
12. Documentation completeness - Quality of life

## Testing Framework Recommendations

1. **Test Structure:** Use pytest with parametrized tests for similar test cases
2. **Test Helpers:** Create utility functions to compare HTTP and CLI responses
3. **Fixtures:** Set up test data in fixtures for reusability
4. **Coverage:** Aim for 100% coverage of endpoint types
5. **CI Integration:** Run equivalence tests as part of CI pipeline

## Success Criteria

For each test to pass:
1. HTTP and CLI must return same status code
2. Response content must be identical (after normalization for timing/dates)
3. Error messages must match
4. Exit codes must be appropriate for the response

## Notes

- Some endpoints may not be suitable for one-shot mode (e.g., WebSocket endpoints)
- POST/PUT/DELETE operations are intentionally not supported in one-shot mode
- Testing should use `--in-memory-db` to avoid affecting persistent database
- Consider environment variables that might affect behavior (auth, features)
