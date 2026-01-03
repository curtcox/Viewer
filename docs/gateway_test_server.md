# Gateway Test Server Support

The gateway server supports using test servers in place of named servers for testing purposes. This allows you to test gateway transforms with local or archived data instead of making requests to external services.

## Overview

The test server feature allows you to:
- Use a local server (like HRX or CIDS archives) to provide responses
- Apply the transforms from a named gateway configuration
- Test gateway behavior without external dependencies
- Create reproducible test scenarios

## URL Pattern

```
/gateway/test/{test-server-path}/as/{server}/{rest-of-request}
```

### Components

- `{test-server-path}`: Path to the test server (e.g., `hrx/ARCHIVE_CID` or `cids/ARCHIVE_CID`)
- `{server}`: Name of the gateway server whose transforms should be used
- `{rest-of-request}`: The remaining path to pass to the gateway transforms

### Example

```
/gateway/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder/posts/1
```

This request:
1. Uses the HRX archive at `AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A`
2. Applies the `jsonplaceholder` gateway transforms
3. Processes the path `/posts/1`

## Meta Page Support

The test pattern also works with meta pages:

```
/gateway/meta/test/{test-server-path}/as/{server}
```

This shows:
- Information about the named server configuration
- The test server that will be used
- The transforms that will be applied

## Creating Test Archives

### Using HRX Format

HRX (HTTP Archive) is a text format for storing HTTP request/response pairs:

```hrx
<==> /posts/1 GET
HTTP/1.1 200 OK
Content-Type: application/json

{
  "userId": 1,
  "id": 1,
  "title": "Example post"
}

<==> /users/1 GET
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 1,
  "name": "Test User"
}
```

### Generating a CID

1. Create your test archive file (e.g., `test_data.hrx`)
2. Generate a CID for it using the project's CID utilities
3. Place the file in the `cids/` directory with the CID as the filename

Example Python code:
```python
import hashlib
import base64
import shutil

# Read content
with open('test_data.hrx', 'rb') as f:
    content = f.read()

# Generate CID (SHA-512/256)
hasher = hashlib.sha512(content)
hash_bytes = hasher.digest()[:32]
cid = 'AAAAA' + base64.urlsafe_b64encode(hash_bytes).decode('ascii').rstrip('=')

# Save to cids directory
shutil.copy('test_data.hrx', f'cids/{cid}')
```

## Alias Support

You can create aliases to make test servers easier to use. For example, the `local_jsonplaceholder` alias:

```
/gateway/jsonplaceholder/** -> /gateway/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder/**
```

When enabled, this alias redirects all jsonplaceholder gateway requests to use the local HRX archive.

### Creating Test Aliases

1. Create a file in `reference_templates/aliases/` (e.g., `my_test_alias.txt`)
2. Define the alias mapping using the test pattern
3. The alias will be disabled by default (as specified by `enabled=False` in the database)

## Example: Testing JSONPlaceholder Gateway

The repository includes a pre-configured test archive for the jsonplaceholder gateway:

**CID:** `AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A`

**Contents:**
- `/posts` - List of posts
- `/posts/1` - Single post
- `/users/1` - User data

**Usage:**
```
# Direct test request
/gateway/test/hrx/AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A/as/jsonplaceholder/posts/1

# Or enable the local_jsonplaceholder alias and use:
/gateway/jsonplaceholder/posts/1
```

## Use Cases

### 1. Development and Testing

Test gateway transforms without requiring external API access:
- Work offline
- Faster test execution
- No rate limiting or API keys needed

### 2. Reproducible Tests

Create consistent test scenarios:
- Fixed responses for unit/integration tests
- Known data for debugging
- Version-controlled test data

### 3. CI/CD Pipelines

Run tests in isolated environments:
- No external dependencies
- Deterministic test results
- Faster CI builds

### 4. Gateway Development

Iterate on transforms quickly:
- Test edge cases with crafted responses
- Validate error handling
- Verify transform logic

## Implementation Details

### Request Flow

1. Gateway receives request at test pattern URL
2. Parses `test-server-path`, `server`, and `rest-of-request`
3. Loads the gateway configuration for `server`
4. Applies the request transform using `server`'s transforms
5. Routes to `test-server-path` instead of the normal server
6. Applies the response transform using `server`'s transforms
7. Returns the transformed response

### Context Enhancement

When using test mode, the context includes:
- `test_mode: true` - Indicates test mode is active
- `test_server_path` - The path to the test server being used

Transforms can check for `test_mode` to adjust behavior if needed.

## Testing

### Unit Tests

Located in `tests/test_gateway_test_support.py`:
- Path parsing validation
- Test target resolution
- Alias definition validation
- CID archive verification

### Integration Tests

Located in `tests/integration/test_gateway_test_server.py`:
- End-to-end test pattern routing
- Meta page with test information
- Alias behavior when enabled/disabled
- Error handling for missing servers/CIDs
- Transform preservation

## Troubleshooting

### Test Server Not Found

**Error:** "No internal target handled path"

**Solution:** Ensure the test server (e.g., HRX or CIDS) is configured and the archive CID exists.

### Transform Errors

**Error:** "Could not load request/response transform"

**Solution:** Verify the gateway configuration includes valid transform CIDs and the transforms are accessible.

### Alias Not Working

**Problem:** Requests don't use the test server

**Solution:** Check that the alias is enabled in the database. Aliases created from reference templates are disabled by default.

## Future Enhancements

Potential improvements for the test server feature:
- Support for CIDS archives (in addition to HRX)
- Test server selection via query parameters
- Test data generation utilities
- Web UI for managing test archives
- Import/export of test scenarios
