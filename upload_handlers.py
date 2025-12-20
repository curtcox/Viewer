"""File upload processing handlers.

This module provides functions for processing different types of uploads:
- File uploads from forms
- Text content uploads
- URL-based content downloads
"""

from typing import Any, Tuple
from urllib.parse import urlparse

import requests

from mime_utils import get_extension_from_mime_type


# ============================================================================
# UPLOAD SIZE LIMITS
# ============================================================================

# Maximum upload size in bytes (100 MB)
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024

# Chunk size for streaming downloads
DOWNLOAD_CHUNK_SIZE_BYTES = 8192

# Request timeout for URL downloads (seconds)
URL_DOWNLOAD_TIMEOUT_SECONDS = 30


# ============================================================================
# USER AGENT FOR REQUESTS
# ============================================================================

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)


# ============================================================================
# FILE UPLOAD HANDLERS
# ============================================================================


def process_file_upload(form: Any) -> Tuple[bytes, str]:
    """Process file upload from form and return file content and filename.

    Args:
        form: Flask form object with file data

    Returns:
        Tuple of (file_content_bytes, filename)

    Example:
        >>> # Mock form with file data
        >>> content, name = process_file_upload(form)
        >>> isinstance(content, bytes)
        True
    """
    uploaded_file = form.file.data
    file_content = uploaded_file.read()
    filename = uploaded_file.filename or "upload"
    return file_content, filename


def process_text_upload(form: Any) -> bytes:
    """Process text upload from form and return file content.

    Args:
        form: Flask form object with text_content field

    Returns:
        Text content encoded as UTF-8 bytes

    Example:
        >>> # Mock form with text data
        >>> content = process_text_upload(form)
        >>> isinstance(content, bytes)
        True
    """
    text_content = form.text_content.data
    file_content = text_content.encode("utf-8")
    return file_content


def process_url_upload(form: Any) -> Tuple[bytes, str]:
    """Process URL upload by downloading content and return file content and MIME type.

    Downloads content from the provided URL, with size limits and streaming.

    Args:
        form: Flask form object with url field

    Returns:
        Tuple of (file_content_bytes, mime_type)

    Raises:
        ValueError: If download fails, file is too large, or URL is invalid

    Example:
        >>> # Mock form with URL
        >>> content, mime = process_url_upload(form)
        >>> isinstance(content, bytes)
        True
        >>> isinstance(mime, str)
        True
    """
    url = form.url.data.strip()

    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}

        response = requests.get(
            url, timeout=URL_DOWNLOAD_TIMEOUT_SECONDS, headers=headers, stream=True
        )
        response.raise_for_status()

        # Extract MIME type from response
        content_type = response.headers.get("content-type", "application/octet-stream")
        mime_type = content_type.split(";")[0].strip().lower()

        # Check content length if provided
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError(
                f"File too large (>{MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB)"
            )

        # Download content with streaming and size checking
        file_content = b""
        downloaded_size = 0

        for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES):
            if chunk:
                downloaded_size += len(chunk)
                if downloaded_size > MAX_UPLOAD_SIZE_BYTES:
                    raise ValueError(
                        f"File too large (>{MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB)"
                    )
                file_content += chunk

        # Generate filename from URL if needed
        parsed_url = urlparse(url)
        filename = parsed_url.path.split("/")[-1]

        if not filename or "." not in filename:
            extension = get_extension_from_mime_type(mime_type)
            if extension:
                filename = f"download.{extension}"
            else:
                filename = "download"

        return file_content, mime_type

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to download from URL: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error processing URL: {str(e)}") from e
