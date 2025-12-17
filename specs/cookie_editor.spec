# Cookie editor

## Cookie editor page is available from the default boot image
* Given the default boot image is loaded
* When I request the page /cookies
* Then the response status should be 200
* And the page should contain "Cookie Editor"
* And the page should contain "Current cookies"
* And the page should contain "Save cookie"

## Cookie editor links external assets
* Given the default boot image is loaded
* When I request the page /cookies
* Then the response status should be 200
* And the page should contain ".css"
* And the page should contain ".js"
* And the page should contain ".svg"
* And the page should contain "Delete"
