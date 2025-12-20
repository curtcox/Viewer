"""Integration tests for the workspace search page."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


_DEFAULT_CATEGORIES = (
    "aliases",
    "servers",
    "cids",
    "variables",
    "secrets",
)


def test_search_page_displays_filters_and_status(client):
    """The search page should render with all filters enabled and helpful copy."""

    response = client.get("/search")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "Workspace Search" in page
    assert "Start typing to search the workspace." in page
    assert 'id="search-query"' in page
    assert 'id="search-endpoint"' in page

    for category in _DEFAULT_CATEGORIES:
        assert f'id="filter-{category}"' in page
        assert f'data-search-category="{category}"' in page
        assert f'data-search-count="{category}"' in page

    assert "static/js/search.js" in page
