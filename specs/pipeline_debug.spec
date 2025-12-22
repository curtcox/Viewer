# Pipeline Debug Mode

These tests verify the pipeline debug mode functionality, which provides
detailed information about each segment in a pipeline when ?debug=true
is included in the request URL.

## Simple server-CID pipeline with debug

* Given a server named "echo" that echoes its input with prefix "received:"
* And a CID containing "test-input"
* When I request /{echo server}/{stored CID}?debug=true
* Then the response should be JSON
* And the response should contain 2 segment entries
* And segment 0 should have type "server"
* And segment 0 should have server_name "echo"
* And segment 1 should have type "cid"
* And segment 1 should have is_valid_cid true

## Chained servers pipeline with debug

* Given a server named "first" that returns "hello"
* And a server named "second" that echoes its input with prefix "got:"
* When I request /second/first?debug=true
* Then the response should be JSON
* And the response should contain 2 segment entries
* And segment 0 should have server_name "second"
* And segment 1 should have server_name "first"

## Three-level pipeline with debug

* Given a server named "s1" that returns "one"
* And a server named "s2" that echoes its input with prefix "two:"
* And a server named "s3" that echoes its input with prefix "three:"
* When I request /s3/s2/s1?debug=true
* Then the response should be JSON
* And the response should contain 3 segment entries
* And segment 0 should have server_name "s3"
* And segment 1 should have server_name "s2"
* And segment 2 should have server_name "s1"

## Debug response defaults to JSON

* Given a server named "simple" that returns "data"
* When I request /simple/input?debug=true
* Then the response Content-Type should be "application/json"
* And the response should be valid JSON

## Debug parameter accepts 1

* Given a server named "echo" that returns "data"
* When I request /echo/input?debug=1
* Then the response should be JSON
* And the response should contain segment entries

## Debug parameter accepts yes

* Given a server named "echo" that returns "data"
* When I request /echo/input?debug=yes
* Then the response should be JSON
* And the response should contain segment entries

## Debug parameter accepts on

* Given a server named "echo" that returns "data"
* When I request /echo/input?debug=on
* Then the response should be JSON
* And the response should contain segment entries

## Debug parameter is case insensitive

* Given a server named "echo" that returns "data"
* When I request /echo/input?debug=TRUE
* Then the response should be JSON
* And the response should contain segment entries

## Debug parameter rejects random value

* Given a server named "echo" that returns "data"
* When I request /echo/input?debug=random
* Then the response should NOT be JSON debug output
* And the response status should be a redirect

## Debug shows intermediate outputs

* Given a server named "s1" that returns "first"
* And a server named "s2" that echoes its input with prefix "second:"
* When I request /s2/s1?debug=true
* Then the response should be JSON
* And segment 1 should have intermediate_output "first"
* And the response final_output should contain "second:"

## Debug shows errors for invalid segments

* Given a CID containing "some content"
* When I request /nonexistent-server/{stored CID}?debug=true
* Then the response should be JSON
* And segment 0 should have type "server"
* And segment 0 should have errors containing "server not found"

## Single segment debug request

* Given a server named "solo" that returns "alone"
* When I request /solo?debug=true
* Then the response should be JSON
* And the response should contain 1 segment entry
* And segment 0 should have type "server"

## Python server with debug shows language

* Given a server named "py-server" that returns "python-result"
* When I request /py-server/input?debug=true
* Then the response should be JSON
* And segment 0 should have implementation_language "python"

## Debug shows chaining support

* Given a server named "chain-test" that returns "chainable"
* When I request /chain-test/input?debug=true
* Then the response should be JSON
* And segment 0 should have supports_chaining true

## Debug success field is true for valid pipeline

* Given a server named "valid" that returns "ok"
* When I request /valid/input?debug=true
* Then the response should be JSON
* And the response success should be true

## Debug success field is false for pipeline with errors

* When I request /nonexistent-server/input?debug=true
* Then the response should be JSON
* And the response success should be false

## CID literal with debug shows execution type

* Given a CID containing python server code that returns "literal-result"
* When I request /{stored CID}.py/next?debug=true
* Then the response should be JSON
* And segment 0 should have resolution_type "execution"

## Parameter segment with debug shows literal type

* Given a server named "param-test" that echoes its input with prefix "got:"
* When I request /param-test/my-parameter?debug=true
* Then the response should be JSON
* And segment 1 should have type "parameter"
* And segment 1 should have resolution_type "literal"
