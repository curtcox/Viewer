# Template Creation and Usage

This specification documents template creation workflow coverage.

## Template creation specs point to integration tests

The comprehensive template creation and usage tests are in:

Tests in tests/test_generate_boot_image.py (unit tests)
Tests in tests/integration/test_boot_image_dynamic_content.py (integration tests)
Specs in specs/upload_templates.spec (upload template specs)

The integration tests verify adding aliases, servers, variables, and templates to boot.source.json and templates.source.json, boot image generation, booting with CID, and creating entities from templates.

* When I request the page /
* The response status should be 200

## New alias form is accessible
* When I navigate to /aliases/new
* The response status should be 200
* The page should contain Create New Alias

## New variable form is accessible
* When I request the page /variables/new
* The response status should be 200
* The page should contain Create New Variable

## New server form is accessible
* When I request the page /servers/new
* The response status should be 200
* The page should contain Create New Server
