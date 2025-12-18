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
* Then the response should redirect to a CID
* And the CID content should contain "does not support URL chaining"

## URL Editor page has required elements
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "URL Editor"
* And the response should contain "Line Indicators"
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

## URL Editor with multiple path elements shows all previews
* Given the default boot image is loaded
* When I navigate to /urleditor in a browser
* And I enter "echo" in the editor
* Then the preview for "echo" should show size and MIME type
* When I add "markdown" to the editor on a new line
* Then the preview for "echo" should show size and MIME type
* And the preview for "markdown" should show size and MIME type
* When I add "shell" to the editor on a new line
* Then the preview for "echo" should show size and MIME type
* And the preview for "markdown" should show size and MIME type
* And the preview for "shell" should show size and MIME type
* And the final output preview should show content
* And the URL fragment should be "/echo/markdown/shell"

## URL Editor validates each path element with indicators
* Given the default boot image is loaded
* When I navigate to /urleditor in a browser
* And I enter "echo" in the editor
* Then the indicator for "echo" should show it is valid
* And the indicator for "echo" should show it is a known server
* And the indicator for "echo" should show the implementation language
* When I add "invalid-server" to the editor on a new line
* Then the indicator for "invalid-server" should show it is not a known server
* When I add a CID like "AAAAAAcXbQDQ" to the editor on a new line
* Then the indicator for the CID should show it is a valid CID

## URL Editor shows preview links for each path element
* Given the default boot image is loaded
* When I navigate to /urleditor#/echo/markdown/shell
* Then the preview for "echo" should have a link to "/echo"
* And the preview for "markdown" should have a link to "/echo/markdown"
* And the preview for "shell" should have a link to "/echo/markdown/shell"
* When I click the preview link for "markdown"
* Then a new tab should open with URL "/echo/markdown"

## URL Editor handles long URL chains correctly
* Given the default boot image is loaded
* When I navigate to /urleditor in a browser
* And I enter a URL chain with 5 path elements
* Then all 5 preview rows should be displayed
* And each preview row should show size, MIME type, and preview text
* And each preview row should have a clickable link
* And the final output preview should show the complete chain output
* And the URL fragment should contain all 5 path elements

## URL Editor Copy URL button works
* Given the default boot image is loaded
* When I navigate to /urleditor#/echo/test
* And I click the "Copy URL" button
* Then the URL "/echo/test" should be copied to clipboard

## URL Editor Open URL button works
* Given the default boot image is loaded
* When I navigate to /urleditor#/echo/test
* And I click the "Open URL" button
* Then a new tab should open with URL "/echo/test"

## URL Editor handles newlines as path separators
* Given the default boot image is loaded
* When I navigate to /urleditor in a browser
* And I enter "echo" on line 1
* And I enter "markdown" on line 2
* And I enter "shell" on line 3
* Then the URL fragment should be "/echo/markdown/shell"
* And there should be 3 preview rows displayed

## URL Editor CID literal conversion
* Given the default boot image is loaded
* When I navigate to /urleditor in a browser
* And I enter "#ls" in the editor
* Then the text "#ls" should be converted to a CID format
* And the indicator should show it is a CID literal
* And the URL fragment should contain the CID literal

## URL Editor uses /meta endpoint for segment information
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "fetchMetadata"
* And the response should contain "/meta/"
* And the response should contain "updateIndicatorsFromMetadata"

## URL Editor has verbose hover text for indicators
* Given the default boot image is loaded
* When I request the resource /urleditor
* Then the response should contain "valid URL path segment"
* And the response should contain "can accept chained input"
* And the response should contain "Content Identifier"
