# Pipeline Requests

This document describes the pipeline request functionality in Viewer, which allows chaining multiple servers, CIDs, and parameters together in a single URL.

## What is a Pipeline?

A pipeline is a URL path that involves at least one server accepting input from something in the URL other than the HTTP request body. Pipelines execute **right-to-left**, where each segment's output becomes the input to the segment on its left.

### Simple Examples

```
/echo/input              # "input" is passed to the echo server
/processor/AAAAAAAA      # CID content is passed to processor server
/s2/s1                   # s1's output is passed to s2
/s3/s2/s1                # s1 → s2 → s3 (three-level chain)
```

## URL Structure

A pipeline URL consists of path segments separated by `/`:

```
/{segment1}/{segment2}/{segment3}...?debug=true
```

### Path Segment Types

Each segment is classified as one of:

| Type | Description | Example |
|------|-------------|---------|
| `server` | Named server from `/servers` | `echo`, `markdown` |
| `cid` | Content Identifier | `AAAAAAAA`, `Qm...` |
| `alias` | Alias that resolves to a server or path | `my-alias` |
| `parameter` | Literal text value | `hello-world` |

### Resolution Types

Each segment is resolved in one of these ways:

| Type | Description | When Used |
|------|-------------|-----------|
| `execution` | Execute as code | `.py`, `.sh`, `.js`, `.ts`, `.clj`, `.cljs` extensions, or servers |
| `contents` | Use as data | `.txt`, `.csv`, `.json`, `.xml`, `.html`, `.md` extensions |
| `literal` | Use text as-is | Parameters with no extension |
| `error` | Unrecognized extension | `.xyz`, `.abc`, etc. |

## Execution Flow

Pipelines execute **right-to-left**:

```
/s3/s2/s1
     ↑  ↑
     │  └── s1 executes first, producing output
     └───── s2 receives s1's output, produces its own output
↑
└── s3 receives s2's output, produces final output
```

### Example Execution

Given servers:
- `s1`: returns `"hello"`
- `s2`: prefixes input with `"got:"`
- `s3`: wraps input with `"[", "]"`

Request: `/s3/s2/s1`

1. `s1` executes → outputs `"hello"`
2. `s2` receives `"hello"` → outputs `"got:hello"`
3. `s3` receives `"got:hello"` → outputs `"[got:hello]"`

Final result: `"[got:hello]"`

## Supported Languages

### Python (.py)

Python servers must define a `main()` function to support chaining:

```python
def main(input_data):
    return {"output": f"processed: {input_data}", "content_type": "text/plain"}
```

Python servers **without** a `main()` function can only be the final (rightmost) segment.

### Bash (.sh)

Bash servers receive input via stdin:

```bash
#!/bin/bash
read input
echo "received: $input"
```

Bash with `$1` parameter:

```bash
#!/bin/bash
pattern=$1
grep "$pattern"
```

### JavaScript (.js)

JavaScript servers executed via Node.js:

**CommonJS:**
```javascript
module.exports = function(input) {
    return "processed: " + input;
}
```

**ES Modules:**
```javascript
export default function main(input) {
    return "processed: " + input;
}
```

### TypeScript (.ts)

TypeScript servers executed via Deno:

```typescript
export default function main(input: string): string {
    return `processed: ${input}`;
}
```

### Clojure (.clj) and ClojureScript (.cljs)

```clojure
(fn [input]
  (str "processed: " input))
```

## Parameter Handling

### Bash Parameter Conventions

```
/grep/pattern/input-data
      ↑       ↑
      $1      stdin
```

- First path segment after server → `$1`
- Next segment → stdin

### Python Parameter Conventions

```
/server/config-value/input-data
        ↑            ↑
        first param  second param
```

For `def main(config, input_data)`:
- `config` receives first path segment
- `input_data` receives second path segment

This follows shell pipeline conventions where configuration arguments come before the pipe.

## Debug Mode

Add `?debug=true` to any pipeline request to get detailed execution information instead of the normal result.

### Enabling Debug Mode

Any of these query parameters enable debug mode:
- `?debug=true`
- `?debug=1`
- `?debug=yes`
- `?debug=on`

Values are case-insensitive.

### Debug Response Format

The debug response respects the final extension in the path:

| Extension | Content-Type | Format |
|-----------|--------------|--------|
| `.json` or none | `application/json` | JSON |
| `.html` | `text/html` | Styled HTML |
| `.txt` | `text/plain` | Plain text |

### Debug Response Fields

```json
{
    "segments": [
        {
            "segment_text": "echo",
            "segment_type": "server",
            "resolution_type": "execution",
            "is_valid_cid": false,
            "cid_validation_error": null,
            "aliases_involved": [],
            "server_name": "echo",
            "server_definition_cid": "ABC123...",
            "supports_chaining": true,
            "implementation_language": "python",
            "input_parameters": [
                {"name": "input_data", "required": true, "source": "path", "value": "hello"}
            ],
            "parameter_values": {"input_data": "hello"},
            "executed": true,
            "input_value": "hello",
            "intermediate_output": "got:hello",
            "intermediate_content_type": "text/plain",
            "server_invocation_cid": "INV456...",
            "errors": []
        }
    ],
    "final_output": "got:hello",
    "final_content_type": "text/plain",
    "success": true,
    "error_message": null
}
```

### Field Descriptions

| Field | Description |
|-------|-------------|
| `segment_text` | Original text from the URL path |
| `segment_type` | server, cid, alias, or parameter |
| `resolution_type` | How the segment is resolved (execution, contents, literal, error) |
| `is_valid_cid` | Whether segment is a valid CID |
| `aliases_involved` | Chain of aliases if resolved through aliases |
| `server_name` | Name of the server (if applicable) |
| `server_definition_cid` | CID of the server definition |
| `supports_chaining` | Whether server can be in non-final position |
| `implementation_language` | python, bash, javascript, typescript, clojure, clojurescript |
| `input_parameters` | List of function parameters |
| `parameter_values` | Actual values assigned to parameters |
| `executed` | Whether this segment was executed |
| `input_value` | Input received from the right |
| `intermediate_output` | Output produced by this segment |
| `intermediate_content_type` | Content type of the output |
| `server_invocation_cid` | CID of the invocation record |
| `errors` | List of any errors encountered |

## Error Handling

### Unrecognized Extensions

Using an unrecognized file extension results in an error:

```
/echo/data.xyz?debug=true
```

Response includes:
```json
{
    "segments": [
        {...},
        {
            "segment_text": "data.xyz",
            "resolution_type": "error",
            "errors": ["unrecognized extension: xyz"]
        }
    ],
    "success": false
}
```

### Server Not Found

Requesting a non-existent server:

```
/nonexistent-server/input?debug=true
```

Response includes:
```json
{
    "segments": [
        {
            "segment_text": "nonexistent-server",
            "segment_type": "server",
            "errors": ["server not found"]
        }
    ],
    "success": false
}
```

### Chaining Not Supported

Python server without `main()` in non-final position:

```json
{
    "segments": [
        {
            "server_name": "no-main-server",
            "supports_chaining": false,
            "errors": ["server does not support chaining (no main function)"]
        }
    ],
    "success": false
}
```

### Runtime Unavailable

When a language runtime is not installed:

```
HTTP 500: Node.js runtime is not available
HTTP 500: Deno runtime is not available
```

## CID Literal Execution

CIDs can be executed as code by adding an extension:

```
/{CID}.py/input    # Execute CID content as Python
/{CID}.sh/input    # Execute CID content as Bash
/{CID}.js/input    # Execute CID content as JavaScript
```

The extension overrides any language detection from the CID content.

## Mixed Language Pipelines

Different languages can be chained together:

```
/{python-cid}.py/{bash-cid}.sh/{javascript-cid}.js/input
```

Each segment executes in its native runtime, with output passed as text.

## Single-Segment Debug

Debug mode works on single segments too:

```
/echo?debug=true
```

Returns debug information for just that server, useful for inspecting server configuration.

## Best Practices

1. **Use explicit extensions** for CID literals to make intent clear
2. **Enable debug mode** when developing pipelines to see intermediate values
3. **Check `supports_chaining`** before placing Python servers in middle positions
4. **Test with debug first** before relying on actual execution
5. **Handle errors gracefully** - check `success` field in debug responses
