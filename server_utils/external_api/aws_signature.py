"""AWS Signature Version 4 implementation.

Reference: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
"""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.parse import quote, urlparse, parse_qs


def sign_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    access_key: str,
    secret_key: str,
    region: str,
    service: str,
    payload: bytes = b"",
    session_token: Optional[str] = None,
) -> Dict[str, str]:
    """Sign an AWS request with Signature Version 4.

    Args:
        method: HTTP method (GET, POST, PUT, etc.)
        url: Full request URL
        headers: Request headers (will be modified with auth headers)
        access_key: AWS access key ID
        secret_key: AWS secret access key
        region: AWS region (e.g., "us-east-1")
        service: AWS service name (e.g., "s3")
        payload: Request body as bytes
        session_token: Optional AWS session token

    Returns:
        Dictionary with signed headers including Authorization header
    """
    # Parse URL
    parsed = urlparse(url)
    host = parsed.netloc
    canonical_uri = parsed.path or "/"
    
    # Get timestamp
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    
    # Add required headers
    request_headers = dict(headers)
    request_headers["Host"] = host
    request_headers["X-Amz-Date"] = amz_date
    
    if session_token:
        request_headers["X-Amz-Security-Token"] = session_token
    
    # Create canonical request
    canonical_headers, signed_headers_list = _create_canonical_headers(request_headers)
    payload_hash = hashlib.sha256(payload).hexdigest()
    canonical_query_string = _create_canonical_query_string(parsed.query)
    
    canonical_request = "\n".join([
        method.upper(),
        canonical_uri,
        canonical_query_string,
        canonical_headers,
        signed_headers_list,
        payload_hash,
    ])
    
    # Create string to sign
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    canonical_request_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
    
    string_to_sign = "\n".join([
        algorithm,
        amz_date,
        credential_scope,
        canonical_request_hash,
    ])
    
    # Calculate signature
    signing_key = _get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    
    # Create authorization header
    authorization_header = (
        f"{algorithm} "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers_list}, "
        f"Signature={signature}"
    )
    
    request_headers["Authorization"] = authorization_header
    
    return request_headers


def _create_canonical_headers(headers: Dict[str, str]) -> tuple[str, str]:
    """Create canonical headers string and signed headers list.
    
    Args:
        headers: Dictionary of request headers
        
    Returns:
        Tuple of (canonical_headers_string, signed_headers_list)
    """
    # Convert to lowercase and sort
    sorted_headers = sorted((k.lower(), v.strip()) for k, v in headers.items())
    
    # Build canonical headers string
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted_headers)
    
    # Build signed headers list
    signed_headers_list = ";".join(k for k, _ in sorted_headers)
    
    return canonical_headers, signed_headers_list


def _create_canonical_query_string(query_string: str) -> str:
    """Create canonical query string.
    
    Args:
        query_string: URL query string
        
    Returns:
        Canonical query string
    """
    if not query_string:
        return ""
    
    # Parse query parameters
    params = parse_qs(query_string, keep_blank_values=True)
    
    # Sort and encode
    sorted_params = []
    for key in sorted(params.keys()):
        for value in sorted(params[key]):
            encoded_key = quote(key, safe="")
            encoded_value = quote(value, safe="")
            sorted_params.append(f"{encoded_key}={encoded_value}")
    
    return "&".join(sorted_params)


def _get_signature_key(secret_key: str, date_stamp: str, region: str, service: str) -> bytes:
    """Derive the signing key for AWS Signature V4.
    
    Args:
        secret_key: AWS secret access key
        date_stamp: Date in YYYYMMDD format
        region: AWS region
        service: AWS service name
        
    Returns:
        Signing key as bytes
    """
    k_date = hmac.new(f"AWS4{secret_key}".encode(), date_stamp.encode(), hashlib.sha256).digest()
    k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
    return k_signing
