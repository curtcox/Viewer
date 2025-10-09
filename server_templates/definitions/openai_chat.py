# ruff: noqa: F821, F706
# This template executes inside the Viewer runtime where `request` and `context` are provided.
import requests

secrets = context.get('secrets') or {}
api_key = secrets.get("OPENAI_API_KEY")
if not api_key:
    return {'output': 'Missing OPENAI_API_KEY'}

form_data = request.get('form_data') or {}
message = form_data.get('message') or "Hello from Viewer!"

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

return {'output': data}
