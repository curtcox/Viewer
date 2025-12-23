# IO Requests

IO requests provide **bidirectional request/response piping** through a chain of servers. Unlike pipeline requests (which flow right-to-left only), IO requests:

- Flow **requests left-to-right**
- Flow **responses right-to-left**
- Invoke **middle servers twice** (once for each phase)
- Invoke the **tail server once** (produces the initial response)

## Data Flow Pattern

```
Request Phase (left-to-right):
    User -> [io] -> [S1] -> [S2] -> [Tail]
                     |       |        |
                  request  request  request
                     v       v        v
                  output   output  response

Response Phase (right-to-left):
                              response
                                 |
    User <- [io] <- [S1] <- [S2] <-+
              |       |       |
           output  output  output
```

## URL Structure

```
/io/server1/param1/server2/param2
```

Where:
- `server1`, `server2` are named servers, aliases, or CIDs
- `param1`, `param2` are literal parameters that configure the server to their left

## Server Roles

### Head (IO Server)
The `/io` server orchestrates the chain:
- Accepts the user request
- Invokes each server in the chain
- Passes data between servers
- Returns the final response to the user

### Middle Servers
Middle servers are invoked **twice**:

1. **Request Phase** (`response is None`):
   - Receives the request (from user or previous server)
   - Produces a transformed request for the next server

2. **Response Phase** (`response is not None`):
   - Receives the original request AND the response from the server to its right
   - Produces a modified response for the server to its left

### Tail Server
The tail (rightmost) server is invoked **once**:
- Receives the request from the previous server
- Produces the initial response
- This response travels back through the chain

## Middle Server Signature

IO-compatible servers should use this signature:

```python
def main(request, response=None, *, context=None):
    """
    Args:
        request: The request data (always present)
        response: Response from server to the right (None in request phase)
        context: Request context

    Returns:
        dict with 'output' and optionally 'content_type'
    """
    if response is None:
        # Request phase: transform request for next server
        return {"output": process_request(request)}
    else:
        # Response phase: modify response before passing back
        return {"output": process_response(request, response)}
```

## Parameter Binding

Parameters bind to the server on their **left** (appear to the **right** of the server they configure):

```
/io/grep/pattern/cat/file.txt
    ^^^^  ^^^^^^^  ^^^  ^^^^^^^^
     |      |       |      |
     |      |       |      +-- param for cat
     |      |       +--------- tail server
     |      +----------------- param for grep
     +------------------------ middle server
```

Execution flow:
1. **Request phase**:
   - `grep` receives `"pattern"` as request
   - `grep` produces a request for `cat`
   - `cat` receives `"file.txt"` AND grep's request
   - `cat` returns file contents

2. **Response phase**:
   - `grep` receives its original request (`"pattern"`) AND the file contents
   - `grep` filters the contents and returns matching lines

## Existing Server Compatibility

Existing servers with signature `def main(input_data, *, context=None)` can be used as:
- **Tail server**: Yes (single invocation)
- **Middle server**: No (requires two-phase signature)

## Debug Mode

Add `?debug=true` to see detailed execution information:

```
/io/server1/server2?debug=true
```

Debug output includes:
- Request phase input/output for each server
- Response phase input/output for each server
- Errors encountered at each stage

Debug format is determined by the **leftmost** server's extension:
- `/io/server.json?debug=true` → JSON output
- `/io/server.html?debug=true` → HTML output
- `/io/server.txt?debug=true` → Plain text output

## Error Handling

### Request Phase Errors
If a server fails during the request phase:
- Execution stops immediately
- Error is returned to the user
- Response phase is not executed

### Response Phase Errors
If a server fails during the response phase:
- Execution stops immediately
- Error is returned to the user
- Remaining servers in the chain are skipped

## Content-Type Handling

- Each server can set `content_type` in its response
- The **leftmost** server's content-type is used for the final response
- If a server doesn't specify content-type, it inherits from the response it received

## Examples

### Simple Echo
```
/io/echo/hello
```
- `echo` receives "hello"
- Returns "hello"

### Two-Server Chain
```
/io/upper/reverse/hello
```
Request phase:
- `upper` receives "hello", produces "HELLO" for reverse
- `reverse` receives "HELLO", produces "OLLEH"

Response phase:
- `upper` receives ("hello", "OLLEH"), could modify but returns "OLLEH"

### Filtering Pattern
```
/io/grep/error/cat/logfile.txt
```
- `cat` returns contents of logfile.txt
- `grep` filters for lines containing "error"

## Comparison with Pipeline Requests

| Aspect | Pipeline | IO |
|--------|----------|-----|
| Request flow | Right-to-left | Left-to-right |
| Response flow | N/A (single pass) | Right-to-left |
| Middle server invocations | Once | Twice |
| Tail server invocations | Once | Once |
| Parameter binding | Right of server | Right of server |
| Implementation | Built-in | Named server |

## When to Use IO vs Pipeline

Use **IO** when you need:
- Bidirectional data transformation
- Context-aware response modification
- Request preprocessing before downstream servers

Use **Pipeline** when you need:
- Simple right-to-left data transformation
- Each server processes independently
- Simpler mental model

## Potential Future IO Servers

The following servers are designed specifically for IO chains. They leverage the bidirectional request/response flow to provide capabilities not possible with simple pipeline servers.

### Request Transformation Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `validate` | Validate requests against schemas, reject invalid | `/io/validate/schema.json/api` |
| `auth` | Add authentication headers/tokens to requests | `/io/auth/bearer/api` |
| `sign` | Cryptographically sign requests | `/io/sign/key/api` |
| `prefix` | Add prefix to request data | `/io/prefix/Hello:/echo/World` |
| `suffix` | Add suffix to request data | `/io/suffix/!/echo/Hello` |

### Response Transformation Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `filter` | Filter response content (regex or jq-style) | `/io/filter/error/cat/log.txt` |
| `transform` | Apply JSONPath/jq transformations to responses | `/io/transform/.data/api` |
| `compress` | Compress responses (gzip, brotli) | `/io/compress/gzip/api` |
| `wrap` | Wrap response in a template | `/io/wrap/template.html/api` |
| `sanitize` | Sanitize HTML/script content from responses | `/io/sanitize/api` |

### Caching and Performance Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `cache` | Cache responses with TTL | `/io/cache/300/api` |
| `rate_limit` | Rate limit requests | `/io/rate_limit/10/api` |
| `timeout` | Set timeout for downstream servers | `/io/timeout/5000/slow_api` |
| `retry` | Retry failed requests with backoff | `/io/retry/3/flaky_api` |
| `delay` | Add artificial delay (testing) | `/io/delay/1000/api` |

### Observability Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `log` | Log requests and responses | `/io/log/api` |
| `count` | Count requests/responses, add statistics | `/io/count/api` |
| `sample` | Sample a percentage of requests | `/io/sample/10/api` |
| `stats` | Collect timing and size statistics | `/io/stats/api` |

### Data Format Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `sql_query` | Translate URL params to SQL queries | `/io/sql_query/csv_to_html/db` |
| `csv_to_html` | Convert CSV responses to HTML tables | `/io/csv_to_html/data.csv` |
| `sql_browser` | Combined SQL query builder with HTML output | `/io/sql_browser/db/users` |

### Testing and Development Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `mock` | Return mock responses for testing | `/io/mock/response.json/api` |
| `fail` | Simulate failures (testing error handling) | `/io/fail/500/api` |
| `echo_both` | Echo both request and response (debugging) | `/io/echo_both/api` |

### Aggregation Servers

| Server | Purpose | Example |
|--------|---------|---------|
| `split` | Split request to multiple downstream servers | `/io/split/api1/api2` |
| `merge` | Merge responses from multiple sources | `/io/merge/api1/api2` |
| `encrypt` | Encrypt request/response data | `/io/encrypt/key/api` |

## Example IO Chains

These chains illustrate common patterns and can be used to test the IO implementation.

### Authenticated API with Caching
```
/io/cache/300/auth/bearer/validate/schema.json/api
```
- Validates request against schema
- Adds bearer token authentication
- Caches response for 5 minutes

### Logged and Filtered Data
```
/io/log/filter/error/cat/application.log
```
- Reads log file
- Filters for error lines
- Logs the request and response

### Rate-Limited API with Retry
```
/io/rate_limit/10/retry/3/timeout/5000/api
```
- Sets 5-second timeout
- Retries up to 3 times on failure
- Rate limits to 10 requests per window

### SQL Query to HTML Table
```
/io/sql_query/select * from users/csv_to_html/db
```
- Builds SQL query from URL
- Executes against database
- Converts CSV result to HTML table

### Request/Response Transformation
```
/io/prefix/REQUEST:/suffix/!/echo/data
```
- Echoes "data"
- Adds suffix "!" → "data!"
- Adds prefix "REQUEST:" → "REQUEST:data!"

### Debug Chain for Testing
```
/io/log/echo_both/delay/100/echo/test?debug=true
```
- Echoes "test" with 100ms delay
- Shows both request and response
- Logs everything
- Debug mode shows full execution trace