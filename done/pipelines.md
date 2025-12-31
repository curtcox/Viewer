# Pipeline Implementation Plan

## Overview

Status: Implemented. Pipeline routing and debug support exist (`routes/pipelines.py`, `server_execution/pipeline_execution.py`, `server_execution/pipeline_debug.py`), with unit tests (`tests/test_pipeline_execution.py`, `tests/test_pipeline_feature_flag.py`) and documentation (`docs/pipeline-requests.md`).

This document details the plan for implementing enhanced pipeline functionality in the Viewer application. A pipeline URL is one that involves at least one server accepting input from something in the URL other than the HTTP request. The implementation will refactor existing chaining logic into a more structured pipeline system with debug capabilities.

## Current State Analysis

### Existing Infrastructure

The application already has basic server chaining support:

- **Location**: `server_execution/code_execution.py` contains the core execution logic
- **Patterns Supported**:
  - `/s/CID` - server `s` receives contents of CID as input
  - `/s2/s1` - server `s2` receives output of `s1` as input
  - `/s2/s1/CID` - server `s2` receives output of `s1` (which receives CID contents) as input
- **Key Functions**:
  - `_evaluate_nested_path_to_value()` - recursive path evaluation
  - `_resolve_chained_input_from_path()` - resolves chained input
  - `_load_server_literal()` - loads CID-based server definitions
  - `_remaining_path_segments()` - extracts path segments after server name
- **Languages Supported**: Python, Bash, JavaScript, Clojure, ClojureScript, TypeScript

### Existing Test Coverage

- **Gauge Specs**: `specs/server_command_chaining.spec` (229 lines)
- **Step Implementations**: `step_impl/chaining_steps.py` (1209 lines)
- **Unit Tests**: Various `tests/test_server_*.py` files

---

## Implementation Architecture

### New File Structure

```
routes/
  pipelines.py              # NEW: Pipeline request recognition and routing

server_execution/
  pipeline_execution.py     # NEW: Pipeline execution logic
  pipeline_debug.py         # NEW: Debug information collection

docs/
  pipeline-requests.md      # NEW: Pipeline documentation
```

### Core Data Structures

```python
@dataclass
class PathSegmentInfo:
    """Information about a single path segment in a pipeline."""

    segment_text: str                    # The raw URL segment text
    segment_type: Literal["server", "parameter", "cid", "alias"]
    resolution_type: Literal["literal", "contents", "execution"]

    # CID validation (only if segment_type == "cid")
    is_valid_cid: bool
    cid_validation_error: Optional[str]

    # Alias resolution
    aliases_involved: List[str]

    # Server information (if segment is a server)
    server_name: Optional[str]
    server_definition_cid: Optional[str]
    supports_chaining: bool
    implementation_language: Optional[str]

    # Server parameters
    input_parameters: List[ParameterInfo]
    parameter_values: Dict[str, Any]

    # Execution state
    executed: bool                       # False if error prevented execution
    input_value: Optional[str]           # Input received from next segment
    intermediate_output: Optional[Any]   # Output produced by this segment
    intermediate_content_type: Optional[str]

    # Invocation tracking
    server_invocation_cid: Optional[str]

    # Errors
    errors: List[str]


@dataclass
class ParameterInfo:
    """Information about a server parameter."""

    name: str
    required: bool
    source: Optional[str]  # "path", "query", "body", "default"
    value: Optional[Any]


@dataclass
class PipelineExecutionResult:
    """Result of pipeline execution."""

    segments: List[PathSegmentInfo]
    final_output: Optional[Any]
    final_content_type: str
    success: bool
    error_message: Optional[str]
```

---

## Detailed Implementation Plan

### Phase 1: Pipeline Recognition (`routes/pipelines.py`)

Create the route handler that recognizes pipeline requests.

#### Functions to Implement

```python
def is_pipeline_request(path: str) -> bool:
    """
    Determine if a request path constitutes a pipeline request.

    A pipeline involves at least one server accepting input from
    something in the URL other than the HTTP request.

    Returns True if:
    - Path has 2+ segments where at least one is a server/CID
    - The path would result in chained execution
    """

def parse_pipeline_path(path: str) -> List[str]:
    """
    Parse a URL path into individual pipeline segments.

    Example: /this/has/four/segments -> ["this", "has", "four", "segments"]
    """

def should_return_debug_response(request) -> bool:
    """
    Check if the request includes debug=true query parameter.
    """

def get_final_extension(path: str) -> Optional[str]:
    """
    Extract the final extension from the base URL (before query params).

    Example: /server/data.json?debug=true -> "json"
    """
```

### Phase 2: Pipeline Execution (`server_execution/pipeline_execution.py`)

Create the core pipeline execution engine.

#### Functions to Implement

```python
def execute_pipeline(path: str, debug: bool = False) -> PipelineExecutionResult:
    """
    Execute a pipeline request and return the result.

    If debug=True, collect detailed information about each segment.
    If debug=False, return only the final result.
    """

def analyze_segment(segment: str, position: int, total_segments: int) -> PathSegmentInfo:
    """
    Analyze a single path segment to determine its type and properties.
    """

def resolve_segment_type(segment: str) -> Literal["server", "parameter", "cid", "alias"]:
    """
    Determine if a segment is a server name, CID, alias, or parameter.
    """

def get_resolution_type(segment: str, segment_type: str) -> Literal["literal", "contents", "execution"]:
    """
    Determine whether the literal value, contents, or execution result will be used.

    - Executable suffixes (.sh, .py, .js, .ts, .clj) -> execution
    - Data suffixes (.txt, .csv, .json) -> contents
    - No suffix -> use heuristics based on content
    """

def detect_language_from_suffix(segment: str) -> Optional[str]:
    """
    Detect the execution language from file suffix.

    .sh -> bash
    .py -> python
    .js -> javascript (via Node.js)
    .ts -> typescript (via Deno)
    .clj -> clojure
    .cljs -> clojurescript
    """

def validate_cid(segment: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a segment is a valid CID.

    Returns (is_valid, error_message if invalid)
    """

def resolve_aliases(segment: str) -> List[str]:
    """
    Return list of alias names involved in resolving this segment.
    """

def get_server_info(segment: str) -> Optional[Dict]:
    """
    Get server information if the segment resolves to a server.

    Returns:
    {
        "name": server_name,
        "definition_cid": cid,
        "supports_chaining": bool,
        "language": str,
        "parameters": List[ParameterInfo]
    }
    """

def check_chaining_support(server_definition: str, language: str) -> bool:
    """
    Determine if a server supports being in a chain position.

    Python servers without main() can only be in the last segment.
    Bash servers with $1 need specific parameter handling.
    """

def execute_segment(
    segment_info: PathSegmentInfo,
    input_value: Optional[str],
    position: int
) -> Tuple[Any, Optional[str]]:
    """
    Execute a single segment with the given input.

    Returns (output, error_message)
    """

def chain_segments(segments: List[PathSegmentInfo]) -> Any:
    """
    Execute segments right-to-left, passing output as input.
    """
```

### Phase 3: Debug Response (`server_execution/pipeline_debug.py`)

Create the debug response formatter.

#### Functions to Implement

```python
def format_debug_response(
    result: PipelineExecutionResult,
    output_format: str = "json"
) -> Response:
    """
    Format the pipeline execution result as a debug response.

    Respects the final extension in the base URL:
    - .json -> JSON response
    - .html -> HTML formatted response
    - .txt -> Plain text response
    """

def segment_info_to_dict(segment: PathSegmentInfo) -> Dict:
    """
    Convert a PathSegmentInfo to a serializable dictionary.
    """
```

### Phase 4: Parameter Handling

#### Bash Parameter Conventions

```python
# rot13 -> /rot13/{this-provides-standard-in}
# Pattern: Server receives stdin from next segment

# grep $1 -> /grep/{this-provides-params}/{this-provides-standard-in}
# Pattern: $1 from first path arg, stdin from second path arg
```

#### Python Parameter Conventions

```python
# main(in) -> /{server}/{input}
# Pattern: Single parameter from next segment

# main(in, config) -> /{server}/{config}/{in}
# Pattern: config from first path arg, in from second path arg
```

---

## Test Plan

### Unit Tests (`tests/test_pipeline_*.py`)

#### Test File: `tests/test_pipeline_recognition.py`

```python
# Pipeline Recognition Tests

class TestIsPipelineRequest:
    """Test is_pipeline_request function."""

    def test_single_segment_not_pipeline(self):
        """Single path segment is not a pipeline."""
        # /server -> False (no chaining)

    def test_two_segments_with_server_is_pipeline(self):
        """Two segments where first is server is a pipeline."""
        # /server/input -> True

    def test_two_segments_both_static_not_pipeline(self):
        """Two static segments that don't chain are not a pipeline."""
        # /static/path -> False (if neither is a server)

    def test_cid_as_input_is_pipeline(self):
        """Server with CID input is a pipeline."""
        # /server/AAAAAAAA -> True

    def test_chained_servers_is_pipeline(self):
        """Chained servers constitute a pipeline."""
        # /server2/server1 -> True

    def test_three_level_chain_is_pipeline(self):
        """Three-level chain is a pipeline."""
        # /s3/s2/s1 -> True

    def test_alias_resolving_to_server_is_pipeline(self):
        """Alias that resolves to server chain is a pipeline."""
        # /alias/input where alias -> server


class TestParsePipelinePath:
    """Test parse_pipeline_path function."""

    def test_simple_path_segments(self):
        """Parse simple path into segments."""
        # /a/b/c -> ["a", "b", "c"]

    def test_empty_segments_filtered(self):
        """Empty segments are filtered out."""
        # /a//b/ -> ["a", "b"]

    def test_url_encoded_segments(self):
        """URL encoded segments are decoded."""
        # /hello%20world -> ["hello world"]

    def test_segments_with_dots(self):
        """Segments with dots preserved."""
        # /server.py/input -> ["server.py", "input"]


class TestShouldReturnDebugResponse:
    """Test debug parameter detection."""

    def test_debug_true_returns_true(self):
        """debug=true query param returns True."""

    def test_debug_false_returns_false(self):
        """debug=false query param returns False."""

    def test_no_debug_param_returns_false(self):
        """Missing debug param returns False."""

    def test_debug_1_returns_true(self):
        """debug=1 query param returns True."""

    def test_debug_yes_returns_true(self):
        """debug=yes query param returns True."""

    def test_debug_on_returns_true(self):
        """debug=on query param returns True."""

    def test_debug_case_insensitive(self):
        """Debug param is case insensitive."""
        # DEBUG=TRUE, Debug=True, debug=YES all work

    def test_debug_0_returns_false(self):
        """debug=0 query param returns False."""

    def test_debug_no_returns_false(self):
        """debug=no query param returns False."""

    def test_debug_off_returns_false(self):
        """debug=off query param returns False."""

    def test_debug_random_value_returns_false(self):
        """debug=random returns False (not in truthy set)."""


class TestGetFinalExtension:
    """Test final extension extraction."""

    def test_extension_before_query(self):
        """Extract extension before query string."""
        # /path/file.json?debug=true -> "json"

    def test_no_extension(self):
        """Handle paths without extension."""
        # /path/file -> None

    def test_multiple_dots(self):
        """Handle multiple dots correctly."""
        # /path/file.tar.gz -> "gz"

    def test_extension_in_middle_segment(self):
        """Only consider final segment extension."""
        # /server.py/input -> None (not "py")
```

#### Test File: `tests/test_pipeline_segment_analysis.py`

```python
# Segment Analysis Tests

class TestResolveSegmentType:
    """Test segment type resolution."""

    def test_named_server_detection(self):
        """Detect segment as named server."""
        # "echo" (if echo server exists) -> "server"

    def test_cid_detection(self):
        """Detect segment as CID."""
        # "AAAAAAAA" -> "cid"

    def test_alias_detection(self):
        """Detect segment as alias."""
        # "myalias" (if alias exists) -> "alias"

    def test_literal_parameter(self):
        """Detect segment as literal parameter."""
        # "hello-world" (no server/alias) -> "parameter"

    def test_cid_with_extension(self):
        """CID with extension still detected."""
        # "AAAAAAAA.py" -> "cid"


class TestGetResolutionType:
    """Test resolution type determination."""

    def test_sh_suffix_is_execution(self):
        """Bash suffix means execution."""
        # segment.sh -> "execution"

    def test_py_suffix_is_execution(self):
        """Python suffix means execution."""
        # segment.py -> "execution"

    def test_js_suffix_is_execution(self):
        """JavaScript suffix means execution."""
        # segment.js -> "execution"

    def test_ts_suffix_is_execution(self):
        """TypeScript suffix means execution."""
        # segment.ts -> "execution"

    def test_clj_suffix_is_execution(self):
        """Clojure suffix means execution."""
        # segment.clj -> "execution"

    def test_cljs_suffix_is_execution(self):
        """ClojureScript suffix means execution."""
        # segment.cljs -> "execution"

    def test_txt_suffix_is_contents(self):
        """Text suffix means contents."""
        # segment.txt -> "contents"

    def test_json_suffix_is_contents(self):
        """JSON suffix means contents."""
        # segment.json -> "contents"

    def test_csv_suffix_is_contents(self):
        """CSV suffix means contents."""
        # segment.csv -> "contents"

    def test_unrecognized_suffix_is_error(self):
        """Unrecognized extension returns error."""
        # segment.xyz -> error "unrecognized extension"

    def test_no_suffix_uses_heuristics(self):
        """No suffix triggers heuristic detection."""
        # Must analyze content

    def test_heuristic_detects_python(self):
        """Heuristic detects Python code."""
        # Content starting with "def main" -> execution

    def test_heuristic_detects_bash(self):
        """Heuristic detects bash code."""
        # Content starting with "#!/bin/bash" -> execution

    def test_heuristic_detects_data(self):
        """Heuristic detects data content."""
        # Plain text without code markers -> contents


class TestValidateCid:
    """Test CID validation."""

    def test_valid_literal_cid(self):
        """Valid literal CID passes validation."""
        # AAAAAAAA -> (True, None)

    def test_valid_hash_cid(self):
        """Valid hash-based CID passes validation."""
        # 94-char CID -> (True, None)

    def test_invalid_characters(self):
        """Invalid characters fail validation."""
        # "AAAA@AAA" -> (False, "invalid characters")

    def test_too_short(self):
        """Too short CID fails validation."""
        # "AAAA" -> (False, "too short")

    def test_malformed_length_prefix(self):
        """Malformed length prefix fails."""
        # CID with bad prefix -> (False, "malformed prefix")

    def test_content_length_mismatch(self):
        """Content length mismatch detected."""
        # Length says 10 but content is 5 -> (False, "length mismatch")


class TestDetectLanguageFromSuffix:
    """Test language detection from suffix."""

    def test_sh_is_bash(self):
        assert detect_language_from_suffix("script.sh") == "bash"

    def test_py_is_python(self):
        assert detect_language_from_suffix("script.py") == "python"

    def test_js_is_javascript(self):
        assert detect_language_from_suffix("script.js") == "javascript"

    def test_ts_is_typescript(self):
        assert detect_language_from_suffix("script.ts") == "typescript"

    def test_clj_is_clojure(self):
        assert detect_language_from_suffix("script.clj") == "clojure"

    def test_cljs_is_clojurescript(self):
        assert detect_language_from_suffix("script.cljs") == "clojurescript"

    def test_unknown_suffix_raises_error(self):
        """Unrecognized suffix should raise error, not return None."""
        # detect_language_from_suffix("data.xyz") raises UnrecognizedExtensionError

    def test_data_suffix_raises_error(self):
        """Data suffixes should raise error indicating data, not code."""
        # detect_language_from_suffix("data.csv") raises DataExtensionError

    def test_no_suffix_returns_none(self):
        assert detect_language_from_suffix("nosuffix") is None
```

#### Test File: `tests/test_pipeline_server_info.py`

```python
# Server Info Tests

class TestGetServerInfo:
    """Test server information retrieval."""

    def test_named_server_info(self):
        """Get info for named server."""
        # Returns name, definition_cid, language, parameters

    def test_cid_server_info(self):
        """Get info for CID-based server."""
        # Returns definition from CID content

    def test_nonexistent_server_returns_none(self):
        """Nonexistent server returns None."""

    def test_disabled_server_returns_none(self):
        """Disabled server returns None."""


class TestCheckChainingSupport:
    """Test chaining support detection."""

    def test_python_with_main_supports_chaining(self):
        """Python server with main() supports chaining."""
        # def main(x): ... -> True

    def test_python_without_main_no_chaining(self):
        """Python server without main() doesn't support chaining."""
        # No main function -> False

    def test_bash_supports_chaining(self):
        """Bash scripts support chaining via stdin."""

    def test_bash_with_dollar_one_supports_chaining(self):
        """Bash with $1 supports chaining with params."""

    def test_javascript_supports_chaining(self):
        """JavaScript scripts support chaining."""

    def test_clojure_supports_chaining(self):
        """Clojure scripts support chaining."""

    def test_typescript_supports_chaining(self):
        """TypeScript scripts support chaining."""


class TestJavaScriptModuleSupport:
    """Test JavaScript CommonJS and ES Module detection."""

    def test_commonjs_module_detected(self):
        """Detect CommonJS module.exports pattern."""
        # module.exports = function(input) { ... }

    def test_esmodule_default_export_detected(self):
        """Detect ES Module default export pattern."""
        # export default function main(input) { ... }

    def test_commonjs_execution(self):
        """Execute CommonJS JavaScript server."""
        # Receives input, returns output

    def test_esmodule_execution(self):
        """Execute ES Module JavaScript server."""
        # Receives input, returns output

    def test_javascript_without_export_error(self):
        """JavaScript without proper export returns error."""
        # No module.exports or export default -> error


class TestRuntimeAvailability:
    """Test runtime availability error handling."""

    def test_nodejs_unavailable_error(self):
        """Error when Node.js is not available."""
        # Returns 500 "Node.js runtime is not available"

    def test_deno_unavailable_error(self):
        """Error when Deno is not available for TypeScript."""
        # Returns 500 "Deno runtime is not available"

    def test_clojure_unavailable_error(self):
        """Error when Clojure is not available."""
        # Returns 500 "Clojure runtime is not available"
```

#### Test File: `tests/test_pipeline_alias_resolution.py`

```python
# Alias Resolution Tests

class TestResolveAliases:
    """Test alias resolution chain tracking."""

    def test_no_alias_returns_empty(self):
        """Non-alias segment returns empty list."""
        # "directserver" -> []

    def test_single_alias_returned(self):
        """Single alias resolution tracked."""
        # "myalias" -> ["myalias"]

    def test_chained_aliases_returned(self):
        """Chained alias resolution tracked."""
        # alias1 -> alias2 -> server
        # Returns ["alias1", "alias2"]

    def test_alias_to_cid_tracked(self):
        """Alias resolving to CID tracked."""
        # alias -> CID content
```

#### Test File: `tests/test_pipeline_parameter_handling.py`

```python
# Parameter Handling Tests

class TestBashParameterHandling:
    """Test bash server parameter handling."""

    def test_stdin_from_following_segment(self):
        """Bash receives stdin from following segment."""
        # /rot13/{input} -> input goes to stdin

    def test_dollar_one_from_first_param(self):
        """Bash $1 receives first path parameter."""
        # /grep/{pattern}/{input} -> pattern is $1

    def test_stdin_from_second_param_with_dollar_one(self):
        """Stdin from second param when $1 used."""
        # /grep/{pattern}/{input} -> input is stdin

    def test_cid_content_as_parameter(self):
        """CID content used as parameter."""
        # /grep/{CID}/{input} -> CID content is $1


class TestPythonParameterHandling:
    """Test python server parameter handling."""

    def test_single_param_from_path(self):
        """Single main param from path."""
        # main(x) with /server/{input} -> x = input

    def test_two_params_config_then_input(self):
        """Two params: config then input."""
        # main(config, x) with /server/{c}/{i} -> config=c, x=i

    def test_optional_params_defaulted(self):
        """Optional params use defaults if not in path."""
        # main(x, y=None) with /server/{input} -> y=None

    def test_cid_content_as_param(self):
        """CID content passed as parameter."""


class TestParameterValueAssignment:
    """Test parameter value assignment tracking."""

    def test_path_sourced_parameter(self):
        """Track parameter sourced from path."""
        # parameter.source == "path"

    def test_query_sourced_parameter(self):
        """Track parameter sourced from query string."""
        # parameter.source == "query"

    def test_body_sourced_parameter(self):
        """Track parameter sourced from request body."""
        # parameter.source == "body"

    def test_default_value_parameter(self):
        """Track parameter using default value."""
        # parameter.source == "default"
```

#### Test File: `tests/test_pipeline_execution.py`

```python
# Pipeline Execution Tests

class TestExecutePipeline:
    """Test full pipeline execution."""

    def test_server_cid_pipeline(self):
        """Execute /server/CID pipeline."""
        # Server receives CID content

    def test_server_server_pipeline(self):
        """Execute /server2/server1 pipeline."""
        # s2 receives s1 output

    def test_three_level_pipeline(self):
        """Execute /s3/s2/s1 pipeline."""
        # Chained execution

    def test_server_cid_with_extension(self):
        """Execute server with CID.extension input."""
        # /server/{CID}.py -> execute CID as Python

    def test_mixed_language_pipeline(self):
        """Execute pipeline with mixed languages."""
        # /python_server/{bash_cid}.sh

    def test_pipeline_with_alias(self):
        """Execute pipeline containing alias."""
        # /server/{alias} where alias -> actual content

    def test_error_propagation(self):
        """Errors propagate through pipeline."""
        # Error in middle segment stops pipeline

    def test_empty_pipeline_result(self):
        """Handle empty pipeline result."""


class TestChainSegments:
    """Test right-to-left segment chaining."""

    def test_right_to_left_execution(self):
        """Segments execute right to left."""
        # /a/b/c -> c executes, output to b, output to a

    def test_output_becomes_input(self):
        """Each segment output becomes next input."""

    def test_final_output_returned(self):
        """Final (leftmost) output is returned."""
```

#### Test File: `tests/test_pipeline_debug.py`

```python
# Debug Mode Tests

class TestDebugResponse:
    """Test debug response generation."""

    def test_debug_includes_all_segments(self):
        """Debug response includes info for all segments."""

    def test_debug_shows_segment_text(self):
        """Debug shows original segment text."""

    def test_debug_shows_segment_type(self):
        """Debug shows segment type (server/parameter/cid/alias)."""

    def test_debug_shows_resolution_type(self):
        """Debug shows resolution type (literal/contents/execution)."""

    def test_debug_shows_cid_validity(self):
        """Debug shows CID validation result."""

    def test_debug_shows_aliases(self):
        """Debug shows alias resolution chain."""

    def test_debug_shows_server_name(self):
        """Debug shows resolved server name."""

    def test_debug_shows_definition_cid(self):
        """Debug shows server definition CID."""

    def test_debug_shows_chaining_support(self):
        """Debug shows whether server supports chaining."""

    def test_debug_shows_language(self):
        """Debug shows implementation language."""

    def test_debug_shows_parameters(self):
        """Debug shows input parameters."""

    def test_debug_shows_parameter_values(self):
        """Debug shows assigned parameter values."""

    def test_debug_shows_invocation_cid(self):
        """Debug shows server invocation CID."""

    def test_debug_shows_errors(self):
        """Debug shows segment errors."""


class TestDebugOutputFormat:
    """Test debug output format respects extension."""

    def test_json_extension_returns_json(self):
        """?debug=true with .json returns JSON."""
        # /server/input.json?debug=true -> application/json

    def test_html_extension_returns_html(self):
        """?debug=true with .html returns HTML."""
        # /server/input.html?debug=true -> text/html

    def test_txt_extension_returns_text(self):
        """?debug=true with .txt returns plain text."""
        # /server/input.txt?debug=true -> text/plain

    def test_no_extension_defaults_json(self):
        """?debug=true without extension returns JSON."""
        # /server/input?debug=true -> application/json


class TestSingleSegmentDebug:
    """Test debug mode for single-segment (non-pipeline) requests."""

    def test_single_server_debug(self):
        """Single server segment returns debug info."""
        # /echo?debug=true -> single segment info

    def test_single_cid_debug(self):
        """Single CID segment returns debug info."""
        # /AAAAAAAA?debug=true -> single segment info

    def test_single_alias_debug(self):
        """Single alias segment returns debug info."""
        # /myalias?debug=true -> single segment info with alias chain

    def test_single_segment_shows_all_fields(self):
        """Single segment debug shows all standard fields."""
        # Includes segment_type, resolution_type, errors, etc.

    def test_single_segment_intermediate_output(self):
        """Single segment debug shows intermediate output."""
        # intermediate_output field present with execution result


class TestDebugErrorCases:
    """Test debug mode error handling."""

    def test_debug_shows_server_not_found(self):
        """Debug shows server not found error."""
        # "server_not_found" in segment.errors

    def test_debug_shows_syntax_error(self):
        """Debug shows server syntax error."""
        # "syntax_error: ..." in segment.errors

    def test_debug_shows_invalid_cid(self):
        """Debug shows invalid CID error."""
        # "invalid_cid: ..." in segment.errors

    def test_debug_shows_chaining_not_supported(self):
        """Debug shows chaining not supported error."""
        # When Python server without main is not in last position

    def test_debug_shows_unrecognized_extension(self):
        """Debug shows unrecognized extension error."""
        # /server/{CID}.xyz -> "unrecognized_extension: xyz" in errors

    def test_debug_continues_after_error(self):
        """Debug analyzes all segments even after error."""
        # Error in segment 1 doesn't prevent segment 2 analysis

    def test_debug_marks_unexecuted_segments(self):
        """Debug marks segments after error as not executed."""
        # Segments after error show executed: false


class TestDebugIntermediateOutputs:
    """Test intermediate output capture in debug mode."""

    def test_debug_shows_each_segment_output(self):
        """Debug shows intermediate output for each segment."""
        # Each segment has intermediate_output field

    def test_debug_output_flows_through_chain(self):
        """Debug shows how output flows between segments."""
        # segment[1].intermediate_output == segment[0].input_value

    def test_debug_shows_final_output(self):
        """Debug shows final pipeline output."""
        # response.final_output matches leftmost segment output

    def test_debug_shows_content_type_per_segment(self):
        """Debug shows content type for each segment output."""
        # Each segment has intermediate_content_type field


class TestDebugInvocationTracking:
    """Test ServerInvocation record creation in debug mode."""

    def test_debug_creates_invocation_records(self):
        """Debug mode creates ServerInvocation records."""
        # Same as normal execution per Q7 resolution

    def test_debug_invocation_has_debug_flag(self):
        """Debug invocations could be identified if needed."""
        # For future: mark invocations as debug-triggered

    def test_debug_invocation_cid_in_response(self):
        """Debug response includes invocation CID."""
        # Each segment shows server_invocation_cid
```

### Integration Tests (`specs/pipeline_execution.spec`)

```gauge
# Pipeline Execution

These tests verify the pipeline execution functionality with debug mode.

## Simple server-CID pipeline with debug

* Given a server named "echo" that echoes its input with prefix "received:"
* And a CID containing "test-input"
* When I request /echo/{stored CID}?debug=true
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
* And segment 0 should have type "server"
* And segment 0 should have server_name "second"
* And segment 1 should have type "server"
* And segment 1 should have server_name "first"

## Pipeline with CID literal execution

* Given a python CID literal server that returns "py-output"
* When I request /{python server CID}.py/ignored?debug=true
* Then the response should contain segment with resolution_type "execution"
* And the response should contain segment with implementation_language "python"

## Pipeline with bash $1 parameter

* Given a bash server named "grep-server" with $1 parameter
* When I request /grep-server/pattern-value/input-data?debug=true
* Then segment 0 should have parameter_values containing "pattern-value" for $1
* And segment 2 should have resolution_type "contents"

## Debug output respects JSON extension

* Given a server named "simple" that returns "data"
* When I request /simple/input.json?debug=true
* Then the response Content-Type should be "application/json"

## Debug output respects HTML extension

* Given a server named "simple" that returns "data"
* When I request /simple/input.html?debug=true
* Then the response Content-Type should be "text/html"

## Pipeline shows server not found error

* When I request /nonexistent-server/input?debug=true
* Then segment 0 should have errors containing "server not found"

## Pipeline shows invalid CID error

* When I request /echo/not-a-valid-cid-format?debug=true
* Then segment 1 should have is_valid_cid false
* And segment 1 should have errors containing "invalid CID"

## Python server without main shows chaining error

* Given a python server "no-main" without main function
* When I request /other-server/no-main/input?debug=true
* Then segment 1 should have supports_chaining false
* And segment 1 should have errors containing "does not support chaining"

## Pipeline shows alias resolution chain

* Given an alias "my-alias" pointing to "actual-server"
* And a server named "actual-server" that returns "result"
* When I request /my-alias/input?debug=true
* Then segment 0 should have aliases_involved containing "my-alias"

## Three-level pipeline execution

* Given a server named "s1" that returns "one"
* And a server named "s2" that echoes its input with prefix "two:"
* And a server named "s3" that echoes its input with prefix "three:"
* When I request /s3/s2/s1?debug=true
* Then the response should contain 3 segment entries
* And all segments should have supports_chaining true

## Normal pipeline execution without debug

* Given a server named "processor" that echoes its input with prefix "processed:"
* And a CID containing "raw-data"
* When I request /processor/{stored CID}
* Then the response should redirect to a CID
* And the CID content should be "processed:raw-data"

## Mixed language pipeline

* Given a python CID literal server that returns "from-python"
* And a bash CID literal server that prefixes input with "bash:"
* When I request /{bash server CID}.sh/{python server CID}.py/end?debug=true
* Then segment 0 should have implementation_language "bash"
* And segment 1 should have implementation_language "python"

## JavaScript CID literal execution

* Given a JavaScript CID literal server that returns "js-output"
* When I request /{javascript server CID}.js/input?debug=true
* Then segment 0 should have implementation_language "javascript"
* And segment 0 should have resolution_type "execution"

## JavaScript chained with Python

* Given a JavaScript CID literal server that returns "from-js"
* And a python CID literal server that prefixes its payload with "py:"
* When I request /{python server CID}.py/{javascript server CID}.js/end?debug=true
* Then segment 0 should have implementation_language "python"
* And segment 1 should have implementation_language "javascript"

## Unrecognized extension returns error

* Given a CID containing "some content"
* When I request /echo/{stored CID}.xyz?debug=true
* Then segment 1 should have errors containing "unrecognized extension"

## Single segment debug request

* Given a server named "echo" that echoes its input with prefix "got:"
* When I request /echo?debug=true
* Then the response should be JSON
* And the response should contain 1 segment entry
* And segment 0 should have type "server"
* And segment 0 should have intermediate_output

## Debug shows intermediate outputs for each segment

* Given a server named "s1" that returns "first"
* And a server named "s2" that echoes its input with prefix "second:"
* When I request /s2/s1?debug=true
* Then segment 1 should have intermediate_output "first"
* And segment 0 should have intermediate_output "second:first"

## Debug creates invocation records

* Given a server named "tracked" that returns "result"
* When I request /tracked/input?debug=true
* Then segment 0 should have server_invocation_cid
* And the invocation record should exist in the database

## JavaScript CommonJS module execution

* Given a JavaScript CID using CommonJS: module.exports = function(input) { return "cjs:" + input; }
* When I request /{javascript server CID}.js/test-input?debug=true
* Then segment 0 should have implementation_language "javascript"
* And the final_output should be "cjs:test-input"

## JavaScript ES Module execution

* Given a JavaScript CID using ES Modules: export default function main(input) { return "esm:" + input; }
* When I request /{javascript server CID}.js/test-input?debug=true
* Then segment 0 should have implementation_language "javascript"
* And the final_output should be "esm:test-input"

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

## Debug parameter rejects random value

* Given a server named "echo" that returns "data"
* When I request /echo/input?debug=random
* Then the response should NOT be JSON debug output
* And the response should be normal execution result

## Node.js runtime unavailable error

* Given Node.js is not available on the system
* When I request /{javascript CID}.js/input
* Then the response status should be 500
* And the response should contain "Node.js runtime is not available"
```

---

## Design Decisions (Resolved)

The following questions have been resolved and inform the implementation:

### 1. Unrecognized Extension Types
**Decision**: Unrecognized extensions (e.g., `.xyz`) are reported as errors.
- Errors clearly indicate the issue rather than silently falling back
- Helps users identify typos or misconfigured pipelines

### 2. JavaScript Support
**Decision**: Execute `.js` files via Node.js and `.ts` files via Deno.
- Both runtimes supported for their respective file types
- Follows the pattern of using the canonical runtime for each language

### 3. Recursive Alias Resolution
**Decision**: Rely on existing cycle detection in `_evaluate_nested_path_to_value`.
- No artificial depth limit needed
- Existing `visited` set prevents infinite loops

### 4. Debug for Non-Pipeline Requests
**Decision**: Yes, return single segment debug info for consistency.
- Single-segment requests (e.g., `/echo?debug=true`) return debug info
- Provides consistent debugging experience across all request types

### 5. Parameter Value Serialization
**Decision**: Use full nested structure for complex values.
- Dicts and lists serialized as complete nested JSON structures
- Enables thorough debugging without truncation

### 6. Error Continuation in Debug Mode
**Decision**: Analyze all segments but mark errors.
- Debug continues analyzing remaining segments after encountering an error
- Error segments marked with `executed: false`
- Provides complete pipeline visibility for debugging

### 7. Invocation Records in Debug Mode
**Decision**: Yes, create ServerInvocation records same as normal execution.
- Debug mode is a full execution with additional metadata returned
- Invocation history captures debug executions for audit/replay

### 8. Python Parameter Ordering
**Decision**: Keep as specified - `/{server}/{config}/{in}` (config first, then input).

**Rationale** (shell pipeline analogy): The ordering follows shell pipeline conventions where no arguments can come after the pipe operator (`|`). In a pipeline like:
```
grep pattern | sort | head
```
The `pattern` argument to `grep` must come before the pipe. Similarly:
```
/grep/{pattern}/{input}
```
The `{pattern}` (config/argument) comes first, followed by `{input}` which could itself expand into a sub-pipeline. If input came first, the config could be pushed arbitrarily far to the right as each input expands.

### 9. Debug with Intermediate Outputs
**Decision**: Debug shows intermediate outputs for each segment.
- Each segment includes `intermediate_output` field
- Enables tracing data flow through the entire pipeline
- `final_output` field contains the leftmost segment's output

### 10. CID Extension vs Content Type
**Decision**: Extension determines handling.
- `{CID}.json` treats content as JSON data, regardless of actual content
- `{CID}.py` executes as Python, regardless of actual content
- Explicit extensions are honored; user intent is respected

---

### 11. Node.js Runtime Availability
**Decision**: Return a 500 error with message "Node.js runtime is not available".
- Consistent with existing pattern for other missing runtimes (Clojure, Deno)
- Clear error message helps users diagnose environment issues

### 12. JavaScript Server Function Signature
**Decision**: Support both CommonJS and ES Modules.
- CommonJS: `module.exports = function(input) { ... }`
- ES Modules: `export default function main(input) { ... }`
- Implementation detects module type and handles accordingly
- Provides flexibility for different JavaScript codebases

### 13. Debug Mode Query Parameter Variants
**Decision**: Accept `true`, `1`, `yes`, `on` (common truthy values).
- Case-insensitive matching
- User-friendly while still explicit
- Consistent with common web conventions

---

## Documentation Updates

### New File: `docs/pipeline-requests.md`

Create comprehensive documentation covering:

1. **What is a Pipeline?**
   - Definition and purpose
   - Comparison to simple server requests

2. **Pipeline URL Structure**
   - Path segment types (servers, CIDs, aliases, parameters)
   - Extension handling
   - Query parameters

3. **Execution Flow**
   - Right-to-left evaluation
   - Input/output chaining
   - Error handling

4. **Debug Mode**
   - Enabling debug mode
   - Understanding debug output
   - Output format options

5. **Server Types and Chaining**
   - Python servers (with/without main)
   - Bash servers (stdin, $1 parameters)
   - Other languages (Clojure, TypeScript)

6. **Examples**
   - Basic pipeline examples
   - Multi-language pipelines
   - Debug mode examples

---

## Implementation Order

1. **Phase 1**: Create `routes/pipelines.py` with recognition logic
2. **Phase 2**: Create `server_execution/pipeline_execution.py` with core execution
3. **Phase 3**: Create `server_execution/pipeline_debug.py` with debug formatting
4. **Phase 4**: Add unit tests for all new functions
5. **Phase 5**: Add integration tests (Gauge specs)
6. **Phase 6**: Create documentation
7. **Phase 7**: Refactor existing chaining code to use new pipeline module

---

## Risk Assessment

### Technical Risks

1. **Circular Dependencies**: New modules may create import cycles with existing code
   - Mitigation: Careful module boundary design, lazy imports

2. **Performance**: Deep pipeline analysis may be slow
   - Mitigation: Cache segment analysis, limit recursion depth

3. **Backward Compatibility**: Changes may break existing chaining behavior
   - Mitigation: Extensive test coverage before refactoring

### Testing Risks

1. **Test Coverage Gaps**: Complex pipelines may have untested edge cases
   - Mitigation: Comprehensive test matrix, property-based testing

2. **Flaky Integration Tests**: Timing-dependent tests may fail intermittently
   - Mitigation: Use test fixtures, avoid external dependencies

---

## Success Criteria

1. All existing `server_command_chaining.spec` tests continue to pass
2. All new unit tests pass
3. All new integration tests pass
4. Debug mode provides complete segment information
5. Documentation is complete and accurate
6. No performance regression for normal pipeline execution
