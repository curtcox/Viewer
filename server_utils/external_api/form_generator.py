"""HTML form generator helpers for external API servers."""

from dataclasses import dataclass
from html import escape
from typing import Any, Dict, List, Optional


@dataclass
class FormField:
    """Definition for an HTML form field."""

    name: str
    label: str
    field_type: str = "text"  # text, textarea, select, hidden
    default: str = ""
    required: bool = False
    options: Optional[List[str]] = None
    placeholder: str = ""
    help_text: str = ""


def generate_form(
    server_name: str,
    title: str,
    description: str,
    fields: List[FormField],
    endpoint: str = "",
    examples: Optional[List[Dict[str, str]]] = None,
    documentation_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate an HTML form for an API server."""

    action = endpoint or f"/{server_name}"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{escape(title)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; max-width: 800px; }}
        h1 {{ color: #333; }}
        .description {{ color: #666; margin-bottom: 20px; }}
        .field {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; }}
        input[type='text'], textarea, select {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        textarea {{ height: 100px; font-family: monospace; }}
        .help {{ font-size: 12px; color: #666; margin-top: 3px; }}
        .required {{ color: red; }}
        button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #0056b3; }}
        .examples {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin-top: 20px; }}
        .examples h3 {{ margin-top: 0; }}
        .example {{ margin-bottom: 10px; }}
        code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #e9ecef; padding: 10px; border-radius: 4px; overflow-x: auto; }}
        .doc-link {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <h1>{escape(title)}</h1>
    <p class="description">{escape(description)}</p>

    <form method="post" action="{escape(action)}">
"""

    for field in fields:
        required_mark = '<span class="required">*</span>' if field.required else ''
        html += "        <div class=\"field\">\n"
        html += f"            <label for=\"{escape(field.name)}\">{escape(field.label)} {required_mark}</label>\n"

        if field.field_type == "textarea":
            html += (
                f"            <textarea name=\"{escape(field.name)}\" id=\"{escape(field.name)}\""
                f" placeholder=\"{escape(field.placeholder)}\">{escape(field.default)}</textarea>\n"
            )
        elif field.field_type == "select" and field.options:
            html += f"            <select name=\"{escape(field.name)}\" id=\"{escape(field.name)}\">\n"
            for option in field.options:
                selected = " selected" if option == field.default else ""
                html += (
                    f"                <option value=\"{escape(option)}\"{selected}>{escape(option)}</option>\n"
                )
            html += "            </select>\n"
        else:
            html += (
                f"            <input type=\"{escape(field.field_type)}\" name=\"{escape(field.name)}\""
                f" id=\"{escape(field.name)}\" value=\"{escape(field.default)}\""
                f" placeholder=\"{escape(field.placeholder)}\" />\n"
            )

        if field.help_text:
            html += f"            <div class=\"help\">{escape(field.help_text)}</div>\n"

        html += "        </div>\n"

    html += "        <button type=\"submit\">Submit</button>\n"
    html += "    </form>\n"

    if examples:
        html += "    <div class=\"examples\">\n"
        html += "        <h3>Examples</h3>\n"
        for example in examples:
            title_text = escape(example.get("title", "Example"))
            description_text = escape(example.get("description", ""))
            request_text = escape(example.get("request", ""))
            html += f"        <div class=\"example\">\n"
            html += f"            <strong>{title_text}</strong><br/>\n"
            if description_text:
                html += f"            <div>{description_text}</div>\n"
            if request_text:
                html += f"            <pre>{request_text}</pre>\n"
            html += "        </div>\n"
        html += "    </div>\n"

    if documentation_url:
        html += (
            f"    <div class=\"doc-link\">\n"
            f"        <a href=\"{escape(documentation_url)}\" target=\"_blank\">View API Documentation</a>\n"
            f"    </div>\n"
        )

    html += "</body>\n</html>"

    return {"output": html, "content_type": "text/html"}
