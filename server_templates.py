"""Predefined server templates available for the server creation form."""

from __future__ import annotations

from textwrap import dedent
from typing import Iterable

# The definitions here are kept as module-level constants so they can be imported
# without performing any additional work each time the new server form is
# rendered.  Callers should use :func:`get_server_templates` to receive copies of
# the template metadata.
_SERVER_TEMPLATES: tuple[dict[str, str], ...] = (
    {
        "id": "echo",
        "name": "Echo request context",
        "description": "Render the incoming request and context as HTML for debugging.",
        "definition": dedent(
            """
            from html import escape

            def dict_to_html_ul(data: dict) -> str:
                if not isinstance(data, dict):
                    raise TypeError("expects a dict at the top level")

                def render(d: dict) -> str:
                    items = d.items()

                    lis = []
                    for k, v in items:
                        k_html = escape(str(k))
                        if isinstance(v, dict):
                            lis.append(f"<li>{k_html}{render(v)}</li>")
                        else:
                            v_html = "" if v is None else escape(str(v))
                            lis.append(f"<li>{k_html}: {v_html}</li>")
                    return "<ul>" + "".join(lis) + "</ul>"

                return render(data)

            out = {
              'request': request,
              'context': context
            }

            html = '<html><body>' + dict_to_html_ul(out) + '</body></html>'

            return { 'output': html }
            """
        ).strip(),
    },
    {
        "id": "openrouter",
        "name": "OpenRouter API call",
        "description": "Call the OpenRouter chat completions API with a sample prompt.",
        "definition": dedent(
            """
            import os
            import requests

            API_KEY = context.get('secrets').get("OPENROUTER_API_KEY")
            if not API_KEY:
                return { 'output': 'Missing OPENROUTER_API_KEY' }

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "nvidia/nemotron-nano-9b-v2:free",
                "messages": [
                    {"role": "user", "content": "What is the meaning of life?"}
                ]
            }

            resp = requests.post(url, headers=headers, json=data, timeout=60)
            resp.raise_for_status()

            return { 'output': resp.json() }
            """
        ).strip(),
    },
)


def get_server_templates() -> list[dict[str, str]]:
    """Return copies of the available server templates.

    The returned dictionaries are shallow copies to prevent callers from
    mutating the module-level constants by accident.
    """

    return [dict(template) for template in _SERVER_TEMPLATES]


def iter_server_templates() -> Iterable[dict[str, str]]:
    """Yield templates one-by-one without exposing internal state."""

    for template in _SERVER_TEMPLATES:
        yield dict(template)
