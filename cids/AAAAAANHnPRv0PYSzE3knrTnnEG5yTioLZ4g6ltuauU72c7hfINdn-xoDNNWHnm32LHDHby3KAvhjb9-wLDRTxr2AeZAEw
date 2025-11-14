# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
# This template executes inside the Viewer runtime where `request` and `context` are provided.
import requests

secrets = context.get('secrets') or {}
api_key = secrets.get("GEMINI_API_KEY")
if not api_key:
    return {'output': 'Missing GEMINI_API_KEY'}

form_data = request.get('form_data') or {}
message = form_data.get('message') or "Hello from Viewer!"

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

return {'output': data}
