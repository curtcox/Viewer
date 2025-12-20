# Gateway Server

These tests verify that the gateway server acts as a proxy to external REST APIs,
with optional request and response transformations.

## Gateway displays examples page without target server
* Given the default server "gateway" is available
* When I request the resource /gateway
* Then the response content type should be "text/html"
* And the response should contain "Gateway Server"
* And the response should contain "API Examples"
* And the response should contain "GitHub API"
* And the response should contain "OpenAI API"

## Gateway examples include required REST APIs
* Given the default server "gateway" is available
* When I request the resource /gateway
* Then the response should contain "GitHub API"
* And the response should contain "OpenAI API"
* And the response should contain "Anthropic API"
* And the response should contain "Google"
* And the response should contain "OpenRouter"
* And the response should contain "Eleven Labs"
* And the response should contain "Vercel"

## Gateway examples include auth requirement indicators
* Given the default server "gateway" is available
* When I request the resource /gateway
* Then the response should contain "API Key Required"
* And the response should contain "No Auth"

## Gateway examples include usage instructions
* Given the default server "gateway" is available
* When I request the resource /gateway
* Then the response should contain "How it Works"
* And the response should contain "target_server"
* And the response should contain "request_transform"
* And the response should contain "response_transform"

## Gateway examples include clickable API links
* Given the default server "gateway" is available
* When I request the resource /gateway
* Then the response should contain "/gateway?target_server=https://api.github.com"
* And the response should contain "/gateway?target_server=https://api.openai.com"
* And the response should contain "/gateway?target_server=https://api.anthropic.com"
