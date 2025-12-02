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

## CID literal executes python content
* Given a CID containing python server code that returns "literal-python"
* When I request the resource /{stored CID}.py/next
* Then the response should redirect to a CID
* And the CID content should be "literal-python"

## CID literal executes bash content
* Given a CID containing bash server code that echoes "literal-bash"
* When I request the resource /{stored CID}.sh/more
* Then the response should contain "literal-bash"

## Python CID literal output chains into bash CID literal
* Given a python CID literal server that returns "py-literal"
* And a bash CID literal server that prefixes input with "bash:"
* When I request the resource /{bash server CID}.sh/{python server CID}.py/final
* Then the response should contain "bash:py-literal"

## Bash CID literal output chains into python CID literal
* Given a bash CID literal server that echoes "bash-into-python"
* And a python CID literal server that wraps its payload with "py::"
* When I request the resource /{python server CID}.py/{bash server CID}.sh/finish
* Then the response should redirect to a CID
* And the CID content should be "py::bash-into-python"
