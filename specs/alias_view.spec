# Alias view

## Alias detail page displays basic information
* Given there is an alias named "test-alias" pointing to /test-target
* When I visit the alias detail page for "test-alias"
* Then the response status should be 200
* And the page should contain "Alias Details"
* And the page should contain "test-alias"
* And the page should contain "/test-target"

## Alias detail page shows navigation buttons
* Given there is an alias named "nav-test" pointing to /guides
* When I visit the alias detail page for "nav-test"
* Then the response status should be 200
* And the page should contain "Back to Aliases"
* And the page should contain "Edit Alias"

## Alias detail page displays status badge
* Given there is an enabled alias named "active-alias" pointing to /active
* When I visit the alias detail page for "active-alias"
* Then the response status should be 200
* And the page should contain "Enabled"

## Alias detail page shows definition section
* Given there is an alias named "def-test" pointing to /definition-target
* When I visit the alias detail page for "def-test"
* Then the response status should be 200
* And the page should contain "Alias Definition"
* And the page should contain "How it Works"
