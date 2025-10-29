# Server form page

## New server form is accessible
* When I request the page /servers/new
* The response status should be 200
* The page should contain Create New Server
* The page should contain Server Configuration
* The page should contain Back to Servers

## Server form stays available without a user session
* When I request the page /servers/new as user "alternate-user"
* The response status should be 200
* The page should contain Create New Server
* When I request the page /servers/new without a user session
* The response status should be 200
* The page should contain Create New Server
