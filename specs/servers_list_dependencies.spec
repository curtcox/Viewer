# Servers list page dependencies

The servers list page displays variables and secrets that match server main parameters.

## Servers list page shows variable and secret dependencies
Tags: servers, dependencies

* Given there is a variable named city with value San Francisco
* And there is a secret named api_key with value test-key-123
* And there is a server named weather_service with main parameters city and api_key
* When I request the page /servers
* The response status should be 200
* The page should contain 'href="/variables/city" class="badge'
* The page should contain 'href="/secrets/api_key" class="badge'

## Servers list page shows only matching dependencies
Tags: servers, dependencies

* Given there is a variable named city with value San Francisco
* And there is a variable named country with value USA
* And there is a secret named api_key with value test-key-123
* And there is a server named weather_service with main parameters city and api_key
* When I request the page /servers
* The response status should be 200
* The page should contain 'href="/variables/city" class="badge'
* The page should contain 'href="/secrets/api_key" class="badge'
* The page should not contain 'href="/variables/country" class="badge'

## Servers list page handles servers without dependencies
Tags: servers, dependencies

* Given there is a variable named city with value San Francisco
* And there is a server named echo_service with main parameter message
* When I request the page /servers
* The response status should be 200
* The page should contain echo_service
* The page should not contain 'href="/variables/city" class="badge'
