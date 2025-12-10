# ruff: noqa: F821, F706
"""Call the Anthropic Claude Messages API using automatic main() mapping."""

from typing import Any, Dict, Optional

import requests


def _get_secret(context: Optional[Dict[str, Any]], name: str) -> Optional[str]:
    if isinstance(context, dict):
        secrets = context.get("secrets")
        if isinstance(secrets, dict):
            return secrets.get(name)
    return None


def main(message: str = "Hello from Viewer!", api_key: Optional[str] = None, *, context=None):
    api_key = api_key or _get_secret(context, "ANTHROPIC_API_KEY")
    if not api_key:
        return {"output": "Missing ANTHROPIC_API_KEY"}

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 512,
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
