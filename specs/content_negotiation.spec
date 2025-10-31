# Content negotiation

## Extension overrides provide alternate representations
* When I request the resource /aliases.json
* The response status should be 200
* The response content type should be application/json
* The response JSON should include alias records

## Detail endpoints expose structured JSON
* When I request the resource /servers/ai_stub.json
* The response status should be 200
* The response content type should be application/json
* The response JSON should describe a server named ai_stub

## Accept headers request alternate representations
* When I request the resource /aliases with accept header text/plain
* The response status should be 200
* The response content type should be text/plain
