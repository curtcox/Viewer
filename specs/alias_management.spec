# Alias management

## Users can create aliases through the form
* Given I am signed in to the workspace
* When I navigate to /aliases/new
* Then I can enter an alias name and target path
* And submitting the form creates the alias

## Users can edit existing aliases
* Given there is an alias named "docs" pointing to /guides
* When I visit /aliases/docs/edit
* Then I can update the alias target and save the changes

## Users can view alias details
* When I request the page /aliases/ai
* Path coverage: /aliases/ai
* The response status should be 200
* The page should contain Alias Details
* The page should contain Edit Alias

## Aliases list shows available shortcuts
* When I request the page /aliases
* Path coverage: /aliases
* The response status should be 200
* The page should contain Aliases
* The page should contain New Alias
