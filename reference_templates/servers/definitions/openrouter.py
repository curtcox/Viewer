# ruff: noqa: F821, F706
"""Call the OpenRouter chat completions API using automatic main() mapping."""

from typing import Any, Dict, Optional

import requests


def _get_secret(context: Optional[Dict[str, Any]], name: str) -> Optional[str]:
    if isinstance(context, dict):
        secrets = context.get("secrets")
        if isinstance(secrets, dict):
            return secrets.get(name)
    return None


def main(message: str = "Hello from Viewer!", api_key: Optional[str] = None, *, context=None):
    api_key = api_key or _get_secret(context, "OPENROUTER_API_KEY")
    if not api_key:
        return {"output": "Missing OPENROUTER_API_KEY"}

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://viewer.app",
        "X-Title": "Viewer Demo",
    }
    payload = {
        "model": "openrouter/auto",
        "messages": [
            {"role": "user", "content": message},
        ],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    return {"output": response.json()}
