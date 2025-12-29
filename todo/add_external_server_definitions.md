# Add External Server Definitions

## Overview

This document outlines the plan for adding server definitions for 100+ external services to the Viewer application. These server definitions will be added to both the default and read-only boot images, enabling users to integrate with popular third-party APIs.

Each external service requires:
1. A Python definition file in `reference_templates/servers/definitions/`
2. A JSON template file in `reference_templates/servers/templates/`
3. An entry in both `default.boot.source.json` and `readonly.boot.source.json`
4. Unit tests, integration tests, and optionally gauge specs

---

## Service Categories and Inventory

### Category 1: Productivity & Workspace (Google Suite)
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Google Sheets | `google_sheets` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/sheets/api |
| Gmail | `gmail` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/gmail/api |
| Google Drive | `google_drive` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/drive/api |
| Google Calendar | `google_calendar` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/calendar/api |
| Google Forms | `google_forms` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/forms/api |
| Google Contacts | `google_contacts` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/people/api |
| Google Docs | `google_docs` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/docs/api |
| Google Ads | `google_ads` | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID` | https://developers.google.com/google-ads/api |
| Google Analytics 4 | `google_analytics` | `GOOGLE_API_KEY` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://developers.google.com/analytics/devguides/reporting |

### Category 2: Productivity & Workspace (Microsoft 365)
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Microsoft 365 Outlook | `microsoft_outlook` | `MICROSOFT_ACCESS_TOKEN` or `MICROSOFT_CLIENT_ID`/`MICROSOFT_CLIENT_SECRET` | https://docs.microsoft.com/en-us/graph/api/resources/mail-api-overview |
| Microsoft Teams | `microsoft_teams` | `MICROSOFT_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/graph/api/resources/teams-api-overview |
| OneDrive | `onedrive` | `MICROSOFT_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/graph/api/resources/onedrive |
| Microsoft Excel | `microsoft_excel` | `MICROSOFT_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/graph/api/resources/excel |
| Microsoft Dynamics 365 | `dynamics365` | `DYNAMICS365_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/dynamics365/customer-engagement/developer/webapi/web-api-reference |

### Category 3: Project Management
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Trello | `trello` | `TRELLO_API_KEY`, `TRELLO_TOKEN` | https://developer.atlassian.com/cloud/trello/rest/ |
| Asana | `asana` | `ASANA_ACCESS_TOKEN` | https://developers.asana.com/docs |
| Monday.com | `monday` | `MONDAY_API_KEY` | https://developer.monday.com/api-reference |
| ClickUp | `clickup` | `CLICKUP_API_KEY` | https://clickup.com/api |
| Jira Cloud | `jira` | `JIRA_API_TOKEN`, `JIRA_EMAIL`, `JIRA_DOMAIN` | https://developer.atlassian.com/cloud/jira/platform/rest/v3/ |
| Confluence | `confluence` | `CONFLUENCE_API_TOKEN`, `CONFLUENCE_EMAIL`, `CONFLUENCE_DOMAIN` | https://developer.atlassian.com/cloud/confluence/rest/v1/ |
| Basecamp | `basecamp` | `BASECAMP_ACCESS_TOKEN` | https://github.com/basecamp/bc3-api |
| Smartsheet | `smartsheet` | `SMARTSHEET_ACCESS_TOKEN` | https://smartsheet-platform.github.io/api-docs/ |
| Todoist | `todoist` | `TODOIST_API_TOKEN` | https://developer.todoist.com/rest/v2/ |

### Category 4: Databases & Productivity Tools
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Airtable | `airtable` | `AIRTABLE_API_KEY` or `AIRTABLE_ACCESS_TOKEN` | https://airtable.com/developers/web/api |
| Notion | `notion` | `NOTION_API_KEY` | https://developers.notion.com/ |
| Coda | `coda` | `CODA_API_TOKEN` | https://coda.io/developers/apis/v1 |

### Category 5: Communication & Messaging
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Slack | `slack` | `SLACK_BOT_TOKEN` or `SLACK_USER_TOKEN` | https://api.slack.com/ |
| Discord | `discord` | `DISCORD_BOT_TOKEN` | https://discord.com/developers/docs |
| Twilio | `twilio` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | https://www.twilio.com/docs/usage/api |
| WhatsApp Business | `whatsapp` | `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | https://developers.facebook.com/docs/whatsapp |
| Telegram | `telegram` | `TELEGRAM_BOT_TOKEN` | https://core.telegram.org/bots/api |

### Category 6: Video Conferencing & Scheduling
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Zoom | `zoom` | `ZOOM_JWT_TOKEN` or `ZOOM_CLIENT_ID`/`ZOOM_CLIENT_SECRET` | https://marketplace.zoom.us/docs/api-reference |
| Calendly | `calendly` | `CALENDLY_API_KEY` | https://developer.calendly.com/api-docs |

### Category 7: CRM & Sales
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| HubSpot | `hubspot` | `HUBSPOT_ACCESS_TOKEN` | https://developers.hubspot.com/docs/api/overview |
| Salesforce | `salesforce` | `SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_INSTANCE_URL` | https://developer.salesforce.com/docs/apis |
| Pipedrive | `pipedrive` | `PIPEDRIVE_API_TOKEN` | https://developers.pipedrive.com/docs/api/v1 |
| Close CRM | `close_crm` | `CLOSE_API_KEY` | https://developer.close.com/ |
| Zoho CRM | `zoho_crm` | `ZOHO_ACCESS_TOKEN` | https://www.zoho.com/crm/developer/docs/api/v2/ |
| Insightly | `insightly` | `INSIGHTLY_API_KEY` | https://api.insightly.com/v3.1/Help |

### Category 8: Customer Support
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Intercom | `intercom` | `INTERCOM_ACCESS_TOKEN` | https://developers.intercom.com/docs |
| Zendesk | `zendesk` | `ZENDESK_API_TOKEN`, `ZENDESK_EMAIL`, `ZENDESK_SUBDOMAIN` | https://developer.zendesk.com/api-reference |
| Freshdesk | `freshdesk` | `FRESHDESK_API_KEY`, `FRESHDESK_DOMAIN` | https://developers.freshdesk.com/api/ |
| Help Scout | `helpscout` | `HELPSCOUT_API_KEY` | https://developer.helpscout.com/ |
| Front | `front` | `FRONT_API_TOKEN` | https://dev.frontapp.com/reference |
| Gorgias | `gorgias` | `GORGIAS_API_KEY`, `GORGIAS_DOMAIN` | https://developers.gorgias.com/ |
| ServiceNow | `servicenow` | `SERVICENOW_INSTANCE`, `SERVICENOW_USERNAME`, `SERVICENOW_PASSWORD` | https://developer.servicenow.com/dev.do |

### Category 9: E-commerce
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Shopify | `shopify` | `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_STORE_URL` | https://shopify.dev/docs/api |
| WooCommerce | `woocommerce` | `WOOCOMMERCE_CONSUMER_KEY`, `WOOCOMMERCE_CONSUMER_SECRET`, `WOOCOMMERCE_STORE_URL` | https://woocommerce.github.io/woocommerce-rest-api-docs/ |
| eBay | `ebay` | `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID` | https://developer.ebay.com/docs |
| Etsy | `etsy` | `ETSY_API_KEY` | https://developers.etsy.com/documentation |

### Category 10: Payment Processing
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Stripe | `stripe` | `STRIPE_API_KEY` | https://stripe.com/docs/api |
| PayPal | `paypal` | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | https://developer.paypal.com/docs/api/overview/ |

### Category 11: Email Marketing
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Mailchimp | `mailchimp` | `MAILCHIMP_API_KEY` | https://mailchimp.com/developer/marketing/api/ |
| Klaviyo | `klaviyo` | `KLAVIYO_API_KEY` | https://developers.klaviyo.com/en/reference/api-overview |
| ActiveCampaign | `activecampaign` | `ACTIVECAMPAIGN_API_KEY`, `ACTIVECAMPAIGN_URL` | https://developers.activecampaign.com/reference |
| MailerLite | `mailerlite` | `MAILERLITE_API_KEY` | https://developers.mailerlite.com/docs |
| SendGrid | `sendgrid` | `SENDGRID_API_KEY` | https://docs.sendgrid.com/api-reference |
| Mailgun | `mailgun` | `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` | https://documentation.mailgun.com/en/latest/api_reference.html |
| Postmark | `postmark` | `POSTMARK_SERVER_TOKEN` | https://postmarkapp.com/developer |

### Category 12: AI & Machine Learning
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| OpenAI (ChatGPT) | `openai_chat` | `OPENAI_API_KEY` | https://platform.openai.com/docs/api-reference (Already exists) |

### Category 13: Document Management & E-Signature
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| DocuSign | `docusign` | `DOCUSIGN_ACCESS_TOKEN`, `DOCUSIGN_ACCOUNT_ID` | https://developers.docusign.com/docs |
| PandaDoc | `pandadoc` | `PANDADOC_API_KEY` | https://developers.pandadoc.com/reference |
| Dropbox | `dropbox` | `DROPBOX_ACCESS_TOKEN` | https://www.dropbox.com/developers/documentation |
| Box | `box` | `BOX_ACCESS_TOKEN` | https://developer.box.com/reference/ |

### Category 14: Developer Tools
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| GitHub | `github` | `GITHUB_TOKEN` | https://docs.github.com/en/rest |
| GitLab | `gitlab` | `GITLAB_ACCESS_TOKEN` | https://docs.gitlab.com/ee/api/ |

### Category 15: Design & Collaboration
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Miro | `miro` | `MIRO_ACCESS_TOKEN` | https://developers.miro.com/reference |
| Figma | `figma` | `FIGMA_ACCESS_TOKEN` | https://www.figma.com/developers/api |

### Category 16: Website Builders
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Webflow | `webflow` | `WEBFLOW_API_TOKEN` | https://developers.webflow.com/ |
| WordPress | `wordpress` | `WORDPRESS_USERNAME`, `WORDPRESS_APP_PASSWORD`, `WORDPRESS_SITE_URL` | https://developer.wordpress.org/rest-api/ |
| Wix | `wix` | `WIX_API_KEY` | https://dev.wix.com/api/rest |
| Squarespace | `squarespace` | `SQUARESPACE_API_KEY` | https://developers.squarespace.com/ |

### Category 17: Forms & Surveys
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Typeform | `typeform` | `TYPEFORM_ACCESS_TOKEN` | https://developer.typeform.com/ |
| Jotform | `jotform` | `JOTFORM_API_KEY` | https://api.jotform.com/docs/ |

### Category 18: Advertising
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Meta Ads | `meta_ads` | `META_ACCESS_TOKEN` | https://developers.facebook.com/docs/marketing-apis |
| LinkedIn Ads | `linkedin_ads` | `LINKEDIN_ACCESS_TOKEN` | https://docs.microsoft.com/en-us/linkedin/marketing/ |
| YouTube | `youtube` | `YOUTUBE_API_KEY` | https://developers.google.com/youtube/v3 |

### Category 19: Finance & Accounting
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| QuickBooks Online | `quickbooks` | `QUICKBOOKS_ACCESS_TOKEN`, `QUICKBOOKS_REALM_ID` | https://developer.intuit.com/app/developer/qbo/docs/api |
| Xero | `xero` | `XERO_ACCESS_TOKEN`, `XERO_TENANT_ID` | https://developer.xero.com/documentation/api |
| FreshBooks | `freshbooks` | `FRESHBOOKS_ACCESS_TOKEN` | https://www.freshbooks.com/api |

### Category 20: Data Processing & Utilities
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| CloudConvert | `cloudconvert` | `CLOUDCONVERT_API_KEY` | https://cloudconvert.com/api/v2 |
| PDF.co | `pdfco` | `PDFCO_API_KEY` | https://developer.pdf.co/ |
| Docparser | `docparser` | `DOCPARSER_API_KEY` | https://dev.docparser.com/ |
| Parseur/Mailparser | `parseur` | `PARSEUR_API_KEY` | https://help.parseur.com/en/articles/5154126 |
| Apify | `apify` | `APIFY_API_TOKEN` | https://docs.apify.com/api/v2 |
| Clearbit | `clearbit` | `CLEARBIT_API_KEY` | https://clearbit.com/docs |
| Hunter.io | `hunter` | `HUNTER_API_KEY` | https://hunter.io/api-documentation |
| Bitly | `bitly` | `BITLY_ACCESS_TOKEN` | https://dev.bitly.com/ |
| UptimeRobot | `uptimerobot` | `UPTIMEROBOT_API_KEY` | https://uptimerobot.com/api/ |

### Category 21: Cloud Storage
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| AWS S3 | `aws_s3` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | https://docs.aws.amazon.com/s3/index.html |
| Google Cloud Storage | `gcs` | `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://cloud.google.com/storage/docs/reference |
| Azure Blob Storage | `azure_blob` | `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY` | https://docs.microsoft.com/en-us/rest/api/storageservices/ |

### Category 22: Databases
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| MySQL | `mysql` | `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Direct connection (not REST API) |
| PostgreSQL | `postgresql` | `POSTGRESQL_HOST`, `POSTGRESQL_USER`, `POSTGRESQL_PASSWORD`, `POSTGRESQL_DATABASE` | Direct connection (not REST API) |
| MongoDB | `mongodb` | `MONGODB_URI` | https://www.mongodb.com/docs/drivers/python/ |

### Category 23: Analytics & Data Warehousing
| Service | Server Name | API Key/Secret Name | API Documentation |
|---------|-------------|---------------------|-------------------|
| Segment | `segment` | `SEGMENT_WRITE_KEY` | https://segment.com/docs/connections/sources/catalog/libraries/server/http-api/ |
| Mixpanel | `mixpanel` | `MIXPANEL_TOKEN`, `MIXPANEL_API_SECRET` | https://developer.mixpanel.com/reference |
| Amplitude | `amplitude` | `AMPLITUDE_API_KEY`, `AMPLITUDE_SECRET_KEY` | https://developers.amplitude.com/docs/http-api-v2 |
| BigQuery | `bigquery` | `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SERVICE_ACCOUNT_JSON` | https://cloud.google.com/bigquery/docs/reference/rest |
| Snowflake | `snowflake` | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE` | https://docs.snowflake.com/en/developer-guide/sql-api |

---

## Implementation Pattern

### Server Definition Template

Each external service server will follow this pattern:

```python
# ruff: noqa: F821, F706
"""Call the {ServiceName} API using automatic main() mapping."""

import os
from typing import Optional

import requests


API_BASE_URL = "https://api.example.com/v1"


def main(
    endpoint: str = "",
    method: str = "GET",
    data: Optional[str] = None,
    *,
    SERVICE_API_KEY: str,
    context=None,
):
    """
    Make a request to the {ServiceName} API.

    Args:
        endpoint: The API endpoint to call (e.g., "/users", "/messages")
        method: HTTP method (GET, POST, PUT, DELETE)
        data: JSON data for POST/PUT requests
        SERVICE_API_KEY: API key for authentication (from secrets)
        context: Request context (optional)

    Returns:
        Dict with 'output' containing the API response
    """
    if not SERVICE_API_KEY:
        return {"output": "Missing SERVICE_API_KEY", "content_type": "text/plain"}

    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {SERVICE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=60)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=60)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=60)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=60)
        else:
            return {"output": f"Unsupported method: {method}", "content_type": "text/plain"}

        response.raise_for_status()
        return {"output": response.json()}

    except requests.exceptions.RequestException as e:
        return {"output": f"API Error: {str(e)}", "content_type": "text/plain"}
```

### JSON Template Pattern

```json
{
  "id": "service_name",
  "name": "Service Name API",
  "description": "Make requests to the Service Name API.",
  "definition_file": "definitions/service_name.py"
}
```

### Boot Image Entry Pattern

```json
{
  "name": "service_name",
  "definition_cid": "reference_templates/servers/definitions/service_name.py",
  "enabled": true
}
```

---

## Test Plan

### Test Categories

#### 1. Unit Tests (per server)
Each server definition needs the following unit tests:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_missing_api_key` | Server returns error when API key is missing |
| `test_{server}_default_endpoint` | Server handles default/empty endpoint |
| `test_{server}_get_request` | Server makes GET request correctly |
| `test_{server}_post_request` | Server makes POST request with data |
| `test_{server}_put_request` | Server makes PUT request with data |
| `test_{server}_delete_request` | Server makes DELETE request |
| `test_{server}_api_error_handling` | Server handles API errors gracefully |
| `test_{server}_timeout_handling` | Server handles request timeouts |
| `test_{server}_invalid_json_response` | Server handles non-JSON responses |
| `test_{server}_rate_limit_response` | Server handles rate limiting (429) |

#### 2. Integration Tests (per server)
Each server needs integration tests with mocked external APIs:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_server_registered_in_boot_image` | Server exists in boot image |
| `test_{server}_accessible_via_url` | Server accessible at expected URL |
| `test_{server}_form_rendering` | Server renders input form when accessed with GET |
| `test_{server}_request_execution` | Server executes request and returns result |
| `test_{server}_chaining_input` | Server accepts chained input from another server |
| `test_{server}_cid_output` | Server output can be stored as CID |

#### 3. Boot Image Tests
General tests for the server collection:

| Test Name | Description |
|-----------|-------------|
| `test_all_external_servers_in_default_boot` | All external servers present in default boot |
| `test_all_external_servers_in_readonly_boot` | All external servers present in readonly boot |
| `test_external_servers_enabled_by_default` | All external servers enabled |
| `test_external_server_cids_valid` | All server CIDs are valid |
| `test_external_server_definitions_valid_python` | All server definitions are valid Python |
| `test_no_duplicate_server_names` | No duplicate server names |
| `test_server_names_follow_convention` | Server names follow naming convention |

#### 4. Template Tests

| Test Name | Description |
|-----------|-------------|
| `test_all_servers_have_templates` | Each server has a corresponding JSON template |
| `test_template_ids_match_server_names` | Template IDs match server names |
| `test_templates_have_required_fields` | Templates have id, name, description, definition_file |
| `test_template_definition_files_exist` | Referenced definition files exist |

---

## Detailed Test Specifications

### Unit Test Template

```python
import unittest
from unittest.mock import Mock, patch

class TestServiceNameServer(unittest.TestCase):
    """Tests for service_name server."""

    def test_service_name_missing_api_key(self):
        """Server returns error when API key is missing."""
        from reference_templates.servers.definitions.service_name import main
        result = main(endpoint="/test", SERVICE_API_KEY="")
        self.assertIn("Missing", result["output"])

    def test_service_name_default_endpoint(self):
        """Server handles default/empty endpoint."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "ok"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            from reference_templates.servers.definitions.service_name import main
            result = main(endpoint="", SERVICE_API_KEY="test-key")
            self.assertIn("status", result["output"])

    @patch("requests.get")
    def test_service_name_get_request(self, mock_get):
        """Server makes GET request correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": [{"id": 1}]}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        from reference_templates.servers.definitions.service_name import main
        result = main(endpoint="/users", method="GET", SERVICE_API_KEY="test-key")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("/users", call_args[0][0])
        self.assertIn("Authorization", call_args[1]["headers"])

    @patch("requests.post")
    def test_service_name_post_request(self, mock_post):
        """Server makes POST request with data."""
        mock_response = Mock()
        mock_response.json.return_value = {"created": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        from reference_templates.servers.definitions.service_name import main
        result = main(
            endpoint="/users",
            method="POST",
            data={"name": "Test"},
            SERVICE_API_KEY="test-key"
        )

        mock_post.assert_called_once()
        self.assertEqual(result["output"]["created"], True)

    @patch("requests.get")
    def test_service_name_api_error_handling(self, mock_get):
        """Server handles API errors gracefully."""
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        from reference_templates.servers.definitions.service_name import main
        result = main(endpoint="/invalid", SERVICE_API_KEY="test-key")

        self.assertIn("Error", result["output"])

    @patch("requests.get")
    def test_service_name_timeout_handling(self, mock_get):
        """Server handles request timeouts."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        from reference_templates.servers.definitions.service_name import main
        result = main(endpoint="/slow", SERVICE_API_KEY="test-key")

        self.assertIn("Error", result["output"])

    @patch("requests.get")
    def test_service_name_rate_limit_response(self, mock_get):
        """Server handles rate limiting (429)."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        mock_get.return_value = mock_response

        from reference_templates.servers.definitions.service_name import main
        result = main(endpoint="/test", SERVICE_API_KEY="test-key")

        self.assertIn("Error", result["output"])
```

### Integration Test Template

```python
import pytest
from unittest.mock import patch, Mock

@pytest.mark.integration
class TestServiceNameIntegration:
    """Integration tests for service_name server."""

    def test_service_name_server_registered_in_boot_image(self, integration_app):
        """Server exists in boot image."""
        with integration_app.app_context():
            from models import Server
            server = Server.query.filter_by(name="service_name").first()
            assert server is not None
            assert server.enabled is True

    def test_service_name_accessible_via_url(self, client, integration_app):
        """Server accessible at expected URL."""
        response = client.get("/service_name")
        assert response.status_code in (200, 302, 400)  # 400 if missing required params

    def test_service_name_form_rendering(self, client, integration_app):
        """Server renders input form when accessed with GET."""
        response = client.get("/service_name")
        # Should show form or parameter hints
        assert response.status_code == 200 or b"endpoint" in response.data

    @patch("requests.get")
    def test_service_name_request_execution(self, mock_get, client, integration_app):
        """Server executes request and returns result."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Set up secret
        with integration_app.app_context():
            from models import Secret
            from app import db
            secret = Secret(name="SERVICE_API_KEY", value="test-key")
            db.session.add(secret)
            db.session.commit()

        response = client.post("/service_name", data={"endpoint": "/test"})
        assert response.status_code == 200
```

### Boot Image Test

```python
import json
import unittest

class TestExternalServerBootImage(unittest.TestCase):
    """Tests for external servers in boot images."""

    @classmethod
    def setUpClass(cls):
        """Load boot images."""
        with open("reference_templates/default.boot.source.json") as f:
            cls.default_boot = json.load(f)
        with open("reference_templates/readonly.boot.source.json") as f:
            cls.readonly_boot = json.load(f)

        # List of all external server names
        cls.external_servers = [
            "google_sheets", "gmail", "google_drive", "google_calendar",
            "google_forms", "google_contacts", "google_docs", "google_ads",
            "google_analytics", "microsoft_outlook", "microsoft_teams",
            "onedrive", "microsoft_excel", "dynamics365", "slack", "discord",
            "trello", "asana", "monday", "clickup", "jira", "confluence",
            "basecamp", "smartsheet", "todoist", "airtable", "notion", "coda",
            "twilio", "whatsapp", "telegram", "zoom", "calendly", "hubspot",
            "salesforce", "pipedrive", "close_crm", "zoho_crm", "insightly",
            "intercom", "zendesk", "freshdesk", "helpscout", "front", "gorgias",
            "servicenow", "shopify", "woocommerce", "ebay", "etsy", "stripe",
            "paypal", "mailchimp", "klaviyo", "activecampaign", "mailerlite",
            "sendgrid", "mailgun", "postmark", "docusign", "pandadoc",
            "dropbox", "box", "github", "gitlab", "miro", "figma", "webflow",
            "wordpress", "wix", "squarespace", "typeform", "jotform",
            "meta_ads", "linkedin_ads", "youtube", "quickbooks", "xero",
            "freshbooks", "cloudconvert", "pdfco", "docparser", "parseur",
            "apify", "clearbit", "hunter", "bitly", "uptimerobot", "aws_s3",
            "gcs", "azure_blob", "mysql", "postgresql", "mongodb", "segment",
            "mixpanel", "amplitude", "bigquery", "snowflake"
        ]

    def test_all_external_servers_in_default_boot(self):
        """All external servers present in default boot."""
        server_names = [s["name"] for s in self.default_boot["servers"]]
        for name in self.external_servers:
            self.assertIn(name, server_names, f"Missing server: {name}")

    def test_all_external_servers_in_readonly_boot(self):
        """All external servers present in readonly boot."""
        server_names = [s["name"] for s in self.readonly_boot["servers"]]
        for name in self.external_servers:
            self.assertIn(name, server_names, f"Missing server: {name}")

    def test_external_servers_enabled_by_default(self):
        """All external servers enabled."""
        for server in self.default_boot["servers"]:
            if server["name"] in self.external_servers:
                self.assertTrue(server["enabled"], f"Server not enabled: {server['name']}")

    def test_external_server_cids_valid(self):
        """All server CIDs reference valid files."""
        import os
        for server in self.default_boot["servers"]:
            if server["name"] in self.external_servers:
                definition_path = server["definition_cid"]
                self.assertTrue(
                    os.path.exists(definition_path),
                    f"Definition file missing: {definition_path}"
                )

    def test_external_server_definitions_valid_python(self):
        """All server definitions are valid Python."""
        import ast
        for server in self.default_boot["servers"]:
            if server["name"] in self.external_servers:
                definition_path = server["definition_cid"]
                with open(definition_path) as f:
                    code = f.read()
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    self.fail(f"Invalid Python in {definition_path}: {e}")

    def test_no_duplicate_server_names(self):
        """No duplicate server names."""
        server_names = [s["name"] for s in self.default_boot["servers"]]
        self.assertEqual(len(server_names), len(set(server_names)))

    def test_server_names_follow_convention(self):
        """Server names follow naming convention (lowercase, underscores)."""
        import re
        pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        for name in self.external_servers:
            self.assertTrue(
                pattern.match(name),
                f"Invalid server name format: {name}"
            )
```

### Template Test

```python
import json
import os
import unittest

class TestExternalServerTemplates(unittest.TestCase):
    """Tests for external server JSON templates."""

    @classmethod
    def setUpClass(cls):
        """Load all template files."""
        cls.templates_dir = "reference_templates/servers/templates"
        cls.definitions_dir = "reference_templates/servers/definitions"
        cls.templates = {}

        for filename in os.listdir(cls.templates_dir):
            if filename.endswith(".json"):
                with open(os.path.join(cls.templates_dir, filename)) as f:
                    cls.templates[filename] = json.load(f)

    def test_all_servers_have_templates(self):
        """Each server has a corresponding JSON template."""
        # Get list of .py definition files
        definition_files = [
            f.replace(".py", "")
            for f in os.listdir(self.definitions_dir)
            if f.endswith(".py")
        ]

        # Get list of .json template files
        template_ids = [t.get("id") for t in self.templates.values()]

        for def_name in definition_files:
            self.assertIn(
                def_name, template_ids,
                f"Missing template for: {def_name}"
            )

    def test_templates_have_required_fields(self):
        """Templates have id, name, description, definition_file."""
        required_fields = ["id", "name", "description", "definition_file"]

        for filename, template in self.templates.items():
            for field in required_fields:
                self.assertIn(
                    field, template,
                    f"Missing field '{field}' in {filename}"
                )

    def test_template_ids_match_server_names(self):
        """Template IDs match server names."""
        for filename, template in self.templates.items():
            expected_id = filename.replace(".json", "")
            self.assertEqual(
                template.get("id"), expected_id,
                f"ID mismatch in {filename}"
            )

    def test_template_definition_files_exist(self):
        """Referenced definition files exist."""
        for filename, template in self.templates.items():
            definition_file = template.get("definition_file", "")
            full_path = os.path.join(
                self.definitions_dir,
                definition_file.replace("definitions/", "")
            )
            self.assertTrue(
                os.path.exists(full_path),
                f"Definition file not found: {full_path} (referenced in {filename})"
            )
```

---

## Service-Specific Test Variations

### OAuth-Based Services (Google, Microsoft, etc.)

Additional tests for OAuth services:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_oauth_token_refresh` | Server handles token refresh |
| `test_{server}_oauth_token_expired` | Server handles expired tokens |
| `test_{server}_oauth_scopes_required` | Server validates required scopes |

### Services with Pagination

Additional tests for paginated APIs:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_pagination_first_page` | Server fetches first page |
| `test_{server}_pagination_next_page` | Server fetches subsequent pages |
| `test_{server}_pagination_cursor_based` | Server handles cursor-based pagination |
| `test_{server}_pagination_offset_based` | Server handles offset-based pagination |

### Services with Rate Limiting

Additional tests for rate-limited APIs:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_rate_limit_headers` | Server reads rate limit headers |
| `test_{server}_rate_limit_backoff` | Server implements backoff strategy |
| `test_{server}_rate_limit_retry` | Server retries after rate limit |

### Database Connections (MySQL, PostgreSQL, MongoDB)

Different test pattern for direct database connections:

| Test Name | Description |
|-----------|-------------|
| `test_{server}_connection_success` | Server connects successfully |
| `test_{server}_connection_failure` | Server handles connection failures |
| `test_{server}_query_execution` | Server executes queries |
| `test_{server}_query_timeout` | Server handles query timeouts |
| `test_{server}_connection_pooling` | Server uses connection pooling |
| `test_{server}_sql_injection_prevention` | Server prevents SQL injection |

---

## Open Questions

### Architecture Questions

1. **OAuth Token Management**: How should OAuth tokens be managed for Google, Microsoft, and other OAuth-based services?
   - Option A: Store refresh tokens in secrets, implement token refresh in each server
   - Option B: Create a shared OAuth token manager that servers can use
   - Option C: Require users to provide fresh access tokens each time
   - **Recommendation**: Option B - shared OAuth manager for consistency

2. **Service Account vs User Authentication**: For Google services, should we support both service accounts and user OAuth?
   - Service accounts are simpler but limited to organization resources
   - User OAuth provides broader access but requires token refresh
   - **Recommendation**: Support both, with service account as default

3. **Database Connections**: Should database servers (MySQL, PostgreSQL, MongoDB) use direct connections or should they go through a connection pooling layer?
   - Direct connections: Simple but may exhaust connection limits
   - Connection pooling: More complex but efficient
   - **Recommendation**: Use connection pooling (e.g., SQLAlchemy for SQL, pymongo for MongoDB)

4. **Webhook Endpoints**: Several services support webhooks (Stripe, Shopify, etc.). Should server definitions include webhook handling?
   - Option A: Separate webhook server definitions
   - Option B: Include webhook handling in main server
   - Option C: Create a generic webhook receiver server
   - **Recommendation**: Option C - generic webhook receiver that dispatches to appropriate handlers

### Implementation Questions

5. **Server Naming Convention**: Should server names use underscores (google_sheets) or hyphens (google-sheets)?
   - Current pattern uses underscores (anthropic_claude, openai_chat)
   - **Recommendation**: Use underscores for consistency

6. **Default Endpoints**: Should servers have a default/demo endpoint for testing without configuration?
   - Pro: Easier to verify server works
   - Con: May confuse users, requires API keys anyway
   - **Recommendation**: Show helpful form/documentation by default, require API key for actual calls

7. **Error Message Format**: Should error messages be plain text or structured JSON?
   - Plain text: Human readable in browser
   - JSON: Machine parseable for chaining
   - **Recommendation**: Return JSON with `error` key, server framework can render appropriately

8. **Batch Operations**: Some APIs support batch operations (e.g., Airtable batch create). Should servers support these?
   - **Recommendation**: Support batch operations where the API provides them, with separate parameters

### Security Questions

9. **Secret Naming Convention**: Should secrets follow the pattern `{SERVICE}_API_KEY` or `{SERVICE}_ACCESS_TOKEN`?
   - API_KEY: For simple API keys
   - ACCESS_TOKEN: For OAuth tokens
   - **Recommendation**: Use the term the service uses (e.g., STRIPE_API_KEY, GOOGLE_ACCESS_TOKEN)

10. **Read-Only Boot Image**: Should all external servers be included in the read-only boot image?
    - Some servers may have write operations (e.g., POST to create records)
    - Read-only mode may want to restrict these
    - **Recommendation**: Include all servers, but document which operations are read vs write

11. **Secret Validation**: Should servers validate secrets before making API calls?
    - Pro: Faster failure, better error messages
    - Con: Some APIs don't have a validation endpoint
    - **Recommendation**: Validate where possible, otherwise fail fast on first API call

### Testing Questions

12. **Mock vs Real API Tests**: Should integration tests use mocked APIs or real API calls?
    - Mocked: Faster, deterministic, no API keys needed
    - Real: More realistic, catches actual API issues
    - **Recommendation**: Mock for CI/CD, option for real tests with API keys in environment

13. **Test API Accounts**: Should we create test/sandbox accounts for each service?
    - Many services offer sandbox modes (Stripe, PayPal, etc.)
    - **Recommendation**: Document sandbox setup for each service, use in integration tests

14. **Coverage Requirements**: What is the minimum test coverage for each server?
    - **Recommendation**: 80% line coverage minimum, 100% for core functionality (authentication, request building)

### Operational Questions

15. **Rate Limit Handling**: Should servers automatically retry on rate limits?
    - Pro: More resilient
    - Con: May delay response, hide issues
    - **Recommendation**: Configurable retry with exponential backoff, max 3 retries

16. **Timeout Configuration**: Should timeouts be configurable per server?
    - Some APIs are slower (file uploads, data processing)
    - **Recommendation**: Default 60s timeout, configurable via parameter

17. **Logging**: What should be logged for external API calls?
    - **Recommendation**: Log request URL, method, response status (never log secrets or sensitive data)

---

## Implementation Phases

### Phase 1: Foundation (10 servers)
Set up patterns and implement first servers as templates:
- google_sheets
- slack
- stripe
- github
- airtable
- notion
- hubspot
- mailchimp
- openai_chat (already exists)
- zoom

### Phase 2: Google Suite (9 servers)
- gmail
- google_drive
- google_calendar
- google_forms
- google_contacts
- google_docs
- google_ads
- google_analytics
- youtube

### Phase 3: Microsoft Suite (5 servers)
- microsoft_outlook
- microsoft_teams
- onedrive
- microsoft_excel
- dynamics365

### Phase 4: Project Management (9 servers)
- trello
- asana
- monday
- clickup
- jira
- confluence
- basecamp
- smartsheet
- todoist

### Phase 5: Communication (4 servers)
- discord
- twilio
- whatsapp
- telegram

### Phase 6: CRM & Sales (6 servers)
- salesforce
- pipedrive
- close_crm
- zoho_crm
- insightly
- calendly

### Phase 7: Customer Support (7 servers)
- intercom
- zendesk
- freshdesk
- helpscout
- front
- gorgias
- servicenow

### Phase 8: E-commerce & Payments (6 servers)
- shopify
- woocommerce
- ebay
- etsy
- paypal
- (stripe already in Phase 1)

### Phase 9: Email Marketing (7 servers)
- klaviyo
- activecampaign
- mailerlite
- sendgrid
- mailgun
- postmark
- (mailchimp already in Phase 1)

### Phase 10: Document & Storage (6 servers)
- docusign
- pandadoc
- dropbox
- box
- (onedrive in Phase 3)
- (google_drive in Phase 2)

### Phase 11: Developer & Design (4 servers)
- gitlab
- miro
- figma
- (github already in Phase 1)

### Phase 12: Website Builders (4 servers)
- webflow
- wordpress
- wix
- squarespace

### Phase 13: Forms & Surveys (2 servers)
- typeform
- jotform

### Phase 14: Advertising (2 servers)
- meta_ads
- linkedin_ads

### Phase 15: Finance (4 servers)
- quickbooks
- xero
- freshbooks
- coda

### Phase 16: Data Processing (10 servers)
- cloudconvert
- pdfco
- docparser
- parseur
- apify
- clearbit
- hunter
- bitly
- uptimerobot
- (airtable/notion already done)

### Phase 17: Cloud Storage (3 servers)
- aws_s3
- gcs
- azure_blob

### Phase 18: Databases (3 servers)
- mysql
- postgresql
- mongodb

### Phase 19: Analytics (5 servers)
- segment
- mixpanel
- amplitude
- bigquery
- snowflake

---

## Acceptance Criteria

### Per Server
- [ ] Definition file exists in `reference_templates/servers/definitions/{name}.py`
- [ ] Template file exists in `reference_templates/servers/templates/{name}.json`
- [ ] Server entry in `default.boot.source.json`
- [ ] Server entry in `readonly.boot.source.json`
- [ ] Server is enabled by default
- [ ] All unit tests pass (minimum 8 tests per server)
- [ ] All integration tests pass (minimum 4 tests per server)
- [ ] API key/secret naming follows convention
- [ ] Error handling is consistent
- [ ] Timeout is set appropriately
- [ ] Documentation includes usage examples

### Overall
- [ ] All 100+ servers implemented
- [ ] Boot images regenerate successfully
- [ ] No duplicate server names
- [ ] All tests pass in CI/CD
- [ ] No security vulnerabilities
- [ ] Performance acceptable (no startup degradation)

---

## References

- Existing server patterns: `reference_templates/servers/definitions/anthropic_claude.py`
- Boot image structure: `reference_templates/default.boot.source.json`
- Test patterns: `tests/test_server_*.py`
- Integration test patterns: `tests/integration/test_server_*.py`
- API documentation links in service tables above

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| Initial | Created plan document | Claude |
