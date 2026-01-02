"""Tests for AWS Signature Version 4 implementation."""

from datetime import datetime, timezone
from unittest.mock import patch

from server_utils.external_api import aws_signature


def test_sign_request_basic():
    """Test basic request signing."""
    # Test data
    method = "GET"
    url = "https://s3.us-east-1.amazonaws.com/"
    headers = {}
    access_key = "AKIAIOSFODNN7EXAMPLE"
    secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    region = "us-east-1"
    service = "s3"
    
    # Mock datetime to get consistent signature
    fixed_time = datetime(2013, 5, 24, 0, 0, 0, tzinfo=timezone.utc)
    with patch("server_utils.external_api.aws_signature.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        mock_datetime.strftime = datetime.strftime
        
        signed_headers = aws_signature.sign_request(
            method=method,
            url=url,
            headers=headers,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            service=service,
        )
    
    # Verify required headers are present
    assert "Authorization" in signed_headers
    assert "Host" in signed_headers
    assert "X-Amz-Date" in signed_headers
    
    # Verify Authorization header format
    auth_header = signed_headers["Authorization"]
    assert auth_header.startswith("AWS4-HMAC-SHA256")
    assert f"Credential={access_key}" in auth_header
    assert "SignedHeaders=" in auth_header
    assert "Signature=" in auth_header


def test_sign_request_with_payload():
    """Test signing with a request body."""
    method = "PUT"
    url = "https://mybucket.s3.us-west-2.amazonaws.com/mykey"
    headers = {"Content-Type": "text/plain"}
    payload = b"Hello, World!"
    
    signed_headers = aws_signature.sign_request(
        method=method,
        url=url,
        headers=headers,
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-west-2",
        service="s3",
        payload=payload,
    )
    
    assert "Authorization" in signed_headers
    assert "Content-Type" in signed_headers
    assert signed_headers["Content-Type"] == "text/plain"


def test_sign_request_with_query_params():
    """Test signing with query parameters."""
    method = "GET"
    url = "https://mybucket.s3.us-east-1.amazonaws.com/?prefix=test&max-keys=10"
    
    signed_headers = aws_signature.sign_request(
        method=method,
        url=url,
        headers={},
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        service="s3",
    )
    
    assert "Authorization" in signed_headers


def test_sign_request_with_session_token():
    """Test signing with a session token."""
    signed_headers = aws_signature.sign_request(
        method="GET",
        url="https://s3.us-east-1.amazonaws.com/",
        headers={},
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        service="s3",
        session_token="FQoGZXIvYXdzEBEaDJKLMNOPQRSTUVWXYZ",
    )
    
    assert "X-Amz-Security-Token" in signed_headers
    assert signed_headers["X-Amz-Security-Token"] == "FQoGZXIvYXdzEBEaDJKLMNOPQRSTUVWXYZ"


def test_create_canonical_headers():
    """Test canonical headers creation."""
    headers = {
        "Host": "s3.amazonaws.com",
        "Content-Type": "text/plain",
        "X-Amz-Date": "20130524T000000Z",
    }
    
    canonical_headers, signed_headers_list = aws_signature._create_canonical_headers(headers)
    
    # Headers should be lowercase and sorted
    assert "content-type:text/plain\n" in canonical_headers
    assert "host:s3.amazonaws.com\n" in canonical_headers
    assert "x-amz-date:20130524T000000Z\n" in canonical_headers
    
    # Signed headers list should be sorted
    assert signed_headers_list == "content-type;host;x-amz-date"


def test_create_canonical_query_string_empty():
    """Test canonical query string with no parameters."""
    result = aws_signature._create_canonical_query_string("")
    assert result == ""


def test_create_canonical_query_string_sorted():
    """Test canonical query string sorting."""
    query_string = "z=last&a=first&m=middle"
    result = aws_signature._create_canonical_query_string(query_string)
    
    # Parameters should be sorted
    assert result.startswith("a=")
    assert "m=" in result
    assert result.endswith("last")


def test_get_signature_key():
    """Test signature key derivation."""
    secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    date_stamp = "20130524"
    region = "us-east-1"
    service = "s3"
    
    signing_key = aws_signature._get_signature_key(secret_key, date_stamp, region, service)
    
    # Should return bytes
    assert isinstance(signing_key, bytes)
    assert len(signing_key) == 32  # SHA256 output is 32 bytes


def test_sign_request_preserves_existing_headers():
    """Test that existing headers are preserved in signing."""
    headers = {
        "Content-Type": "application/json",
        "X-Custom-Header": "custom-value",
    }
    
    signed_headers = aws_signature.sign_request(
        method="POST",
        url="https://s3.us-east-1.amazonaws.com/",
        headers=headers,
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        service="s3",
        payload=b'{"key":"value"}',
    )
    
    # Original headers should be preserved
    assert "Content-Type" in signed_headers
    assert "X-Custom-Header" in signed_headers
    assert signed_headers["Content-Type"] == "application/json"
    assert signed_headers["X-Custom-Header"] == "custom-value"


def test_sign_request_different_services():
    """Test signing for different AWS services."""
    for service in ["s3", "dynamodb", "ec2", "lambda"]:
        signed_headers = aws_signature.sign_request(
            method="GET",
            url=f"https://{service}.us-east-1.amazonaws.com/",
            headers={},
            access_key="AKIAIOSFODNN7EXAMPLE",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            service=service,
        )
        
        assert "Authorization" in signed_headers
        # Credential scope should include the service
        assert f"/{service}/aws4_request" in signed_headers["Authorization"]
