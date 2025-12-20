# ruff: noqa: F821, F706
# pylint: disable=undefined-variable,return-outside-function
import os
import mimetypes
from html import escape


def serve_directory(path):
    items = []
    try:
        entries = sorted(os.listdir(path))
        for entry in entries:
            full_path = os.path.join(path, entry)
            name = escape(entry)
            # Normalize path and ensure it starts with /file/
            normalized_path = full_path.replace('\\', '/')
            if normalized_path.startswith('./'):
                normalized_path = normalized_path[2:]
            url = escape("/file/" + normalized_path)
            link = f'<a href="{url}">{name}</a>'
            if os.path.isdir(full_path):
                items.append(f'<li>{link}/</li>')
            else:
                items.append(f'<li>{link}</li>')
    except PermissionError:
        return {'output': '<html><body><h1>403 Forbidden</h1></body></html>', 'status': 403}
    
    html = f'<html><body><h1>Directory listing: {escape(path)}</h1><ul>{"".join(items)}</ul></body></html>'
    return {'output': html}

request_path = request['path']
if request_path.startswith('/file/'):
    request_path = request_path[6:]
elif request_path.startswith('/'):
    request_path = request_path[1:]

file_path = os.path.join('.', request_path)

if not os.path.exists(file_path):
    out = {'output': f'<html><body><h1>404 Not Found</h1>{file_path}</body></html>', 'status': 404}
elif os.path.isdir(file_path):
    out = serve_directory(file_path)
else:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        out = {'output': content, 'content_type': mime_type}
    except PermissionError:
        out = {'output': '<html><body><h1>403 Forbidden</h1></body></html>', 'status': 403}
    except Exception:
        out = {'output': '<html><body><h1>500 Internal Server Error</h1></body></html>', 'status': 500}

return out