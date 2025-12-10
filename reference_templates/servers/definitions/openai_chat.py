# ruff: noqa: F821, F706
"""Call the OpenAI chat completions API using automatic main() mapping."""

from typing import Any, Dict, Optional

import requests


def _get_secret(context: Optional[Dict[str, Any]], name: str) -> Optional[str]:
    if isinstance(context, dict):
        secrets = context.get("secrets")
        if isinstance(secrets, dict):
            return secrets.get(name)
    return None


def main(message: str = "Hello from Viewer!", *, OPENAI_API_KEY: str, context=None):
    api_key = OPENAI_API_KEY or _get_secret(context, "OPENAI_API_KEY")
    if not api_key:
        return {"output": "Missing OPENAI_API_KEY"}

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": message},
        ],
        "temperature": 0.7,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    return {"output": data}
