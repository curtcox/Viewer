# Server command chaining

These tests verify that servers can be chained together, passing output from one
server as input to another. The chaining patterns are:
- /s/CID - server s receives contents of CID as input
- /s2/s1 - server s2 receives output of s1 as input
- /s2/s1/CID - server s2 receives output of s1 (which receives CID contents) as input

## Chained server receives CID content as input
* Given a server named "processor" that echoes its input with prefix "processed:"
* And a CID containing "raw-data"
* When I request the processor server with the stored CID
* Then the response should redirect to a CID
* And the CID content should be "processed:raw-data"

## Two servers chain together
* Given a server named "first" that returns "hello"
* And a server named "second" that echoes its input with prefix "from-first:"
* When I request the chained resource /second/first
* Then the response should redirect to a CID
* And the CID content should be "from-first:hello"

## Three-level server chain with CID input
* Given a server named "level1" that echoes its input with prefix "L1:"
* And a server named "level2" that echoes its input with prefix "L2:"
* And a CID containing "initial"
* When I request the level2/level1 servers with the stored CID
* Then the response should redirect to a CID
* And the CID content should be "L2:L1:initial"

## Default markdown server consumes chained CID input
* Given the default server "markdown" is available
* And a CID containing "# Gauge Markdown"
* When I request the resource /markdown/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "Gauge Markdown"
* And the CID content should contain "markdown-body"

## Default markdown server output chains to the left
* Given the default server "markdown" is available
* And a wrapping server named "md-wrapper" that wraps payload with "md::"
* And a CID containing "# Wrapped Markdown"
* When I request the resource /md-wrapper/markdown/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "md::"
* And the CID content should contain "Wrapped Markdown"

## Default shell server consumes chained CID input
* Given the default server "shell" is available
* And a CID containing "echo gauge shell"
* When I request the resource /shell/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "echo gauge shell"
* And the CID content should contain "exit"

## Default shell server output chains to the left
* Given the default server "shell" is available
* And a wrapping server named "shell-wrapper" that wraps payload with "sh::"
* And a CID containing "echo wrapped shell"
* When I request the resource /shell-wrapper/shell/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "sh::"
* And the CID content should contain "echo wrapped shell"

## Default ai_stub server consumes chained CID input
* Given the default server "ai_stub" is available
* And a CID containing "Gauge adjustment"
* When I request the resource /ai_stub/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "Gauge adjustment"
* And the CID content should contain "message"

## Default ai_stub server output chains to the left
* Given the default server "ai_stub" is available
* And a wrapping server named "ai-wrapper" that wraps payload with "ai::"
* And a CID containing "Gauge wrapper"
* When I request the resource /ai-wrapper/ai_stub/{stored CID}
* Then the response should redirect to a CID
* And the CID content should contain "ai::"
* And the CID content should contain "Gauge wrapper"
