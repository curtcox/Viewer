# ruff: noqa: F821, F706
# This template executes inside the Viewer runtime where `context` is provided.
import requests

API_KEY = context.get('secrets', {}).get("OPENROUTER_API_KEY")
if not API_KEY:
    return {'output': 'Missing OPENROUTER_API_KEY'}

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
data = {
    "model": "nvidia/nemotron-nano-9b-v2:free",
    "messages": [
        {"role": "user", "content": "What is the meaning of life?"}
    ]
}

resp = requests.post(url, headers=headers, json=data, timeout=60)
resp.raise_for_status()

return {'output': resp.json()}
