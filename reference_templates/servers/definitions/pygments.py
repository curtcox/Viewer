# ruff: noqa: F401, F706, F821
# pylint: disable=undefined-variable,return-outside-function
# This template runs inside the Viewer runtime where helpers such as `request`
# and `load` are provided by the execution sandbox.
from html import escape

from syntax_highlighting import highlight_source


def _parse_request_path(info):
    data = info or {}
    raw_path = str(data.get("path") or "")
    segments = [segment for segment in raw_path.split("/") if segment]

    if not segments:
        return "", "", ""

    server_segment = segments[0]
    if len(segments) == 1:
        return "", "", server_segment

    target = segments[-1]
    cid_part, dot, ext_part = target.rpartition(".")
    if dot:
        return cid_part.strip(), ext_part.strip().lower(), server_segment

    return target.strip(), "", server_segment


def _build_error_page(message, title):
    safe_title = escape(title or "Pygments Viewer")
    safe_message = escape(message or "Unable to load the requested CID.")
    return {
        "output": f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <title>{safe_title}</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8f9fa;
            margin: 0;
            padding: 2rem;
        }}
        .notice {{
            width: 100%;
            margin: 0;
            padding: 2rem;
            background: #fff;
            border-radius: 0.75rem;
            box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.08);
        }}
    </style>
</head>
<body>
    <section class=\"notice\">
        <h1>{safe_title}</h1>
        <p>{safe_message}</p>
    </section>
</body>
</html>
""",
        "content_type": "text/html",
    }


cid, extension, server_hint = _parse_request_path(request)
filename = f"{cid}.{extension}" if extension else cid

if not cid:
    expected = escape(server_hint or "this-server")
    message = f"Provide a CID path such as /{expected}/CID.py to render highlighted source."
    raise_return = _build_error_page(message, "CID required")
    return raise_return

try:
    source_text = load(cid)
except Exception as exc:  # noqa: BLE001 - surface errors to the caller
    return _build_error_page(str(exc) or "Unable to read CID content.", f"Error loading {escape(filename)}")

highlighted_html, syntax_css = highlight_source(
    source_text,
    filename=filename or None,
    fallback_lexer=extension or None,
)

if not highlighted_html:
    highlighted_html = escape(source_text)
    syntax_css = ""

base_css = """
body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f2f5;
    margin: 0;
    padding: 2rem;
}
main {
    width: 100%;
    margin: 0;
}
header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
}
h1 {
    font-size: 1.5rem;
    margin: 0;
    color: #1f2937;
}
article {
    background: #ffffff;
    border-radius: 0.75rem;
    box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.08);
    padding: 1.5rem;
    overflow-x: auto;
}
.codehilite {
    font-family: 'JetBrains Mono', 'Fira Code', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
    font-size: 0.95rem;
    line-height: 1.6;
}
.codehilite pre {
    margin: 0;
}
""".strip()

css_block = "\n".join(part for part in [syntax_css or "", base_css] if part).strip()
if css_block:
    css_block = f"<style>\n{css_block}\n</style>"

if "<pre" not in highlighted_html:
    highlighted_html = f"<pre>{highlighted_html}</pre>"

title_text = escape(filename or cid)

html_output = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <title>{title_text}</title>
    {css_block}
</head>
<body>
    <main>
        <header>
            <h1>{title_text}</h1>
            <p style=\"margin: 0; color: #6b7280;\">Rendering from CID <code>{escape(cid)}</code></p>
        </header>
        <article class=\"codehilite\">
            {highlighted_html}
        </article>
    </main>
</body>
</html>
"""

return {
    "output": html_output,
    "content_type": "text/html",
}
