# Gauge Spec Failures - Remediation Plan

## Current Status

**Test Results:** 66 passing, 47 failing

### Key Finding

Investigation revealed that `ai_editor` and `urleditor` servers ARE being loaded correctly by `ensure_default_resources()` and are available in the database with `enabled=True`. Some specs pass while others fail, suggesting possible test infrastructure issues rather than code issues.

### Remaining Failures by Category

1. **AI editor** (3 failures):
   - Server is available in default boot image
   - Request payload is embedded for editing
   - Server rejects being used in a chain

2. **Server command chaining** (34 failures):
   - Most chaining scenarios failing across Python/Bash/Clojure/ClojureScript/TypeScript
   - Affects CID literal execution and server chaining

3. **Server events dashboard** (1 failure):
   - Dashboard accessibility

4. **Servers list dependencies** (3 failures):
   - Dependency display on servers list page

5. **URL editor** (6 failures):
   - Server is available in default boot image
   - Subpath redirect to fragment
   - Chain rejection
   - Required elements
   - Multiple path element previews
   - Preview links

## Plan to Eliminate Remaining Failures

### 1. Investigate Test Infrastructure Issues

Since servers are confirmed to be loaded but "availability" tests still fail, investigate:
- How Gauge specs check for "server is available in default boot image"
- Timing issues in test setup/teardown
- Context isolation between test scenarios
- Whether tests are checking the right database/state

**Priority: High** - This may resolve many failures at once

### 2. Fix Server Command Chaining (34 failures)

Debug the chaining pipeline to understand why CID execution and server chaining scenarios fail:
- Verify CID creation and storage in test scenarios
- Check request routing for chained commands
- Validate language-specific runner stubs (TypeScript/Clojure placeholders may be incomplete)
- Ensure server events are being tracked and surfaced correctly

**Priority: High** - Largest category of failures

### 3. Fix AI Editor Failures (3 failures)

Address remaining AI editor issues:
- Debug "availability" test (likely infrastructure issue per key finding above)
- Verify request payload embedding in editor page
- Confirm chain rejection logic returns appropriate responses

**Priority: Medium** - Small number but important functionality

### 4. Fix URL Editor Failures (6 failures)

Address remaining URL editor issues:
- Debug "availability" test (likely infrastructure issue)
- Verify subpath-to-fragment redirect logic
- Confirm chain rejection behavior
- Validate required page elements are rendered
- Fix preview functionality for multiple path elements
- Ensure preview links work correctly

**Priority: Medium** - Important user-facing feature

### 5. Fix Server Dependencies Display (3 failures)

Ensure dependency information displays correctly on servers list page:
- Verify dependency data collection
- Check template rendering logic
- Validate test assertions match actual UI structure

**Priority: Low** - Smaller impact

### 6. Fix Server Events Dashboard (1 failure)

Resolve dashboard accessibility issue:
- Verify route registration
- Check authentication/authorization requirements
- Ensure dashboard page renders correctly

**Priority: Low** - Single failure

## Recommended Approach

1. Start with test infrastructure investigation (#1) - could resolve multiple categories
2. Tackle server command chaining (#2) - largest failure category
3. Address editor issues (#3, #4) in parallel
4. Clean up remaining issues (#5, #6)
