# ruff: noqa: F821, F706
"""Call the OpenRouter chat completions API using automatic main() mapping."""

import requests


def main(message: str = "Hello from Viewer!", *, OPENROUTER_API_KEY: str, context=None):
    if not OPENROUTER_API_KEY:
        return {"output": "Missing OPENROUTER_API_KEY"}

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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
