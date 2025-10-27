"""Property tests for serving CID content."""

from datetime import datetime, timezone
from types import SimpleNamespace

from flask import Flask
from hypothesis import given, strategies as st

from cid_utils import EXTENSION_TO_MIME, serve_cid_content

_app = Flask(__name__)


@given(content_bytes=st.binary())
def test_cid_page_returns_exact_content(content_bytes):
    """A /CID request returns exactly the stored content."""

    path = "/propertytestcid"
    created_at = datetime.now(timezone.utc)

    with _app.test_request_context(path):
        cid_content = SimpleNamespace(file_data=content_bytes, created_at=created_at)
        response = serve_cid_content(cid_content, path)

    assert response is not None
    assert response.get_data() == content_bytes


_extension_strategy = st.sampled_from(sorted(EXTENSION_TO_MIME.items()))


@given(extension_entry=_extension_strategy, content_bytes=st.binary())
def test_cid_page_mime_matches_extension(extension_entry, content_bytes):
    """When an extension is provided, the MIME type matches the extension."""

    extension, base_mime = extension_entry
    path = f"/propertytestcid.{extension}"
    created_at = datetime.now(timezone.utc)

    with _app.test_request_context(path):
        cid_content = SimpleNamespace(file_data=content_bytes, created_at=created_at)
        response = serve_cid_content(cid_content, path)

    assert response is not None

    expected_mime = "text/plain; charset=utf-8" if base_mime == "text/plain" else base_mime
    assert response.headers.get("Content-Type") == expected_mime
