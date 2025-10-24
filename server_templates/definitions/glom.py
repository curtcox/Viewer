# ruff: noqa: F821, F706
# This template runs inside the Viewer runtime where helpers like `request`
# and `load` are provided by the execution sandbox.
import json
from html import escape
from urllib.parse import parse_qs

from glom import GlomError, glom


def _parse_request_path(info):
    data = info or {}
    raw_path = str(data.get("path") or "")
    segments = [segment for segment in raw_path.split("/") if segment]

    if not segments:
        return "", ""

    server_segment = segments[0]
    if len(segments) == 1:
        return "", server_segment

    target = segments[-1]
    cid_part, dot, _ = target.partition(".")
    if dot:
        return cid_part.strip(), server_segment

    return target.strip(), server_segment



def _extract_query(info):
    data = info or {}
    args = data.get("args") or {}
    value = args.get("q")

    if isinstance(value, list):
        value = value[0] if value else ""

    if value is not None and value != "":
        return str(value)

    query_string = data.get("query_string") or ""
    if query_string:
        parsed = parse_qs(query_string, keep_blank_values=True)
        values = parsed.get("q")
        if values:
            return str(values[0])

    return ""


def _render_page(title, body):
    safe_title = escape(title or "Glom viewer")
    return {
        "output": f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <title>{safe_title}</title>
    <style>
        :root {{
            color-scheme: light dark;
        }}
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8fafc;
            margin: 0;
            padding: 2rem;
        }}
        main {{
            width: 100%;
            margin: 0;
        }}
        section {{
            background: #ffffff;
            border-radius: 0.75rem;
            box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.08);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        pre {{
            background: #0f172a;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
        }}
        code {{
            font-family: 'JetBrains Mono', 'Fira Code', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
        }}
        h1 {{
            margin-top: 0;
        }}
        p {{
            color: #475569;
        }}
    </style>
</head>
<body>
    <main>
        {body}
    </main>
</body>
</html>
""",
        "content_type": "text/html",
    }


def _render_notice(title, message, *, hint=None):
    safe_title = escape(title)
    safe_message = escape(message)
    hint_block = ""
    if hint:
        hint_block = f"<p><code>{escape(hint)}</code></p>"

    body = f"""
<section>
    <h1>{safe_title}</h1>
    <p>{safe_message}</p>
    {hint_block}
</section>
"""
    return _render_page(title, body)


def _format_result(value):
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        except Exception:  # noqa: BLE001 - fall back to string representation
            pass
    return str(value)


cid, server_hint = _parse_request_path(request)
if not cid:
    expected = server_hint or "glom"
    example = f"/{expected}/CID?q=path.to.value"
    raise_return = _render_notice(
        "CID required",
        "Provide a CID in the path to glom its contents.",
        hint=example,
    )
    return raise_return

query = _extract_query(request)
if not query:
    example = f"/{server_hint or 'glom'}/{cid}?q=path.to.value"
    raise_return = _render_notice(
        "Glom query missing",
        "Provide the `q` query parameter to select data from the CID.",
        hint=example,
    )
    return raise_return

try:
    raw_content = load(cid)
except Exception as exc:  # noqa: BLE001 - surface loader errors to callers
    return _render_notice("Unable to load CID", str(exc))

if isinstance(raw_content, bytes):
    try:
        raw_text = raw_content.decode("utf-8")
    except Exception:  # noqa: BLE001 - handle decoding issues gracefully
        return _render_notice(
            "Unsupported CID encoding",
            "Expected UTF-8 encoded text for glom operations.",
        )
else:
    raw_text = str(raw_content)

raw_text = raw_text.strip()
if not raw_text:
    return _render_notice("Empty CID content", "The CID did not contain any JSON data to glom.")

try:
    data = json.loads(raw_text)
except json.JSONDecodeError as exc:
    location = f"line {exc.lineno}, column {exc.colno}" if exc.lineno and exc.colno else ""
    details = f" at {location}" if location else ""
    message = f"Unable to parse CID as JSON{details}."
    return _render_notice("Invalid JSON", message)

try:
    result = glom(data, query)
except GlomError as exc:
    return _render_notice("Glom query failed", str(exc))

formatted = escape(_format_result(result))
body = f"""
<section>
    <h1>Glom result</h1>
    <p>Extracted using query <code>{escape(query)}</code> from CID <code>{escape(cid)}</code>.</p>
    <pre>{formatted}</pre>
</section>
"""

return _render_page("Glom result", body)
