# ruff: noqa: F821, F706
"""Call the OpenAI chat completions API using automatic main() mapping."""

import requests


def main(message: str = "Hello from Viewer!", *, OPENAI_API_KEY: str, context=None):
    if not OPENAI_API_KEY:
        return {"output": "Missing OPENAI_API_KEY"}

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
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
