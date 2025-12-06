# URL Editor Server

The URL Editor server provides an interactive interface for building and testing
chained server URLs. It stores state in the browser URL fragment.

## Server is available in default boot image
* Given the default boot image is loaded
* When I check the available servers
* Then the server "urleditor" should be present

## Accessing urleditor without parameters shows editor page
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "URL Editor"
* And the response should contain "url-editor"
* And the response should contain "ace.edit"

## Accessing urleditor with subpath redirects to fragment
* Given the default boot image is loaded
* When I request the resource /urleditor/echo/test
* Then the response should be a redirect
* And the redirect location should be "/urleditor#/echo/test"

## Server rejects being used in a chain
* Given the default boot image is loaded
* And a server named "test-chain" that returns "chain-output"
* When I request the resource /urleditor/test-chain
* Then the response should contain "does not support URL chaining"
* And the response status should be "400"

## URL Editor page has required elements
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "URL Editor"
* And the response should contain "Line Indicators"
* And the response should contain "Line Previews"
* And the response should contain "Copy URL"
* And the response should contain "Open URL"
* And the response should contain "Final Output Preview"

## URL Editor page includes Ace editor
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "ace.edit"
* And the response should contain "url-editor"
* And the response should contain "ace/theme/"

## URL Editor JavaScript handles URL normalization
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "normalizeUrl"
* And the response should contain "updateFromEditor"
* And the response should contain "updateHash"

## URL Editor has three-column layout
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "editor-section"
* And the response should contain "indicators-section"
* And the response should contain "preview-section"
* And the response should contain "grid-template-columns"
