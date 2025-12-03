# Authorization

## All requests pass through authorization check
* When I request the page /
* Path coverage: /
* The response status should be 200
* When I request the page /aliases
* The response status should be 200
* When I request the page /servers
* The response status should be 200

## Authorization allows POST requests
* When I POST to /aliases/new with form data name "test-alias" and target "/test"
* The response should contain Create New Alias

## Authorization allows API requests
* When I request the page /api/routes
* The response status should be 200

## Source link in footer points to authorization module
* When I request the page /
* The page should contain User management is handled externally
* The page should contain href="/source/authorization.py"

## Authorization returns JSON errors for API paths
tags: authorization, api
* Given authorization is configured to reject requests with 401
* When I request the page /api/test with Accept header "application/json"
* The response status should be 401
* The response should be valid JSON
* The response should contain error
* The response should contain Authorization failed

## Authorization returns HTML errors for web pages
tags: authorization, html
* Given authorization is configured to reject requests with 403
* When I request the page / with Accept header "text/html"
* The response status should be 403
* The page should contain 403
* The page should contain Forbidden

## Authorization returns text errors for plain text requests
tags: authorization, text
* Given authorization is configured to reject requests with 401
* When I request the page /test with Accept header "text/plain"
* The response status should be 401
* The response should contain Error 401
