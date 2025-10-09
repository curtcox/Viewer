# ruff: noqa: F821, F706
# This template executes inside the Viewer runtime where `request` and `context` are provided.
import requests

secrets = context.get('secrets') or {}
api_key = secrets.get("ANTHROPIC_API_KEY")
if not api_key:
    return {'output': 'Missing ANTHROPIC_API_KEY'}

form_data = request.get('form_data') or {}
message = form_data.get('message') or "Hello from Viewer!"

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

return {'output': data}
