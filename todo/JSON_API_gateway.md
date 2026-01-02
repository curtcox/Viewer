# JSON API Gateway Implementation Plan

## Overview

**Status: PLANNING**

This plan describes the implementation of a generalized JSON API gateway that transforms JSON responses from arbitrary servers into navigable HTML pages. The gateway renders JSON with syntax highlighting and automatically detects references to related resources, converting them into clickable links for seamless API exploration.

### Core Goals

1. **Render JSON as formatted HTML** with syntax coloring matching the existing JSONPlaceholder gateway style
2. **Detect linkable references** in JSON responses and convert them to navigation links
3. **Support multiple link detection strategies** including full URLs, partial URLs, ID-based references, and composite references
4. **Generalize the approach** beyond JSONPlaceholder to work with arbitrary REST APIs

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           JSON API Gateway                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │ Request Transform │ -> │  Target Server   │ -> │  Response Transform  │   │
│  │  (pass-through)   │    │  (internal/ext)  │    │  (JSON → HTML)       │   │
│  └──────────────────┘    └──────────────────┘    └──────────────────────┘   │
│                                                             │                │
│                                                             ▼                │
│                                                   ┌──────────────────────┐   │
│                                                   │   Link Detector      │   │
│                                                   │   Registry           │   │
│                                                   ├──────────────────────┤   │
│                                                   │ • Full URL Detector  │   │
│                                                   │ • Partial URL Det.   │   │
│                                                   │ • ID Reference Det.  │   │
│                                                   │ • Composite Det.     │   │
│                                                   └──────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| `reference_templates/servers/definitions/gateway.py` | Core gateway routing (existing) |
| `reference_templates/gateways/transforms/json_api_request.py` | Request transform (NEW) |
| `reference_templates/gateways/transforms/json_api_response.py` | Response transform with link detection (NEW) |
| `reference_templates/gateways/templates/json_api_data.html` | HTML template for JSON display (NEW) |
| `reference_templates/gateways/link_detectors/*.py` | Pluggable link detector modules (NEW) |

---

## Link Detection Strategies

The gateway must handle four distinct patterns for detecting linkable references in JSON:

### Strategy 1: Full Literal URL

The JSON response contains a complete, absolute URL that can be fetched directly.

**Pattern Recognition:**
- Value is a string starting with `http://` or `https://`
- Value is a valid URL format

**Example JSON:**
```json
{
  "id": 1,
  "name": "John Doe",
  "html_url": "https://api.github.com/users/johndoe",
  "repos_url": "https://api.github.com/users/johndoe/repos"
}
```

**Rendered Link:**
```html
"repos_url": <a href="/gateway/github?target=https://api.github.com/users/johndoe/repos">
  "https://api.github.com/users/johndoe/repos"
</a>
```

---

### Strategy 2: Partial URL (Path Only)

The JSON contains a path that must be combined with a base URL known to the gateway.

**Pattern Recognition:**
- Value is a string starting with `/`
- Key name suggests a path (e.g., `*_path`, `*_url`, `href`, `path`)
- Gateway configuration specifies base URL

**Example JSON:**
```json
{
  "id": 123,
  "title": "Feature Request",
  "comments_path": "/repos/owner/repo/issues/123/comments"
}
```

**Rendered Link (with gateway base URL `https://api.github.com`):**
```html
"comments_path": <a href="/gateway/github/repos/owner/repo/issues/123/comments">
  "/repos/owner/repo/issues/123/comments"
</a>
```

---

### Strategy 3: ID Reference (Multiple Fields in Response)

The JSON contains an ID that references another resource. The gateway must know how to construct the URL from the ID and the resource type.

**Pattern Recognition:**
- Key matches a pattern like `{resource}_id` (e.g., `user_id`, `post_id`, `album_id`)
- Value is an integer or string ID
- Gateway configuration maps resource types to URL patterns

**Example JSON:**
```json
{
  "id": 42,
  "title": "My Post",
  "userId": 7,
  "albumId": 3
}
```

**Rendered Links:**
```html
"userId": <a href="/gateway/jsonplaceholder/users/7">7</a>
"albumId": <a href="/gateway/jsonplaceholder/albums/3">3</a>
```

**Configuration Example:**
```json
{
  "id_patterns": {
    "userId": "/users/{id}",
    "postId": "/posts/{id}",
    "albumId": "/albums/{id}",
    "customerId": "/customers/{id}"
  }
}
```

---

### Strategy 4: Composite Reference (Request URL + Response Data)

The link URL must be constructed by combining information from the original request URL with data from the response.

**Pattern Recognition:**
- Response contains an ID or identifier
- The URL path requires context from the request (e.g., owner, repo, project)
- Gateway configuration specifies composite patterns

**Example:**
- Request URL: `/gateway/github/repos/microsoft/vscode/issues`
- Response JSON:
```json
[
  {
    "number": 12345,
    "title": "Bug Report",
    "user": {
      "id": 789,
      "login": "johndoe"
    }
  }
]
```

**Rendered Links (using context from request path `repos/microsoft/vscode`):**
```html
"number": <a href="/gateway/github/repos/microsoft/vscode/issues/12345">12345</a>
"login": <a href="/gateway/github/users/johndoe">"johndoe"</a>
```

**Configuration Example:**
```json
{
  "composite_patterns": {
    "number": {
      "context_pattern": "repos/{owner}/{repo}/issues",
      "url_template": "/repos/{owner}/{repo}/issues/{number}"
    },
    "login": {
      "url_template": "/users/{login}"
    }
  }
}
```

---

## Validation Servers

Three servers have been selected to validate the implementation. Each server exercises different link detection strategies.

### Server 1: JSONPlaceholder

**Base URL:** `https://jsonplaceholder.typicode.com` (proxied via `/gateway/jsonplaceholder`)

**API Structure:**
- `/posts` - List posts
- `/posts/{id}` - Single post
- `/users` - List users
- `/users/{id}` - Single user
- `/comments` - List comments
- `/albums` - List albums
- `/photos` - List photos
- `/todos` - List todos

**Link Detection Strategies Used:**
- Strategy 3: ID Reference (`userId`, `postId`, `albumId`)

---

### Server 2: GitHub API

**Base URL:** `https://api.github.com` (would be proxied via `/gateway/github`)

**API Structure:**
- `/users/{username}` - User details
- `/users/{username}/repos` - User repositories
- `/repos/{owner}/{repo}` - Repository details
- `/repos/{owner}/{repo}/issues` - Issues list
- `/repos/{owner}/{repo}/issues/{number}` - Single issue
- `/repos/{owner}/{repo}/pulls` - Pull requests

**Link Detection Strategies Used:**
- Strategy 1: Full URL (`html_url`, `repos_url`, `followers_url`, `avatar_url`)
- Strategy 2: Partial URL (`url` fields containing paths)
- Strategy 3: ID Reference (`user.id`, `assignee.id`)
- Strategy 4: Composite Reference (issue `number` + repo context)

---

### Server 3: Stripe API

**Base URL:** `https://api.stripe.com/v1` (would be proxied via `/gateway/stripe`)

**API Structure:**
- `/customers` - List customers
- `/customers/{id}` - Single customer
- `/charges` - List charges
- `/charges/{id}` - Single charge
- `/payment_intents` - Payment intents
- `/invoices` - Invoices

**Link Detection Strategies Used:**
- Strategy 3: ID Reference (`customer` field containing `cus_xxx` ID)
- Object references (Stripe uses expandable object patterns)

---

## Test Specifications

### JSONPlaceholder Tests

#### Test JP-1: Post contains userId linked to user
**Request:** `/gateway/jsonplaceholder/posts/1`
**Expected JSON field:** `"userId": 1`
**Expected Link:** The value `1` is rendered as a link to `/gateway/jsonplaceholder/users/1`
**Strategy:** ID Reference

#### Test JP-2: Comment contains postId linked to post
**Request:** `/gateway/jsonplaceholder/comments/1`
**Expected JSON field:** `"postId": 1`
**Expected Link:** The value `1` is rendered as a link to `/gateway/jsonplaceholder/posts/1`
**Strategy:** ID Reference

#### Test JP-3: Photo contains albumId linked to album
**Request:** `/gateway/jsonplaceholder/photos/1`
**Expected JSON field:** `"albumId": 1`
**Expected Link:** The value `1` is rendered as a link to `/gateway/jsonplaceholder/albums/1`
**Strategy:** ID Reference

#### Test JP-4: Post list contains multiple userId links
**Request:** `/gateway/jsonplaceholder/posts`
**Expected:** Each post object in the array has its `userId` field rendered as a link
**Strategy:** ID Reference (array context)

#### Test JP-5: User object has no internal links (leaf node)
**Request:** `/gateway/jsonplaceholder/users/1`
**Expected:** No fields in the user object generate links (it's a terminal resource)
**Strategy:** None (negative test)

#### Test JP-6: Nested object address/company in user not linked
**Request:** `/gateway/jsonplaceholder/users/1`
**Expected:** Nested objects like `address` and `company` are rendered as formatted JSON but not linked
**Strategy:** None (nested object handling)

---

### GitHub API Tests

#### Test GH-1: User contains full URL (html_url)
**Request:** `/gateway/github/users/octocat`
**Expected JSON field:** `"html_url": "https://github.com/octocat"`
**Expected Link:** The URL string is rendered as a link that proxies through the gateway
**Strategy:** Full Literal URL

#### Test GH-2: User contains repos_url (full URL to related resource)
**Request:** `/gateway/github/users/octocat`
**Expected JSON field:** `"repos_url": "https://api.github.com/users/octocat/repos"`
**Expected Link:** The URL is rendered as a link to `/gateway/github/users/octocat/repos`
**Strategy:** Full Literal URL (with base URL stripping)

#### Test GH-3: User contains followers_url (full URL)
**Request:** `/gateway/github/users/octocat`
**Expected JSON field:** `"followers_url": "https://api.github.com/users/octocat/followers"`
**Expected Link:** The URL is rendered as a link
**Strategy:** Full Literal URL

#### Test GH-4: Repository contains owner.login (nested reference)
**Request:** `/gateway/github/repos/microsoft/vscode`
**Expected JSON field:** `"owner": { "login": "microsoft", ... }`
**Expected Link:** The `login` value "microsoft" is rendered as a link to `/gateway/github/users/microsoft`
**Strategy:** ID Reference (nested object)

#### Test GH-5: Issue contains number (composite with repo context)
**Request:** `/gateway/github/repos/microsoft/vscode/issues`
**Expected JSON field (in array):** `"number": 12345`
**Expected Link:** The issue number is rendered as a link to `/gateway/github/repos/microsoft/vscode/issues/12345`
**Strategy:** Composite Reference (requires parsing request path to get owner/repo)

#### Test GH-6: Issue contains user.login (assignee reference)
**Request:** `/gateway/github/repos/microsoft/vscode/issues/1`
**Expected JSON field:** `"user": { "login": "someuser", ... }`
**Expected Link:** The `login` value is rendered as a link to `/gateway/github/users/someuser`
**Strategy:** ID Reference (nested)

#### Test GH-7: Repository contains partial URL in url field
**Request:** `/gateway/github/repos/microsoft/vscode`
**Expected JSON field:** `"url": "https://api.github.com/repos/microsoft/vscode"`
**Expected Link:** The URL is converted to a gateway path `/gateway/github/repos/microsoft/vscode`
**Strategy:** Full URL with base stripping

#### Test GH-8: Issue comments URL derived from issue number
**Request:** `/gateway/github/repos/microsoft/vscode/issues/1`
**Expected JSON field:** `"comments_url": "https://api.github.com/repos/microsoft/vscode/issues/1/comments"`
**Expected Link:** Link to `/gateway/github/repos/microsoft/vscode/issues/1/comments`
**Strategy:** Full Literal URL

#### Test GH-9: Pull request contains head.ref (branch reference)
**Request:** `/gateway/github/repos/microsoft/vscode/pulls/1`
**Expected JSON field:** `"head": { "ref": "feature-branch", "sha": "abc123" }`
**Expected Link:** Branch name could link to `/gateway/github/repos/microsoft/vscode/branches/feature-branch`
**Strategy:** Composite Reference (optional - may not be implemented initially)

#### Test GH-10: Labels array contains label objects with URLs
**Request:** `/gateway/github/repos/microsoft/vscode/issues/1`
**Expected JSON field:** `"labels": [{ "name": "bug", "url": "https://..." }]`
**Expected Link:** Each label's URL field is linked
**Strategy:** Full Literal URL (in array of objects)

---

### Stripe API Tests

#### Test ST-1: Charge contains customer ID
**Request:** `/gateway/stripe/charges/ch_xxx`
**Expected JSON field:** `"customer": "cus_12345"`
**Expected Link:** The customer ID is rendered as a link to `/gateway/stripe/customers/cus_12345`
**Strategy:** ID Reference (prefixed ID format)

#### Test ST-2: Customer list contains customer IDs
**Request:** `/gateway/stripe/customers`
**Expected JSON field (in data array):** `"id": "cus_12345"`
**Expected Link:** Each customer ID links to `/gateway/stripe/customers/cus_12345`
**Strategy:** ID Reference

#### Test ST-3: Invoice contains customer and subscription references
**Request:** `/gateway/stripe/invoices/in_xxx`
**Expected JSON fields:** `"customer": "cus_xxx"`, `"subscription": "sub_xxx"`
**Expected Links:** Customer links to customers endpoint, subscription links to subscriptions endpoint
**Strategy:** ID Reference (multiple resource types)

#### Test ST-4: Charge contains payment_intent reference
**Request:** `/gateway/stripe/charges/ch_xxx`
**Expected JSON field:** `"payment_intent": "pi_xxx"`
**Expected Link:** Links to `/gateway/stripe/payment_intents/pi_xxx`
**Strategy:** ID Reference (prefixed ID)

#### Test ST-5: Nested object (source) not auto-linked
**Request:** `/gateway/stripe/charges/ch_xxx`
**Expected JSON field:** `"source": { "id": "card_xxx", ... }`
**Expected:** The source object is rendered as JSON but `card_xxx` is not linked (card is not a top-level resource)
**Strategy:** None (negative test - selective linking)

#### Test ST-6: data array pagination
**Request:** `/gateway/stripe/customers?limit=10`
**Expected JSON field:** `"has_more": true`, `"url": "/v1/customers"`
**Expected Link:** The `url` field as a partial URL links to `/gateway/stripe/customers`
**Strategy:** Partial URL

---

## Edge Case Tests

### Array Handling

#### Test E-1: Empty array renders correctly
**Input:** `[]`
**Expected Output:** `[]` (no links)

#### Test E-2: Array of primitives (no links)
**Input:** `[1, 2, 3]`
**Expected Output:** `[1, 2, 3]` (numbers not linked)

#### Test E-3: Array of strings (potential URLs)
**Input:** `["https://example.com", "not-a-url", "/partial/path"]`
**Expected Output:** First and third items linked (if URL detection enabled for strings in arrays)

#### Test E-4: Deeply nested arrays
**Input:** `{ "data": [{ "items": [{ "id": 1 }] }] }`
**Expected Output:** Nested structure preserved, IDs linked if matching pattern

---

### Null and Empty Handling

#### Test E-5: Null value renders as null
**Input:** `{ "userId": null }`
**Expected Output:** `"userId": <span class="json-null">null</span>` (not linked)

#### Test E-6: Empty string not linked
**Input:** `{ "url": "" }`
**Expected Output:** `"url": <span class="json-string">""</span>` (not linked)

#### Test E-7: Empty object renders correctly
**Input:** `{}`
**Expected Output:** `{}`

---

### Special Characters

#### Test E-8: URL with query parameters
**Input:** `{ "url": "https://api.example.com/search?q=test&page=1" }`
**Expected Output:** URL linked with query string preserved

#### Test E-9: URL with fragments
**Input:** `{ "url": "https://example.com/page#section" }`
**Expected Output:** URL linked with fragment preserved

#### Test E-10: JSON key with special characters
**Input:** `{ "user-id": 123, "data.nested": "value" }`
**Expected Output:** Keys rendered correctly, linking based on configured patterns only

#### Test E-11: Unicode in values
**Input:** `{ "name": "José García", "emoji": "🚀" }`
**Expected Output:** Unicode preserved and rendered correctly

---

### Malformed Data

#### Test E-12: Invalid URL format not linked
**Input:** `{ "url": "not://valid" }`
**Expected Output:** Value rendered as string, not linked

#### Test E-13: ID field with wrong type
**Input:** `{ "userId": "not-a-number" }`
**Expected Output:** If ID linking expects integers, this string is not linked

#### Test E-14: Mixed ID formats
**Input:** `{ "id": 123, "ref_id": "ABC-123", "uuid": "550e8400-e29b-41d4-a716-446655440000" }`
**Expected Output:** Each ID type handled according to configuration

---

### Request Context Tests

#### Test E-15: Request path with trailing slash
**Request:** `/gateway/github/repos/owner/repo/`
**Expected:** Trailing slash normalized, composite patterns still work

#### Test E-16: Request path with query parameters
**Request:** `/gateway/github/repos/owner/repo/issues?state=open`
**Expected:** Query params preserved for pagination/filtering, composite patterns use path only

#### Test E-17: Root request path
**Request:** `/gateway/jsonplaceholder/`
**Expected:** List endpoints work, no composite context needed

---

### Performance Tests

#### Test E-18: Large array response (100+ items)
**Input:** Array with 100 objects, each with linkable IDs
**Expected:** All items rendered with links, acceptable latency (<500ms)

#### Test E-19: Deeply nested object (10+ levels)
**Input:** Object with 10+ levels of nesting
**Expected:** All levels rendered, links detected at all levels

---

## Configuration Schema

### Gateway Configuration

```json
{
  "json_api": {
    "description": "Generalized JSON API gateway with link detection",
    "request_transform_cid": "AAAAA_request_transform_cid",
    "response_transform_cid": "AAAAA_response_transform_cid",
    "templates": {
      "json_api_data.html": "AAAAA_template_cid"
    },
    "config": {
      "link_detection": {
        "full_url": {
          "enabled": true,
          "base_url_strip": "https://api.example.com",
          "gateway_prefix": "/gateway/example"
        },
        "partial_url": {
          "enabled": true,
          "key_patterns": ["*_url", "*_path", "href", "url"],
          "gateway_prefix": "/gateway/example"
        },
        "id_reference": {
          "enabled": true,
          "patterns": {
            "userId": "/users/{id}",
            "postId": "/posts/{id}",
            "customer": "/customers/{id}",
            "owner.login": "/users/{login}"
          }
        },
        "composite_reference": {
          "enabled": true,
          "patterns": {
            "number": {
              "context_regex": "repos/([^/]+)/([^/]+)/issues",
              "context_vars": ["owner", "repo"],
              "url_template": "/repos/{owner}/{repo}/issues/{number}"
            }
          }
        }
      }
    }
  }
}
```

### Per-Server Configuration Examples

#### JSONPlaceholder Config
```json
{
  "link_detection": {
    "id_reference": {
      "enabled": true,
      "patterns": {
        "userId": "/users/{id}",
        "postId": "/posts/{id}",
        "albumId": "/albums/{id}"
      }
    }
  }
}
```

#### GitHub Config
```json
{
  "link_detection": {
    "full_url": {
      "enabled": true,
      "base_url_strip": "https://api.github.com",
      "gateway_prefix": "/gateway/github"
    },
    "id_reference": {
      "enabled": true,
      "patterns": {
        "owner.login": "/users/{login}",
        "user.login": "/users/{login}",
        "assignee.login": "/users/{login}"
      }
    },
    "composite_reference": {
      "enabled": true,
      "patterns": {
        "number": {
          "context_regex": "repos/([^/]+)/([^/]+)/(issues|pulls)",
          "context_vars": ["owner", "repo", "type"],
          "url_template": "/repos/{owner}/{repo}/{type}/{number}"
        }
      }
    }
  }
}
```

#### Stripe Config
```json
{
  "link_detection": {
    "partial_url": {
      "enabled": true,
      "key_patterns": ["url"],
      "gateway_prefix": "/gateway/stripe"
    },
    "id_reference": {
      "enabled": true,
      "patterns": {
        "customer": "/customers/{id}",
        "subscription": "/subscriptions/{id}",
        "payment_intent": "/payment_intents/{id}",
        "invoice": "/invoices/{id}"
      }
    }
  }
}
```

---

## Implementation Phases

### Phase 1: Core JSON Rendering

**Files to create:**
- `reference_templates/gateways/transforms/json_api_response.py`
- `reference_templates/gateways/templates/json_api_data.html`

**Tasks:**
1. Create response transform that formats JSON as syntax-highlighted HTML
2. Reuse color scheme from JSONPlaceholder: keys (#9cdcfe), strings (#ce9178), numbers (#b5cea8), booleans (#569cd6), links (#4ec9b0)
3. Handle all JSON types: null, boolean, number, string, array, object
4. Add breadcrumb navigation based on request path
5. Create HTML template matching JSONPlaceholder style

**Tests to pass:** E-1, E-2, E-5, E-6, E-7, E-11

---

### Phase 2: Full URL Detection (Strategy 1)

**Tasks:**
1. Implement URL detection for string values matching `https?://`
2. Convert detected URLs to gateway links
3. Implement base URL stripping (convert `https://api.github.com/...` to `/gateway/github/...`)
4. Handle URLs with query parameters and fragments

**Tests to pass:** GH-1, GH-2, GH-3, GH-7, GH-8, E-8, E-9, E-12

---

### Phase 3: Partial URL Detection (Strategy 2)

**Tasks:**
1. Implement detection of path-like strings starting with `/`
2. Match key patterns (`*_url`, `*_path`, `href`, `url`)
3. Prepend gateway prefix to detected paths
4. Handle partial URL in Stripe `url` field

**Tests to pass:** ST-6, E-16

---

### Phase 4: ID Reference Detection (Strategy 3)

**Tasks:**
1. Implement configurable ID pattern matching
2. Support simple patterns: `userId`, `postId`, `customer`
3. Support nested patterns: `owner.login`, `user.login`
4. Handle prefixed IDs (Stripe format: `cus_xxx`, `ch_xxx`)
5. Build URLs from pattern templates

**Tests to pass:** JP-1, JP-2, JP-3, JP-4, ST-1, ST-2, ST-3, ST-4, E-13, E-14

---

### Phase 5: Composite Reference Detection (Strategy 4)

**Tasks:**
1. Parse request path to extract context variables
2. Match context against configured regex patterns
3. Combine context with response data to build URLs
4. Handle issue/PR numbers in GitHub repo context

**Tests to pass:** GH-4, GH-5, GH-6, E-15, E-17

---

### Phase 6: Nested Object and Array Handling

**Tasks:**
1. Recursively process nested objects
2. Apply link detection at all nesting levels
3. Handle arrays of objects with link detection
4. Handle deeply nested structures

**Tests to pass:** JP-6, GH-10, E-3, E-4, ST-5, E-18, E-19

---

### Phase 7: Configuration System

**Tasks:**
1. Define configuration schema for link detection
2. Load configuration from gateway config
3. Create default configurations for JSONPlaceholder, GitHub, Stripe
4. Validate configuration at gateway startup

---

### Phase 8: Integration and Testing

**Tasks:**
1. Integration tests with all three validation servers
2. End-to-end testing of link navigation
3. Performance testing with large responses
4. Error handling and edge cases

---

## HTML Template Specification

### Color Scheme (CSS Classes)

```css
.json-key { color: #9cdcfe; }      /* Blue - object keys */
.json-string { color: #ce9178; }   /* Orange - string values */
.json-number { color: #b5cea8; }   /* Green - numeric values */
.json-boolean { color: #569cd6; }  /* Purple - true/false */
.json-null { color: #569cd6; }     /* Purple - null */
.json-link { color: #4ec9b0; text-decoration: underline; }  /* Teal - clickable links */
```

### Template Structure

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ gateway_name }} - {{ request_path }}</title>
    <style>
        /* Dark theme matching JSONPlaceholder */
        body {
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
        }
        pre {
            background: #252526;
            padding: 1.5rem;
            border-radius: 8px;
        }
        /* JSON syntax highlighting classes */
        /* Link hover states */
    </style>
</head>
<body>
    <div class="breadcrumb">{{ breadcrumb | safe }}</div>
    <div class="nav">{{ navigation | safe }}</div>
    <h1>{{ title }}</h1>
    <pre>{{ formatted_json | safe }}</pre>
</body>
</html>
```

---

## Open Questions

### Q1: How should conflicting link patterns be resolved?

**Context:** A field might match multiple detection strategies. For example, a URL field containing `https://api.github.com/users/1` could be detected as:
- Strategy 1: Full URL
- Strategy 2: Partial URL (if the key matches `*_url`)

**Options:**
1. First match wins (order strategies by priority)
2. Most specific match wins (full URL over partial)
3. Configuration explicitly sets priority per field
4. Error if multiple matches (strict mode)

**Recommendation:** Option 2 - most specific wins. Full URL > ID Reference > Partial URL > Composite.

---

### Q2: Should the gateway cache link detection configurations?

**Context:** Parsing configuration on every request adds latency.

**Options:**
1. No caching (simplest, matches current template behavior)
2. Request-scoped caching (parse once per request)
3. TTL-based caching (parse every N seconds)

**Recommendation:** Option 2 - parse configuration once at start of request processing.

---

### Q3: How should invalid/unreachable links be handled?

**Context:** A detected link might point to a resource that doesn't exist.

**Options:**
1. Always create the link (let user discover 404)
2. Validate links before rendering (expensive)
3. Mark links as "unverified" visually
4. Configuration option per gateway

**Recommendation:** Option 1 - always create links. Users can navigate and handle 404s.

---

### Q4: Should nested object paths be flattened for ID detection?

**Context:** For `owner.login` pattern matching, should we:
- Only match exact nested structure `{ "owner": { "login": "..." } }`
- Also match flattened keys like `"owner.login": "..."`

**Options:**
1. Only nested objects
2. Both nested and flattened
3. Configuration option

**Recommendation:** Option 1 - only match nested objects. Flattened keys are rare and ambiguous.

---

### Q5: How should the gateway handle non-JSON responses?

**Context:** Target server might return HTML, XML, or error pages.

**Options:**
1. Pass through non-JSON unchanged
2. Wrap in error template
3. Attempt to format as text/code

**Recommendation:** Option 2 - wrap in error template with raw content display.

---

### Q6: Should URL fields in arrays be treated differently?

**Context:** An array like `["https://a.com", "https://b.com"]` vs object with URL field.

**Options:**
1. Treat identically (link all URLs)
2. Only link URLs in objects (skip array primitives)
3. Configuration option per detection strategy

**Recommendation:** Option 1 - link all detected URLs regardless of context.

---

### Q7: How should self-referential links be handled?

**Context:** A response for `/gateway/api/users/1` might contain `"id": 1` which would link to the same page.

**Options:**
1. Create the link anyway (user can still click)
2. Detect self-references and skip linking
3. Style self-references differently (e.g., dimmed)

**Recommendation:** Option 1 - create all links consistently.

---

### Q8: Should the gateway support expandable object previews?

**Context:** Large nested objects could be collapsed by default.

**Options:**
1. No collapsing (render everything expanded)
2. Collapse objects beyond N levels
3. Collapse arrays beyond N items
4. Interactive expand/collapse with JavaScript

**Recommendation:** Defer to future enhancement. Start with Option 1 - fully expanded.

---

### Q9: How should pagination links be detected?

**Context:** APIs often have `next`, `previous`, `first`, `last` links for pagination.

**Options:**
1. Treat as regular URL fields
2. Special handling for pagination (render as navigation bar)
3. Detect `Link` header for pagination

**Recommendation:** Option 1 for initial implementation. Pagination UI is a future enhancement.

---

### Q10: What is the maximum URL length to detect?

**Context:** Extremely long URLs might be data URIs or malformed.

**Options:**
1. No limit
2. Maximum 2048 characters (browser limit)
3. Maximum 8192 characters (common server limit)

**Recommendation:** Option 2 - 2048 character limit matches browser URL bar.

---

## Success Criteria

1. **All test cases pass** for the three validation servers
2. **JSON is rendered identically** to the current JSONPlaceholder gateway style
3. **All four link detection strategies** work correctly
4. **Configuration is flexible** enough to support arbitrary REST APIs
5. **Performance is acceptable** (<200ms added latency for typical responses)
6. **Edge cases are handled gracefully** (nulls, empty values, malformed data)
7. **Links are navigable** and lead to valid gateway paths

---

## Files to Create

| File | Purpose |
|------|---------|
| `reference_templates/gateways/transforms/json_api_request.py` | Pass-through request transform |
| `reference_templates/gateways/transforms/json_api_response.py` | JSON→HTML response transform with link detection |
| `reference_templates/gateways/templates/json_api_data.html` | HTML template for JSON display |
| `reference_templates/gateways/link_detectors/__init__.py` | Link detector module |
| `reference_templates/gateways/link_detectors/full_url.py` | Full URL detection |
| `reference_templates/gateways/link_detectors/partial_url.py` | Partial URL detection |
| `reference_templates/gateways/link_detectors/id_reference.py` | ID reference detection |
| `reference_templates/gateways/link_detectors/composite.py` | Composite reference detection |
| `tests/test_json_api_gateway.py` | Unit tests |
| `tests/integration/test_json_api_gateway.py` | Integration tests |

## Files to Modify

| File | Changes |
|------|---------|
| `reference_templates/gateways.json` | Add json_api gateway configuration |
| `reference_templates/gateways.source.json` | Add json_api gateway source config |

---

## Appendix: Sample Rendered Output

### JSONPlaceholder Post Response

**Request:** `/gateway/jsonplaceholder/posts/1`

**Raw JSON:**
```json
{
  "userId": 1,
  "id": 1,
  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
  "body": "quia et suscipit\nsuscipit recusandae..."
}
```

**Rendered HTML (pre content):**
```html
{
  <span class="json-key">"userId"</span>: <a href="/gateway/jsonplaceholder/users/1" class="json-link"><span class="json-number">1</span></a>,
  <span class="json-key">"id"</span>: <span class="json-number">1</span>,
  <span class="json-key">"title"</span>: <span class="json-string">"sunt aut facere..."</span>,
  <span class="json-key">"body"</span>: <span class="json-string">"quia et suscipit..."</span>
}
```

### GitHub User Response

**Request:** `/gateway/github/users/octocat`

**Raw JSON (excerpt):**
```json
{
  "login": "octocat",
  "id": 1,
  "avatar_url": "https://github.com/images/error/octocat_happy.gif",
  "html_url": "https://github.com/octocat",
  "repos_url": "https://api.github.com/users/octocat/repos",
  "type": "User"
}
```

**Rendered HTML (pre content):**
```html
{
  <span class="json-key">"login"</span>: <span class="json-string">"octocat"</span>,
  <span class="json-key">"id"</span>: <span class="json-number">1</span>,
  <span class="json-key">"avatar_url"</span>: <a href="https://github.com/images/error/octocat_happy.gif" class="json-link"><span class="json-string">"https://github.com/images/error/octocat_happy.gif"</span></a>,
  <span class="json-key">"html_url"</span>: <a href="https://github.com/octocat" class="json-link"><span class="json-string">"https://github.com/octocat"</span></a>,
  <span class="json-key">"repos_url"</span>: <a href="/gateway/github/users/octocat/repos" class="json-link"><span class="json-string">"https://api.github.com/users/octocat/repos"</span></a>,
  <span class="json-key">"type"</span>: <span class="json-string">"User"</span>
}
```

### Stripe Charge Response

**Request:** `/gateway/stripe/charges/ch_1234`

**Raw JSON (excerpt):**
```json
{
  "id": "ch_1234",
  "amount": 2000,
  "currency": "usd",
  "customer": "cus_5678",
  "payment_intent": "pi_9012",
  "status": "succeeded"
}
```

**Rendered HTML (pre content):**
```html
{
  <span class="json-key">"id"</span>: <span class="json-string">"ch_1234"</span>,
  <span class="json-key">"amount"</span>: <span class="json-number">2000</span>,
  <span class="json-key">"currency"</span>: <span class="json-string">"usd"</span>,
  <span class="json-key">"customer"</span>: <a href="/gateway/stripe/customers/cus_5678" class="json-link"><span class="json-string">"cus_5678"</span></a>,
  <span class="json-key">"payment_intent"</span>: <a href="/gateway/stripe/payment_intents/pi_9012" class="json-link"><span class="json-string">"pi_9012"</span></a>,
  <span class="json-key">"status"</span>: <span class="json-string">"succeeded"</span>
}
```
