# ruff: noqa: F821, F706
"""AI stub server template that mimics the legacy in-browser behaviour."""

import json
from typing import Any, Dict, Optional


def _summarise_context(context: Any) -> Optional[str]:
    """Return a short summary of context keys when possible."""

    if not isinstance(context, dict):
        return None

    keys = [str(key) for key in context.keys()]
    if not keys:
        return None

    return "Context keys: " + ", ".join(keys)


def _summarise_form(form_summary: Any) -> Optional[str]:
    """Return a summary of captured form field names."""

    if not isinstance(form_summary, dict):
        return None

    keys = [str(key) for key in form_summary.keys()]
    if not keys:
        return None

    return "Form fields captured: " + ", ".join(keys)


def _build_stub_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the same output produced by the previous JavaScript stub."""

    request_text = payload.get("request_text") or ""
    original_text = payload.get("original_text") or ""
    target_label = payload.get("target_label") or "the text"
    context_data = payload.get("context_data")
    form_summary = payload.get("form_summary")

    separator = ""
    if original_text and request_text and not original_text.endswith("\n"):
        separator = "\n"

    updated_text = original_text + separator + request_text
    message = f"OK I changed {target_label} by {request_text}"

    context_summary = _summarise_context(context_data)
    form_summary_text = _summarise_form(form_summary)
    if form_summary_text:
        context_summary = (
            f"{context_summary}\n{form_summary_text}"
            if context_summary
            else form_summary_text
        )

    return {
        "updated_text": updated_text,
        "message": message,
        "context_summary": context_summary or "",
    }


def main(
    request_text=None,
    original_text=None,
    target_label=None,
    context_data=None,
    form_summary=None,
):
    """Entry point executed by the Viewer runtime."""

    payload = {
        "request_text": request_text,
        "original_text": original_text,
        "target_label": target_label,
        "context_data": context_data,
        "form_summary": form_summary,
    }
    result = _build_stub_response(payload)

    return {
        "output": json.dumps(result),
        "content_type": "application/json",
    }
