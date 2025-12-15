# GitHub PR Import and Export

## Users can export definitions to GitHub PRs
* Given an origin site with a server named "test-server" returning "Hello from origin"
* When I export the server to a GitHub PR with mock repository "owner/repo"
* Then the PR should be created successfully
* And the PR should contain the boot image file with the exported server

## Users can import definitions from GitHub PRs
* Given a GitHub PR with mock URL containing a server named "imported-server"
* When I import from the GitHub PR URL
* Then the destination site should have a server named "imported-server"
* And executing "/imported-server" on the destination site should return "Hello from PR"

## Export shows helpful errors when GitHub access fails
* Given an origin site with a server named "test-server" returning "Test"
* When I attempt to export to GitHub PR without a token
* Then I should see an error message "GitHub token is required"

## Import shows helpful errors when PR format is wrong
* Given a GitHub PR URL that doesn't modify the boot image file
* When I attempt to import from that PR URL
* Then I should see an error message "does not modify the boot image file"
