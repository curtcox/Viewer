# Plan: Mock External Servers via CID Archives

## Overview

Create CID archives that simulate external API servers (GitHub, GitLab, OpenAI, etc.) for testing gateway functionality without requiring real API credentials or network access.

**Pattern**: Use `/gateway/test/cids/{mock-archive-cid}/as/{server}/{rest-of-request}` in place of `/gateway/{server}/{rest-of-request}`

**Reference Implementation**: The existing `jsonplaceholder` mock demonstrates the pattern.

---

## File Structure

```
reference/
├── archive/
│   └── cids/
│       ├── jsonplaceholder.source.cids    # Existing reference
│       │
│       │   # Group 1: Version Control
│       ├── mock-github.source.cids
│       ├── mock-gitlab.source.cids
│       │
│       │   # Group 2: AI/LLM Services
│       ├── mock-openai.source.cids
│       ├── mock-anthropic.source.cids
│       ├── mock-gemini.source.cids
│       │
│       │   # Group 3: Communication Platforms
│       ├── mock-slack.source.cids
│       ├── mock-discord.source.cids
│       ├── mock-teams.source.cids
│       ├── mock-telegram.source.cids
│       │
│       │   # Group 4: CRM Systems
│       ├── mock-hubspot.source.cids
│       ├── mock-salesforce.source.cids
│       ├── mock-jira.source.cids
│       │
│       │   # Group 5: Payment Processing
│       ├── mock-stripe.source.cids
│       ├── mock-paypal.source.cids
│       │
│       │   # Group 6: Email & Marketing
│       ├── mock-mailchimp.source.cids
│       ├── mock-sendgrid.source.cids
│       │
│       │   # Group 7: Productivity & Knowledge
│       ├── mock-notion.source.cids
│       ├── mock-airtable.source.cids
│       │
│       │   # Group 8: E-commerce
│       └── mock-shopify.source.cids
│
└── files/
    ├── jsonplaceholder_*.json              # Existing reference
    │
    │   # Group 1: Version Control
    ├── github/
    │   ├── repos_owner_repo_issues.json
    │   ├── repos_owner_repo_issues_1.json
    │   ├── repos_owner_repo_issues_2.json
    │   └── rate_limit.json
    ├── gitlab/
    │   ├── api_v4_projects.json
    │   ├── api_v4_projects_1.json
    │   ├── api_v4_projects_1_issues.json
    │   ├── api_v4_projects_1_issues_1.json
    │   └── api_v4_projects_1_merge_requests.json
    │
    │   # Group 2: AI/LLM Services
    ├── openai/
    │   ├── v1_chat_completions.json
    │   └── v1_models.json
    ├── anthropic/
    │   └── v1_messages.json
    ├── gemini/
    │   └── v1beta_models_gemini_generateContent.json
    │
    │   # Group 3: Communication Platforms
    ├── slack/
    │   ├── api_chat_postMessage.json
    │   └── api_conversations_list.json
    ├── discord/
    │   ├── users_@me_guilds.json
    │   ├── guilds_123.json
    │   ├── guilds_123_channels.json
    │   └── channels_456_messages.json
    ├── teams/
    │   ├── me_joinedTeams.json
    │   ├── teams_123.json
    │   ├── teams_123_channels.json
    │   └── teams_123_channels_456_messages.json
    │
    │   # Group 4: CRM Systems
    ├── hubspot/
    │   ├── crm_v3_objects_contacts.json
    │   ├── crm_v3_objects_contacts_1.json
    │   ├── crm_v3_objects_companies.json
    │   └── crm_v3_objects_companies_1.json
    ├── salesforce/
    │   ├── services_data_v59_query_accounts.json
    │   ├── services_data_v59_sobjects_Account_001.json
    │   └── services_data_v59_sobjects_Contact_003.json
    ├── jira/
    │   ├── rest_api_3_project.json
    │   ├── rest_api_3_project_PROJ.json
    │   ├── rest_api_3_search.json
    │   └── rest_api_3_issue_PROJ-1.json
    │
    │   # Group 5: Payment Processing
    ├── stripe/
    │   ├── v1_customers.json
    │   ├── v1_customers_cus_123.json
    │   ├── v1_charges.json
    │   └── v1_charges_ch_123.json
    ├── paypal/
    │   ├── v2_checkout_orders.json
    │   └── v2_checkout_orders_123.json
    │
    │   # Group 6: Email & Marketing
    ├── mailchimp/
    │   ├── 3.0_lists.json
    │   ├── 3.0_lists_abc123.json
    │   ├── 3.0_lists_abc123_members.json
    │   └── 3.0_campaigns.json
    ├── sendgrid/
    │   └── v3_mail_send.json
    │
    │   # Group 7: Productivity & Knowledge
    ├── notion/
    │   ├── v1_search.json
    │   ├── v1_pages_abc123.json
    │   └── v1_databases_def456_query.json
    ├── airtable/
    │   ├── v0_meta_bases.json
    │   └── v0_app123_Table1.json
    │
    │   # Group 8: E-commerce
    └── shopify/
        ├── admin_api_2024-01_products.json
        ├── admin_api_2024-01_products_123.json
        ├── admin_api_2024-01_orders.json
        └── admin_api_2024-01_customers.json
```

---

## Server Groups (Independent Chunks)

### Group 1: Version Control (GitHub, GitLab)
**Priority**: High - Most commonly used for issue tracking

#### GitHub Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/repos/{owner}/{repo}/issues` | `github/repos_owner_repo_issues.json` | List issues |
| `/repos/{owner}/{repo}/issues/1` | `github/repos_owner_repo_issues_1.json` | Get issue #1 |
| `/repos/{owner}/{repo}/issues/2` | `github/repos_owner_repo_issues_2.json` | Get issue #2 |
| `/rate_limit` | `github/rate_limit.json` | API rate limit status |

#### GitLab Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/api/v4/projects` | `gitlab/api_v4_projects.json` | List projects |
| `/api/v4/projects/1` | `gitlab/api_v4_projects_1.json` | Get project |
| `/api/v4/projects/1/issues` | `gitlab/api_v4_projects_1_issues.json` | List project issues |
| `/api/v4/projects/1/issues/1` | `gitlab/api_v4_projects_1_issues_1.json` | Get issue |
| `/api/v4/projects/1/merge_requests` | `gitlab/api_v4_projects_1_merge_requests.json` | List MRs |

---

### Group 2: AI/LLM Services (OpenAI, Anthropic, Gemini)
**Priority**: High - Core AI functionality

#### OpenAI Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v1/chat/completions` | `openai/v1_chat_completions.json` | Chat completion response |
| `/v1/models` | `openai/v1_models.json` | List available models |

#### Anthropic Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v1/messages` | `anthropic/v1_messages.json` | Message response |

#### Google Gemini Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v1beta/models/gemini-1.5-flash-latest:generateContent` | `gemini/v1beta_models_gemini_generateContent.json` | Generate content |

---

### Group 3: Communication Platforms (Slack, Discord, Teams, Telegram)
**Priority**: Medium - Collaboration integrations

#### Slack Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/api/chat.postMessage` | `slack/api_chat_postMessage.json` | Post message response |
| `/api/conversations.list` | `slack/api_conversations_list.json` | List channels |

#### Discord Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/users/@me/guilds` | `discord/users_@me_guilds.json` | List user guilds |
| `/guilds/123` | `discord/guilds_123.json` | Get guild |
| `/guilds/123/channels` | `discord/guilds_123_channels.json` | List guild channels |
| `/channels/456/messages` | `discord/channels_456_messages.json` | List channel messages |

#### Microsoft Teams Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/me/joinedTeams` | `teams/me_joinedTeams.json` | List joined teams |
| `/teams/123` | `teams/teams_123.json` | Get team |
| `/teams/123/channels` | `teams/teams_123_channels.json` | List team channels |
| `/teams/123/channels/456/messages` | `teams/teams_123_channels_456_messages.json` | List messages |

#### Telegram Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/bot{token}/getUpdates` | `telegram/getUpdates.json` | Get bot updates |
| `/bot{token}/sendMessage` | `telegram/sendMessage.json` | Send message response |

---

### Group 4: CRM Systems (HubSpot, Salesforce, Jira)
**Priority**: Medium - Business integrations

#### HubSpot Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/crm/v3/objects/contacts` | `hubspot/crm_v3_objects_contacts.json` | List contacts |
| `/crm/v3/objects/contacts/1` | `hubspot/crm_v3_objects_contacts_1.json` | Get contact |
| `/crm/v3/objects/companies` | `hubspot/crm_v3_objects_companies.json` | List companies |
| `/crm/v3/objects/companies/1` | `hubspot/crm_v3_objects_companies_1.json` | Get company |

#### Salesforce Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/services/data/v59.0/query?q=SELECT...` | `salesforce/services_data_v59_query_accounts.json` | SOQL query |
| `/services/data/v59.0/sobjects/Account/001` | `salesforce/services_data_v59_sobjects_Account_001.json` | Get account |
| `/services/data/v59.0/sobjects/Contact/003` | `salesforce/services_data_v59_sobjects_Contact_003.json` | Get contact |

#### Jira Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/rest/api/3/project` | `jira/rest_api_3_project.json` | List projects |
| `/rest/api/3/project/PROJ` | `jira/rest_api_3_project_PROJ.json` | Get project |
| `/rest/api/3/search?jql=...` | `jira/rest_api_3_search.json` | JQL search |
| `/rest/api/3/issue/PROJ-1` | `jira/rest_api_3_issue_PROJ-1.json` | Get issue |

---

### Group 5: Payment Processing (Stripe, PayPal)
**Priority**: Low - Specialized use cases

#### Stripe Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v1/customers` | `stripe/v1_customers.json` | List customers |
| `/v1/customers/cus_123` | `stripe/v1_customers_cus_123.json` | Get customer |
| `/v1/charges` | `stripe/v1_charges.json` | List charges |
| `/v1/charges/ch_123` | `stripe/v1_charges_ch_123.json` | Get charge |

#### PayPal Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v2/checkout/orders` | `paypal/v2_checkout_orders.json` | List orders |
| `/v2/checkout/orders/123` | `paypal/v2_checkout_orders_123.json` | Get order |

---

### Group 6: Email & Marketing (Mailchimp, SendGrid)
**Priority**: Low - Specialized use cases

#### Mailchimp Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/3.0/lists` | `mailchimp/3.0_lists.json` | List mailing lists |
| `/3.0/lists/abc123` | `mailchimp/3.0_lists_abc123.json` | Get list |
| `/3.0/lists/abc123/members` | `mailchimp/3.0_lists_abc123_members.json` | List members |
| `/3.0/campaigns` | `mailchimp/3.0_campaigns.json` | List campaigns |

#### SendGrid Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v3/mail/send` | `sendgrid/v3_mail_send.json` | Send mail response |

---

### Group 7: Productivity & Knowledge (Notion, Airtable)
**Priority**: Low - Specialized use cases

#### Notion Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v1/search` | `notion/v1_search.json` | Search results |
| `/v1/pages/abc123` | `notion/v1_pages_abc123.json` | Get page |
| `/v1/databases/def456/query` | `notion/v1_databases_def456_query.json` | Query database |

#### Airtable Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/v0/meta/bases` | `airtable/v0_meta_bases.json` | List bases |
| `/v0/app123/Table1` | `airtable/v0_app123_Table1.json` | List table records |

---

### Group 8: E-commerce (Shopify)
**Priority**: Low - Specialized use cases

#### Shopify Mock Endpoints
| Path | File | Description |
|------|------|-------------|
| `/admin/api/2024-01/products.json` | `shopify/admin_api_2024-01_products.json` | List products |
| `/admin/api/2024-01/products/123.json` | `shopify/admin_api_2024-01_products_123.json` | Get product |
| `/admin/api/2024-01/orders.json` | `shopify/admin_api_2024-01_orders.json` | List orders |
| `/admin/api/2024-01/customers.json` | `shopify/admin_api_2024-01_customers.json` | List customers |

---

## Source CID File Format

Each `.source.cids` file maps API paths to local JSON files:

```
# mock-github.source.cids
/repos/owner/repo/issues ../../files/github/repos_owner_repo_issues.json
/repos/owner/repo/issues/1 ../../files/github/repos_owner_repo_issues_1.json
/repos/owner/repo/issues/2 ../../files/github/repos_owner_repo_issues_2.json
/rate_limit ../../files/github/rate_limit.json
```

---

## Implementation Phases

### Phase 1: Version Control (Group 1)
1. Create `reference/files/github/` directory with mock JSON files
2. Create `reference/archive/cids/mock-github.source.cids`
3. Create gateway configuration for github with transforms
4. Write integration tests
5. Repeat for GitLab

### Phase 2: AI/LLM Services (Group 2)
1. Create mock response files for OpenAI, Anthropic, Gemini
2. Create source.cids files
3. Configure gateways with transforms
4. Write integration tests

### Phase 3: Communication Platforms (Group 3)
1. Create mock response files for Slack, Discord, Teams, Telegram
2. Create source.cids files
3. Configure gateways with transforms
4. Write integration tests

### Phase 4-8: Remaining Groups
Follow same pattern for CRM, Payment, Email, Productivity, E-commerce groups.

---

## Test Specifications

### Unit Tests (`tests/unit/test_mock_archives.py`)

#### Source CID Parsing Tests
```gherkin
Scenario: Parse source.cids file correctly
  Given a source.cids file with path mappings
  When the file is parsed
  Then each line should map a path to a file reference

Scenario: Handle empty lines in source.cids
  Given a source.cids file with empty lines and comments
  When the file is parsed
  Then empty lines and comments should be ignored

Scenario: Handle relative paths in source.cids
  Given a source.cids file with relative file paths
  When the file is resolved
  Then paths should be relative to the cids directory
```

#### JSON Mock File Tests
```gherkin
Scenario: Mock files contain valid JSON
  Given a mock JSON file for GitHub issues
  When the file is read
  Then it should parse as valid JSON

Scenario: Mock files match expected API response structure
  Given a mock JSON file for GitHub issues
  When the structure is validated
  Then it should contain expected fields (id, title, state, user, etc.)
```

---

### Integration Tests (`tests/integration/test_mock_servers.py`)

#### Gateway Routing Tests

```gherkin
Scenario: Route GitHub mock via CID archive
  Given a CID archive for mock-github
  And a gateway configured for github
  When I request /gateway/test/cids/{mock-github-cid}/as/github/repos/owner/repo/issues
  Then I should receive the mock issues list
  And the Content-Type should be application/json

Scenario: Route GitHub issue detail via CID archive
  Given a CID archive for mock-github
  When I request /gateway/test/cids/{mock-github-cid}/as/github/repos/owner/repo/issues/1
  Then I should receive issue #1 details
  And the response should contain id, title, body, state

Scenario: Handle 404 for unmapped paths
  Given a CID archive for mock-github
  When I request /gateway/test/cids/{mock-github-cid}/as/github/repos/owner/repo/issues/999
  Then I should receive a 404 response
```

#### Response Transform Tests

```gherkin
Scenario: GitHub response transform adds navigation links
  Given a CID archive for mock-github
  When I request /gateway/test/cids/{mock-github-cid}/as/github/repos/owner/repo/issues
  And the response is HTML
  Then issue IDs should be clickable links to issue detail pages
  And user references should be clickable links

Scenario: OpenAI response transform formats chat completion
  Given a CID archive for mock-openai
  When I request /gateway/test/cids/{mock-openai-cid}/as/openai/v1/chat/completions
  Then the response should contain the assistant message content
  And usage statistics should be displayed
```

#### Link Rewriting Tests

```gherkin
Scenario: Internal links rewrite to maintain test context
  Given a CID archive for mock-github
  When viewing issues list at /gateway/test/cids/{cid}/as/github/repos/owner/repo/issues
  And clicking on an issue link
  Then the link should be /gateway/test/cids/{cid}/as/github/repos/owner/repo/issues/1
  Not /gateway/github/repos/owner/repo/issues/1

Scenario: Cross-resource links rewrite correctly
  Given a CID archive for mock-github
  When viewing an issue that references a user
  Then the user link should stay within the test context
```

---

### AI/LLM Service Tests (`tests/integration/test_mock_ai_services.py`)

```gherkin
Scenario: OpenAI chat completion mock returns expected structure
  Given a CID archive for mock-openai
  When I request /gateway/test/cids/{cid}/as/openai/v1/chat/completions
  Then the response should have structure:
    | Field | Type |
    | id | string starting with "chatcmpl-" |
    | object | "chat.completion" |
    | created | integer timestamp |
    | model | string |
    | choices | array with message objects |
    | usage | object with token counts |

Scenario: Anthropic message mock returns expected structure
  Given a CID archive for mock-anthropic
  When I request /gateway/test/cids/{cid}/as/anthropic/v1/messages
  Then the response should have structure:
    | Field | Type |
    | id | string starting with "msg_" |
    | type | "message" |
    | role | "assistant" |
    | content | array with text blocks |
    | model | string |
    | stop_reason | string |
    | usage | object with token counts |

Scenario: Gemini generate content mock returns expected structure
  Given a CID archive for mock-gemini
  When I request /gateway/test/cids/{cid}/as/gemini/v1beta/models/gemini-1.5-flash-latest:generateContent
  Then the response should have structure:
    | Field | Type |
    | candidates | array |
    | candidates[0].content.parts | array with text parts |
    | usageMetadata | object |
```

---

### Communication Platform Tests (`tests/integration/test_mock_communication.py`)

```gherkin
Scenario: Slack mock returns channel list
  Given a CID archive for mock-slack
  When I request /gateway/test/cids/{cid}/as/slack/api/conversations.list
  Then the response should have ok: true
  And channels should be an array of channel objects

Scenario: Discord mock returns guild list
  Given a CID archive for mock-discord
  When I request /gateway/test/cids/{cid}/as/discord/users/@me/guilds
  Then the response should be an array of guild objects
  And each guild should have id, name, icon fields

Scenario: Teams mock returns joined teams
  Given a CID archive for mock-teams
  When I request /gateway/test/cids/{cid}/as/teams/me/joinedTeams
  Then the response should have value array of team objects
  And each team should have id, displayName fields
```

---

### CRM Tests (`tests/integration/test_mock_crm.py`)

```gherkin
Scenario: HubSpot mock returns contacts list
  Given a CID archive for mock-hubspot
  When I request /gateway/test/cids/{cid}/as/hubspot/crm/v3/objects/contacts
  Then the response should have results array
  And each contact should have id, properties fields

Scenario: Salesforce mock returns SOQL query results
  Given a CID archive for mock-salesforce
  When I request /gateway/test/cids/{cid}/as/salesforce/services/data/v59.0/query
  With query parameter q=SELECT Id, Name FROM Account
  Then the response should have records array
  And totalSize should be an integer

Scenario: Jira mock returns issue details
  Given a CID archive for mock-jira
  When I request /gateway/test/cids/{cid}/as/jira/rest/api/3/issue/PROJ-1
  Then the response should have key, fields
  And fields should contain summary, description, status
```

---

### Payment Tests (`tests/integration/test_mock_payment.py`)

```gherkin
Scenario: Stripe mock returns customers list
  Given a CID archive for mock-stripe
  When I request /gateway/test/cids/{cid}/as/stripe/v1/customers
  Then the response should have object: "list"
  And data should be an array of customer objects
  And has_more should be a boolean

Scenario: Stripe mock returns individual customer
  Given a CID archive for mock-stripe
  When I request /gateway/test/cids/{cid}/as/stripe/v1/customers/cus_123
  Then the response should have object: "customer"
  And id should match the requested customer ID
```

---

### Error Handling Tests (`tests/integration/test_mock_errors.py`)

```gherkin
Scenario: Return 404 for unmapped endpoint
  Given a CID archive for mock-github
  When I request /gateway/test/cids/{cid}/as/github/nonexistent/path
  Then I should receive a 404 Not Found response

Scenario: Return 405 for unsupported HTTP method
  Given a CID archive configured for GET only
  When I POST to /gateway/test/cids/{cid}/as/github/repos/owner/repo/issues
  Then I should receive a 405 Method Not Allowed response

Scenario: Handle malformed CID gracefully
  When I request /gateway/test/cids/invalid-cid/as/github/repos/owner/repo/issues
  Then I should receive an appropriate error response
  And the error message should indicate invalid CID

Scenario: Handle missing archive gracefully
  When I request /gateway/test/cids/nonexistent-cid/as/github/repos/owner/repo/issues
  Then I should receive a 404 response
  And the error message should indicate archive not found
```

---

### Pagination Tests (`tests/integration/test_mock_pagination.py`)

```gherkin
Scenario: Mock supports per_page parameter
  Given a CID archive for mock-github with multiple issues
  When I request /gateway/test/cids/{cid}/as/github/repos/owner/repo/issues?per_page=1
  Then I should receive exactly 1 issue
  And Link header should indicate more pages

Scenario: Mock supports page parameter
  Given a CID archive for mock-github with paginated responses
  When I request /gateway/test/cids/{cid}/as/github/repos/owner/repo/issues?page=2
  Then I should receive the second page of issues
```

---

### Content-Type Tests (`tests/integration/test_mock_content_types.py`)

```gherkin
Scenario: Return JSON with correct Content-Type
  Given a CID archive for mock-github
  When I request /gateway/test/cids/{cid}/as/github/repos/owner/repo/issues
  With Accept: application/json header
  Then Content-Type should be application/json

Scenario: Return HTML when transforms render HTML
  Given a CID archive for mock-github
  When I request via browser (Accept: text/html)
  Then the response may be rendered as HTML with navigation
```

---

## Additional Paths Needed

### Gateway Configuration Paths
```
reference/templates/gateways.json         # Add mock server gateway configs
reference/templates/gateways/transforms/
  ├── github_request.py                   # Request transform for GitHub
  ├── github_response.py                  # Response transform for GitHub
  ├── gitlab_request.py
  ├── gitlab_response.py
  ├── openai_request.py
  ├── openai_response.py
  ├── anthropic_request.py
  ├── anthropic_response.py
  ... (one pair per external server)
```

### Test Paths
```
tests/
├── integration/
│   ├── test_mock_servers.py              # General mock server tests
│   ├── test_mock_github.py               # GitHub-specific tests
│   ├── test_mock_gitlab.py               # GitLab-specific tests
│   ├── test_mock_ai_services.py          # OpenAI/Anthropic/Gemini tests
│   ├── test_mock_communication.py        # Slack/Discord/Teams tests
│   ├── test_mock_crm.py                  # HubSpot/Salesforce/Jira tests
│   ├── test_mock_payment.py              # Stripe/PayPal tests
│   └── test_mock_errors.py               # Error handling tests
└── fixtures/
    └── mock_cids/                        # Pre-compiled test CIDs
```

### Spec Paths
```
specs/
├── mock_servers.spec                     # Cucumber specs for mock servers
├── mock_github.spec                      # GitHub-specific specs
├── mock_ai.spec                          # AI services specs
└── mock_communication.spec               # Communication platform specs
```

---

## Open Questions

### Q1: Path Matching Strategy
**Question**: How should dynamic path segments (e.g., `{owner}`, `{repo}`, `{issue_number}`) be handled in CID archives?

**Options**:
1. **Fixed placeholders**: Use literal strings like `/repos/owner/repo/issues` - simple but inflexible
2. **Pattern matching**: Support glob patterns like `/repos/*/*/issues` - flexible but more complex
3. **Multiple entries**: Create entries for common scenarios (`/repos/octocat/hello-world/issues`)

**Current thinking**: Start with fixed placeholders (option 1) for simplicity, with clear mock owner/repo names like "mock-owner/mock-repo".

---

### Q2: POST/PUT Request Handling
**Question**: CID archives are read-only. How should mock servers handle POST/PUT/DELETE requests?

**Options**:
1. **Return static success response**: Always return a successful creation/update response
2. **Echo back input**: Return the posted data as if it was created
3. **Separate endpoints**: Have `/issues` for GET and `/issues/create` for POST mock response
4. **Reject mutations**: Return 405 Method Not Allowed for non-GET requests

**Current thinking**: Option 1 or 2 - return static success responses that look realistic.

---

### Q3: Authentication Mocking
**Question**: Should mock servers validate authentication headers, or ignore them entirely?

**Options**:
1. **Ignore auth**: Accept any request regardless of headers
2. **Require header presence**: Check that Authorization header exists (any value)
3. **Mock auth errors**: Support a "mock-invalid-token" that returns 401

**Current thinking**: Option 1 for simplicity in testing. Auth validation is the real server's job.

---

### Q4: Query Parameter Handling
**Question**: How should query parameters (filtering, pagination) be handled?

**Options**:
1. **Ignore all params**: Return same response regardless of query string
2. **Key-based routing**: Different files for `?state=open` vs `?state=closed`
3. **Client-side filtering**: Return all data, let transforms filter

**Current thinking**: Start with option 1, add option 2 for critical params like pagination.

---

### Q5: Error Response Mocking
**Question**: How should we mock API error responses (rate limits, auth failures, etc.)?

**Options**:
1. **Separate error archives**: Create `mock-github-errors.source.cids` with error responses
2. **Special paths**: Use paths like `/errors/401` or `/errors/rate_limit`
3. **Header-triggered**: Return errors based on special request headers

**Current thinking**: Option 2 - special paths for common error scenarios.

---

### Q6: Response Headers
**Question**: Should mock responses include realistic headers (rate limit info, pagination links)?

**Options**:
1. **Minimal headers**: Only Content-Type
2. **Common headers**: Add X-RateLimit-*, Link for pagination, ETag
3. **Full headers**: Replicate all headers from real API

**Current thinking**: Option 2 - include headers that tests might depend on.

---

### Q7: Versioning Mock Data
**Question**: How should mock data be versioned when APIs change?

**Options**:
1. **Single version**: One mock per service, update as needed
2. **Version directories**: `github/v3/`, `github/v4/` for different API versions
3. **Date-based**: `github/2024-01/` for point-in-time snapshots

**Current thinking**: Start with option 1, add versioning if API changes require it.

---

### Q8: Realistic Data Generation
**Question**: Should mock data be hand-crafted or generated?

**Options**:
1. **Hand-crafted**: Manually create representative sample data
2. **Generated**: Use scripts to generate realistic-looking data
3. **Captured**: Record real API responses and sanitize them

**Current thinking**: Option 1 for core data, with clear fake data (e.g., "Mock User", "mock@example.com").

---

### Q9: Transform Reuse
**Question**: Can we reuse transforms between mock and real servers?

**Answer**: Yes - the same request/response transforms should work for both mock and real servers. The mock CID archive just replaces the external API call.

---

### Q10: Archive Compilation
**Question**: Should `.source.cids` files be compiled to `.cids` (with actual CIDs) as part of the build?

**Options**:
1. **Manual compilation**: Run script to compile when files change
2. **Automatic**: Compile as part of CI/CD or build process
3. **On-demand**: Compile when first accessed

**Current thinking**: Option 1 initially, move to option 2 for CI/CD.

---

## Success Criteria

1. **All mock archives compile successfully** to valid CID files
2. **All tests pass** with 100% coverage of mock endpoints
3. **Gateway routing works** for `/gateway/test/cids/{cid}/as/{server}/{path}` pattern
4. **Response transforms** produce correct HTML/JSON output
5. **Link rewriting** maintains test context for all internal links
6. **Error handling** is graceful and informative
7. **Documentation** explains how to use mock servers for testing

---

## Next Steps

1. Answer open questions through iteration
2. Implement Group 1 (GitHub, GitLab) as proof of concept
3. Write integration tests for Group 1
4. Validate pattern works end-to-end
5. Proceed with remaining groups

---

## Appendix: Sample Mock Data Formats

### GitHub Issue (reference)
```json
{
  "id": 1,
  "number": 1,
  "title": "Mock Issue Title",
  "body": "This is a mock issue body for testing.",
  "state": "open",
  "user": {
    "login": "mock-user",
    "id": 1,
    "avatar_url": "https://example.com/avatar.png"
  },
  "labels": [
    {"id": 1, "name": "bug", "color": "d73a4a"}
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### OpenAI Chat Completion (reference)
```json
{
  "id": "chatcmpl-mock123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This is a mock response from the OpenAI API."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

### Anthropic Message (reference)
```json
{
  "id": "msg_mock123",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "This is a mock response from the Anthropic API."
    }
  ],
  "model": "claude-sonnet-4-20250514",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 15
  }
}
```
