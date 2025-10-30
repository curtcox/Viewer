# Content negotiation

## Extension overrides provide alternate representations
* When I request the resource /aliases.json
* The response status should be 200
* The response content type should be application/json

## Accept headers request alternate representations
* When I request the resource /aliases with accept header text/plain
* The response status should be 200
* The response content type should be text/plain
