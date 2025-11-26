# One-Shot Run Test Proposals

This document outlines proposed tests to verify the one-shot run functionality provides equivalent responses to HTTP requests.

## Overview

One-shot run mode allows the application to be invoked from the command line with a URL parameter, returning the same response as if the request came via HTTP. This mode is useful for:
- Testing endpoints without running a server
- Scripting and automation
- CI/CD pipelines
- Verifying identical behavior between HTTP and CLI

## Implemented Tests

The following tests have been implemented in `tests/integration/test_one_shot_equivalence.py`:

1. **Entity Endpoints** - ✅ Implemented
   - `/aliases.json` equivalence (test_aliases_json_equivalence)
   - `/variables.json` equivalence (test_variables_json_equivalence)
   - `/secrets.json` equivalence (test_secrets_json_equivalence)
   - `/servers.json` equivalence (test_servers_json_equivalence)

2. **Content Negotiation** - ✅ Implemented
   - JSON format equivalence (test_servers_json_equivalence)
   - HTML format equivalence (test_html_format_equivalence)
   - Plain text format equivalence (test_cid_text_format_equivalence)

3. **CID Content Access** - ✅ Implemented
   - Direct CID access equivalence (test_cid_from_boot_image_equivalence)
   - CID with .json extension (test_cid_with_json_extension)
   - CID with .txt extension (test_cid_text_format_equivalence)

4. **Query Parameters and Filtering** - ✅ Implemented
   - Filtered server list (test_filtered_enabled_servers)
   - Query parameters in general (test_json_endpoint_with_query_params)
   - Search page equivalence (test_search_page_equivalence)
   - Search results empty query (test_search_results_empty_query_equivalence)
   - Search results with query (test_search_results_with_query_equivalence)
   - Search results with category filter (test_search_results_with_category_filter_equivalence)
   - Search results multiple filters (test_search_results_multiple_filters_equivalence)

5. **Error Handling** - ✅ Implemented
   - 404 consistency (test_404_equivalence)
   - Invalid CID format error (test_invalid_cid_format_error)

6. **Boot CID Integration** - ✅ Implemented
   - Boot CID data availability (test_servers_json_with_boot_cid)

7. **Special Endpoints** - ✅ Implemented
   - OpenAPI spec equivalence (test_openapi_json_equivalence)

8. **Exit Codes** - ✅ Implemented
   - Success exit code (test_exit_code_success)
   - Error exit code (test_exit_code_error)

9. **Unicode and International Content** - ✅ Implemented
   - Unicode content equivalence (test_unicode_content_equivalence)

10. **Root Path** - ✅ Implemented
    - Root path equivalence (test_root_path_equivalence)

## Remaining Test Proposals

### 5. Error Handling

#### 5.3 Method Not Allowed
**Test:** Verify that CLI GET-only limitation matches HTTP GET restrictions
- **Why:** HTTP method restrictions should be clear
- **What to check:** Error handling for POST-only endpoints accessed via CLI
- **CLI command:** `python main.py /some-post-only-endpoint`
- **Status:** ⚠️ Not implemented - need to identify POST-only endpoints

### 6. Integration with Boot CIDs

#### 6.2 Boot CID Override
**Test:** Verify boot CID data overrides existing data consistently
- **Why:** Data precedence rules should be the same
- **What to check:** Boot CID data takes precedence
- **CLI command:** Test with conflicting boot CID
- **Status:** ⚠️ Not implemented - complex scenario requiring conflicting data setup

### 7. Special Endpoints

#### 7.2 Health Check Endpoint
**Test:** Verify health check endpoints work identically
- **Why:** Health checks are critical for monitoring
- **What to check:** Status and diagnostic information
- **CLI command:** `python main.py /health` (if such endpoint exists)
- **Status:** ⚠️ Not implemented - depends on whether health endpoint exists

### 8. Performance and Edge Cases

#### 8.1 Large Response Handling
**Test:** Verify large responses (>1MB) are handled identically
- **Why:** Large responses can reveal buffering differences
- **What to check:** Complete content delivery, no truncation
- **CLI command:** `python main.py /{large_cid}`
- **Status:** ⚠️ Not implemented - requires creating large test content

#### 8.2 Binary Content
**Test:** Verify binary content (images, PDFs) is delivered correctly via CLI
- **Why:** Binary data encoding can differ between methods
- **What to check:** Binary output is identical to HTTP
- **CLI command:** `python main.py /{binary_cid}`
- **Status:** ⚠️ Not implemented - requires binary test fixtures

#### 8.3 Concurrent One-Shot Invocations
**Test:** Verify multiple one-shot invocations can run concurrently without conflicts
- **Why:** CLI should support parallel execution for automation
- **What to check:** No database locking issues, correct results
- **CLI command:** Run multiple `python main.py /path` in parallel
- **Status:** ⚠️ Not implemented - requires parallel test execution

### 9. Content Headers and Metadata

#### 9.1 Content-Type Header Consistency
**Test:** Verify Content-Type headers are reported correctly in one-shot mode
- **Why:** Content type detection should be identical
- **What to check:** Status output includes correct content type
- **CLI command:** Check output of `python main.py /some.json`
- **Status:** ⚠️ Not implemented - would need to parse CLI output format

#### 9.2 Cache Headers
**Test:** Verify caching headers (if any) are documented in CLI output
- **Why:** Caching behavior should be transparent
- **What to check:** Cache-related headers in status output
- **CLI command:** `python main.py /{cacheable_cid}`
- **Status:** ⚠️ Not implemented - depends on caching implementation

### 10. Documentation and Help

#### 10.1 Help Text Completeness
**Test:** Verify `--help` fully documents one-shot mode
- **Why:** Users need clear documentation
- **What to check:** One-shot mode described, examples provided
- **CLI command:** `python main.py --help`
- **Status:** ⚠️ Not implemented - documentation test

#### 10.2 Example Commands Work
**Test:** Verify all example commands in help text actually work
- **Why:** Documentation examples must be accurate
- **What to check:** Each example executes successfully
- **CLI commands:** Test each example from help
- **Status:** ⚠️ Not implemented - depends on 10.1

### 12. UTF-8 and International Content

#### 12.2 Special Characters in URLs
**Test:** Verify URL-encoded special characters work in one-shot mode
- **Why:** URL encoding should be handled consistently
- **What to check:** Special characters properly decoded
- **CLI command:** `python main.py "/search?q=test%20query"`
- **Status:** ⚠️ Not implemented - requires URL encoding test cases

## Implementation Status Summary

**Implemented (23 tests):**
- ✅ All entity endpoints (aliases, variables, servers, secrets)
- ✅ Content negotiation (JSON, HTML, text formats)
- ✅ CID content access (direct access, .json, .txt extensions)
- ✅ Query parameters and filtering
- ✅ Search endpoints (/search page, /search/results with query and filters)
- ✅ Error handling (404, invalid CID format)
- ✅ Boot CID integration (data availability)
- ✅ OpenAPI specification endpoint
- ✅ Exit codes (success and error)
- ✅ Unicode content handling
- ✅ Root path access

**Not Implemented (10 proposals):**
- ⚠️ Method not allowed (POST-only endpoints)
- ⚠️ Boot CID override (complex scenario)
- ⚠️ Health check endpoint (depends on endpoint existence)
- ⚠️ Large response handling (requires large test content)
- ⚠️ Binary content (requires binary test fixtures)
- ⚠️ Concurrent invocations (requires parallel test execution)
- ⚠️ Content-Type header inspection (CLI output format parsing)
- ⚠️ Cache headers (depends on caching implementation)
- ⚠️ Help text completeness (documentation test)
- ⚠️ URL-encoded special characters (requires URL encoding test cases)

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

## Open Questions and Missing Test Considerations

### Open Questions:
1. **Search endpoint**: ✅ Answered - Yes, the application has `/search` (HTML page) and `/search/results` (JSON API) endpoints. Both work in one-shot mode and tests have been implemented.
2. **Health check endpoint**: Is there a health check endpoint (e.g., `/health`, `/status`) that should be tested?
3. **POST-only endpoints**: Which endpoints are POST-only and should return appropriate errors in one-shot mode?
4. **Caching behavior**: Are there any caching headers or behaviors that differ between HTTP and CLI?
5. **Binary content handling**: How should binary content (images, PDFs) be output in CLI mode? Direct to stdout?
6. **Content-Type header output**: Should the CLI output include Content-Type information beyond the Status line?

### Missing Tests That Could Be Added:
1. **CID with .html extension**: Test that `/{cid}.html` returns HTML-formatted content
2. **Large CID content**: Test handling of CIDs with content >1MB to verify no truncation
3. **Binary CID content**: Test that binary content (e.g., images) is correctly output
4. **Multiple query parameters**: Test endpoints with multiple query parameters (e.g., `?name=x&enabled=true`)
5. **Pagination parameters**: If pagination is supported, test `?page=1&per_page=10`
6. **Alias resolution**: Test that aliases are resolved correctly in one-shot mode
7. **Template rendering**: Test that server templates are rendered identically
8. **Error pages with different formats**: Test error pages with .json, .html extensions
9. **Concurrent execution stress test**: Run many parallel invocations to check for race conditions
10. **Database snapshot functionality**: Test that `--snapshot` works correctly with one-shot mode

### Test Improvements:
1. **More comprehensive CID testing**: Test CIDs with various content types (JSON, HTML, Markdown, etc.)
2. **Edge case query parameters**: Test empty values, special characters, very long values
3. **Boot CID scenarios**: Test multiple boot CIDs, nested CIDs, invalid boot CIDs
4. **Performance benchmarks**: Compare response times between HTTP and CLI (should be similar)
5. **Memory usage**: Verify CLI mode doesn't leak memory on repeated invocations

### Documentation Needs:
1. Document which endpoints are available in one-shot mode
2. Document exit code meanings (0 = success, 1 = HTTP error, other codes?)
3. Document any differences in behavior between HTTP and CLI modes
4. Provide examples of common use cases for one-shot mode
5. Document how to pass authentication/authorization in one-shot mode (if applicable)
