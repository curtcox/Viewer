# ruff: noqa: F821, F706
"""Call the Anthropic Claude Messages API using automatic main() mapping."""

import os
from typing import Optional

import requests


DEFAULT_MODEL = "claude-sonnet-4-20250514"


def main(
    message: str = "Hello from Viewer!",
    *,
    ANTHROPIC_API_KEY: str,
    model: Optional[str] = None,
    context=None,
):
    if not ANTHROPIC_API_KEY:
        return {"output": "Missing ANTHROPIC_API_KEY"}

    model_id = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model_id,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                ],
            }
        ],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    return {"output": data}
