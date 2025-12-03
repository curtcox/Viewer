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
* When I request the resource /markdown/\{stored CID\}
* Then the response should redirect to a CID
* And the CID content should contain "Gauge Markdown"
* And the CID content should contain "markdown-body"

## Default markdown server output chains to the left
* Given the default server "markdown" is available
* And a wrapping server named "md-wrapper" that wraps payload with "md::"
* And a CID containing "# Wrapped Markdown"
* When I request the resource /md-wrapper/markdown/\{stored CID\}
* Then the response should redirect to a CID
* And the CID content should contain "md::"
* And the CID content should contain "Wrapped Markdown"

## Default shell server consumes chained CID input
* Given the default server "shell" is available
* And a CID containing "echo gauge shell"
* When I request the resource /shell/\{stored CID\}
* Then the response should redirect to a CID
* And the CID content should contain "echo gauge shell"
* And the CID content should contain "exit"

## Default shell server output chains to the left
* Given the default server "shell" is available
* And a wrapping server named "shell-wrapper" that wraps payload with "sh::"
* And a CID containing "echo wrapped shell"
* When I request the resource /shell-wrapper/shell/\{stored CID\}
* Then the response should redirect to a CID
* And the CID content should contain "sh::"
* And the CID content should contain "echo wrapped shell"

## Default ai_stub server consumes chained CID input
* Given the default server "ai_stub" is available
* And a CID containing "Gauge adjustment"
* When I request the resource /ai_stub/\{stored CID\}
* Then the response should redirect to a CID
* And the CID content should contain "Gauge adjustment"
* And the CID content should contain "message"

## Default ai_stub server output chains to the left
* Given the default server "ai_stub" is available
* And a wrapping server named "ai-wrapper" that wraps payload with "ai::"
* And a CID containing "Gauge wrapper"
* When I request the resource /ai-wrapper/ai_stub/\{stored CID\}
* Then the response should redirect to a CID
* And the CID content should contain "ai::"
* And the CID content should contain "Gauge wrapper"

## CID literal executes python content
* Given a CID containing python server code that returns "literal-python"
* When I request the resource /\{stored CID\}.py/next
* Then the response should redirect to a CID
* And the CID content should be "literal-python"

## CID literal executes bash content
* Given a CID containing bash server code that echoes "literal-bash"
* When I request the resource /\{stored CID\}.sh/more
* Then the response should contain "literal-bash"

## Python CID literal output chains into bash CID literal
* Given a python CID literal server that returns "py-literal"
* And a bash CID literal server that prefixes input with "bash:"
* When I request the resource /\{bash server CID\}.sh/\{python server CID\}.py/final
* Then the response should contain "bash:py-literal"

## Bash CID literal output chains into python CID literal
* Given a bash CID literal server that echoes "bash-into-python"
* And a python CID literal server that wraps its payload with "py::"
* When I request the resource /\{python server CID\}.py/\{bash server CID\}.sh/finish
* Then the response should redirect to a CID
* And the CID content should be "py::bash-into-python"

## Clojure CID literal output chains into python CID literal
* Given a clojure CID literal server that emits "clj->python"
* And a python CID literal server that prefixes its payload with "py:"
* When I request the resource /\{python server CID\}.py/\{clojure server CID\}.clj/final
* Then the response should redirect to a CID
* And the CID content should be "py:clj->python"

## Clojure CID literal output chains into bash CID literal
* Given a clojure CID literal server that emits "clj->bash"
* And a bash CID literal server that prefixes its payload with "bash:"
* When I request the resource /\{bash server CID\}.sh/\{clojure server CID\}.clj/result
* Then the response should contain "bash:clj->bash"

## Bash CID literal output chains into clojure CID literal
* Given a bash CID literal server that echoes "bash->clj"
* And a clojure CID literal server that prefixes its payload with "clj:"
* When I request the resource /\{clojure server CID\}.clj/\{bash server CID\}.sh
* Then the response should contain "clj:bash->clj"

## Python CID literal output chains into clojure CID literal
* Given a python CID literal server that returns "py->clj"
* And a clojure CID literal server that prefixes its payload with "clj:"
* When I request the resource /\{clojure server CID\}.clj/\{python server CID\}.py
* Then the response should contain "clj:py->clj"

## Clojure CID literal output chains into clojure CID literal
* Given a clojure CID literal server that emits "clj-right"
* And a clojure CID literal server that prefixes its payload with "clj:"
* When I request the resource /\{left clojure server CID\}.clj/\{right clojure server CID\}.clj
* Then the response should contain "clj:clj-right"

## Clojure CID literal with no extension executes
* Given a clojure CID literal server stored without an extension that emits "clj-noext"
* When I request the resource /\{clojure CID\}/tail
* Then the response should contain "clj-noext"

## ClojureScript CID literal output chains into python CID literal
* Given a clojurescript CID literal server that emits "cljs->python"
* And a python CID literal server that prefixes its payload with "py:"
* When I request the resource /\{python server CID\}.py/\{clojurescript server CID\}.cljs/final
* Then the response should redirect to a CID
* And the CID content should be "py:cljs->python"

## ClojureScript CID literal output chains into bash CID literal
* Given a clojurescript CID literal server that emits "cljs->bash"
* And a bash CID literal server that prefixes its payload with "bash:"
* When I request the resource /\{bash server CID\}.sh/\{clojurescript server CID\}.cljs/result
* Then the response should contain "bash:cljs->bash"

## ClojureScript CID literal output chains into clojurescript CID literal
* Given a clojurescript CID literal server that emits "cljs-right"
* And a clojurescript CID literal server that prefixes its payload with "cljs:"
* When I request the resource /\{left clojurescript server CID\}.cljs/\{right clojurescript server CID\}.cljs
* Then the response should contain "cljs:cljs-right"

## Python CID literal output chains into clojurescript CID literal
* Given a python CID literal server that returns "py->cljs"
* And a clojurescript CID literal server that prefixes its payload with "cljs:"
* When I request the resource /\{clojurescript server CID\}.cljs/\{python server CID\}.py
* Then the response should contain "cljs:py->cljs"

## Bash CID literal output chains into clojurescript CID literal
* Given a bash CID literal server that echoes "bash->cljs"
* And a clojurescript CID literal server that prefixes its payload with "cljs:"
* When I request the resource /\{clojurescript server CID\}.cljs/\{bash server CID\}.sh
* Then the response should contain "cljs:bash->cljs"

## Named clojurescript server receives chained python input
* Given a server named "cljs-chain" defined in /servers that prefixes its payload with "cljs:"
* And a python CID literal server that returns "named->cljs"
* When I request the resource /cljs-chain/\{python server CID\}.py/output
* Then the response should contain "cljs:named->cljs"

## ClojureScript CID literal with no extension executes
* Given a clojurescript CID literal server stored without an extension that emits "cljs-noext"
* When I request the resource /\{clojurescript CID\}/tail
* Then the response should contain "cljs-noext"

## TypeScript CID literal output chains into python CID literal
* Given a TypeScript CID literal server that emits "ts->python"
* And a python CID literal server that prefixes its payload with "py:"
* When I request the resource /\{python server CID\}.py/\{typescript server CID\}.ts/final
* Then the response should redirect to a CID
* And the CID content should be "py:ts->python"

## TypeScript CID literal output chains into bash CID literal
* Given a TypeScript CID literal server that emits "ts->bash"
* And a bash CID literal server that prefixes its payload with "bash:"
* When I request the resource /\{bash server CID\}.sh/\{typescript server CID\}.ts/result
* Then the response should contain "bash:ts->bash"

## TypeScript CID literal output chains into TypeScript CID literal
* Given a TypeScript CID literal server that emits "ts-right"
* And a TypeScript CID literal server that prefixes its payload with "ts:"
* When I request the resource /\{left typescript server CID\}.ts/\{right typescript server CID\}.ts
* Then the response should contain "ts:ts-right"

## Python CID literal output chains into TypeScript CID literal
* Given a python CID literal server that returns "py->ts"
* And a TypeScript CID literal server that prefixes its payload with "ts:"
* When I request the resource /\{typescript server CID\}.ts/\{python server CID\}.py
* Then the response should contain "ts:py->ts"

## Bash CID literal output chains into TypeScript CID literal
* Given a bash CID literal server that echoes "bash->ts"
* And a TypeScript CID literal server that prefixes its payload with "ts:"
* When I request the resource /\{typescript server CID\}.ts/\{bash server CID\}.sh
* Then the response should contain "ts:bash->ts"

## Named TypeScript server receives chained python input
* Given a server named "ts-chain" defined in /servers that prefixes its payload with "ts:"
* And a python CID literal server that returns "named->ts"
* When I request the resource /ts-chain/\{python server CID\}.py/output
* Then the response should contain "ts:named->ts"

## TypeScript CID literal with no extension executes
* Given a TypeScript CID literal server stored without an extension that emits "ts-noext"
* When I request the resource /\{typescript CID\}/tail
* Then the response should contain "ts-noext"

## TypeScript CID literal with .ts extension executes
* Given a TypeScript CID literal server stored with a .ts extension that emits "ts-ext"
* When I request the resource /\{typescript CID\}.ts/tail
* Then the response should contain "ts-ext"
