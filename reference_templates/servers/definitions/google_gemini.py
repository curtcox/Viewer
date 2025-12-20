# ruff: noqa: F821, F706
"""Call the Google Gemini API using automatic main() mapping."""

import requests


def main(message: str = "Hello from Viewer!", *, GEMINI_API_KEY: str, context=None):
    if not GEMINI_API_KEY:
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

    response = requests.post(
        url, params={"key": GEMINI_API_KEY}, json=payload, timeout=60
    )
    response.raise_for_status()

    data = response.json()

    return {"output": data}
