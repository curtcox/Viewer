# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
# This template executes inside the Viewer runtime where `request` and `context` are provided.
import requests

secrets = context.get('secrets') or {}
api_key = secrets.get("OPENROUTER_API_KEY")
if not api_key:
    return {'output': 'Missing OPENROUTER_API_KEY'}

form_data = request.get('form_data') or {}
message = form_data.get('message') or "Hello from Viewer!"

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

return {'output': response.json()}
