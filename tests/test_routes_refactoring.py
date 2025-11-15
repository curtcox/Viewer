"""Tests for refactored routes functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from routes.servers import enrich_invocation_with_links
from routes.uploads import _save_cid_content, _store_or_find_content


def test_enrich_invocation_with_links_adds_all_attributes():
    """Test that enrich_invocation_with_links adds all expected link attributes."""
    invocation = MagicMock()
    invocation.invocation_cid = 'test-invocation-cid'
    invocation.request_details_cid = 'test-request-cid'
    invocation.result_cid = 'test-result-cid'
    invocation.servers_cid = 'test-servers-cid'

    result = enrich_invocation_with_links(invocation)

    # Should return the same object
    assert result is invocation

    # Should have all link attributes
    assert hasattr(invocation, 'invocation_link')
    assert hasattr(invocation, 'invocation_label')
    assert hasattr(invocation, 'request_details_link')
    assert hasattr(invocation, 'request_details_label')
    assert hasattr(invocation, 'result_link')
    assert hasattr(invocation, 'result_label')
    assert hasattr(invocation, 'servers_cid_link')
    assert hasattr(invocation, 'servers_cid_label')


def test_enrich_invocation_with_links_handles_none_cids():
    """Test that enrich_invocation_with_links handles None CID values gracefully."""
    invocation = MagicMock()
    invocation.invocation_cid = None
    invocation.request_details_cid = None
    invocation.result_cid = None
    invocation.servers_cid = None

    result = enrich_invocation_with_links(invocation)

    # Should still add attributes even with None values
    assert result is invocation
    assert hasattr(invocation, 'invocation_link')
    assert hasattr(invocation, 'invocation_label')


@patch('routes.uploads._store_or_find_content')
def test_save_cid_content_delegates_to_store_or_find(mock_store):
    """Test that _save_cid_content properly delegates to _store_or_find_content."""
    mock_store.return_value = 'test-cid-value'
    text_content = "Hello, World!"

    result = _save_cid_content(text_content)

    # Should call _store_or_find_content with encoded bytes
    mock_store.assert_called_once()
    call_args = mock_store.call_args[0]
    assert call_args[0] == text_content.encode('utf-8')

    # Should return the CID value
    assert result == 'test-cid-value'


@patch('routes.uploads.create_cid_record')
@patch('routes.uploads.get_cid_by_path')
@patch('routes.uploads.flash')
def test_store_or_find_content_creates_new_content(mock_flash, mock_get_cid, mock_create):
    """Test that _store_or_find_content creates new content when it doesn't exist."""
    mock_get_cid.return_value = None
    file_content = b"Test content"

    _store_or_find_content(file_content)

    # Should create new record
    mock_create.assert_called_once()
    # Should flash success message
    assert mock_flash.call_count == 1
    flash_call = mock_flash.call_args[0]
    assert 'uploaded successfully' in str(flash_call[0]).lower()


@patch('routes.uploads.create_cid_record')
@patch('routes.uploads.get_cid_by_path')
@patch('routes.uploads.flash')
def test_store_or_find_content_finds_existing_content(mock_flash, mock_get_cid, mock_create):
    """Test that _store_or_find_content finds existing content."""
    mock_existing = MagicMock()
    mock_get_cid.return_value = mock_existing
    file_content = b"Test content"

    _store_or_find_content(file_content)

    # Should not create new record
    mock_create.assert_not_called()
    # Should flash warning message
    assert mock_flash.call_count == 1
    flash_call = mock_flash.call_args[0]
    assert 'already exists' in str(flash_call[0]).lower()
