# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
"""IO Server - Bidirectional request/response piping.

The io server provides bidirectional data flow through a chain of servers:
- Requests flow left-to-right
- Responses flow right-to-left

Unlike pipeline execution (which flows right-to-left only), io execution
invokes middle servers twice - once for the request phase and once for
the response phase.

Data Flow:
    User Request -> [io] -> [S1] -> [S2] -> [S3] -> (tail returns response)
                                    |
    User Response <- [io] <- [S1] <- [S2] <- [S3]

Usage:
    /io/server1/param/server2/param2
    - server1 receives 'param' in request phase
    - server1 produces request for server2
    - server2 receives 'param2' AND request from server1
    - server2 (tail) returns response
    - server1 receives original request + response from server2
    - server1 returns final response to user
"""

from html import escape


def main(*path_segments, context=None):
    """IO server main entry point.

    When invoked with no additional servers, returns the landing page.
    When invoked with servers, orchestrates the IO chain execution.

    Args:
        *path_segments: Path segments after /io (servers and parameters)
        context: Request context (automatically provided)

    Returns:
        dict with 'output' and 'content_type' keys
    """
    # If no path segments, return landing page
    if not path_segments or all(not seg for seg in path_segments):
        return _render_landing_page()

    # Filter out empty segments
    segments = [seg for seg in path_segments if seg]

    if not segments:
        return _render_landing_page()

    # Execute the IO chain
    try:
        from server_execution.io_execution import execute_io_chain

        # Get the full path for execution
        path = "/io/" + "/".join(segments)

        # Execute without a server executor for now - this will be enhanced
        # to actually invoke the chained servers
        result = execute_io_chain(path, debug=False)

        if not result.success:
            return {
                "output": _render_error_page(
                    "IO Chain Error", result.error_message or "Unknown error"
                ),
                "content_type": "text/html",
            }

        if result.final_output is None:
            return _render_landing_page()

        return {
            "output": result.final_output,
            "content_type": result.final_content_type,
        }

    except ImportError:
        # Fallback if io_execution module not available
        return {
            "output": _render_error_page(
                "IO Server Not Available",
                "The IO execution engine is not available. Please check your installation.",
            ),
            "content_type": "text/html",
        }
    except Exception as e:
        return {
            "output": _render_error_page("IO Execution Error", str(e)),
            "content_type": "text/html",
        }


def _render_landing_page():
    """Render the IO server landing/documentation page."""
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>IO Server</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 900px;
            margin: 2rem auto;
            padding: 0 1rem;
            line-height: 1.6;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 0.5rem;
        }
        h2 {
            color: #34495e;
            margin-top: 2rem;
        }
        .diagram {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 1.5rem;
            font-family: monospace;
            white-space: pre;
            overflow-x: auto;
            margin: 1rem 0;
        }
        .example {
            background: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 4px 4px 0;
        }
        .example code {
            background: #fff;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        .info {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 4px 4px 0;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .link-box {
            display: inline-block;
            margin-top: 1rem;
            padding: 0.75rem 1.5rem;
            background: #3498db;
            color: white;
            border-radius: 4px;
            text-decoration: none;
        }
        .link-box:hover {
            background: #2980b9;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <h1>IO Server</h1>

    <p>The IO server provides <strong>bidirectional request/response piping</strong>
    through a chain of servers.</p>

    <h2>How It Works</h2>

    <div class="diagram">
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
    </div>

    <h2>Server Roles</h2>

    <ul>
        <li><strong>Head (io)</strong>: Accepts user request, orchestrates chain, returns final response</li>
        <li><strong>Middle servers</strong>: Invoked twice - once for request phase, once for response phase</li>
        <li><strong>Tail server</strong>: Invoked once, produces the initial response</li>
    </ul>

    <h2>Middle Server Signature</h2>

    <div class="example">
        <p>Middle servers should use this signature to handle both phases:</p>
        <code>def main(request, response=None, *, context=None):</code>
        <ul>
            <li><strong>Request phase</strong>: <code>response is None</code></li>
            <li><strong>Response phase</strong>: <code>response</code> contains data from the server to the right</li>
        </ul>
    </div>

    <h2>Parameter Binding</h2>

    <p>Parameters bind to the server on their <strong>left</strong> (appear to the right of the server):</p>

    <div class="example">
        <code>/io/grep/pattern/cat/file.txt</code>
        <ul>
            <li><code>grep</code> receives <code>"pattern"</code> as its request</li>
            <li><code>cat</code> receives <code>"file.txt"</code> AND the request from grep</li>
        </ul>
    </div>

    <div class="info">
        <strong>Note:</strong> Existing servers can be used as the tail server only.
        For middle positions, servers must support the two-phase invocation pattern.
    </div>

    <h2>Learn More</h2>

    <p>For complete documentation on IO requests, see:</p>

    <a href="/help/io-requests" class="link-box">IO Requests Documentation</a>

</body>
</html>"""

    return {
        "output": html,
        "content_type": "text/html",
    }


def _render_error_page(title, message):
    """Render an error page."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{escape(title)}</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 2rem auto;
            padding: 0 1rem;
        }}
        .error {{
            background: #fee;
            border-left: 4px solid #c33;
            padding: 1rem;
            border-radius: 0 4px 4px 0;
        }}
        h1 {{
            color: #c33;
        }}
    </style>
</head>
<body>
    <div class="error">
        <h1>{escape(title)}</h1>
        <p>{escape(message)}</p>
    </div>
</body>
</html>"""

    return {
        "output": html,
        "content_type": "text/html",
    }
