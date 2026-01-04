# Plan: CID Archive Files for External API Responses

## Scope

**This plan covers creating static CID archive files only.** These archives contain realistic API response data that can be used by gateways and mock servers. The gateways that consume these archives and any mock server implementations are out of scope for this plan.

**Pattern**: CID archives provide static response data accessed via `/gateway/test/cids/{archive-cid}/as/{server}/{path}`

**Reference Implementation**: The existing `jsonplaceholder` archive in `reference/files/` and `reference/archive/cids/`.

---

## File Structure

```
reference/
├── archive/
│   └── cids/
│       ├── jsonplaceholder.source.cids    # Existing reference
│       │
│       │   # Group 1: Version Control
│       ├── github.source.cids
│       ├── gitlab.source.cids
│       │
│       │   # Group 2: AI/LLM Services
│       ├── openai.source.cids
│       ├── anthropic.source.cids
│       ├── gemini.source.cids
│       │
│       │   # Group 3: Communication Platforms
│       ├── slack.source.cids
│       ├── discord.source.cids
│       ├── teams.source.cids
│       ├── telegram.source.cids
│       │
│       │   # Group 4: CRM Systems
│       ├── hubspot.source.cids
│       ├── salesforce.source.cids
│       ├── jira.source.cids
│       │
│       │   # Group 5: Payment Processing
│       ├── stripe.source.cids
│       ├── paypal.source.cids
│       │
│       │   # Group 6: Email & Marketing
│       ├── mailchimp.source.cids
│       ├── sendgrid.source.cids
│       │
│       │   # Group 7: Productivity & Knowledge
│       ├── notion.source.cids
│       ├── airtable.source.cids
│       │
│       │   # Group 8: E-commerce
│       └── shopify.source.cids
│
└── files/
    ├── jsonplaceholder_*.json              # Existing reference
    │
    │   # Group 1: Version Control
    ├── github/
    │   ├── repos_acme-corp_widgets_issues.json
    │   ├── repos_acme-corp_widgets_issues_1.json
    │   ├── repos_acme-corp_widgets_issues_2.json
    │   ├── rate_limit.json
    │   └── errors/
    │       ├── 401_unauthorized.json
    │       ├── 403_rate_limited.json
    │       └── 404_not_found.json
    ├── gitlab/
    │   ├── api_v4_projects.json
    │   ├── api_v4_projects_42.json
    │   ├── api_v4_projects_42_issues.json
    │   ├── api_v4_projects_42_issues_7.json
    │   ├── api_v4_projects_42_merge_requests.json
    │   └── errors/
    │       ├── 401_unauthorized.json
    │       └── 404_not_found.json
    │
    │   # Group 2: AI/LLM Services
    ├── openai/
    │   ├── v1_chat_completions.json
    │   ├── v1_models.json
    │   └── errors/
    │       ├── 401_invalid_api_key.json
    │       └── 429_rate_limited.json
    ├── anthropic/
    │   ├── v1_messages.json
    │   └── errors/
    │       ├── 401_invalid_api_key.json
    │       └── 529_overloaded.json
    ├── gemini/
    │   ├── v1beta_models_gemini-1.5-flash-latest_generateContent.json
    │   └── errors/
    │       └── 400_invalid_request.json
    │
    │   # Group 3: Communication Platforms
    ├── slack/
    │   ├── api_chat.postMessage.json
    │   ├── api_conversations.list.json
    │   └── errors/
    │       ├── channel_not_found.json
    │       └── not_authed.json
    ├── discord/
    │   ├── users_@me_guilds.json
    │   ├── guilds_8675309.json
    │   ├── guilds_8675309_channels.json
    │   ├── channels_42_messages.json
    │   └── errors/
    │       └── 401_unauthorized.json
    ├── teams/
    │   ├── me_joinedTeams.json
    │   ├── teams_abc-123.json
    │   ├── teams_abc-123_channels.json
    │   ├── teams_abc-123_channels_general_messages.json
    │   └── errors/
    │       └── 401_unauthorized.json
    ├── telegram/
    │   ├── getUpdates.json
    │   ├── sendMessage.json
    │   └── errors/
    │       └── 401_unauthorized.json
    │
    │   # Group 4: CRM Systems
    ├── hubspot/
    │   ├── crm_v3_objects_contacts.json
    │   ├── crm_v3_objects_contacts_501.json
    │   ├── crm_v3_objects_companies.json
    │   ├── crm_v3_objects_companies_101.json
    │   └── errors/
    │       └── 401_unauthorized.json
    ├── salesforce/
    │   ├── services_data_v59.0_query.json
    │   ├── services_data_v59.0_sobjects_Account_001ABC.json
    │   ├── services_data_v59.0_sobjects_Contact_003XYZ.json
    │   └── errors/
    │       └── 401_session_expired.json
    ├── jira/
    │   ├── rest_api_3_project.json
    │   ├── rest_api_3_project_ACME.json
    │   ├── rest_api_3_search.json
    │   ├── rest_api_3_issue_ACME-42.json
    │   └── errors/
    │       └── 401_unauthorized.json
    │
    │   # Group 5: Payment Processing
    ├── stripe/
    │   ├── v1_customers.json
    │   ├── v1_customers_cus_DrBogusMcFakester.json
    │   ├── v1_charges.json
    │   ├── v1_charges_ch_1234567890.json
    │   └── errors/
    │       ├── 401_invalid_api_key.json
    │       └── 402_card_declined.json
    ├── paypal/
    │   ├── v2_checkout_orders.json
    │   ├── v2_checkout_orders_5O190127TN364715T.json
    │   └── errors/
    │       └── 401_unauthorized.json
    │
    │   # Group 6: Email & Marketing
    ├── mailchimp/
    │   ├── 3.0_lists.json
    │   ├── 3.0_lists_abc123def.json
    │   ├── 3.0_lists_abc123def_members.json
    │   ├── 3.0_campaigns.json
    │   └── errors/
    │       └── 401_api_key_invalid.json
    ├── sendgrid/
    │   ├── v3_mail_send.json
    │   └── errors/
    │       └── 401_unauthorized.json
    │
    │   # Group 7: Productivity & Knowledge
    ├── notion/
    │   ├── v1_search.json
    │   ├── v1_pages_abc123.json
    │   ├── v1_databases_def456_query.json
    │   └── errors/
    │       └── 401_unauthorized.json
    ├── airtable/
    │   ├── v0_meta_bases.json
    │   ├── v0_appXYZ123_Projects.json
    │   └── errors/
    │       └── 401_unauthorized.json
    │
    │   # Group 8: E-commerce
    └── shopify/
        ├── admin_api_2024-01_products.json
        ├── admin_api_2024-01_products_7654321.json
        ├── admin_api_2024-01_orders.json
        ├── admin_api_2024-01_customers.json
        └── errors/
            └── 401_unauthorized.json
```

---

## Server Groups (Independent Chunks)

### Group 1: Version Control (GitHub, GitLab)
**Priority**: High - Most commonly used for issue tracking

#### GitHub Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/repos/acme-corp/widgets/issues` | `github/repos_acme-corp_widgets_issues.json` | List issues for Acme Corp's widgets repo |
| `/repos/acme-corp/widgets/issues/1` | `github/repos_acme-corp_widgets_issues_1.json` | Issue #1: "Widget fails on Tuesdays" |
| `/repos/acme-corp/widgets/issues/2` | `github/repos_acme-corp_widgets_issues_2.json` | Issue #2: "Add support for hexagonal widgets" |
| `/rate_limit` | `github/rate_limit.json` | API rate limit status |
| `/errors/401` | `github/errors/401_unauthorized.json` | Bad credentials error |
| `/errors/403` | `github/errors/403_rate_limited.json` | Rate limit exceeded |
| `/errors/404` | `github/errors/404_not_found.json` | Not found |

#### GitLab Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/api/v4/projects` | `gitlab/api_v4_projects.json` | List projects |
| `/api/v4/projects/42` | `gitlab/api_v4_projects_42.json` | Acme Corp's flagship project |
| `/api/v4/projects/42/issues` | `gitlab/api_v4_projects_42_issues.json` | Project issues |
| `/api/v4/projects/42/issues/7` | `gitlab/api_v4_projects_42_issues_7.json` | Issue #7 details |
| `/api/v4/projects/42/merge_requests` | `gitlab/api_v4_projects_42_merge_requests.json` | List MRs |
| `/errors/401` | `gitlab/errors/401_unauthorized.json` | Unauthorized |
| `/errors/404` | `gitlab/errors/404_not_found.json` | Not found |

---

### Group 2: AI/LLM Services (OpenAI, Anthropic, Gemini)
**Priority**: High - Core AI functionality

#### OpenAI Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v1/chat/completions` | `openai/v1_chat_completions.json` | Chat completion response |
| `/v1/models` | `openai/v1_models.json` | List available models |
| `/errors/401` | `openai/errors/401_invalid_api_key.json` | Invalid API key |
| `/errors/429` | `openai/errors/429_rate_limited.json` | Rate limited |

#### Anthropic Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v1/messages` | `anthropic/v1_messages.json` | Message response |
| `/errors/401` | `anthropic/errors/401_invalid_api_key.json` | Invalid API key |
| `/errors/529` | `anthropic/errors/529_overloaded.json` | API overloaded |

#### Google Gemini Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v1beta/models/gemini-1.5-flash-latest:generateContent` | `gemini/v1beta_models_gemini-1.5-flash-latest_generateContent.json` | Generate content |
| `/errors/400` | `gemini/errors/400_invalid_request.json` | Invalid request |

---

### Group 3: Communication Platforms (Slack, Discord, Teams, Telegram)
**Priority**: Medium - Collaboration integrations

#### Slack Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/api/chat.postMessage` | `slack/api_chat.postMessage.json` | Post message success response |
| `/api/conversations.list` | `slack/api_conversations.list.json` | List channels |
| `/errors/channel_not_found` | `slack/errors/channel_not_found.json` | Channel not found error |
| `/errors/not_authed` | `slack/errors/not_authed.json` | Not authenticated |

#### Discord Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/users/@me/guilds` | `discord/users_@me_guilds.json` | List user's guilds |
| `/guilds/8675309` | `discord/guilds_8675309.json` | "The Lounge" guild |
| `/guilds/8675309/channels` | `discord/guilds_8675309_channels.json` | Guild channels |
| `/channels/42/messages` | `discord/channels_42_messages.json` | Channel messages |
| `/errors/401` | `discord/errors/401_unauthorized.json` | Unauthorized |

#### Microsoft Teams Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/me/joinedTeams` | `teams/me_joinedTeams.json` | List joined teams |
| `/teams/abc-123` | `teams/teams_abc-123.json` | "Project Phoenix" team |
| `/teams/abc-123/channels` | `teams/teams_abc-123_channels.json` | Team channels |
| `/teams/abc-123/channels/general/messages` | `teams/teams_abc-123_channels_general_messages.json` | Channel messages |
| `/errors/401` | `teams/errors/401_unauthorized.json` | Unauthorized |

#### Telegram Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/getUpdates` | `telegram/getUpdates.json` | Bot updates |
| `/sendMessage` | `telegram/sendMessage.json` | Send message response |
| `/errors/401` | `telegram/errors/401_unauthorized.json` | Invalid bot token |

---

### Group 4: CRM Systems (HubSpot, Salesforce, Jira)
**Priority**: Medium - Business integrations

#### HubSpot Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/crm/v3/objects/contacts` | `hubspot/crm_v3_objects_contacts.json` | List contacts |
| `/crm/v3/objects/contacts/501` | `hubspot/crm_v3_objects_contacts_501.json` | Jane Doe contact |
| `/crm/v3/objects/companies` | `hubspot/crm_v3_objects_companies.json` | List companies |
| `/crm/v3/objects/companies/101` | `hubspot/crm_v3_objects_companies_101.json` | Acme Corporation |
| `/errors/401` | `hubspot/errors/401_unauthorized.json` | Unauthorized |

#### Salesforce Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/services/data/v59.0/query` | `salesforce/services_data_v59.0_query.json` | SOQL query results |
| `/services/data/v59.0/sobjects/Account/001ABC` | `salesforce/services_data_v59.0_sobjects_Account_001ABC.json` | Acme Inc account |
| `/services/data/v59.0/sobjects/Contact/003XYZ` | `salesforce/services_data_v59.0_sobjects_Contact_003XYZ.json` | Jane Doe contact |
| `/errors/401` | `salesforce/errors/401_session_expired.json` | Session expired |

#### Jira Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/rest/api/3/project` | `jira/rest_api_3_project.json` | List projects |
| `/rest/api/3/project/ACME` | `jira/rest_api_3_project_ACME.json` | ACME project |
| `/rest/api/3/search` | `jira/rest_api_3_search.json` | JQL search results |
| `/rest/api/3/issue/ACME-42` | `jira/rest_api_3_issue_ACME-42.json` | Issue ACME-42 |
| `/errors/401` | `jira/errors/401_unauthorized.json` | Unauthorized |

---

### Group 5: Payment Processing (Stripe, PayPal)
**Priority**: Lower - Specialized use cases

#### Stripe Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v1/customers` | `stripe/v1_customers.json` | List customers |
| `/v1/customers/cus_DrBogusMcFakester` | `stripe/v1_customers_cus_DrBogusMcFakester.json` | Dr. Bogus McFakester |
| `/v1/charges` | `stripe/v1_charges.json` | List charges |
| `/v1/charges/ch_1234567890` | `stripe/v1_charges_ch_1234567890.json` | Charge details |
| `/errors/401` | `stripe/errors/401_invalid_api_key.json` | Invalid API key |
| `/errors/402` | `stripe/errors/402_card_declined.json` | Card declined |

#### PayPal Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v2/checkout/orders` | `paypal/v2_checkout_orders.json` | List orders |
| `/v2/checkout/orders/5O190127TN364715T` | `paypal/v2_checkout_orders_5O190127TN364715T.json` | Order details |
| `/errors/401` | `paypal/errors/401_unauthorized.json` | Unauthorized |

---

### Group 6: Email & Marketing (Mailchimp, SendGrid)
**Priority**: Lower - Specialized use cases

#### Mailchimp Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/3.0/lists` | `mailchimp/3.0_lists.json` | List mailing lists |
| `/3.0/lists/abc123def` | `mailchimp/3.0_lists_abc123def.json` | "Monthly Newsletter" list |
| `/3.0/lists/abc123def/members` | `mailchimp/3.0_lists_abc123def_members.json` | List subscribers |
| `/3.0/campaigns` | `mailchimp/3.0_campaigns.json` | List campaigns |
| `/errors/401` | `mailchimp/errors/401_api_key_invalid.json` | API key invalid |

#### SendGrid Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v3/mail/send` | `sendgrid/v3_mail_send.json` | Send mail response (202 Accepted) |
| `/errors/401` | `sendgrid/errors/401_unauthorized.json` | Unauthorized |

---

### Group 7: Productivity & Knowledge (Notion, Airtable)
**Priority**: Lower - Specialized use cases

#### Notion Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v1/search` | `notion/v1_search.json` | Search results |
| `/v1/pages/abc123` | `notion/v1_pages_abc123.json` | "Project Roadmap" page |
| `/v1/databases/def456/query` | `notion/v1_databases_def456_query.json` | Database query results |
| `/errors/401` | `notion/errors/401_unauthorized.json` | Unauthorized |

#### Airtable Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/v0/meta/bases` | `airtable/v0_meta_bases.json` | List bases |
| `/v0/appXYZ123/Projects` | `airtable/v0_appXYZ123_Projects.json` | Projects table records |
| `/errors/401` | `airtable/errors/401_unauthorized.json` | Unauthorized |

---

### Group 8: E-commerce (Shopify)
**Priority**: Lower - Specialized use cases

#### Shopify Archive Endpoints
| Request Path | File | Description |
|------|------|-------------|
| `/admin/api/2024-01/products.json` | `shopify/admin_api_2024-01_products.json` | List products |
| `/admin/api/2024-01/products/7654321.json` | `shopify/admin_api_2024-01_products_7654321.json` | "Artisanal Widget Deluxe" |
| `/admin/api/2024-01/orders.json` | `shopify/admin_api_2024-01_orders.json` | List orders |
| `/admin/api/2024-01/customers.json` | `shopify/admin_api_2024-01_customers.json` | List customers |
| `/errors/401` | `shopify/errors/401_unauthorized.json` | Unauthorized |

---

## Source CID File Format

Each `.source.cids` file maps request paths to local JSON files. The file extension on the CID determines the MIME type.

```
# github.source.cids
/repos/acme-corp/widgets/issues ../../files/github/repos_acme-corp_widgets_issues.json
/repos/acme-corp/widgets/issues/1 ../../files/github/repos_acme-corp_widgets_issues_1.json
/repos/acme-corp/widgets/issues/2 ../../files/github/repos_acme-corp_widgets_issues_2.json
/rate_limit ../../files/github/rate_limit.json
/errors/401 ../../files/github/errors/401_unauthorized.json
/errors/403 ../../files/github/errors/403_rate_limited.json
/errors/404 ../../files/github/errors/404_not_found.json
```

The `.json` extension on file paths ensures responses are served with `application/json` MIME type.

---

## Resolved Design Decisions

### Path Matching Strategy
**Decision**: Fixed strings with realistic fake names.

Use specific, clearly fake but realistic names:
- Organizations: "Acme Corp", "Widgets Inc", "Globex Corporation"
- People: "Jane Doe", "John Smith", "Dr. Bogus McFakester"
- Domains: "example.com", "acme-corp.example.com"
- IDs: Realistic formats (e.g., `cus_DrBogusMcFakester`, `ACME-42`)

### Request Method Handling
**Decision**: Out of scope - CID archives are static files.

CID archives contain static response data. How different HTTP methods (POST, PUT, DELETE) are handled is the responsibility of the gateway or mock server that consumes these archives.

### Authentication Mocking
**Decision**: Out of scope - CID archives don't validate authentication.

CID archives simply serve static content. Authentication validation would be handled by the consuming gateway or mock server.

### Query Parameter Handling
**Decision**: Fixed paths matching realistic request URLs.

Archive paths should match realistic request URLs against the real server. For example:
- `/repos/acme-corp/widgets/issues` (not `/repos/{owner}/{repo}/issues`)
- `/v1/customers/cus_DrBogusMcFakester` (not `/v1/customers/{id}`)

### Error Response Mocking
**Decision**: Special `/errors/{status_code}` paths.

Each archive includes an `errors/` subdirectory with error responses:
- `/errors/401` - Authentication errors
- `/errors/403` - Authorization/rate limit errors
- `/errors/404` - Not found errors
- Service-specific errors (e.g., Slack's `channel_not_found`)

### Response Headers
**Decision**: Determined by CID file extension.

The `.json` extension on CID file paths ensures `application/json` MIME type. Additional headers would be added by the consuming gateway.

### Versioning
**Decision**: One archive per service.

Start with single archives per service. Add versioning if API changes require different response formats.

### Data Generation
**Decision**: Either hand-crafted or generated is acceptable.

Use clearly fake data with realistic structure. All mock data should use fictional names, emails, and identifiers that are obviously not real.

### Transform Reuse
**Decision**: Yes - archives replace internal server calls.

The same request/response transforms work for both real APIs and CID archives. The CID archive replaces the external API call portion of the internal server.

### Archive Compilation
**Decision**: Already part of CI/CD.

The `.source.cids` files are compiled to `.cids` files (with actual CIDs) as part of the existing CI/CD pipeline.

---

## Test Specifications

### Archive Structure Tests

```gherkin
Scenario: Source CID file exists for each service
  Given the reference/archive/cids/ directory
  Then there should be a .source.cids file for each planned service

Scenario: All referenced files exist
  Given a .source.cids file
  When each line references a file path
  Then that file should exist in reference/files/

Scenario: All JSON files are valid
  Given a JSON file in reference/files/
  When the file is parsed
  Then it should be valid JSON

Scenario: JSON files have correct structure for their API
  Given github/repos_acme-corp_widgets_issues.json
  When validated against GitHub API schema
  Then it should have required fields: url, repository_url, labels_url, etc.
  And each issue should have: id, number, title, state, user
```

### Response Content Tests

```gherkin
Scenario: GitHub issues list has realistic content
  Given github/repos_acme-corp_widgets_issues.json
  Then it should contain multiple issues
  And issues should have realistic titles and bodies
  And user.login values should be fictional names
  And all URLs should reference acme-corp/widgets

Scenario: OpenAI completion has correct structure
  Given openai/v1_chat_completions.json
  Then it should have id starting with "chatcmpl-"
  And object should be "chat.completion"
  And choices array should contain message with role "assistant"
  And usage should have prompt_tokens, completion_tokens, total_tokens

Scenario: Anthropic message has correct structure
  Given anthropic/v1_messages.json
  Then it should have id starting with "msg_"
  And type should be "message"
  And role should be "assistant"
  And content should be array with type "text"
  And stop_reason should be "end_turn"

Scenario: Slack response has ok field
  Given slack/api_chat.postMessage.json
  Then it should have ok: true
  And channel should be a valid channel ID format
  And ts should be a timestamp string

Scenario: Stripe customer has correct structure
  Given stripe/v1_customers_cus_DrBogusMcFakester.json
  Then object should be "customer"
  And id should be "cus_DrBogusMcFakester"
  And email should be a fictional email address
```

### Error Response Tests

```gherkin
Scenario: GitHub 401 error has correct structure
  Given github/errors/401_unauthorized.json
  Then it should have message field
  And documentation_url should be a valid GitHub docs URL

Scenario: GitHub 403 rate limit error has rate limit info
  Given github/errors/403_rate_limited.json
  Then it should have message about rate limit
  And documentation_url should reference rate limiting

Scenario: OpenAI 401 error has correct structure
  Given openai/errors/401_invalid_api_key.json
  Then error.type should be "invalid_api_key" or similar
  And error.message should mention API key

Scenario: Slack error has ok: false
  Given slack/errors/channel_not_found.json
  Then ok should be false
  And error should be "channel_not_found"

Scenario: Stripe 402 error has decline details
  Given stripe/errors/402_card_declined.json
  Then error.type should be "card_error"
  And error.code should indicate decline reason
```

### Data Consistency Tests

```gherkin
Scenario: Cross-references are consistent
  Given github/repos_acme-corp_widgets_issues.json
  When an issue references user.login "janedoe"
  Then that user should appear consistently across all files

Scenario: IDs are consistent within service
  Given stripe/v1_customers.json (list)
  And stripe/v1_customers_cus_DrBogusMcFakester.json (detail)
  Then the customer in the detail file should appear in the list

Scenario: Fictional data is clearly fake
  Given any mock JSON file
  Then email addresses should use example.com or similar
  And company names should be obviously fictional (Acme, Globex)
  And person names should be obviously fake (Jane Doe, Dr. Bogus McFakester)
```

### MIME Type Tests

```gherkin
Scenario: JSON files specify correct MIME type
  Given a .source.cids file
  When a path maps to a .json file
  Then the file extension should cause application/json MIME type

Scenario: All paths map to JSON files for API archives
  Given any API service .source.cids file
  Then all file references should end in .json
```

### Source CID Compilation Tests

```gherkin
Scenario: Source CID files compile without errors
  Given a valid .source.cids file
  When compiled by CI/CD
  Then a corresponding .cids file should be created
  And no compilation errors should occur

Scenario: All file paths in source.cids are valid
  Given a .source.cids file
  Then all relative paths should resolve to existing files
  And paths should use consistent forward slash separators
```

---

## Implementation Phases

### Phase 1: Version Control (Group 1) - GitHub & GitLab
1. Create `reference/files/github/` directory
2. Create mock JSON files for GitHub endpoints
3. Create `reference/archive/cids/github.source.cids`
4. Repeat for GitLab
5. Run tests to validate structure

### Phase 2: AI/LLM Services (Group 2) - OpenAI, Anthropic, Gemini
1. Create mock response files with realistic AI completions
2. Include proper token counts and model identifiers
3. Create source.cids files
4. Run tests

### Phase 3: Communication Platforms (Group 3) - Slack, Discord, Teams, Telegram
1. Create mock responses for each platform
2. Use realistic channel/guild/team names
3. Create source.cids files
4. Run tests

### Phase 4-8: Remaining Groups
Follow same pattern for CRM, Payment, Email, Productivity, E-commerce groups.

---

## Sample Mock Data

### GitHub Issue (repos_acme-corp_widgets_issues_1.json)
```json
{
  "id": 1,
  "node_id": "I_kwDOExample",
  "url": "https://api.github.com/repos/acme-corp/widgets/issues/1",
  "repository_url": "https://api.github.com/repos/acme-corp/widgets",
  "number": 1,
  "title": "Widget fails to spin on Tuesdays",
  "body": "## Description\n\nThe widget refuses to spin when the current day is Tuesday. This affects all widget models manufactured after 2023.\n\n## Steps to Reproduce\n1. Wait until Tuesday\n2. Attempt to spin widget\n3. Observe failure\n\n## Expected Behavior\nWidget should spin regardless of day of week.",
  "state": "open",
  "user": {
    "login": "janedoe",
    "id": 12345,
    "avatar_url": "https://avatars.example.com/janedoe",
    "type": "User"
  },
  "labels": [
    {"id": 1, "name": "bug", "color": "d73a4a"},
    {"id": 2, "name": "priority: high", "color": "ff0000"}
  ],
  "assignee": {
    "login": "johnsmith",
    "id": 67890,
    "type": "User"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-16T14:22:00Z",
  "comments": 3
}
```

### OpenAI Chat Completion (v1_chat_completions.json)
```json
{
  "id": "chatcmpl-abc123def456",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm a simulated response from the OpenAI API. This is mock data for testing purposes. How can I help you today?"
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 28,
    "total_tokens": 40
  },
  "system_fingerprint": "fp_mock123"
}
```

### Anthropic Message (v1_messages.json)
```json
{
  "id": "msg_mock123abc",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! I'm a simulated response from the Anthropic API. This is mock data for testing gateway functionality."
    }
  ],
  "model": "claude-sonnet-4-20250514",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 15,
    "output_tokens": 24
  }
}
```

### Stripe Customer (v1_customers_cus_DrBogusMcFakester.json)
```json
{
  "id": "cus_DrBogusMcFakester",
  "object": "customer",
  "created": 1704067200,
  "email": "bogus@fakester.example.com",
  "name": "Dr. Bogus McFakester",
  "description": "Test customer for mock API responses",
  "phone": "+1-555-FAKE-123",
  "address": {
    "line1": "123 Fictional Street",
    "city": "Faketown",
    "state": "FS",
    "postal_code": "12345",
    "country": "US"
  },
  "currency": "usd",
  "default_source": null,
  "livemode": false,
  "metadata": {
    "test": "true"
  }
}
```

### GitHub 403 Rate Limit Error (errors/403_rate_limited.json)
```json
{
  "message": "API rate limit exceeded for user ID 12345. See https://docs.github.com/rest/overview/rate-limits-for-the-rest-api for more information.",
  "documentation_url": "https://docs.github.com/rest/overview/rate-limits-for-the-rest-api"
}
```

---

## Follow-up Questions

### Q1: Should error paths include the HTTP status code or descriptive name?
Currently proposed: `/errors/401`, `/errors/403`, etc.
Alternative: `/errors/unauthorized`, `/errors/rate_limited`, etc.

**Recommendation**: Use status codes as primary since they're what callers will look up. The file names can include descriptions (e.g., `401_unauthorized.json`).

### Q2: Should we include pagination tokens/links in list responses?
Some APIs (GitHub, Stripe) return pagination info (Link headers, `has_more` fields, next/prev cursors).

**Recommendation**: Include pagination fields in responses to test that consuming code handles them correctly, but with values indicating "end of list" (e.g., `has_more: false`).

### Q3: How should query strings be handled in path matching?
Example: `/services/data/v59.0/query?q=SELECT...`

The source.cids format uses space-separated path and file. Should query strings be:
- Ignored (path only matching)
- Encoded in the path somehow
- Handled by separate mechanism

**Recommendation**: For now, use base paths without query strings. The actual query string handling would be part of the gateway, which is out of scope.

### Q4: Should list endpoints return 1, 2, or more items?
For list responses like `/repos/acme-corp/widgets/issues`, how many items should be included?

**Recommendation**: 2-3 items is sufficient to demonstrate list behavior without excessive file size. Include enough to show variety.

---

## Success Criteria

1. **All .source.cids files exist** for planned services
2. **All referenced JSON files exist** and parse correctly
3. **JSON structure matches** real API response formats
4. **Error responses exist** for common error cases per service
5. **All tests pass** validating structure and content
6. **Data is clearly fictional** (no real emails, companies, etc.)
7. **CI/CD compilation** produces valid .cids files

---

## Next Steps

1. **Resolve follow-up questions** through iteration
2. **Implement Phase 1** (GitHub, GitLab) as proof of concept
3. **Run structure validation tests**
4. **Verify CI/CD compilation** works for new archives
5. **Proceed with remaining phases**
