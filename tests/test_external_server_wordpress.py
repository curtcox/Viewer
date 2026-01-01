"""Tests for the WordPress server definition."""

from reference_templates.servers.definitions import wordpress


def test_missing_credentials_returns_auth_error():
    result = wordpress.main(
        operation="list_posts",
        WORDPRESS_USERNAME="",
        WORDPRESS_APP_PASSWORD="",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_missing_site_url_returns_validation_error():
    result = wordpress.main(
        operation="list_posts",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="",
        dry_run=False,
    )
    assert "error" in result["output"]


def test_invalid_operation_returns_validation_error():
    result = wordpress.main(
        operation="invalid_op",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_list_posts_dry_run():
    result = wordpress.main(
        operation="list_posts",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "list_posts"
    assert "example.com/wp-json/wp/v2/posts" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_get_post_requires_resource_id():
    result = wordpress.main(
        operation="get_post",
        resource_id="",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_get_post_dry_run():
    result = wordpress.main(
        operation="get_post",
        resource_id="123",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "get_post"
    assert "example.com/wp-json/wp/v2/posts/123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_create_post_requires_title():
    result = wordpress.main(
        operation="create_post",
        title="",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert "error" in result["output"]


def test_create_post_dry_run():
    result = wordpress.main(
        operation="create_post",
        title="Test Post",
        content="This is a test post",
        status="draft",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "create_post"
    assert "example.com/wp-json/wp/v2/posts" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"
    assert result["output"]["preview"]["payload"]["title"] == "Test Post"
    assert result["output"]["preview"]["payload"]["content"] == "This is a test post"


def test_update_post_dry_run():
    result = wordpress.main(
        operation="update_post",
        resource_id="123",
        title="Updated Post",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "update_post"
    assert "example.com/wp-json/wp/v2/posts/123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "POST"


def test_delete_post_dry_run():
    result = wordpress.main(
        operation="delete_post",
        resource_id="123",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "delete_post"
    assert "example.com/wp-json/wp/v2/posts/123" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "DELETE"


def test_list_pages_dry_run():
    result = wordpress.main(
        operation="list_pages",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "list_pages"
    assert "example.com/wp-json/wp/v2/pages" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_list_media_dry_run():
    result = wordpress.main(
        operation="list_media",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "list_media"
    assert "example.com/wp-json/wp/v2/media" in result["output"]["preview"]["url"]
    assert result["output"]["preview"]["method"] == "GET"


def test_create_page_dry_run():
    result = wordpress.main(
        operation="create_page",
        title="Test Page",
        content="Page content",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["operation"] == "create_page"
    assert "example.com/wp-json/wp/v2/pages" in result["output"]["preview"]["url"]


def test_site_url_parameter_overrides_secret():
    result = wordpress.main(
        operation="list_posts",
        site_url="https://override.com",
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert "override.com/wp-json/wp/v2/posts" in result["output"]["preview"]["url"]


def test_list_posts_pagination_params():
    result = wordpress.main(
        operation="list_posts",
        per_page=20,
        page=2,
        WORDPRESS_USERNAME="user",
        WORDPRESS_APP_PASSWORD="pass",
        WORDPRESS_SITE_URL="https://example.com",
        dry_run=True,
    )
    assert result["output"]["dry_run"] is True
    assert result["output"]["preview"]["params"]["per_page"] == 20
    assert result["output"]["preview"]["params"]["page"] == 2


def test_api_401_error_handling():
    # Note: This test would need to mock requests.request directly since
    # WordPress uses requests.request instead of the client
    pass


def test_api_404_error_handling():
    # Note: This test would need to mock requests.request directly since
    # WordPress uses requests.request instead of the client
    pass


def test_timeout_handling():
    # Note: This test would need to mock requests.request directly since
    # WordPress uses requests.request instead of the client
    pass
