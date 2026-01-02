"""Azure Shared Key authentication implementation.

Reference: https://docs.microsoft.com/en-us/rest/api/storageservices/authorize-with-shared-key
"""

import base64
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict
from urllib.parse import urlparse, unquote


def sign_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    account_name: str,
    account_key: str,
    content_length: int = 0,
) -> Dict[str, str]:
    """Sign an Azure Blob Storage request with Shared Key authentication.

    Args:
        method: HTTP method (GET, POST, PUT, etc.)
        url: Full request URL
        headers: Request headers (will be modified with auth headers)
        account_name: Azure storage account name
        account_key: Azure storage account key
        content_length: Length of request body in bytes

    Returns:
        Dictionary with signed headers including Authorization header
    """
    # Parse URL
    parsed = urlparse(url)
    
    # Get timestamp
    now = datetime.now(timezone.utc)
    x_ms_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Add required headers
    request_headers = dict(headers)
    request_headers["x-ms-date"] = x_ms_date
    request_headers["x-ms-version"] = request_headers.get("x-ms-version", "2021-08-06")
    
    # Build canonicalized headers
    canonicalized_headers = _build_canonicalized_headers(request_headers)
    
    # Build canonicalized resource
    canonicalized_resource = _build_canonicalized_resource(account_name, parsed.path, parsed.query)
    
    # Build string to sign
    content_encoding = request_headers.get("Content-Encoding", "")
    content_language = request_headers.get("Content-Language", "")
    content_md5 = request_headers.get("Content-MD5", "")
    content_type = request_headers.get("Content-Type", "")
    date = request_headers.get("Date", "")
    if_modified_since = request_headers.get("If-Modified-Since", "")
    if_match = request_headers.get("If-Match", "")
    if_none_match = request_headers.get("If-None-Match", "")
    if_unmodified_since = request_headers.get("If-Unmodified-Since", "")
    range_header = request_headers.get("Range", "")
    
    string_to_sign = "\n".join([
        method.upper(),
        content_encoding,
        content_language,
        str(content_length) if content_length > 0 else "",
        content_md5,
        content_type,
        date,
        if_modified_since,
        if_match,
        if_none_match,
        if_unmodified_since,
        range_header,
        canonicalized_headers,
        canonicalized_resource,
    ])
    
    # Sign the string
    decoded_key = base64.b64decode(account_key)
    signature = base64.b64encode(
        hmac.new(decoded_key, string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")
    
    # Add authorization header
    request_headers["Authorization"] = f"SharedKey {account_name}:{signature}"
    
    return request_headers


def _build_canonicalized_headers(headers: Dict[str, str]) -> str:
    """Build the canonicalized headers string.
    
    Args:
        headers: Dictionary of request headers
        
    Returns:
        Canonicalized headers string
    """
    # Filter x-ms-* headers, convert to lowercase, and sort
    x_ms_headers = {
        k.lower(): v.strip()
        for k, v in headers.items()
        if k.lower().startswith("x-ms-")
    }
    
    sorted_headers = sorted(x_ms_headers.items())
    
    # Build canonicalized string
    return "\n".join(f"{k}:{v}" for k, v in sorted_headers)


def _build_canonicalized_resource(account_name: str, path: str, query: str) -> str:
    """Build the canonicalized resource string.
    
    Args:
        account_name: Azure storage account name
        path: URL path
        query: URL query string
        
    Returns:
        Canonicalized resource string
    """
    # Start with account and path
    canonicalized_resource = f"/{account_name}{path}"
    
    # Add query parameters if present
    if query:
        # Parse and sort query parameters
        params = {}
        for param in query.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                # Decode and lowercase the key
                key = unquote(key).lower()
                value = unquote(value)
                # Handle multiple values for same key
                if key in params:
                    if isinstance(params[key], list):
                        params[key].append(value)
                    else:
                        params[key] = [params[key], value]
                else:
                    params[key] = value
        
        # Sort and format parameters
        sorted_params = sorted(params.items())
        for key, value in sorted_params:
            if isinstance(value, list):
                # Multiple values should be comma-separated
                canonicalized_resource += f"\n{key}:{','.join(value)}"
            else:
                canonicalized_resource += f"\n{key}:{value}"
    
    return canonicalized_resource
