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
