# Gateway.py Refactoring Plan

## Executive Summary

The `gateway.py` file is currently 2479 lines with multiple responsibilities mixed together. This plan proposes breaking it into focused modules with clear boundaries, comprehensive test coverage, and simplified logic flows.

## Current Issues

### 1. **Single Responsibility Violations**
- One file handles: routing, request transformation, response transformation, template loading, CID resolution, error rendering, form handling, test mode, internal request execution, redirect following, and diagnostics
- Functions exceed 200+ lines with deeply nested logic
- Mixed abstraction levels (low-level string manipulation with high-level business logic)

### 2. **Testing Challenges**
- Large functions with many dependencies are difficult to unit test
- Side effects and global state (Flask request context, database access)
- Complex conditional logic paths that are hard to isolate
- Difficult to mock dependencies cleanly

### 3. **Code Duplication**
- Similar patterns for loading/validating request and response transforms
- Repeated error handling logic throughout
- Duplicate code in `_handle_gateway_request` and `_handle_gateway_test_request`
- Multiple places that parse and normalize CID values

### 4. **Maintainability Issues**
- Unclear boundaries between components
- Functions with too many parameters (8+ in some cases)
- Inconsistent error handling approaches
- Hard to understand control flow with early returns and nested conditionals

### 5. **Enhancement Barriers**
- Adding new gateway features requires touching many functions
- New transformation types would require duplicating validation logic
- Extending routing patterns means modifying complex path parsing logic
- Difficult to add new target types or execution modes

## Proposed Architecture

### Module Structure

```
reference/templates/servers/definitions/gateway/
├── __init__.py                    # Main entry point
├── core.py                        # Core gateway orchestration
├── routing.py                     # Route parsing and dispatch
├── config.py                      # Gateway configuration loading
├── transforms/
│   ├── __init__.py
│   ├── loader.py                  # Transform loading and compilation
│   ├── validator.py               # Transform validation
│   ├── request.py                 # Request transformation logic
│   └── response.py                # Response transformation logic
├── templates/
│   ├── __init__.py
│   ├── loader.py                  # Template file loading
│   └── resolver.py                # Template name resolution
├── execution/
│   ├── __init__.py
│   ├── target.py                  # Target resolution
│   ├── internal.py                # Internal server execution
│   └── redirects.py               # Redirect following logic
├── cid/
│   ├── __init__.py
│   ├── resolver.py                # CID content resolution
│   └── normalizer.py              # CID path normalization
├── handlers/
│   ├── __init__.py
│   ├── request.py                 # Gateway request handler
│   ├── test.py                    # Test mode handler
│   ├── meta.py                    # Meta page handler
│   └── forms.py                   # Form handlers
├── rendering/
│   ├── __init__.py
│   ├── error.py                   # Error page rendering
│   └── diagnostic.py              # Diagnostic info extraction
└── models.py                      # Data classes for type safety
```

## Refactoring Strategy

### Phase 1: Extract Pure Functions (Low Risk)
Extract functions with no side effects and clear inputs/outputs:

1. **String/Data Manipulation**
   - `_format_exception_summary` → `rendering/diagnostic.py`
   - `_derive_exception_summary_from_traceback` → `rendering/diagnostic.py`
   - `_extract_exception_summary_from_internal_error_html` → `rendering/diagnostic.py`
   - `_extract_stack_trace_list_from_internal_error_html` → `rendering/diagnostic.py`
   - `_parse_hrx_gateway_args` → `routing.py`
   - `_normalize_cid_lookup` → `cid/normalizer.py`
   - `_safe_preview_request_details` → `rendering/diagnostic.py`
   - `_format_exception_detail` → `rendering/diagnostic.py`

2. **Validation Functions**
   - `_validate_direct_response` → `transforms/validator.py`
   - `_load_and_validate_transform` → `transforms/validator.py`
   - `_load_and_validate_template` → `templates/loader.py`

### Phase 2: Extract Data Classes (Medium Risk)
Create typed data structures to replace dicts:

```python
# models.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class GatewayConfig:
    name: str
    request_transform_cid: Optional[str] = None
    response_transform_cid: Optional[str] = None
    templates: Dict[str, str] = None
    target_url: Optional[str] = None

    def __post_init__(self):
        if self.templates is None:
            self.templates = {}

@dataclass
class RequestDetails:
    path: str
    method: str = "GET"
    query_string: str = ""
    headers: Dict[str, str] = None
    json: Optional[Any] = None
    data: Optional[str] = None
    url: Optional[str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

@dataclass
class ResponseDetails:
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json: Optional[Any] = None
    request_path: str = ""
    source: str = "server"

@dataclass
class TransformResult:
    output: str | bytes
    content_type: str = "text/plain"
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None

@dataclass
class Target:
    mode: str  # "internal" only
    url: str

    def validate(self):
        if self.mode != "internal":
            raise ValueError(f"Unsupported target mode: {self.mode}")
        if not self.url.startswith("/"):
            raise ValueError("Gateway target must be an internal path")
```

### Phase 3: Extract Service Classes (Medium-High Risk)
Create classes to encapsulate related functionality:

```python
# transforms/loader.py
class TransformLoader:
    def __init__(self, cid_resolver):
        self.cid_resolver = cid_resolver

    def load_transform(self, cid: str, context: dict) -> Optional[callable]:
        """Load and compile a transform function from a CID."""
        ...

    def compile_transform(self, source: str) -> Optional[callable]:
        """Compile transform source into a callable function."""
        ...

# execution/target.py
class TargetExecutor:
    def __init__(self, app):
        self.app = app

    def execute(self, target: Target, request_details: RequestDetails) -> ResponseDetails:
        """Execute request against a target and return response."""
        ...

    def _follow_redirects(self, response, max_hops: int = 3) -> ResponseDetails:
        """Follow internal redirects to final content."""
        ...

# cid/resolver.py
class CIDResolver:
    def resolve(self, cid_value: str, as_bytes: bool = False) -> Optional[str | bytes]:
        """Resolve a CID value to its content."""
        ...

    def _try_database(self, cid_path: str, as_bytes: bool) -> Optional[str | bytes]:
        ...

    def _try_filesystem(self, cid_value: str, as_bytes: bool) -> Optional[str | bytes]:
        ...
```

### Phase 4: Refactor Main Request Handlers (High Risk)
Break down the massive request handling functions:

```python
# handlers/request.py
class GatewayRequestHandler:
    def __init__(
        self,
        config_loader,
        transform_loader,
        template_resolver,
        target_executor,
        error_renderer
    ):
        self.config_loader = config_loader
        self.transform_loader = transform_loader
        self.template_resolver = template_resolver
        self.target_executor = target_executor
        self.error_renderer = error_renderer

    def handle(self, server_name: str, rest_path: str, context: dict):
        """Handle a gateway request with clear separation of concerns."""
        config = self._load_config(server_name)
        request_details = self._build_request_details(rest_path)

        # Apply request transform
        transformed_request, direct_response = self._apply_request_transform(
            config, request_details, context
        )

        if direct_response:
            return self._finalize_response(direct_response, config, context)

        # Execute target
        response_details = self._execute_target(config, transformed_request)

        # Apply response transform
        return self._apply_response_transform(
            config, response_details, context
        )

    def _load_config(self, server_name: str) -> GatewayConfig:
        """Load gateway config with error handling."""
        ...

    def _build_request_details(self, rest_path: str) -> RequestDetails:
        """Build request details from Flask request."""
        ...

    def _apply_request_transform(
        self,
        config: GatewayConfig,
        request_details: RequestDetails,
        context: dict
    ) -> tuple[RequestDetails, Optional[ResponseDetails]]:
        """Apply request transform, return (request, direct_response)."""
        ...
```

### Phase 5: Simplify Routing (Medium Risk)

```python
# routing.py
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Route:
    pattern: str
    handler: callable
    path_params: List[str]

class GatewayRouter:
    def __init__(self):
        self.routes = []
        self._register_routes()

    def _register_routes(self):
        """Register all gateway routes in priority order."""
        self.routes = [
            Route("", self._handle_instruction),
            Route("request", self._handle_request_form),
            Route("response", self._handle_response_form),
            Route("meta/<server>", self._handle_meta),
            Route("meta/test/<test_path>/as/<server>", self._handle_meta_test),
            Route("test/<test_path>/as/<server>/<rest>", self._handle_test),
            Route("<server>/<rest>", self._handle_gateway),
            Route("<server>", self._handle_gateway),
        ]

    def route(self, path: str, context: dict):
        """Match path to handler and execute."""
        for route in self.routes:
            params = self._match(route.pattern, path)
            if params is not None:
                return route.handler(**params, context=context)

        return self._handle_not_found(path)

    def _match(self, pattern: str, path: str) -> Optional[dict]:
        """Match path against pattern, return params or None."""
        ...
```

## Detailed Test Plan

### Unit Tests

#### 1. CID Resolution Tests (cid/resolver.py)
```python
def test_resolve_cid_from_database()
def test_resolve_cid_from_filesystem()
def test_resolve_cid_with_leading_slash()
def test_resolve_cid_without_leading_slash()
def test_resolve_cid_as_bytes()
def test_resolve_cid_as_text()
def test_resolve_cid_not_found_returns_none()
def test_resolve_cid_with_unicode_content()
def test_resolve_cid_with_binary_content()
def test_resolve_cid_handles_database_error_gracefully()
def test_resolve_cid_handles_filesystem_error_gracefully()
def test_resolve_relative_path()
def test_resolve_absolute_path()
```

#### 2. CID Normalization Tests (cid/normalizer.py)
```python
def test_normalize_none_returns_none()
def test_normalize_empty_string_returns_none()
def test_normalize_whitespace_only_returns_none()
def test_normalize_strips_whitespace()
def test_normalize_extracts_cid_from_path()
def test_normalize_adds_leading_slash_for_cid()
def test_normalize_preserves_non_cid_paths()
def test_normalize_handles_cid_with_extension()
```

#### 3. Request Details Building Tests (handlers/request.py)
```python
def test_build_request_details_from_flask_request()
def test_build_request_details_extracts_path()
def test_build_request_details_extracts_query_string()
def test_build_request_details_extracts_method()
def test_build_request_details_extracts_headers_without_cookie()
def test_build_request_details_parses_json_body()
def test_build_request_details_handles_json_parse_error()
def test_build_request_details_extracts_raw_body()
def test_build_request_details_handles_empty_body()
```

#### 4. Transform Loading Tests (transforms/loader.py)
```python
def test_load_transform_from_file_path()
def test_load_transform_from_cid()
def test_load_transform_returns_none_when_not_found()
def test_compile_transform_with_transform_request()
def test_compile_transform_with_transform_response()
def test_compile_transform_with_both_functions_prefers_request()
def test_compile_transform_with_no_functions_returns_none()
def test_compile_transform_with_syntax_error_returns_none()
def test_load_transform_handles_unicode_source()
def test_load_transform_handles_database_error()
```

#### 5. Transform Validation Tests (transforms/validator.py)
```python
def test_validate_transform_with_valid_syntax()
def test_validate_transform_with_syntax_error()
def test_validate_transform_missing_required_function()
def test_validate_transform_function_with_too_few_params()
def test_validate_transform_function_with_correct_params()
def test_validate_transform_not_found()
def test_validate_direct_response_with_valid_output()
def test_validate_direct_response_missing_output_key()
def test_validate_direct_response_invalid_output_type()
def test_validate_direct_response_invalid_content_type()
def test_validate_direct_response_invalid_status_code()
def test_validate_direct_response_with_all_optional_fields()
```

#### 6. Template Resolution Tests (templates/resolver.py)
```python
def test_create_template_resolver()
def test_resolve_template_by_name()
def test_resolve_template_not_in_config_raises_value_error()
def test_resolve_template_cid_not_found_raises_lookup_error()
def test_resolve_template_returns_jinja2_template()
def test_template_resolver_caches_templates()
def test_extract_resolve_template_calls_from_source()
def test_extract_resolve_template_calls_with_single_quotes()
def test_extract_resolve_template_calls_with_double_quotes()
def test_extract_resolve_template_calls_with_no_matches()
```

#### 7. Target Resolution Tests (execution/target.py)
```python
def test_resolve_target_from_config()
def test_resolve_target_with_explicit_url()
def test_resolve_target_with_relative_url()
def test_resolve_target_rejects_external_url()
def test_resolve_target_defaults_to_server_name()
def test_resolve_test_target_adds_leading_slash()
def test_resolve_test_target_preserves_leading_slash()
```

#### 8. Target Execution Tests (execution/internal.py)
```python
def test_execute_internal_target()
def test_execute_internal_target_with_query_string()
def test_execute_internal_target_with_extra_path()
def test_execute_internal_target_with_headers()
def test_execute_internal_target_with_json_body()
def test_execute_internal_target_rejects_external_url()
def test_execute_internal_target_handles_not_found()
def test_execute_internal_target_with_post_method()
```

#### 9. Redirect Following Tests (execution/redirects.py)
```python
def test_follow_redirects_with_no_redirect_returns_original()
def test_follow_redirects_resolves_cid_location()
def test_follow_redirects_handles_301()
def test_follow_redirects_handles_302()
def test_follow_redirects_handles_307()
def test_follow_redirects_stops_at_max_hops()
def test_follow_redirects_preserves_content_type()
def test_follow_redirects_with_extension_in_location()
def test_follow_redirects_with_no_location_header()
def test_follow_redirects_with_invalid_cid()
```

#### 10. HRX Args Parsing Tests (routing.py)
```python
def test_parse_hrx_args_with_archive_and_path()
def test_parse_hrx_args_with_archive_only()
def test_parse_hrx_args_with_empty_string()
def test_parse_hrx_args_with_none()
def test_parse_hrx_args_with_leading_slash()
def test_parse_hrx_args_with_trailing_slash()
def test_parse_hrx_args_with_multiple_slashes()
```

#### 11. Routing Tests (routing.py)
```python
def test_route_to_instruction_page()
def test_route_to_request_form()
def test_route_to_response_form()
def test_route_to_meta_page()
def test_route_to_meta_test_page()
def test_route_to_test_server()
def test_route_to_gateway_request()
def test_route_with_rest_path()
def test_route_removes_gateway_prefix()
def test_route_handles_empty_path()
def test_route_not_found()
```

#### 12. Direct Response Building Tests (transforms/response.py)
```python
def test_build_direct_response_details_with_string_output()
def test_build_direct_response_details_with_bytes_output()
def test_build_direct_response_details_with_status_code()
def test_build_direct_response_details_with_content_type()
def test_build_direct_response_details_with_headers()
def test_build_direct_response_details_defaults_status_200()
def test_build_direct_response_details_preserves_original_output()
```

#### 13. Error Rendering Tests (rendering/error.py)
```python
def test_render_error_basic()
def test_render_error_with_exception_summary()
def test_render_error_with_error_detail()
def test_render_error_with_stack_trace()
def test_render_error_with_gateway_archive()
def test_render_error_derives_exception_from_traceback()
def test_render_error_includes_internal_target_path()
def test_render_error_escapes_html_in_messages()
```

#### 14. Diagnostic Extraction Tests (rendering/diagnostic.py)
```python
def test_format_exception_summary_with_message()
def test_format_exception_summary_without_message()
def test_derive_exception_summary_from_traceback()
def test_derive_exception_summary_from_empty_traceback()
def test_derive_exception_summary_with_no_colon()
def test_extract_exception_from_html()
def test_extract_exception_from_html_with_no_match()
def test_extract_stack_trace_from_html()
def test_extract_stack_trace_from_html_with_no_match()
def test_extract_internal_target_path_from_json()
def test_extract_internal_target_path_with_invalid_json()
```

#### 15. Response Adapter Tests (execution/internal.py)
```python
def test_adapt_flask_response()
def test_adapt_dict_response()
def test_adapt_response_with_status_code()
def test_adapt_response_with_headers()
def test_adapt_response_with_content()
def test_adapt_response_json_parsing()
def test_adapt_response_with_invalid_type_raises()
```

#### 16. Gateway Config Loading Tests (config.py)
```python
def test_load_gateways_from_context_variables()
def test_load_gateways_from_dict()
def test_load_gateways_from_json_string()
def test_load_gateways_from_cid_string()
def test_load_gateways_from_named_value_resolver()
def test_load_gateways_returns_empty_dict_on_error()
def test_load_gateways_logs_warning_on_failure()
```

### Integration Tests

#### 1. Full Request Flow Tests
```python
def test_gateway_request_with_no_transforms()
def test_gateway_request_with_request_transform_only()
def test_gateway_request_with_response_transform_only()
def test_gateway_request_with_both_transforms()
def test_gateway_request_with_direct_response()
def test_gateway_request_with_template_resolution()
def test_gateway_request_with_query_parameters()
def test_gateway_request_with_post_body()
def test_gateway_request_with_json_body()
def test_gateway_request_handles_404()
def test_gateway_request_handles_500()
```

#### 2. Test Mode Integration Tests
```python
def test_test_mode_with_cids_archive()
def test_test_mode_with_custom_test_server()
def test_test_mode_url_rewriting()
def test_test_mode_preserves_transforms()
def test_test_mode_with_direct_response()
def test_test_mode_listing_generation()
def test_test_mode_with_empty_archive()
```

#### 3. Meta Page Integration Tests
```python
def test_meta_page_shows_transform_status()
def test_meta_page_validates_transforms()
def test_meta_page_shows_template_info()
def test_meta_page_shows_test_paths()
def test_meta_page_with_missing_transforms()
def test_meta_page_with_invalid_transforms()
def test_meta_test_page_includes_test_context()
```

#### 4. Form Handler Integration Tests
```python
def test_request_form_load_invocation()
def test_request_form_preview_transform()
def test_request_form_execute_request()
def test_response_form_load_invocation()
def test_response_form_transform_response()
def test_form_handles_invalid_cid()
def test_form_handles_missing_gateway()
```

#### 5. Error Handling Integration Tests
```python
def test_request_transform_error_rendering()
def test_response_transform_error_rendering()
def test_target_execution_error_rendering()
def test_gateway_not_found_error()
def test_transform_not_found_error()
def test_invalid_direct_response_error()
def test_internal_server_error_extraction()
```

### End-to-End Tests

#### 1. Real Gateway Scenarios
```python
def test_man_page_gateway_flow()
def test_tldr_gateway_flow()
def test_jsonplaceholder_gateway_flow()
def test_hrx_gateway_flow()
def test_cids_gateway_flow()
```

#### 2. Edge Cases
```python
def test_gateway_with_redirect_chain()
def test_gateway_with_unicode_content()
def test_gateway_with_binary_content()
def test_gateway_with_malformed_transform()
def test_gateway_with_infinite_redirect_loop()
def test_gateway_with_very_large_response()
def test_gateway_with_slow_target()
```

### Property-Based Tests (using Hypothesis)
```python
@given(path=text(), method=sampled_from(['GET', 'POST', 'PUT', 'DELETE']))
def test_request_details_building_never_crashes(path, method)

@given(cid=text())
def test_cid_normalization_always_returns_string_or_none(cid)

@given(status_code=integers(min_value=100, max_value=599))
def test_redirect_following_handles_all_status_codes(status_code)
```

## Open Questions

### 1. Architecture Questions
- **Q1.1**: Should we use dependency injection or a service locator pattern for component wiring?
- **Q1.2**: Should transform functions be cached, or loaded fresh each time?
- **Q1.3**: Should we maintain backward compatibility with the current `gateways` dict format, or introduce versioning?
- **Q1.4**: Should template resolution be lazy (on-demand) or eager (at gateway load time)?
- **Q1.5**: Should we support pluggable transform types (not just request/response)?

### 2. Error Handling Questions
- **Q2.1**: Should transform errors be recoverable (with fallback behavior) or always fatal?
- **Q2.2**: Should we capture and log all transform exceptions, or let some propagate?
- **Q2.3**: Should error pages be customizable per gateway?
- **Q2.4**: What's the desired behavior when a CID is referenced but not found - error or silent fallback?
- **Q2.5**: Should we add retry logic for transient errors (e.g., database timeouts)?

### 3. Testing Questions
- **Q3.1**: Should we mock the database layer or use an in-memory test database?
- **Q3.2**: Should we test against real Flask request contexts or mock them?
- **Q3.3**: What's the minimum test coverage target (80%, 90%, 95%)?
- **Q3.4**: Should we add performance benchmarks as part of the test suite?
- **Q3.5**: Should we test backwards compatibility with existing gateways?

### 4. Transform Function Questions
- **Q4.1**: Should transforms run in a sandboxed environment (restricted builtins)?
- **Q4.2**: Should there be a timeout for transform execution?
- **Q4.3**: Should transforms have access to secrets from the context?
- **Q4.4**: Should we validate transform function signatures at load time or runtime?
- **Q4.5**: Should transforms be able to access other internal servers?

### 5. Performance Questions
- **Q5.1**: Should we cache compiled transforms?
- **Q5.2**: Should we cache CID resolutions?
- **Q5.3**: Should we add connection pooling for internal requests?
- **Q5.4**: What's the acceptable latency budget for gateway requests?
- **Q5.5**: Should we add instrumentation/metrics for monitoring?

### 6. Configuration Questions
- **Q6.1**: Should gateway configurations be versioned?
- **Q6.2**: Should we support environment-specific gateway configs (dev/staging/prod)?
- **Q6.3**: Should gateway configs be hot-reloadable without restart?
- **Q6.4**: Should we validate gateway configs at load time?
- **Q6.5**: Should we support gateway inheritance/composition?

### 7. Test Mode Questions
- **Q7.1**: Should test mode support recording and playback of requests?
- **Q7.2**: Should we allow test mode to override transforms?
- **Q7.3**: Should test archives be versioned?
- **Q7.4**: Should test mode be available in production environments?
- **Q7.5**: Should we support diffs between test and production behavior?

### 8. Direct Response Questions
- **Q8.1**: Should direct responses from request transforms skip the response transform?
- **Q8.2**: Should we support streaming direct responses?
- **Q8.3**: Should direct responses support setting custom headers?
- **Q8.4**: What's the maximum size for a direct response?
- **Q8.5**: Should direct responses be cacheable?

### 9. Routing Questions
- **Q9.1**: Should routing patterns support regex?
- **Q9.2**: Should we add middleware support for gateways?
- **Q9.3**: Should routing be declarative (annotations) or imperative (registration)?
- **Q9.4**: Should we support route constraints (e.g., numeric-only params)?
- **Q9.5**: Should we add route priorities or keep them ordered?

### 10. Migration Questions
- **Q10.1**: Should we maintain a deprecated gateway.py shim during migration?
- **Q10.2**: How long should we support the old API?
- **Q10.3**: Should we provide automated migration tools for existing gateways?
- **Q10.4**: Should we version the gateway server API?
- **Q10.5**: What's the rollback strategy if the refactor introduces issues?

## Test Coverage Requirements

### Must Test (Critical Paths)
1. All routing patterns resolve correctly
2. Request and response transforms execute successfully
3. Error handling renders appropriate error pages
4. CID resolution finds content correctly
5. Internal target execution works for all server types
6. Direct response handling bypasses target execution
7. Test mode correctly rewrites URLs
8. Template resolution finds and loads templates
9. Transform validation catches syntax errors
10. Configuration loading handles all formats

### Should Test (Important Paths)
1. Transform functions with edge case inputs
2. Redirect following with various status codes
3. Form handlers with invalid inputs
4. Meta page with missing/invalid transforms
5. Gateway request with missing configuration
6. Archive-specific path parsing (HRX, CIDS)
7. Response adapters for different result types
8. Diagnostic extraction from various error formats
9. Unicode and binary content handling
10. Large response handling

### Nice to Test (Edge Cases)
1. Concurrent gateway requests
2. Very long redirect chains
3. Malformed CID values
4. Template variables extraction
5. Server definition info retrieval
6. External service server collection
7. Mock server CID generation
8. Query string encoding/decoding
9. Header filtering (cookie removal)
10. Exception summary derivation

## Success Metrics

### Code Quality Metrics
- **Cyclomatic Complexity**: Maximum 10 per function (currently 30+)
- **Function Length**: Maximum 50 lines per function (currently 200+)
- **File Length**: Maximum 300 lines per file (currently 2479)
- **Test Coverage**: Minimum 85% line coverage, 90% branch coverage
- **Type Hints**: 100% of public APIs have type hints

### Performance Metrics
- **Gateway Request Latency**: < 100ms p50, < 500ms p99
- **Transform Compilation**: < 10ms per transform
- **CID Resolution**: < 5ms per CID
- **Memory Usage**: < 50MB per gateway configuration

### Maintainability Metrics
- **Time to Add New Feature**: < 2 hours for simple features
- **Time to Fix Bug**: < 1 hour for typical bugs
- **Time for New Developer Onboarding**: < 1 day to make first contribution
- **Documentation Coverage**: 100% of public APIs documented

## Implementation Priorities

### Phase 1 (Week 1): Foundation
1. Create module structure
2. Extract pure functions (no side effects)
3. Create data classes
4. Write unit tests for extracted functions
5. Validate 100% test pass rate

### Phase 2 (Week 2): Core Services
1. Extract CID resolution logic
2. Extract transform loading/validation
3. Extract template resolution
4. Write unit tests for services
5. Validate integration tests still pass

### Phase 3 (Week 3): Request Handling
1. Refactor request handler
2. Refactor test mode handler
3. Extract target execution
4. Write integration tests
5. Validate end-to-end tests pass

### Phase 4 (Week 4): Routing & Forms
1. Implement new routing system
2. Refactor form handlers
3. Refactor meta page handler
4. Write integration tests
5. Performance testing

### Phase 5 (Week 5): Polish & Migration
1. Update documentation
2. Create migration guide
3. Add backward compatibility layer
4. Performance optimization
5. Final review and merge

## Notes for Iteration

### Ambiguities to Resolve
1. **Transform Execution Scope**: What should transforms be allowed to access?
2. **Error Recovery**: When should errors be recoverable vs. fatal?
3. **Caching Strategy**: What should be cached and for how long?
4. **Test Mode Availability**: Should it be enabled in production?
5. **Configuration Validation**: When should validation occur?

### Edge Cases to Cover
1. Circular redirects in internal requests
2. Transform functions that return invalid types
3. CIDs that resolve to empty content
4. Templates with undefined variables
5. Concurrent modifications to gateway configs
6. Very large responses (> 10MB)
7. Binary content in text fields
8. Malformed UTF-8 in responses
9. Request/response cycles that timeout
10. Database connection failures during request

### Performance Concerns
1. Transform compilation should be cached
2. CID lookups should be cached with TTL
3. Template loading should be lazy and cached
4. Internal request execution should reuse connections
5. Error rendering should not load heavy resources

### Security Considerations
1. Transform functions execute arbitrary Python code - needs sandboxing
2. User input in paths needs sanitization
3. CID values from users need validation
4. Template variables from users need escaping
5. Error messages should not leak sensitive info

## Next Steps

1. **Review this plan** with the team and gather feedback
2. **Answer open questions** by investigating current usage patterns
3. **Prioritize test coverage** based on risk and usage frequency
4. **Create detailed task breakdown** for Phase 1
5. **Set up feature branch** for refactoring work
6. **Begin implementation** starting with pure function extraction

---

**Document Status**: Draft v1.0
**Last Updated**: 2026-01-09
**Owner**: Development Team
**Review Date**: TBD
