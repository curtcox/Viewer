# ruff: noqa: F821, F706
"""Interact with WordPress REST API to manage posts, pages, and media."""

from __future__ import annotations

from typing import Any, Dict, Optional

from server_utils.external_api import (
    ExternalApiClient,
    OperationDefinition,
    RequiredField,
    error_output,
    execute_json_request,
    validate_and_build_payload,
    validation_error,
)


_DEFAULT_CLIENT = ExternalApiClient()

_OPERATIONS = {
    "list_posts": OperationDefinition(),
    "get_post": OperationDefinition(required=(RequiredField("resource_id"),)),
    "create_post": OperationDefinition(
        required=(RequiredField("title"),),
        payload_builder=lambda title, content, status, author, **_: _build_post_payload(
            title=title,
            content=content,
            status=status,
            author=author,
        ),
    ),
    "update_post": OperationDefinition(
        required=(RequiredField("resource_id"),),
        payload_builder=lambda title, content, status, author, **_: _build_post_payload(
            title=title,
            content=content,
            status=status,
            author=author,
        ),
    ),
    "delete_post": OperationDefinition(required=(RequiredField("resource_id"),)),
    "list_pages": OperationDefinition(),
    "get_page": OperationDefinition(required=(RequiredField("resource_id"),)),
    "create_page": OperationDefinition(
        required=(RequiredField("title"),),
        payload_builder=lambda title, content, status, author, **_: _build_post_payload(
            title=title,
            content=content,
            status=status,
            author=author,
        ),
    ),
    "update_page": OperationDefinition(
        required=(RequiredField("resource_id"),),
        payload_builder=lambda title, content, status, author, **_: _build_post_payload(
            title=title,
            content=content,
            status=status,
            author=author,
        ),
    ),
    "delete_page": OperationDefinition(required=(RequiredField("resource_id"),)),
    "list_media": OperationDefinition(),
    "get_media": OperationDefinition(required=(RequiredField("resource_id"),)),
}

_METHODS = {
    "create_post": "POST",
    "update_post": "POST",
    "delete_post": "DELETE",
    "create_page": "POST",
    "update_page": "POST",
    "delete_page": "DELETE",
}

_ENDPOINTS = {
    "list_posts": "posts",
    "get_post": "posts",
    "create_post": "posts",
    "update_post": "posts",
    "delete_post": "posts",
    "list_pages": "pages",
    "get_page": "pages",
    "create_page": "pages",
    "update_page": "pages",
    "delete_page": "pages",
    "list_media": "media",
    "get_media": "media",
}


def _build_post_payload(
    *,
    title: str,
    content: str,
    status: str,
    author: Optional[int],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if title:
        payload["title"] = title
    if content:
        payload["content"] = content
    if status:
        payload["status"] = status
    if author:
        payload["author"] = author
    return payload


def _build_url(
    base_url: str,
    *,
    operation: str,
    resource_id: str,
) -> str:
    endpoint = _ENDPOINTS[operation]
    if operation in {"get_post", "update_post", "delete_post", "get_page", "update_page", "delete_page", "get_media"}:
        return f"{base_url}/{endpoint}/{resource_id}"
    return f"{base_url}/{endpoint}"


def _build_params(operation: str, *, per_page: int, page: int) -> Optional[Dict[str, Any]]:
    if operation in {"list_posts", "list_pages", "list_media"}:
        return {"per_page": per_page, "page": page}
    return None


def _build_preview(
    *,
    operation: str,
    url: str,
    method: str,
    payload: Optional[Dict[str, Any]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "operation": operation,
        "url": url,
        "method": method,
        "auth": "Application Password",
    }
    if params:
        preview["params"] = params
    if payload:
        preview["payload"] = payload
    return preview


def _wordpress_error_message(response: object, data: object) -> str:
    status_code = getattr(response, "status_code", None)
    if status_code == 401:
        return (
            "Invalid WordPress credentials. Check your username and Application Password"
        )
    if status_code == 403:
        return (
            "Insufficient permissions for this operation. Check your user role has permission for this action"
        )
    if status_code == 404:
        return "Resource not found"
    if isinstance(data, dict):
        return data.get("message") or data.get("error") or "WordPress API error"
    return "WordPress API error"


def main(
    *,
    operation: str = "list_posts",
    site_url: str = "",
    resource_id: str = "",
    title: str = "",
    content: str = "",
    status: str = "draft",
    author: Optional[int] = None,
    per_page: int = 10,
    page: int = 1,
    WORDPRESS_USERNAME: str = "",
    WORDPRESS_APP_PASSWORD: str = "",
    WORDPRESS_SITE_URL: str = "",
    dry_run: bool = True,
    timeout: int = 60,
    client: Optional[ExternalApiClient] = None,
    context=None,
) -> Dict[str, Any]:
    """List and manage posts, pages, and media in WordPress.

    Operations:
    - list_posts: List all posts (supports pagination with page and per_page)
    - get_post: Get post details (requires resource_id)
    - create_post: Create a new post (requires title and content)
    - update_post: Update a post (requires resource_id, title, and/or content)
    - delete_post: Delete a post (requires resource_id)
    - list_pages: List all pages (supports pagination)
    - get_page: Get page details (requires resource_id)
    - create_page: Create a new page (requires title and content)
    - update_page: Update a page (requires resource_id, title, and/or content)
    - delete_page: Delete a page (requires resource_id)
    - list_media: List all media items (supports pagination)
    - get_media: Get media details (requires resource_id)

    Args:
        operation: The operation to perform
        site_url: WordPress site URL (falls back to WORDPRESS_SITE_URL)
        resource_id: Post/Page/Media ID for get/update/delete operations
        title: Title for create/update operations
        content: Content for create/update operations
        status: Post status (draft, publish, private, etc.)
        author: Author ID for create/update operations
        per_page: Number of items per page for list operations
        page: Page number for list operations
        WORDPRESS_USERNAME: WordPress username
        WORDPRESS_APP_PASSWORD: Application Password from WordPress profile
        WORDPRESS_SITE_URL: WordPress site URL (e.g., https://example.com)
        dry_run: If True, return preview without making actual API call
        timeout: Request timeout in seconds
        client: Optional ExternalApiClient for testing
        context: Request context
    """

    effective_site_url = site_url or WORDPRESS_SITE_URL

    if operation not in _OPERATIONS:
        return validation_error(
            f"Unsupported operation: {operation}. Must be one of {', '.join(sorted(_OPERATIONS))}",
            field="operation",
        )

    if not effective_site_url:
        return validation_error(
            "Missing required site_url or WORDPRESS_SITE_URL", field="site_url"
        )

    if not WORDPRESS_USERNAME or not WORDPRESS_APP_PASSWORD:
        return error_output(
            "Missing WORDPRESS_USERNAME or WORDPRESS_APP_PASSWORD. Create an Application Password in your WordPress profile settings",
            status_code=401,
        )

    result = validate_and_build_payload(
        operation,
        _OPERATIONS,
        resource_id=resource_id,
        title=title,
        content=content,
        status=status,
        author=author,
    )
    if isinstance(result, tuple):
        return validation_error(result[0], field=result[1])

    base_url = f"{effective_site_url.rstrip('/')}/wp-json/wp/v2"
    url = _build_url(base_url, operation=operation, resource_id=resource_id)
    method = _METHODS.get(operation, "GET")
    payload = result
    params = _build_params(operation, per_page=per_page, page=page)

    if dry_run:
        preview = _build_preview(
            operation=operation,
            url=url,
            method=method,
            payload=payload,
            params=params,
        )
        return {"output": {"dry_run": True, "preview": preview}}

    api_client = client or _DEFAULT_CLIENT
    headers = {
        "Content-Type": "application/json",
    }

    return execute_json_request(
        api_client,
        method,
        url,
        headers=headers,
        auth=(WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD),
        params=params,
        json=payload,
        timeout=timeout,
        error_parser=_wordpress_error_message,
        request_error_message="WordPress API request failed",
    )
