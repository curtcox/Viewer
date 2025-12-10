# ruff: noqa: F821, F706
"""Call the Google Gemini API using automatic main() mapping."""

from typing import Any, Dict, Optional

import requests


def _get_secret(context: Optional[Dict[str, Any]], name: str) -> Optional[str]:
    if isinstance(context, dict):
        secrets = context.get("secrets")
        if isinstance(secrets, dict):
            return secrets.get(name)
    return None


def main(message: str = "Hello from Viewer!", api_key: Optional[str] = None, *, context=None):
    api_key = api_key or _get_secret(context, "GEMINI_API_KEY")
    if not api_key:
        return {"output": "Missing GEMINI_API_KEY"}

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": message},
                ],
            }
        ]
    }

    response = requests.post(url, params={"key": api_key}, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    return {"output": data}
