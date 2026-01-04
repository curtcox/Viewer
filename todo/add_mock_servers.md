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
│       │   # Group 1: Version Control & Dev Tools (4 servers)
│       ├── github.source.cids
│       ├── gitlab.source.cids
│       ├── jira.source.cids
│       ├── confluence.source.cids
│       │
│       │   # Group 2: AI/LLM Services (7 servers)
│       ├── openai.source.cids
│       ├── anthropic.source.cids
│       ├── gemini.source.cids
│       ├── openrouter.source.cids
│       ├── nvidia_nim.source.cids
│       ├── ai_assist.source.cids
│       │
│       │   # Group 3: Communication Platforms (5 servers)
│       ├── slack.source.cids
│       ├── discord.source.cids
│       ├── teams.source.cids
│       ├── telegram.source.cids
│       ├── whatsapp.source.cids
│       │
│       │   # Group 4: CRM Systems (8 servers)
│       ├── hubspot.source.cids
│       ├── salesforce.source.cids
│       ├── pipedrive.source.cids
│       ├── close_crm.source.cids
│       ├── activecampaign.source.cids
│       ├── insightly.source.cids
│       ├── gorgias.source.cids
│       ├── zoho_crm.source.cids
│       │
│       │   # Group 5: Payment & Finance (5 servers)
│       ├── stripe.source.cids
│       ├── paypal.source.cids
│       ├── quickbooks.source.cids
│       ├── xero.source.cids
│       ├── freshbooks.source.cids
│       │
│       │   # Group 6: Email & Marketing (10 servers)
│       ├── sendgrid.source.cids
│       ├── mailchimp.source.cids
│       ├── postmark.source.cids
│       ├── mailgun.source.cids
│       ├── mailerlite.source.cids
│       ├── klaviyo.source.cids
│       ├── amplitude.source.cids
│       ├── segment.source.cids
│       ├── mixpanel.source.cids
│       ├── typeform.source.cids
│       │
│       │   # Group 7: Project Management & Productivity (9 servers)
│       ├── notion.source.cids
│       ├── airtable.source.cids
│       ├── asana.source.cids
│       ├── trello.source.cids
│       ├── monday.source.cids
│       ├── todoist.source.cids
│       ├── clickup.source.cids
│       ├── coda.source.cids
│       ├── basecamp.source.cids
│       │
│       │   # Group 8: E-commerce (7 servers)
│       ├── shopify.source.cids
│       ├── woocommerce.source.cids
│       ├── ebay.source.cids
│       ├── etsy.source.cids
│       ├── squarespace.source.cids
│       ├── wix.source.cids
│       │
│       │   # Group 9: Google Workspace (10 servers)
│       ├── google_sheets.source.cids
│       ├── google_docs.source.cids
│       ├── google_drive.source.cids
│       ├── google_calendar.source.cids
│       ├── gmail.source.cids
│       ├── google_contacts.source.cids
│       ├── google_forms.source.cids
│       ├── google_ads.source.cids
│       ├── google_analytics.source.cids
│       ├── youtube.source.cids
│       │
│       │   # Group 10: Microsoft Services (5 servers)
│       ├── onedrive.source.cids
│       ├── microsoft_outlook.source.cids
│       ├── microsoft_excel.source.cids
│       ├── dynamics365.source.cids
│       │
│       │   # Group 11: Cloud Storage (5 servers)
│       ├── dropbox.source.cids
│       ├── box.source.cids
│       ├── aws_s3.source.cids
│       ├── azure_blob.source.cids
│       ├── gcs.source.cids
│       │
│       │   # Group 12: Support & Ticketing (4 servers)
│       ├── zendesk.source.cids
│       ├── freshdesk.source.cids
│       ├── helpscout.source.cids
│       ├── intercom.source.cids
│       │
│       │   # Group 13: Document & File Services (5 servers)
│       ├── docusign.source.cids
│       ├── docparser.source.cids
│       ├── pdfco.source.cids
│       ├── cloudconvert.source.cids
│       ├── pandadoc.source.cids
│       │
│       │   # Group 14: Content & Design (5 servers)
│       ├── wordpress.source.cids
│       ├── webflow.source.cids
│       ├── figma.source.cids
│       ├── calendly.source.cids
│       ├── miro.source.cids
│       │
│       │   # Group 15: Video & Meetings (2 servers)
│       ├── zoom.source.cids
│       │
│       │   # Group 16: Data Services & Enrichment (6 servers)
│       ├── hunter.source.cids
│       ├── clearbit.source.cids
│       ├── bitly.source.cids
│       ├── apify.source.cids
│       ├── parseur.source.cids
│       ├── jotform.source.cids
│       │
│       │   # Group 17: Advertising (2 servers)
│       ├── linkedin_ads.source.cids
│       ├── meta_ads.source.cids
│       │
│       │   # Group 18: Database Services (3 servers)
│       ├── bigquery.source.cids
│       ├── snowflake.source.cids
│       ├── mongodb.source.cids
│       │
│       │   # Group 19: Business & Operations (4 servers)
│       ├── servicenow.source.cids
│       ├── uptimerobot.source.cids
│       ├── front.source.cids
│       ├── twilio.source.cids
│       │
│       │   # Group 20: Generic/Utility
│       └── proxy.source.cids
│
└── files/
    │   # Organized by service - see detailed structure below
    ├── github/
    ├── gitlab/
    ├── jira/
    ... (93 service directories)
```

---

## Complete Server List (93 External APIs)

### Group 1: Version Control & Dev Tools (4 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| github | `https://api.github.com` | list_issues, get_issue, create_issue |
| gitlab | `https://gitlab.com/api/v4` | list_projects, list_issues, list_merge_requests |
| jira | `https://{domain}/rest/api/3` | list_projects, search, get_issue, create_issue |
| confluence | `https://{domain}/wiki/rest/api` | get_page, search, create_page |

### Group 2: AI/LLM Services (7 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| openai | `https://api.openai.com` | chat/completions, models |
| anthropic | `https://api.anthropic.com` | messages |
| gemini | `https://generativelanguage.googleapis.com` | generateContent |
| openrouter | `https://openrouter.ai/api/v1` | chat/completions |
| nvidia_nim | `https://integrate.api.nvidia.com` | chat/completions |
| ai_assist | `https://openrouter.ai/api/v1` | chat/completions |
| jsonplaceholder | `https://jsonplaceholder.typicode.com` | posts, users, comments (test API) |

### Group 3: Communication Platforms (5 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| slack | `https://slack.com/api` | chat.postMessage, conversations.list |
| discord | `https://discord.com/api/v10` | guilds, channels, messages |
| teams | `https://graph.microsoft.com/v1.0` | joinedTeams, channels, messages |
| telegram | `https://api.telegram.org` | getUpdates, sendMessage |
| whatsapp | `https://graph.facebook.com/v18.0` | messages |

### Group 4: CRM Systems (8 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| hubspot | `https://api.hubapi.com` | contacts, companies, deals |
| salesforce | `https://{instance}.salesforce.com` | query, sobjects |
| pipedrive | `https://api.pipedrive.com/v1` | deals, persons, organizations |
| close_crm | `https://api.close.com/api/v1` | leads, contacts, opportunities |
| activecampaign | `https://{account}.api-us1.com` | contacts, deals, lists |
| insightly | `https://api.insightly.com/v3.1` | contacts, opportunities, projects |
| gorgias | `https://{domain}.gorgias.com/api` | tickets, customers |
| zoho_crm | `https://www.zohoapis.com/crm/v3` | Leads, Contacts, Deals |

### Group 5: Payment & Finance (5 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| stripe | `https://api.stripe.com/v1` | customers, charges, subscriptions |
| paypal | `https://api-m.paypal.com` | orders, payments |
| quickbooks | `https://quickbooks.api.intuit.com` | invoices, customers, items |
| xero | `https://api.xero.com/api.xro/2.0` | Invoices, Contacts, Accounts |
| freshbooks | `https://api.freshbooks.com` | clients, invoices, expenses |

### Group 6: Email & Marketing (10 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| sendgrid | `https://api.sendgrid.com/v3` | mail/send, contacts |
| mailchimp | `https://{dc}.api.mailchimp.com/3.0` | lists, members, campaigns |
| postmark | `https://api.postmarkapp.com` | email, templates |
| mailgun | `https://api.mailgun.net/v3` | messages, domains |
| mailerlite | `https://connect.mailerlite.com/api` | subscribers, campaigns |
| klaviyo | `https://a.klaviyo.com/api` | profiles, lists, campaigns |
| amplitude | `https://api2.amplitude.com` | events, identify |
| segment | `https://api.segment.io/v1` | track, identify |
| mixpanel | `https://api.mixpanel.com` | track, engage |
| typeform | `https://api.typeform.com` | forms, responses |

### Group 7: Project Management & Productivity (9 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| notion | `https://api.notion.com/v1` | search, pages, databases |
| airtable | `https://api.airtable.com/v0` | bases, records |
| asana | `https://app.asana.com/api/1.0` | tasks, projects, workspaces |
| trello | `https://api.trello.com/1` | boards, lists, cards |
| monday | `https://api.monday.com/v2` | boards, items (GraphQL) |
| todoist | `https://api.todoist.com/rest/v2` | tasks, projects |
| clickup | `https://api.clickup.com/api/v2` | tasks, lists, spaces |
| coda | `https://coda.io/apis/v1` | docs, tables, rows |
| basecamp | `https://3.basecampapi.com` | projects, todos, messages |

### Group 8: E-commerce (7 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| shopify | `https://{store}/admin/api/2024-01` | products, orders, customers |
| woocommerce | `{store}/wp-json/wc/v3` | products, orders, customers |
| ebay | `https://api.ebay.com` | browse, sell |
| etsy | `https://openapi.etsy.com/v3` | listings, shops, receipts |
| squarespace | `https://api.squarespace.com/1.0` | orders, products, inventory |
| wix | `https://www.wixapis.com` | stores, products, orders |

### Group 9: Google Workspace (10 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| google_sheets | `https://sheets.googleapis.com/v4` | values, spreadsheets |
| google_docs | `https://docs.googleapis.com/v1` | documents |
| google_drive | `https://www.googleapis.com/drive/v3` | files, permissions |
| google_calendar | `https://www.googleapis.com/calendar/v3` | events, calendars |
| gmail | `https://gmail.googleapis.com/gmail/v1` | messages, labels |
| google_contacts | `https://people.googleapis.com/v1` | people, connections |
| google_forms | `https://forms.googleapis.com/v1` | forms, responses |
| google_ads | `https://googleads.googleapis.com` | campaigns, ad_groups |
| google_analytics | `https://analyticsdata.googleapis.com` | reports, properties |
| youtube | `https://www.googleapis.com/youtube/v3` | videos, channels, playlists |

### Group 10: Microsoft Services (5 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| onedrive | `https://graph.microsoft.com/v1.0` | files, folders |
| microsoft_outlook | `https://graph.microsoft.com/v1.0` | messages, calendar |
| microsoft_excel | `https://graph.microsoft.com/v1.0` | workbooks, worksheets |
| dynamics365 | `https://{org}.api.crm.dynamics.com` | accounts, contacts, leads |

### Group 11: Cloud Storage (5 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| dropbox | `https://api.dropboxapi.com/2` | files, folders, sharing |
| box | `https://api.box.com/2.0` | files, folders, collaborations |
| aws_s3 | AWS S3 endpoints | buckets, objects |
| azure_blob | Azure Blob endpoints | containers, blobs |
| gcs | `https://storage.googleapis.com` | buckets, objects |

### Group 12: Support & Ticketing (4 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| zendesk | `https://{subdomain}.zendesk.com/api/v2` | tickets, users, organizations |
| freshdesk | `https://{domain}.freshdesk.com/api/v2` | tickets, contacts, companies |
| helpscout | `https://api.helpscout.net/v2` | conversations, customers |
| intercom | `https://api.intercom.io` | contacts, conversations, companies |

### Group 13: Document & File Services (5 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| docusign | `https://demo.docusign.net/restapi` | envelopes, templates |
| docparser | `https://api.docparser.com/v1` | parsers, documents |
| pdfco | `https://api.pdf.co/v1` | pdf operations |
| cloudconvert | `https://api.cloudconvert.com/v2` | jobs, tasks |
| pandadoc | `https://api.pandadoc.com/public/v1` | documents, templates |

### Group 14: Content & Design (5 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| wordpress | `{site}/wp-json/wp/v2` | posts, pages, media |
| webflow | `https://api.webflow.com` | sites, collections, items |
| figma | `https://api.figma.com/v1` | files, images, comments |
| calendly | `https://api.calendly.com` | events, users, invitees |
| miro | `https://api.miro.com/v2` | boards, items, widgets |

### Group 15: Video & Meetings (2 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| zoom | `https://api.zoom.us/v2` | meetings, users, recordings |
| youtube | (in Google group) | videos, channels |

### Group 16: Data Services & Enrichment (6 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| hunter | `https://api.hunter.io/v2` | domain-search, email-finder |
| clearbit | `https://company.clearbit.com/v2` | companies, people |
| bitly | `https://api-ssl.bitly.com/v4` | shorten, clicks |
| apify | `https://api.apify.com/v2` | actors, runs, datasets |
| parseur | `https://api.parseur.com/v1` | mailboxes, documents |
| jotform | `https://api.jotform.com` | forms, submissions |

### Group 17: Advertising (2 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| linkedin_ads | `https://api.linkedin.com/v2` | adAccounts, campaigns |
| meta_ads | `https://graph.facebook.com/v18.0` | adaccounts, campaigns |

### Group 18: Database Services (3 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| bigquery | Google BigQuery API | query, tables, datasets |
| snowflake | Snowflake SQL API | queries, warehouses |
| mongodb | MongoDB Atlas API | clusters, databases, collections |

### Group 19: Business & Operations (4 servers)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| servicenow | `https://{instance}.service-now.com/api` | incidents, requests |
| uptimerobot | `https://api.uptimerobot.com/v2` | monitors, alert_contacts |
| front | `https://api2.frontapp.com` | conversations, inboxes |
| twilio | `https://api.twilio.com` | messages, calls |

### Group 20: Generic/Utility (1 server)
| Server | Base URL | Key Operations |
|--------|----------|----------------|
| proxy | Configurable | Generic HTTP proxy |

---

## Detailed Archive Structure by Group

### Group 1: Version Control & Dev Tools

#### GitHub (`reference/files/github/`)
```
github/
├── repos/acme-corp/widgets/issues                    # List (0 items case)
├── repos/acme-corp/widgets/issues?state=open         # List (multiple items)
├── repos/acme-corp/widgets/issues/1                  # Single issue
├── repos/acme-corp/widgets/issues/2                  # Another issue
├── rate_limit                                        # Rate limit status
└── errors/
    ├── 401_bad_credentials.json
    ├── 403_rate_limited.json
    └── 404_not_found.json
```

#### GitLab (`reference/files/gitlab/`)
```
gitlab/
├── api/v4/projects                                   # List projects
├── api/v4/projects?per_page=1                        # Single item
├── api/v4/projects/42                                # Project detail
├── api/v4/projects/42/issues                         # Project issues
├── api/v4/projects/42/issues/7                       # Issue detail
├── api/v4/projects/42/merge_requests                 # MRs
└── errors/
    ├── 401_unauthorized.json
    └── 404_not_found.json
```

#### Jira (`reference/files/jira/`)
```
jira/
├── rest/api/3/project                                # List projects
├── rest/api/3/project/ACME                           # Project detail
├── rest/api/3/search?jql=project=ACME                # Search results
├── rest/api/3/issue/ACME-42                          # Issue detail
└── errors/
    └── 401_unauthorized.json
```

#### Confluence (`reference/files/confluence/`)
```
confluence/
├── wiki/rest/api/content                             # List content
├── wiki/rest/api/content/12345                       # Page detail
├── wiki/rest/api/content?spaceKey=ACME               # Space content
└── errors/
    └── 401_unauthorized.json
```

### Group 2: AI/LLM Services

#### OpenAI (`reference/files/openai/`)
```
openai/
├── v1/chat/completions                               # Chat response
├── v1/models                                         # Model list
└── errors/
    ├── 401_invalid_api_key.json
    └── 429_rate_limited.json
```

#### Anthropic (`reference/files/anthropic/`)
```
anthropic/
├── v1/messages                                       # Message response
└── errors/
    ├── 401_invalid_api_key.json
    └── 529_overloaded.json
```

#### Gemini (`reference/files/gemini/`)
```
gemini/
├── v1beta/models/gemini-1.5-flash-latest:generateContent
└── errors/
    └── 400_invalid_request.json
```

### Group 3: Communication Platforms

#### Slack (`reference/files/slack/`)
```
slack/
├── api/chat.postMessage                              # Post response
├── api/conversations.list                            # Channel list
├── api/conversations.list?limit=1                    # Single channel
└── errors/
    ├── channel_not_found.json
    └── not_authed.json
```

#### Discord (`reference/files/discord/`)
```
discord/
├── users/@me/guilds                                  # Guild list
├── guilds/8675309                                    # Guild detail
├── guilds/8675309/channels                           # Channel list
├── channels/42/messages                              # Message list
├── channels/42/messages?limit=1                      # Single message
└── errors/
    └── 401_unauthorized.json
```

#### Teams (`reference/files/teams/`)
```
teams/
├── me/joinedTeams                                    # Team list
├── teams/abc-123                                     # Team detail
├── teams/abc-123/channels                            # Channel list
├── teams/abc-123/channels/general/messages           # Messages
└── errors/
    └── 401_unauthorized.json
```

### Group 4: CRM Systems

#### HubSpot (`reference/files/hubspot/`)
```
hubspot/
├── crm/v3/objects/contacts                           # Contact list
├── crm/v3/objects/contacts?limit=0                   # Empty list
├── crm/v3/objects/contacts?limit=1                   # Single contact
├── crm/v3/objects/contacts/501                       # Contact detail
├── crm/v3/objects/companies                          # Company list
├── crm/v3/objects/companies/101                      # Company detail
├── crm/v3/objects/deals                              # Deal list
└── errors/
    └── 401_unauthorized.json
```

#### Salesforce (`reference/files/salesforce/`)
```
salesforce/
├── services/data/v59.0/query?q=SELECT+Id,Name+FROM+Account
├── services/data/v59.0/sobjects/Account/001ABC
├── services/data/v59.0/sobjects/Contact/003XYZ
├── services/data/v59.0/sobjects/Opportunity/006DEF
└── errors/
    └── 401_session_expired.json
```

#### Pipedrive (`reference/files/pipedrive/`)
```
pipedrive/
├── v1/deals                                          # Deal list
├── v1/deals/123                                      # Deal detail
├── v1/persons                                        # Person list
├── v1/organizations                                  # Org list
└── errors/
    └── 401_unauthorized.json
```

### Group 5: Payment & Finance

#### Stripe (`reference/files/stripe/`)
```
stripe/
├── v1/customers                                      # Customer list
├── v1/customers?limit=0                              # Empty list
├── v1/customers/cus_DrBogusMcFakester                # Customer detail
├── v1/charges                                        # Charge list
├── v1/charges/ch_1234567890                          # Charge detail
├── v1/subscriptions                                  # Subscription list
└── errors/
    ├── 401_invalid_api_key.json
    └── 402_card_declined.json
```

#### PayPal (`reference/files/paypal/`)
```
paypal/
├── v2/checkout/orders                                # Order list
├── v2/checkout/orders/5O190127TN364715T              # Order detail
└── errors/
    └── 401_unauthorized.json
```

#### QuickBooks (`reference/files/quickbooks/`)
```
quickbooks/
├── v3/company/1234567890/query?query=select+*+from+Invoice
├── v3/company/1234567890/invoice/123
├── v3/company/1234567890/customer/456
└── errors/
    └── 401_unauthorized.json
```

### Group 6: Email & Marketing

#### SendGrid (`reference/files/sendgrid/`)
```
sendgrid/
├── v3/mail/send                                      # 202 Accepted response
├── v3/marketing/contacts                             # Contact list
└── errors/
    └── 401_unauthorized.json
```

#### Mailchimp (`reference/files/mailchimp/`)
```
mailchimp/
├── 3.0/lists                                         # List of lists
├── 3.0/lists/abc123def                               # List detail
├── 3.0/lists/abc123def/members                       # Member list
├── 3.0/lists/abc123def/members?count=0               # Empty
├── 3.0/campaigns                                     # Campaign list
└── errors/
    └── 401_api_key_invalid.json
```

### Group 7: Project Management & Productivity

#### Notion (`reference/files/notion/`)
```
notion/
├── v1/search                                         # Search results
├── v1/pages/abc123                                   # Page detail
├── v1/databases/def456/query                         # Query results
└── errors/
    └── 401_unauthorized.json
```

#### Airtable (`reference/files/airtable/`)
```
airtable/
├── v0/meta/bases                                     # Base list
├── v0/appXYZ123/Projects                             # Table records
├── v0/appXYZ123/Projects?maxRecords=0                # Empty
└── errors/
    └── 401_unauthorized.json
```

#### Asana (`reference/files/asana/`)
```
asana/
├── api/1.0/tasks                                     # Task list
├── api/1.0/tasks/12345                               # Task detail
├── api/1.0/projects                                  # Project list
├── api/1.0/workspaces                                # Workspace list
└── errors/
    └── 401_unauthorized.json
```

#### Trello (`reference/files/trello/`)
```
trello/
├── 1/boards/abc123                                   # Board detail
├── 1/boards/abc123/lists                             # List of lists
├── 1/boards/abc123/cards                             # Card list
├── 1/cards/xyz789                                    # Card detail
└── errors/
    └── 401_unauthorized.json
```

### Group 8: E-commerce

#### Shopify (`reference/files/shopify/`)
```
shopify/
├── admin/api/2024-01/products.json                   # Product list
├── admin/api/2024-01/products.json?limit=0           # Empty
├── admin/api/2024-01/products/7654321.json           # Product detail
├── admin/api/2024-01/orders.json                     # Order list
├── admin/api/2024-01/customers.json                  # Customer list
└── errors/
    └── 401_unauthorized.json
```

### Group 9: Google Workspace

#### Google Sheets (`reference/files/google_sheets/`)
```
google_sheets/
├── v4/spreadsheets/1BxiMVs0XRA5nFMdKvBd                 # Spreadsheet
├── v4/spreadsheets/1BxiMVs0XRA5nFMdKvBd/values/Sheet1!A1:C10
└── errors/
    └── 401_unauthorized.json
```

#### Google Drive (`reference/files/google_drive/`)
```
google_drive/
├── drive/v3/files                                    # File list
├── drive/v3/files?q=mimeType='application/pdf'       # Filtered
├── drive/v3/files/abc123                             # File detail
└── errors/
    └── 401_unauthorized.json
```

### Group 10: Microsoft Services

#### OneDrive (`reference/files/onedrive/`)
```
onedrive/
├── v1.0/me/drive/root/children                       # File list
├── v1.0/me/drive/items/abc123                        # Item detail
└── errors/
    └── 401_unauthorized.json
```

### Group 11: Cloud Storage

#### Dropbox (`reference/files/dropbox/`)
```
dropbox/
├── 2/files/list_folder                               # Folder contents
├── 2/files/get_metadata                              # File metadata
└── errors/
    └── 401_unauthorized.json
```

#### AWS S3 (`reference/files/aws_s3/`)
```
aws_s3/
├── list_buckets                                      # Bucket list
├── list_objects?bucket=acme-widgets                  # Object list
└── errors/
    └── 403_access_denied.json
```

### Group 12: Support & Ticketing

#### Zendesk (`reference/files/zendesk/`)
```
zendesk/
├── api/v2/tickets                                    # Ticket list
├── api/v2/tickets.json?page[size]=0                  # Empty
├── api/v2/tickets/12345                              # Ticket detail
├── api/v2/users                                      # User list
└── errors/
    └── 401_unauthorized.json
```

#### Freshdesk (`reference/files/freshdesk/`)
```
freshdesk/
├── api/v2/tickets                                    # Ticket list
├── api/v2/tickets/67890                              # Ticket detail
├── api/v2/contacts                                   # Contact list
└── errors/
    └── 401_unauthorized.json
```

### Group 13: Document & File Services

#### DocuSign (`reference/files/docusign/`)
```
docusign/
├── restapi/v2.1/accounts/abc123/envelopes            # Envelope list
├── restapi/v2.1/accounts/abc123/envelopes/xyz789     # Envelope detail
└── errors/
    └── 401_unauthorized.json
```

### Group 14: Content & Design

#### WordPress (`reference/files/wordpress/`)
```
wordpress/
├── wp-json/wp/v2/posts                               # Post list
├── wp-json/wp/v2/posts/123                           # Post detail
├── wp-json/wp/v2/pages                               # Page list
└── errors/
    └── 401_unauthorized.json
```

#### Figma (`reference/files/figma/`)
```
figma/
├── v1/files/abc123                                   # File detail
├── v1/files/abc123/images                            # Image exports
└── errors/
    └── 401_unauthorized.json
```

### Group 15: Video & Meetings

#### Zoom (`reference/files/zoom/`)
```
zoom/
├── v2/users/me/meetings                              # Meeting list
├── v2/meetings/12345                                 # Meeting detail
└── errors/
    └── 401_unauthorized.json
```

### Group 16: Data Services & Enrichment

#### Hunter (`reference/files/hunter/`)
```
hunter/
├── v2/domain-search?domain=acme.example.com          # Domain search
├── v2/email-finder?domain=acme.example.com&first_name=Jane
└── errors/
    └── 401_unauthorized.json
```

#### Clearbit (`reference/files/clearbit/`)
```
clearbit/
├── v2/companies/find?domain=acme.example.com         # Company lookup
└── errors/
    └── 401_unauthorized.json
```

### Group 17: Advertising

#### LinkedIn Ads (`reference/files/linkedin_ads/`)
```
linkedin_ads/
├── v2/adAccountsV2                                   # Account list
├── v2/adCampaignsV2?search.account.values[0]=urn:li:sponsoredAccount:123
└── errors/
    └── 401_unauthorized.json
```

### Group 18: Database Services

#### BigQuery (`reference/files/bigquery/`)
```
bigquery/
├── bigquery/v2/projects/my-project/datasets          # Dataset list
├── bigquery/v2/projects/my-project/queries           # Query result
└── errors/
    └── 401_unauthorized.json
```

### Group 19: Business & Operations

#### Twilio (`reference/files/twilio/`)
```
twilio/
├── 2010-04-01/Accounts/AC123/Messages.json           # Message list
├── 2010-04-01/Accounts/AC123/Messages/SM456.json     # Message detail
├── 2010-04-01/Accounts/AC123/Calls.json              # Call list
└── errors/
    └── 401_unauthorized.json
```

#### ServiceNow (`reference/files/servicenow/`)
```
servicenow/
├── api/now/table/incident                            # Incident list
├── api/now/table/incident/abc123                     # Incident detail
└── errors/
    └── 401_unauthorized.json
```

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
**Decision**: Full URL path including query string.

Archive keys are the URL minus protocol, server, and port. Query strings are included as-is:
- `/repos/acme-corp/widgets/issues?state=open`
- `/v1/customers?limit=10`
- `/services/data/v59.0/query?q=SELECT+Id,Name+FROM+Account`

No special encoding needed - URLs cannot contain spaces, so space-separated format works.

### Error Response Mocking
**Decision**: Special `/errors/{status_code}` paths.

Each archive includes an `errors/` subdirectory with error responses:
- `/errors/401` - Authentication errors
- `/errors/403` - Authorization/rate limit errors
- `/errors/404` - Not found errors
- Service-specific errors (e.g., Slack's `channel_not_found`)

### Response Headers
**Decision**: Determined by CID file extension.

The `.json` extension on CID file paths ensures `application/json` MIME type.

### Versioning
**Decision**: One archive per service.

### Data Generation
**Decision**: Either hand-crafted or generated is acceptable.

### List Response Item Counts
**Decision**: Cover 0, 1, and multiple items.

For list endpoints, provide variants to test edge cases:
- Empty list: `?limit=0` or `?count=0` → 0 items
- Single item: `?limit=1` or `?per_page=1` → 1 item
- Multiple items: Default → 2-3 realistic items

This ensures tests cover all list handling scenarios.

### Pagination in List Responses
**Decision**: Include pagination fields indicating end of list.

Include realistic pagination fields but with values showing no more pages:
- `has_more: false`
- `next_cursor: null`
- No `Link` header for next page

### Transform Reuse
**Decision**: Yes - archives replace internal server calls.

### Archive Compilation
**Decision**: Already part of CI/CD.

---

## Source CID File Format

Each `.source.cids` file maps request paths (including query strings) to local JSON files:

```
# github.source.cids
/repos/acme-corp/widgets/issues ../../files/github/repos/acme-corp/widgets/issues.json
/repos/acme-corp/widgets/issues?state=open ../../files/github/repos/acme-corp/widgets/issues_state_open.json
/repos/acme-corp/widgets/issues/1 ../../files/github/repos/acme-corp/widgets/issues/1.json
/rate_limit ../../files/github/rate_limit.json
/errors/401 ../../files/github/errors/401_bad_credentials.json
```

The `.json` extension ensures `application/json` MIME type.

---

## Test Specifications

### Archive Structure Tests

```gherkin
Scenario: Source CID file exists for each of the 93 services
  Given the reference/archive/cids/ directory
  Then there should be a .source.cids file for each external API service

Scenario: All referenced files exist
  Given a .source.cids file
  When each line references a file path
  Then that file should exist in reference/files/

Scenario: All JSON files are valid
  Given a JSON file in reference/files/
  When the file is parsed
  Then it should be valid JSON
```

### List Response Tests

```gherkin
Scenario: List endpoints have empty, single, and multiple item variants
  Given a service with list endpoints
  Then there should be a variant returning 0 items
  And there should be a variant returning 1 item
  And there should be a variant returning multiple items

Scenario: Empty list response has correct structure
  Given hubspot/crm/v3/objects/contacts?limit=0
  Then results array should be empty
  And paging should indicate no more results

Scenario: Single item list response has one element
  Given hubspot/crm/v3/objects/contacts?limit=1
  Then results array should have exactly 1 element

Scenario: Multiple item list response has variety
  Given hubspot/crm/v3/objects/contacts
  Then results array should have 2-3 elements
  And elements should have different IDs and data
```

### Query String Tests

```gherkin
Scenario: Paths with query strings are valid keys
  Given github.source.cids contains "/repos/acme-corp/widgets/issues?state=open"
  Then the key should be stored without additional encoding
  And the file path should use underscores for special characters

Scenario: Query string variations map to different files
  Given paths "/v1/customers" and "/v1/customers?limit=10"
  Then each should map to a different response file
```

### Response Content Tests

```gherkin
Scenario: GitHub issues list has realistic content
  Given github/repos/acme-corp/widgets/issues.json
  Then it should contain 2-3 issues
  And issues should have realistic titles and bodies
  And user.login values should be fictional names
  And all URLs should reference acme-corp/widgets

Scenario: OpenAI completion has correct structure
  Given openai/v1/chat/completions.json
  Then it should have id starting with "chatcmpl-"
  And object should be "chat.completion"
  And choices array should contain message with role "assistant"
  And usage should have prompt_tokens, completion_tokens, total_tokens

Scenario: Stripe customer list has correct pagination
  Given stripe/v1/customers.json
  Then object should be "list"
  And has_more should be false
  And data should contain 2-3 customer objects
```

### Error Response Tests

```gherkin
Scenario: Each service has at least a 401 error response
  Given any service directory in reference/files/
  Then it should have an errors/ subdirectory
  And errors/ should contain at least 401_*.json

Scenario: Error responses match API format
  Given github/errors/401_bad_credentials.json
  Then it should have message field
  And documentation_url should be a valid GitHub docs URL
```

### Data Consistency Tests

```gherkin
Scenario: IDs are consistent within service
  Given stripe/v1/customers.json (list)
  And stripe/v1/customers/cus_DrBogusMcFakester.json (detail)
  Then the customer in the detail file should appear in the list

Scenario: Fictional data is clearly fake
  Given any mock JSON file
  Then email addresses should use example.com or similar
  And company names should be obviously fictional
  And person names should be obviously fake
```

---

## Implementation Phases

### Phase 1: Version Control & Dev Tools (4 servers)
GitHub, GitLab, Jira, Confluence

### Phase 2: AI/LLM Services (7 servers)
OpenAI, Anthropic, Gemini, OpenRouter, NVIDIA NIM, AI Assist, JSONPlaceholder

### Phase 3: Communication Platforms (5 servers)
Slack, Discord, Teams, Telegram, WhatsApp

### Phase 4: CRM Systems (8 servers)
HubSpot, Salesforce, Pipedrive, Close CRM, ActiveCampaign, Insightly, Gorgias, Zoho CRM

### Phase 5: Payment & Finance (5 servers)
Stripe, PayPal, QuickBooks, Xero, FreshBooks

### Phase 6: Email & Marketing (10 servers)
SendGrid, Mailchimp, Postmark, Mailgun, MailerLite, Klaviyo, Amplitude, Segment, Mixpanel, Typeform

### Phase 7: Project Management (9 servers)
Notion, Airtable, Asana, Trello, Monday, Todoist, ClickUp, Coda, Basecamp

### Phase 8: E-commerce (7 servers)
Shopify, WooCommerce, eBay, Etsy, Squarespace, Wix

### Phase 9: Google Workspace (10 servers)
Sheets, Docs, Drive, Calendar, Gmail, Contacts, Forms, Ads, Analytics, YouTube

### Phase 10: Microsoft Services (5 servers)
OneDrive, Outlook, Excel, Dynamics 365, (Teams in Group 3)

### Phase 11: Cloud Storage (5 servers)
Dropbox, Box, AWS S3, Azure Blob, GCS

### Phase 12: Support & Ticketing (4 servers)
Zendesk, Freshdesk, HelpScout, Intercom

### Phase 13: Document & File Services (5 servers)
DocuSign, Docparser, PDF.co, CloudConvert, PandaDoc

### Phase 14: Content & Design (5 servers)
WordPress, Webflow, Figma, Calendly, Miro

### Phase 15: Video & Meetings (2 servers)
Zoom, (YouTube in Google group)

### Phase 16: Data Services (6 servers)
Hunter, Clearbit, Bitly, Apify, Parseur, JotForm

### Phase 17: Advertising (2 servers)
LinkedIn Ads, Meta Ads

### Phase 18: Database Services (3 servers)
BigQuery, Snowflake, MongoDB

### Phase 19: Business & Operations (4 servers)
ServiceNow, UptimeRobot, Front, Twilio

### Phase 20: Generic (1 server)
Proxy

---

## Sample Mock Data

### GitHub Issue List (repos/acme-corp/widgets/issues.json)
```json
[
  {
    "id": 1,
    "number": 1,
    "title": "Widget fails to spin on Tuesdays",
    "state": "open",
    "user": {"login": "janedoe", "id": 12345}
  },
  {
    "id": 2,
    "number": 2,
    "title": "Add support for hexagonal widgets",
    "state": "open",
    "user": {"login": "johnsmith", "id": 67890}
  }
]
```

### Empty List (hubspot/crm/v3/objects/contacts?limit=0)
```json
{
  "results": [],
  "paging": {}
}
```

### Single Item List (hubspot/crm/v3/objects/contacts?limit=1)
```json
{
  "results": [
    {
      "id": "501",
      "properties": {
        "firstname": "Jane",
        "lastname": "Doe",
        "email": "jane.doe@example.com"
      }
    }
  ],
  "paging": {
    "next": null
  }
}
```

### Stripe Customer List (v1/customers.json)
```json
{
  "object": "list",
  "url": "/v1/customers",
  "has_more": false,
  "data": [
    {
      "id": "cus_DrBogusMcFakester",
      "object": "customer",
      "email": "bogus@fakester.example.com",
      "name": "Dr. Bogus McFakester"
    },
    {
      "id": "cus_JaneDoe123",
      "object": "customer",
      "email": "jane.doe@example.com",
      "name": "Jane Doe"
    }
  ]
}
```

---

## Open Questions (From Implementation)

The following questions arose during implementation of the HubSpot CID archive:

### Q1: File Naming Convention for Query String Variants

When a source.cids key includes a query string like `/crm/v3/objects/contacts?limit=0`, what should the corresponding file be named?

**Options:**
1. **Semantic names**: `contacts_empty.json`, `contacts_single.json` (current approach)
2. **Query-encoded names**: `contacts_limit_0.json`, `contacts_limit_1.json`
3. **URL-encoded names**: `contacts%3Flimit%3D0.json` (not recommended)

**Current approach**: Semantic names (`contacts_empty.json`)

**Trade-offs**:
- Semantic names are clearer but don't match the source.cids key directly
- Query-encoded names are mechanical but may be confusing when query strings are complex
- Need consistency across 93 services

---

### Q2: Directory Structure - Flat vs Nested

Should files be organized in a flat structure or nested to match the API path?

**Options:**
1. **Flat**: `hubspot/contacts.json`, `hubspot/contacts_501.json`
2. **Nested**: `hubspot/crm/v3/objects/contacts.json`, `hubspot/crm/v3/objects/contacts/501.json`
3. **Hybrid**: Flat within service but grouped by resource type

**Current approach**: Flat structure

**Trade-offs**:
- Flat is simpler and avoids deeply nested directories
- Nested mirrors the API structure but creates many directories
- Flat may have naming conflicts for complex APIs

---

### Q3: Cross-Platform Filename Compatibility

Query strings in source.cids keys can contain characters that are invalid in Windows filenames (`?`, `<`, `>`, `:`, `*`, `|`, `"`).

**Current approach**: Files use safe names; source.cids maps query-string paths to those safe filenames

**Confirmed**: The source.cids file handles the mapping, so filenames don't need to contain special characters.

---

## Success Criteria

1. **All 93 .source.cids files exist** for external API services
2. **All referenced JSON files exist** and parse correctly
3. **JSON structure matches** real API response formats
4. **List endpoints have 0, 1, and multiple item variants**
5. **Error responses exist** for common error cases per service
6. **All tests pass** validating structure and content
7. **Data is clearly fictional** (no real emails, companies, etc.)
8. **CI/CD compilation** produces valid .cids files

---

## Total File Count Estimate

- 93 services
- ~5-10 endpoints per service average
- ~3 variants for list endpoints (0, 1, many)
- ~2-3 error responses per service

**Estimated total: ~800-1000 JSON files**

---

## Next Steps

1. **Implement Phase 1** (GitHub, GitLab, Jira, Confluence) as proof of concept
2. **Run structure validation tests**
3. **Verify CI/CD compilation** works for new archives
4. **Proceed with remaining phases**
