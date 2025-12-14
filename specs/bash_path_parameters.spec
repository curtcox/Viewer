# Bash path parameters

These tests verify that bash servers using $1 correctly receive path parameters
and chain input from subsequent path segments.

## Awk server accepts pattern from path parameter

* Given the awk server is available
* And a CID containing "word1 word2 word3"
* When I request the awk server with pattern "{print $1}" and the stored CID
* Then the response should redirect to a CID
* And the CID content should contain "word1"

## Awk server accepts CID pattern

* Given the awk server is available
* And a CID containing "{print $2}" as pattern_cid
* And a CID containing "a1 b1 c1"
* When I request the awk server with CID pattern and the stored CID
* Then the response should redirect to a CID
* And the CID content should contain "b1"

## Awk server provides input to left server

* Given the awk server is available
* And a wrapping server named "awk-wrapper" that wraps payload with "AWK:"
* And a CID containing "hello world"
* When I request the resource /awk-wrapper/awk/{print $1}/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "AWK:hello"

## Sed server accepts expression from path parameter

* Given the sed server is available
* And a CID containing "hello world"
* When I request the sed server with expression "s/world/universe/" and the stored CID
* Then the response should redirect to a CID
* And the CID content should contain "hello universe"

## Sed server provides input to left server

* Given the sed server is available
* And a wrapping server named "sed-wrapper" that wraps payload with "SED:"
* And a CID containing "foo bar"
* When I request the resource /sed-wrapper/sed/s%2Fbar%2Fbaz%2F/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "SED:foo baz"

## Grep server accepts pattern from path parameter

* Given the grep server is available
* And a CID containing multiline grep test data
* When I request the grep server with pattern "apple" and the stored CID
* Then the response should redirect to a CID
* And the CID content should contain "apple"
* And the CID content should not contain "banana"

## Grep server provides input to left server

* Given the grep server is available
* And a wrapping server named "grep-wrapper" that wraps payload with "GREP:"
* And a CID containing multiline grep test data
* When I request the resource /grep-wrapper/grep/apple/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "GREP:"
* And the CID content should contain "apple"

## Jq server accepts filter from path parameter

* Given the jq server is available
* And a CID containing JSON data '{"name": "test", "value": 42}'
* When I request the jq server with filter ".name" and the stored CID
* Then the response should redirect to a CID
* And the CID content should contain "test"

## Jq server provides input to left server

* Given the jq server is available
* And a wrapping server named "jq-wrapper" that wraps payload with "JQ:"
* And a CID containing JSON data '{"key": "secret"}'
* When I request the resource /jq-wrapper/jq/.key/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "JQ:"
* And the CID content should contain "secret"

## Standard bash server without $1 still works

* Given a simple bash server without path parameters
* And a server named "input-source" that returns "input data"
* When I request the resource /simple-bash/input-source
* Then the response should redirect to a CID
* And the CID content should contain "input data"
