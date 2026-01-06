# Default boot servers

These tests verify that servers loaded from the default boot CID work correctly.

## Reflect server returns HTML output
* Given the reflect server is available
* When I request the resource /reflect
* Then the response status should be 200
* And the response content type should be text/html
* And the page should contain "request"
* And the page should contain "context"

## Shell server shows form on GET request
* Given the shell server is available
* When I request the resource /shell
* Then the response status should be 200
* And the response content type should be text/html
* And the page should contain "form"
* And the page should contain "command"
