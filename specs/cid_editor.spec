# CID Editor Controls

## Editor shows convert to CID button for regular content
* When I request the page /variables/new
* Path coverage: /variables/new
* The response status should be 200
* The page should contain Convert to CID

## Editor shows expand CID button for CID content with embedded content
* Given there is a variable named "test-cid-var" with definition "AAAAAAAA"
* When I request the page /variables/test-cid-var/edit
* The response status should be 200
* The page should contain Expand CID

## CID check API returns not_a_cid for regular text
* When I POST to /api/cid/check with JSON content "Hello World"
* The response status should be 200
* The response should contain is_cid false
* The response should contain status not_a_cid

## CID check API returns content_embedded for small CID
* When I POST to /api/cid/check with JSON content "AAAAAAAEdGVzdA"
* The response status should be 200
* The response should contain is_cid true
* The response should contain status content_embedded
* The response should contain has_content true

## CID generate API creates CID for content
* When I POST to /api/cid/generate with JSON content "test"
* The response status should be 200
* The response should contain cid_value
* The response should contain cid_link_html
