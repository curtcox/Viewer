# Upload Templates

## Upload page displays template options when configured
* Given I am signed in to the workspace
* And I have upload templates configured
* When I navigate to /upload
* Then I should see "Start from a Template" label
* And I should see template selection buttons

## Upload page shows template status link
* Given I am signed in to the workspace
* And I have upload templates configured
* When I navigate to /upload
* Then I should see a link to "/variables/templates?type=uploads"
* And the link should show the template count

## Upload page hides templates when none configured
* Given I am signed in to the workspace
* And I have no upload templates configured
* When I navigate to /upload
* Then I should not see "Start from a Template" buttons

## Template content populates text field when selected
* Given I am signed in to the workspace
* And I have an upload template named "Hello World" with content "Hello, World!"
* When I navigate to /upload
* And I click the "Hello World" template button
* Then the text content field should contain "Hello, World!"

## Upload templates support CID references
* Given I am signed in to the workspace
* And I have a CID containing "Template content from CID"
* And I have an upload template referencing that CID
* When I navigate to /upload
* Then the template should be available for selection
* And clicking it should populate with the CID content
