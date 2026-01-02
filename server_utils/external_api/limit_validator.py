"""Validation utilities for pagination and limit parameters.

This module provides validation for limit/pagination parameters across external
API servers. Each service has its own maximum allowed limit based on the
external API's documented constraints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .error_response import validation_error


# Service-specific maximum limits based on API documentation
# These values are derived from official API documentation and represent
# the maximum number of results that can be requested in a single API call.

# Cloud Storage Services
AWS_S3_MAX_KEYS = 1000  # AWS S3 API maximum keys per list operation
GCS_MAX_RESULTS = 1000  # Google Cloud Storage maximum results per page
AZURE_BLOB_MAX_RESULTS = 5000  # Azure Blob Storage maximum results per page
DROPBOX_MAX_RESULTS = 2000  # Dropbox API maximum files per list
BOX_MAX_LIMIT = 1000  # Box API maximum items per page

# Version Control & Project Management
GITHUB_MAX_PER_PAGE = 100  # GitHub API maximum items per page
GITLAB_MAX_PER_PAGE = 100  # GitLab API maximum items per page
ASANA_MAX_LIMIT = 100  # Asana API maximum tasks per page
TRELLO_MAX_LIMIT = 1000  # Trello API maximum cards per list

# Communication & Collaboration
SLACK_MAX_LIMIT = 1000  # Slack API maximum messages per request
DISCORD_MAX_LIMIT = 100  # Discord API maximum messages per request
ZOOM_MAX_PAGE_SIZE = 300  # Zoom API maximum participants per page
TELEGRAM_MAX_LIMIT = 100  # Telegram API maximum updates per request
TWILIO_MAX_PAGE_SIZE = 1000  # Twilio API maximum records per page

# CRM & Sales
SALESFORCE_MAX_LIMIT = 2000  # Salesforce SOQL query maximum rows
HUBSPOT_MAX_LIMIT = 100  # HubSpot API maximum results per page
PIPEDRIVE_MAX_LIMIT = 500  # Pipedrive API maximum items per page
ZOHO_CRM_MAX_LIMIT = 200  # Zoho CRM API maximum records per page
CLOSE_CRM_MAX_LIMIT = 100  # Close CRM API maximum results per page

# E-commerce & Payments
SHOPIFY_MAX_LIMIT = 250  # Shopify API maximum products per page
WOOCOMMERCE_MAX_PER_PAGE = 100  # WooCommerce API maximum items per page
STRIPE_MAX_LIMIT = 100  # Stripe API maximum objects per list
ETSY_MAX_LIMIT = 100  # Etsy API maximum listings per page
EBAY_MAX_LIMIT = 200  # eBay API maximum items per search
SQUARESPACE_MAX_LIMIT = 100  # Squarespace Commerce API maximum items

# Email & Marketing
GMAIL_MAX_RESULTS = 500  # Gmail API maximum messages per query
MAILCHIMP_MAX_COUNT = 1000  # Mailchimp API maximum members per page
SENDGRID_MAX_LIMIT = 500  # SendGrid API maximum contacts per page

# Document & Forms
GOOGLE_DRIVE_MAX_RESULTS = 1000  # Google Drive API maximum files per page
GOOGLE_CALENDAR_MAX_RESULTS = 2500  # Google Calendar API maximum events per page
GOOGLE_CONTACTS_MAX_RESULTS = 1000  # Google Contacts API maximum contacts per page
TYPEFORM_MAX_PAGE_SIZE = 1000  # Typeform API maximum responses per page
JOTFORM_MAX_LIMIT = 1000  # JotForm API maximum submissions per page
YOUTUBE_MAX_RESULTS = 50  # YouTube Data API maximum results per page

# Databases
MONGODB_MAX_LIMIT = 10000  # Practical limit for MongoDB queries
BIGQUERY_MAX_RESULTS = 10000  # BigQuery maximum rows per page

# Social & Ads
META_ADS_MAX_LIMIT = 100  # Meta (Facebook) Ads API maximum per page
LINKEDIN_ADS_MAX_COUNT = 100  # LinkedIn Ads API maximum per page

# Design & Collaboration
MIRO_MAX_LIMIT = 50  # Miro API maximum items per page
FIGMA_MAX_LIMIT = 100  # Figma API maximum comments per page
CODA_MAX_LIMIT = 500  # Coda API maximum rows per page

# Website Builders
WIX_MAX_PAGE_SIZE = 100  # Wix API maximum items per page
WORDPRESS_MAX_PER_PAGE = 100  # WordPress REST API maximum posts per page
WEBFLOW_MAX_LIMIT = 100  # Webflow API maximum items per page

# Default fallback for services without specific limits
DEFAULT_MAX_LIMIT = 1000

# Mapping of common parameter names to their semantic meaning
LIMIT_PARAM_ALIASES = {
    "limit",
    "max_keys",
    "max_results",
    "per_page",
    "page_size",
    "max_count",
    "count",
}


def validate_limit(
    limit: int,
    max_allowed: int,
    field_name: str = "limit",
    min_value: int = 1,
) -> Optional[Dict[str, Any]]:
    """Validate that a limit/pagination parameter is within acceptable bounds.

    This function ensures that pagination limits are:
    1. Positive (>= min_value, typically 1)
    2. Not exceeding the service's documented maximum

    Args:
        limit: The limit value to validate
        max_allowed: Maximum limit allowed by the external API
        field_name: Name of the parameter being validated (for error messages)
        min_value: Minimum acceptable value (default: 1)

    Returns:
        None if validation passes, otherwise a validation error dict

    Examples:
        >>> # GitHub API with max 100 per page
        >>> error = validate_limit(50, GITHUB_MAX_PER_PAGE, "per_page")
        >>> error is None
        True

        >>> # Exceeds GitHub's limit
        >>> error = validate_limit(200, GITHUB_MAX_PER_PAGE, "per_page")
        >>> error["output"]["error"]["message"]
        'per_page exceeds maximum allowed value of 100'

        >>> # Negative limit
        >>> error = validate_limit(-5, GITHUB_MAX_PER_PAGE, "per_page")
        >>> error["output"]["error"]["message"]
        'per_page must be at least 1'

    Rationale for enforcement:
        - Prevents API errors from exceeding service limits
        - Provides early feedback to users about constraints
        - Documented in preview/dry-run responses for transparency
        - Based on official API documentation for each service
    """
    if limit < min_value:
        return validation_error(
            f"{field_name} must be at least {min_value}",
            field=field_name,
            details={
                "provided": limit,
                "minimum": min_value,
                "maximum": max_allowed,
                "rationale": f"Service requires {field_name} >= {min_value}",
            },
        )

    if limit > max_allowed:
        return validation_error(
            f"{field_name} exceeds maximum allowed value of {max_allowed}",
            field=field_name,
            details={
                "provided": limit,
                "maximum": max_allowed,
                "minimum": min_value,
                "rationale": f"External API enforces {field_name} <= {max_allowed}",
            },
        )

    return None


def validate_pagination_params(
    limit: Optional[int] = None,
    max_allowed: int = DEFAULT_MAX_LIMIT,
    offset: Optional[int] = None,
    page: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Validate common pagination parameters together.

    Args:
        limit: Number of items to return (if provided)
        max_allowed: Maximum limit for this service
        offset: Starting offset (if provided)
        page: Page number (if provided)

    Returns:
        None if all validations pass, otherwise the first validation error

    Examples:
        >>> # Valid pagination
        >>> error = validate_pagination_params(limit=50, offset=0, page=1)
        >>> error is None
        True

        >>> # Invalid limit
        >>> error = validate_pagination_params(limit=5000, max_allowed=100)
        >>> "exceeds maximum" in error["output"]["error"]["message"]
        True
    """
    if limit is not None:
        if error := validate_limit(limit, max_allowed, "limit"):
            return error

    if offset is not None and offset < 0:
        return validation_error(
            "offset must be non-negative",
            field="offset",
            details={"provided": offset, "minimum": 0},
        )

    if page is not None and page < 1:
        return validation_error(
            "page must be at least 1",
            field="page",
            details={"provided": page, "minimum": 1},
        )

    return None


def get_limit_info(limit: int, max_allowed: int, field_name: str = "limit") -> Dict[str, Any]:
    """Get information about a limit value for inclusion in previews/docs.

    This provides transparency about limit constraints in dry-run responses.

    Args:
        limit: The limit value being used
        max_allowed: Maximum allowed by the API
        field_name: Name of the limit parameter

    Returns:
        Dictionary with limit information for documentation

    Example:
        >>> info = get_limit_info(50, 100, "per_page")
        >>> info["current"]
        50
        >>> info["maximum"]
        100
    """
    return {
        "parameter": field_name,
        "current": limit,
        "maximum": max_allowed,
        "status": "valid" if limit <= max_allowed else "exceeds_maximum",
        "constraint_source": "external_api_documentation",
    }
