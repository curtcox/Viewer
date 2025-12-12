# AI Request Editor Server

The AI request editor allows users to inspect and adjust AI requests before sending them to the /ai endpoint.

## Server is available in default boot image
* Given the default boot image is loaded
* When I check the available servers
* Then the server "ai_editor" should be present

## Accessing ai_editor shows the editor page
* Given the default boot image is loaded
* When I request the resource /ai_editor
* Then the response should contain "AI request editor"
* And the response should contain "request_text"
* And the response should contain "AI response"

## Request payload is embedded for editing
* Given the default boot image is loaded
* When I submit a form post to /ai_editor with payload '\{"request_text": "Hello", "context_data": \{"foo": "bar"\}\}'
* Then the response should contain "Hello"
* And the response should contain "\"foo\": \"bar\""

## Navigation and information menu are present
* Given the default boot image is loaded
* When I request the resource /ai_editor
* Then the response should contain "/search"
* And the response should contain "Server Events"

## Server rejects being used in a chain
* Given the default boot image is loaded
* And a server named "test-chain" that returns "chain-output"
* When I request the resource /ai_editor/test-chain
* Then the response status should be "400"
* And the response should contain "cannot be used in a server chain"
