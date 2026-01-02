"""Tests for Azure Shared Key authentication implementation."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from server_utils.external_api import azure_signature


def test_sign_request_basic():
    """Test basic request signing."""
    method = "GET"
    url = "https://myaccount.blob.core.windows.net/mycontainer"
    headers = {}
    account_name = "myaccount"
    account_key = "SGVsbG8sIFdvcmxkIQ=="  # Base64 encoded test key
    
    # Mock datetime to get consistent signature
    fixed_time = datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    with patch("server_utils.external_api.azure_signature.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_time
        mock_datetime.strftime = datetime.strftime
        
        signed_headers = azure_signature.sign_request(
            method=method,
            url=url,
            headers=headers,
            account_name=account_name,
            account_key=account_key,
        )
    
    # Verify required headers are present
    assert "Authorization" in signed_headers
    assert "x-ms-date" in signed_headers
    assert "x-ms-version" in signed_headers
    
    # Verify Authorization header format
    auth_header = signed_headers["Authorization"]
    assert auth_header.startswith(f"SharedKey {account_name}:")
    assert len(auth_header.split(":")[1]) > 0  # Signature should be present


def test_sign_request_with_content():
    """Test signing with content length."""
    method = "PUT"
    url = "https://myaccount.blob.core.windows.net/mycontainer/myblob"
    headers = {"Content-Type": "text/plain"}
    account_name = "myaccount"
    account_key = "SGVsbG8sIFdvcmxkIQ=="
    content_length = 13
    
    signed_headers = azure_signature.sign_request(
        method=method,
        url=url,
        headers=headers,
        account_name=account_name,
        account_key=account_key,
        content_length=content_length,
    )
    
    assert "Authorization" in signed_headers
    assert "Content-Type" in signed_headers


def test_sign_request_with_custom_version():
    """Test signing with custom API version."""
    headers = {"x-ms-version": "2020-10-02"}
    
    signed_headers = azure_signature.sign_request(
        method="GET",
        url="https://myaccount.blob.core.windows.net/",
        headers=headers,
        account_name="myaccount",
        account_key="SGVsbG8sIFdvcmxkIQ==",
    )
    
    assert signed_headers["x-ms-version"] == "2020-10-02"


def test_sign_request_with_query_params():
    """Test signing with query parameters."""
    method = "GET"
    url = "https://myaccount.blob.core.windows.net/mycontainer?restype=container&comp=list"
    
    signed_headers = azure_signature.sign_request(
        method=method,
        url=url,
        headers={},
        account_name="myaccount",
        account_key="SGVsbG8sIFdvcmxkIQ==",
    )
    
    assert "Authorization" in signed_headers


def test_build_canonicalized_headers():
    """Test canonicalized headers creation."""
    headers = {
        "x-ms-date": "Sun, 15 Jan 2023 10:30:00 GMT",
        "x-ms-version": "2021-08-06",
        "Content-Type": "text/plain",
        "X-Ms-Meta-Name": "value",
    }
    
    result = azure_signature._build_canonicalized_headers(headers)
    
    # Only x-ms-* headers should be included, lowercase and sorted
    assert "x-ms-date:" in result
    assert "x-ms-meta-name:" in result
    assert "x-ms-version:" in result
    assert "content-type:" not in result


def test_build_canonicalized_headers_sorted():
    """Test that canonicalized headers are sorted."""
    headers = {
        "x-ms-zebra": "z",
        "x-ms-alpha": "a",
        "x-ms-middle": "m",
    }
    
    result = azure_signature._build_canonicalized_headers(headers)
    lines = result.split("\n")
    
    # Should be sorted alphabetically
    assert lines[0].startswith("x-ms-alpha:")
    assert lines[1].startswith("x-ms-middle:")
    assert lines[2].startswith("x-ms-zebra:")


def test_build_canonicalized_resource_simple():
    """Test canonicalized resource with simple path."""
    account_name = "myaccount"
    path = "/mycontainer/myblob"
    query = ""
    
    result = azure_signature._build_canonicalized_resource(account_name, path, query)
    
    assert result == "/myaccount/mycontainer/myblob"


def test_build_canonicalized_resource_with_query():
    """Test canonicalized resource with query parameters."""
    account_name = "myaccount"
    path = "/mycontainer"
    query = "restype=container&comp=list"
    
    result = azure_signature._build_canonicalized_resource(account_name, path, query)
    
    assert result.startswith("/myaccount/mycontainer")
    assert "\ncomp:list" in result
    assert "\nrestype:container" in result


def test_build_canonicalized_resource_query_sorted():
    """Test that query parameters are sorted in canonicalized resource."""
    account_name = "myaccount"
    path = "/container"
    query = "z=last&a=first&m=middle"
    
    result = azure_signature._build_canonicalized_resource(account_name, path, query)
    
    lines = result.split("\n")
    # First line is the path, rest are parameters
    assert len(lines) == 4
    assert lines[1].startswith("a:")
    assert lines[2].startswith("m:")
    assert lines[3].startswith("z:")


def test_sign_request_preserves_existing_headers():
    """Test that existing headers are preserved in signing."""
    headers = {
        "Content-Type": "application/octet-stream",
        "x-ms-blob-type": "BlockBlob",
        "X-Custom-Header": "custom-value",
    }
    
    signed_headers = azure_signature.sign_request(
        method="PUT",
        url="https://myaccount.blob.core.windows.net/container/blob",
        headers=headers,
        account_name="myaccount",
        account_key="SGVsbG8sIFdvcmxkIQ==",
        content_length=1024,
    )
    
    # Original headers should be preserved
    assert "Content-Type" in signed_headers
    assert "x-ms-blob-type" in signed_headers
    assert "X-Custom-Header" in signed_headers
    assert signed_headers["Content-Type"] == "application/octet-stream"
    assert signed_headers["x-ms-blob-type"] == "BlockBlob"


def test_sign_request_different_methods():
    """Test signing for different HTTP methods."""
    for method in ["GET", "PUT", "POST", "DELETE", "HEAD"]:
        signed_headers = azure_signature.sign_request(
            method=method,
            url="https://myaccount.blob.core.windows.net/container",
            headers={},
            account_name="myaccount",
            account_key="SGVsbG8sIFdvcmxkIQ==",
        )
        
        assert "Authorization" in signed_headers
        assert signed_headers["Authorization"].startswith("SharedKey myaccount:")
