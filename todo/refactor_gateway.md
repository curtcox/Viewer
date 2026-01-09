# Gateway.py Refactoring Plan

## Executive Summary

The `gateway.py` file is currently 2479 lines with multiple responsibilities mixed together. This plan proposes breaking it into focused modules with clear boundaries, comprehensive test coverage, and simplified logic flows.

## Design Decisions

### Architecture
- **Component Wiring**: Service locator pattern
- **Transform Loading**: Fresh load each time (no caching)
- **Template Resolution**: Lazy (on-demand)
- **Configuration Format**: No versioning; open to improved format if proposed
- **Configuration Reloading**: Hot-reloadable without restart
- **Configuration Validation**: Yes, at load time

### Error Handling
- **Transform Errors**: Fatal with detailed diagnostics for correction
- **Exception Handling**: Log all exceptions and propagate them
- **Error Pages**: Customizable per gateway
- **Missing CIDs**: Error (not silent fallback)
- **Retry Logic**: None

### Testing Approach
- **Philosophy**: Red-green-refactor; no coverage targets
- **Database**: Either mock or real in-memory DB is acceptable
- **Flask Contexts**: Mock them
- **Performance**: No benchmarks
- **Compatibility**: No backwards compatibility testing needed (no existing users)

### Transform Functions
- **Sandboxing**: None - transforms run with full Python access
- **Timeouts**: None
- **Secrets Access**: Yes, transforms can access secrets from context
- **Signature Validation**: Runtime validation
- **Internal Server Access**: Yes, transforms can call other internal servers (that's the point)

### Performance
- **Caching**: None (transforms, CIDs, templates, connections)
- **Latency Budget**: Unlimited
- **Connection Pooling**: None

### Test Mode
- **Recording/Playback**: Yes (but not unique to test mode)
- **Transform Override**: No
- **Archive Versioning**: No
- **Production Availability**: Yes

### Direct Responses
- **Response Transform**: Still runs (but knows it was a direct response)
- **Streaming**: No
- **Size Limits**: None
- **Caching**: Not cacheable
- **Custom Headers**: Not supported initially (add later if needed)

### Routing
- **Scope**: Internal to /gateway/ only (does not touch Flask routing elsewhere)
- **Strategy**: First-match-wins (ordered routing, no priorities)
- **Reserved Names**: Servers named "meta", "request", "response", or "test" need aliases to be accessible via gateway
- **Regex Support**: Internal implementation detail
- **Middleware**: Yes
- **Constraints**: No (gateway delegates, doesn't constrain)

### Observability
- **Instrumentation**: None built-in
- **Logging**: Delegate to pluggable logging (not implemented in gateway directly)
- **Metrics**: External concern (use separate services)

### Gateway Organization
- **Transform Types**: Only request and response transforms (no additional pluggable types)
- **Gateway Relationships**: Independent (no inheritance or composition)
- **Test/Production Diffs**: External concern (use separate comparison services, not built into gateway)

### Migration
- **Compatibility Shim**: None needed (no existing users)
- **Migration Tools**: None needed
- **API Versioning**: None
- **Rollback Strategy**: No rollback - branch won't merge if problems can't be resolved

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
├── __init__.py                    # Main entry point with service locator
├── core.py                        # Core gateway orchestration
├── routing.py                     # Route parsing and dispatch
├── middleware.py                  # Middleware support
├── config.py                      # Gateway configuration loading & validation
├── transforms/
│   ├── __init__.py
│   ├── loader.py                  # Transform loading and compilation (no cache)
│   ├── validator.py               # Transform validation
│   ├── request.py                 # Request transformation logic
│   └── response.py                # Response transformation logic
├── templates/
│   ├── __init__.py
│   ├── loader.py                  # Template file loading (lazy)
│   └── resolver.py                # Template name resolution
├── execution/
│   ├── __init__.py
│   ├── target.py                  # Target resolution
│   ├── internal.py                # Internal server execution
│   └── redirects.py               # Redirect following logic
├── cid/
│   ├── __init__.py
│   ├── resolver.py                # CID content resolution (no cache)
│   └── normalizer.py              # CID path normalization
├── handlers/
│   ├── __init__.py
│   ├── request.py                 # Gateway request handler
│   ├── test.py                    # Test mode handler
│   ├── meta.py                    # Meta page handler
│   └── forms.py                   # Form handlers
├── rendering/
│   ├── __init__.py
│   ├── error.py                   # Error page rendering (per-gateway customizable)
│   └── diagnostic.py              # Diagnostic info extraction
└── models.py                      # Data classes for type safety
```

### Service Locator Pattern

```python
# __init__.py
class ServiceLocator:
    """Central registry for gateway services."""

    def __init__(self):
        self._services = {}

    def register(self, name: str, service):
        """Register a service by name."""
        self._services[name] = service

    def get(self, name: str):
        """Get a service by name."""
        if name not in self._services:
            raise KeyError(f"Service not registered: {name}")
        return self._services[name]

    def register_default_services(self):
        """Register all default gateway services."""
        from .cid.resolver import CIDResolver
        from .cid.normalizer import CIDNormalizer
        from .transforms.loader import TransformLoader
        from .transforms.validator import TransformValidator
        from .templates.resolver import TemplateResolver
        from .execution.target import TargetExecutor
        from .rendering.error import ErrorRenderer
        from .rendering.diagnostic import DiagnosticExtractor
        from .config import ConfigLoader

        self.register('cid_resolver', CIDResolver())
        self.register('cid_normalizer', CIDNormalizer())
        self.register('transform_loader', TransformLoader(self.get('cid_resolver')))
        self.register('transform_validator', TransformValidator())
        self.register('template_resolver', TemplateResolver(self.get('cid_resolver')))
        self.register('target_executor', TargetExecutor())
        self.register('error_renderer', ErrorRenderer())
        self.register('diagnostic_extractor', DiagnosticExtractor())
        self.register('config_loader', ConfigLoader(self.get('cid_resolver')))

# Global service locator instance
_services = ServiceLocator()

def get_services() -> ServiceLocator:
    """Get the global service locator."""
    return _services
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
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class GatewayConfig:
    """Configuration for a gateway server."""
    name: str
    request_transform_cid: Optional[str] = None
    response_transform_cid: Optional[str] = None
    templates: Dict[str, str] = field(default_factory=dict)
    target_url: Optional[str] = None
    custom_error_template_cid: Optional[str] = None  # Per-gateway error pages

@dataclass
class RequestDetails:
    """Details of an incoming gateway request."""
    path: str
    method: str = "GET"
    query_string: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    json: Optional[Any] = None
    data: Optional[str] = None
    url: Optional[str] = None

@dataclass
class ResponseDetails:
    """Details of a response from target server or direct response."""
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json: Optional[Any] = None
    request_path: str = ""
    source: str = "server"  # "server", "test_server", or "request_transform"
    is_direct_response: bool = False  # Flag for response transform

@dataclass
class TransformResult:
    """Result from a transform function."""
    output: str | bytes
    content_type: str = "text/plain"
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None

@dataclass
class Target:
    """Internal target for gateway execution."""
    mode: str  # "internal" only
    url: str

    def validate(self):
        """Validate target configuration."""
        if self.mode != "internal":
            raise ValueError(f"Unsupported target mode: {self.mode}")
        if not self.url.startswith("/"):
            raise ValueError("Gateway target must be an internal path")

@dataclass
class DirectResponse:
    """Direct response from request transform (bypasses target execution)."""
    output: str | bytes
    content_type: str = "text/html"
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None
```

### Phase 3: Extract Service Classes (Medium-High Risk)
Create classes to encapsulate related functionality:

```python
# transforms/loader.py
class TransformLoader:
    """Loads and compiles transform functions (no caching)."""

    def __init__(self, cid_resolver):
        self.cid_resolver = cid_resolver

    def load_transform(self, cid: str, context: dict) -> Optional[callable]:
        """Load and compile a transform function from a CID.

        Always loads fresh - no caching.
        """
        ...

    def compile_transform(self, source: str) -> Optional[callable]:
        """Compile transform source into a callable function.

        No sandboxing - full Python access.
        """
        ...

# execution/target.py
class TargetExecutor:
    """Executes requests against internal targets."""

    def __init__(self):
        pass  # No connection pooling

    def execute(self, target: Target, request_details: RequestDetails) -> ResponseDetails:
        """Execute request against a target and return response.

        No timeout - unlimited execution time.
        """
        ...

    def _follow_redirects(self, response, max_hops: int = 3) -> ResponseDetails:
        """Follow internal redirects to final content."""
        ...

# cid/resolver.py
class CIDResolver:
    """Resolves CID values to content (no caching)."""

    def resolve(self, cid_value: str, as_bytes: bool = False) -> Optional[str | bytes]:
        """Resolve a CID value to its content.

        Always resolves fresh - no caching.
        Raises error if CID not found (no silent fallback).
        """
        ...
```

### Phase 4: Refactor Main Request Handlers (High Risk)
Break down the massive request handling functions:

```python
# handlers/request.py
class GatewayRequestHandler:
    """Handles gateway requests with clear separation of concerns."""

    def __init__(self, services: ServiceLocator):
        self.services = services

    def handle(self, server_name: str, rest_path: str, context: dict):
        """Handle a gateway request.

        Flow:
        1. Load config
        2. Build request details
        3. Apply request transform (may return direct response)
        4. Execute target (if no direct response)
        5. Apply response transform (always, even for direct responses)
        6. Return final response
        """
        config = self._load_config(server_name)
        request_details = self._build_request_details(rest_path)

        # Apply request transform
        transformed_request, direct_response = self._apply_request_transform(
            config, request_details, context
        )

        # Execute target or use direct response
        if direct_response:
            response_details = direct_response
            response_details.is_direct_response = True
        else:
            response_details = self._execute_target(config, transformed_request)

        # Apply response transform (always runs, even for direct responses)
        return self._apply_response_transform(
            config, response_details, context
        )
```

### Phase 5: Add Middleware & Routing (Medium Risk)

```python
# middleware.py
class Middleware:
    """Base class for gateway middleware."""

    def before_request(self, request_details: RequestDetails, context: dict) -> RequestDetails:
        """Called before request transform."""
        return request_details

    def after_request(self, response: TransformResult, context: dict) -> TransformResult:
        """Called after response transform."""
        return response

    def on_error(self, error: Exception, context: dict):
        """Called when an error occurs."""
        pass

class MiddlewareChain:
    """Manages middleware execution."""

    def __init__(self):
        self.middleware: List[Middleware] = []

    def add(self, middleware: Middleware):
        """Add middleware to the chain."""
        self.middleware.append(middleware)

    def execute_before_request(self, request_details: RequestDetails, context: dict):
        """Execute all before_request middleware."""
        for mw in self.middleware:
            request_details = mw.before_request(request_details, context)
        return request_details

    def execute_after_request(self, response: TransformResult, context: dict):
        """Execute all after_request middleware."""
        for mw in reversed(self.middleware):
            response = mw.after_request(response, context)
        return response

    def execute_on_error(self, error: Exception, context: dict):
        """Execute all on_error middleware."""
        for mw in self.middleware:
            mw.on_error(error, context)

# routing.py
class GatewayRouter:
    """Routes gateway requests using first-match-wins strategy.

    Routing is scoped to /gateway/ only - does not affect Flask routing elsewhere.

    Reserved route patterns (checked first):
    - "" (empty) -> instruction page
    - "request" -> request form
    - "response" -> response form
    - "meta/<server>" -> meta page
    - "meta/test/<test_path>/as/<server>" -> meta test page
    - "test/<test_path>/as/<server>/<rest>" -> test mode

    Gateway server routes (checked last):
    - "<server>/<rest>" -> gateway request with path
    - "<server>" -> gateway request without path

    Important: Servers named "meta", "request", "response", or "test" will be
    shadowed by reserved routes and need aliases to be accessible via gateway.
    """

    def __init__(self, handlers):
        self.handlers = handlers
        self._init_routes()

    def _init_routes(self):
        """Initialize routes in first-match-wins order.

        Order matters! More specific routes must come before general patterns.
        """
        # Reserved routes come first
        self.routes = [
            ("", self.handlers.instruction),
            ("request", self.handlers.request_form),
            ("response", self.handlers.response_form),
            ("meta/test/{test_path:path}/as/{server}", self.handlers.meta_test),
            ("meta/{server}", self.handlers.meta),
            ("test/{test_path:path}/as/{server}/{rest:path}", self.handlers.test),
            ("test/{test_path:path}/as/{server}", self.handlers.test),
            # Gateway server routes come last
            ("{server}/{rest:path}", self.handlers.gateway_request),
            ("{server}", self.handlers.gateway_request),
        ]

    def route(self, path: str, context: dict):
        """Match path to handler using first-match-wins.

        Args:
            path: Request path after /gateway/ prefix
            context: Request context

        Returns:
            Handler result
        """
        # Strip leading/trailing slashes
        path = path.strip("/")

        for pattern, handler in self.routes:
            params = self._match(pattern, path)
            if params is not None:
                return handler(**params, context=context)

        # No match found
        return self.handlers.not_found(path=path, context=context)

    def _match(self, pattern: str, path: str) -> Optional[dict]:
        """Match path against pattern, return params or None.

        Pattern syntax:
        - "" matches empty path only
        - "foo" matches "foo" exactly
        - "{var}" matches one segment, captures as 'var'
        - "{var:path}" matches remaining path, captures as 'var'
        """
        # Implement simple pattern matching (can be regex internally)
        # This is a simplified example - actual implementation may vary
        ...
```

## Proposed Configuration Format

Since no versioning is needed and we're open to a better format, here's a proposed improvement:

### Current Format (Dict-based)
```python
{
    "man": {
        "request_transform_cid": "/CID1",
        "response_transform_cid": "/CID2",
        "templates": {
            "man_page.html": "/CID3"
        }
    }
}
```

### Proposed Format (More Explicit)
```python
{
    "man": {
        "transforms": {
            "request": "/CID1",
            "response": "/CID2"
        },
        "templates": {
            "man_page.html": "/CID3"
        },
        "error_handling": {
            "custom_error_template": "/CID4",  # Optional per-gateway error page
            "log_level": "ERROR"                # Optional logging level
        },
        "target": {
            "url": "/man"  # Explicit target URL (defaults to /{gateway_name})
        }
    }
}
```

**Benefits:**
- More explicit structure
- Easier to add new transform types
- Clearer separation of concerns
- Optional per-gateway error handling
- Explicit target configuration

**Migration:** Since there are no existing users, we can use the new format from the start.

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
def test_resolve_cid_not_found_raises_error()  # Changed: raises instead of None
def test_resolve_cid_with_unicode_content()
def test_resolve_cid_with_binary_content()
def test_resolve_cid_logs_database_error_and_propagates()  # Changed: propagates
def test_resolve_cid_logs_filesystem_error_and_propagates()  # Changed: propagates
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
def test_build_request_details_logs_json_parse_error_and_propagates()  # Changed
def test_build_request_details_extracts_raw_body()
def test_build_request_details_handles_empty_body()
```

#### 4. Transform Loading Tests (transforms/loader.py)
```python
def test_load_transform_from_file_path()
def test_load_transform_from_cid()
def test_load_transform_not_found_raises_error()  # Changed: raises
def test_compile_transform_with_transform_request()
def test_compile_transform_with_transform_response()
def test_compile_transform_with_both_functions_prefers_request()
def test_compile_transform_with_no_functions_returns_none()
def test_compile_transform_with_syntax_error_logs_and_propagates()  # Changed
def test_load_transform_handles_unicode_source()
def test_load_transform_logs_database_error_and_propagates()  # Changed
def test_load_transform_always_fresh_no_cache()  # New: verify no caching
def test_compile_transform_full_python_access()  # New: verify no sandboxing
```

#### 5. Transform Validation Tests (transforms/validator.py)
```python
def test_validate_transform_with_valid_syntax()
def test_validate_transform_with_syntax_error_logs_and_fails()  # Changed
def test_validate_transform_missing_required_function_fails()  # Changed
def test_validate_transform_function_signature_at_runtime()  # New: runtime validation
def test_validate_transform_function_with_correct_params()
def test_validate_transform_not_found_raises()  # Changed
def test_validate_direct_response_with_valid_output()
def test_validate_direct_response_missing_output_key()
def test_validate_direct_response_invalid_output_type()
def test_validate_direct_response_invalid_content_type()
def test_validate_direct_response_invalid_status_code()
def test_validate_direct_response_with_all_optional_fields()
def test_validate_direct_response_unlimited_size()  # New: no size limit
```

#### 6. Template Resolution Tests (templates/resolver.py)
```python
def test_create_template_resolver()
def test_resolve_template_by_name_lazy_loading()  # New: verify lazy
def test_resolve_template_not_in_config_raises_value_error()
def test_resolve_template_cid_not_found_raises_lookup_error()
def test_resolve_template_returns_jinja2_template()
def test_template_resolver_no_caching()  # New: verify no caching
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
def test_execute_internal_target_no_timeout()  # New: verify no timeout
def test_execute_internal_target_no_connection_pooling()  # New: verify no pooling
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
def test_follow_redirects_with_invalid_cid_raises()  # Changed: raises
def test_follow_redirects_logs_errors_and_propagates()  # New
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
def test_route_middleware_execution_order()  # New: middleware
```

#### 12. Direct Response Tests (transforms/response.py)
```python
def test_build_direct_response_details_with_string_output()
def test_build_direct_response_details_with_bytes_output()
def test_build_direct_response_details_with_status_code()
def test_build_direct_response_details_with_content_type()
def test_build_direct_response_details_with_headers()
def test_build_direct_response_details_defaults_status_200()
def test_build_direct_response_details_preserves_original_output()
def test_build_direct_response_details_unlimited_size()  # New
def test_direct_response_flags_is_direct_response()  # New: flag for response transform
def test_direct_response_still_runs_response_transform()  # New: verify behavior
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
def test_render_error_custom_template_per_gateway()  # New: per-gateway customization
def test_render_error_logs_and_propagates_exceptions()  # New
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
def test_load_gateways_validation_at_load_time()  # New: load-time validation
def test_load_gateways_logs_errors_and_propagates()  # Changed
def test_load_gateways_supports_new_format()  # New: proposed format
def test_load_gateways_hot_reload()  # New: hot-reloadable
```

#### 17. Service Locator Tests (__init__.py)
```python
def test_service_locator_register()
def test_service_locator_get()
def test_service_locator_get_unregistered_raises()
def test_service_locator_register_default_services()
def test_service_locator_resolves_dependencies()
```

#### 18. Middleware Tests (middleware.py)
```python
def test_middleware_before_request()
def test_middleware_after_request()
def test_middleware_on_error()
def test_middleware_chain_execution_order()
def test_middleware_chain_before_request()
def test_middleware_chain_after_request()
def test_middleware_chain_on_error()
def test_multiple_middleware_composition()
```

### Integration Tests

#### 1. Full Request Flow Tests
```python
def test_gateway_request_with_no_transforms()
def test_gateway_request_with_request_transform_only()
def test_gateway_request_with_response_transform_only()
def test_gateway_request_with_both_transforms()
def test_gateway_request_with_direct_response()
def test_gateway_request_direct_response_still_runs_response_transform()  # New
def test_gateway_request_with_template_resolution()
def test_gateway_request_with_query_parameters()
def test_gateway_request_with_post_body()
def test_gateway_request_with_json_body()
def test_gateway_request_handles_404()
def test_gateway_request_handles_500()
def test_gateway_request_transforms_access_secrets()  # New
def test_gateway_request_transforms_call_internal_servers()  # New
def test_gateway_request_with_middleware()  # New
def test_gateway_request_with_custom_error_page()  # New
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
def test_test_mode_available_in_production()  # New: verify production availability
def test_test_mode_cannot_override_transforms()  # New: verify restriction
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
def test_request_transform_error_rendering_with_diagnostics()  # Changed
def test_response_transform_error_rendering_with_diagnostics()  # Changed
def test_target_execution_error_rendering()
def test_gateway_not_found_error()
def test_transform_not_found_error()
def test_invalid_direct_response_error()
def test_internal_server_error_extraction()
def test_cid_not_found_error_rendering()  # New: not silent fallback
def test_all_errors_logged_and_propagated()  # New
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
def test_gateway_with_very_large_response()  # No max size
def test_gateway_with_slow_target()  # No timeout
def test_gateway_hot_reload_config()  # New: hot-reload
def test_transform_imports_modules()  # New: no sandboxing
def test_transform_accesses_filesystem()  # New: no sandboxing
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

## Design Philosophy Summary

### Simplicity First
- **No caching** - Keep it simple, load fresh every time
- **No sandboxing** - Trust developers, provide full Python access
- **No timeouts** - Let operations complete naturally
- **No built-in instrumentation** - Delegate to external logging
- **No inheritance/composition** - Keep gateways independent and explicit
- **Fatal errors** - Fail fast with rich diagnostics for quick debugging

### Clear Separation of Concerns
- **Gateway scope**: Only handles routing under /gateway/, doesn't touch Flask routing elsewhere
- **Transform scope**: Only request and response transforms (no additional types needed)
- **External concerns**: Test/prod diffs, metrics, monitoring handled by separate services
- **Reserved names**: Special routes (meta, request, response, test) take precedence; conflicting server names need aliases

### Developer Experience
- **Rich diagnostics** - All errors provide detailed context for correction
- **Hot-reload** - Configuration changes without restart
- **Middleware support** - Extensibility without modifying core
- **Type safety** - Data classes for clear APIs
- **Red-green-refactor** - Test-driven development, no arbitrary coverage targets

## Test Coverage Requirements

### Philosophy: Red-Green-Refactor
- Write failing test first (red)
- Write minimal code to pass (green)
- Refactor with confidence (tests still green)
- No coverage percentage targets
- Focus on behavior, not lines of code

### Critical Paths (Must Test)
1. All routing patterns resolve correctly
2. Request and response transforms execute successfully
3. Error handling renders appropriate error pages with diagnostics
4. CID resolution finds content or raises clear errors
5. Internal target execution works for all server types
6. Direct response handling still runs response transform
7. Test mode correctly rewrites URLs
8. Template resolution finds and loads templates
9. Transform validation catches syntax errors
10. Configuration loading handles all formats
11. All errors are logged and propagated
12. Transforms can access secrets and internal servers
13. Middleware executes in correct order
14. Custom error pages work per gateway
15. Hot-reloading of configuration

### Important Paths (Should Test)
1. Transform functions with edge case inputs
2. Redirect following with various status codes
3. Form handlers with invalid inputs
4. Meta page with missing/invalid transforms
5. Gateway request with missing configuration
6. Archive-specific path parsing (HRX, CIDS)
7. Response adapters for different result types
8. Diagnostic extraction from various error formats
9. Unicode and binary content handling
10. Large response handling (no size limits)
11. Slow targets (no timeouts)
12. Service locator dependency resolution

### Edge Cases (Nice to Test)
1. Concurrent gateway requests
2. Very long redirect chains
3. Malformed CID values raise errors
4. Template variables extraction
5. Server definition info retrieval
6. External service server collection
7. Mock server CID generation
8. Query string encoding/decoding
9. Header filtering (cookie removal)
10. Exception summary derivation
11. Transform imports external modules (no sandboxing)
12. Transform file system access (no sandboxing)

## Success Metrics

### Code Quality
- **Cyclomatic Complexity**: Maximum 10 per function (currently 30+)
- **Function Length**: Maximum 50 lines per function (currently 200+)
- **File Length**: Maximum 300 lines per file (currently 2479)
- **Type Hints**: 100% of public APIs have type hints
- **Test Philosophy**: Red-green-refactor (no coverage targets)

### Maintainability
- **Time to Add New Feature**: < 2 hours for simple features
- **Time to Fix Bug**: < 1 hour for typical bugs
- **Time for New Developer Onboarding**: < 1 day to make first contribution
- **Documentation Coverage**: 100% of public APIs documented

### Performance (No Targets, But Track)
- Track gateway request latency (no maximum)
- Track transform compilation time (no caching)
- Track CID resolution time (no caching)
- Track memory usage (no limits)
- Use for identifying regressions, not as gates

## Implementation Priorities

### Phase 1 (Week 1): Foundation
1. Create module structure
2. Extract pure functions (no side effects)
3. Create data classes
4. Implement service locator
5. Write unit tests for extracted functions
6. Validate 100% test pass rate

### Phase 2 (Week 2): Core Services
1. Extract CID resolution logic (no caching)
2. Extract transform loading/validation (no caching, no sandboxing)
3. Extract template resolution (lazy, no caching)
4. Write unit tests for services
5. Validate integration tests still pass

### Phase 3 (Week 3): Request Handling
1. Refactor request handler (no timeouts, no pooling)
2. Refactor test mode handler
3. Extract target execution
4. Implement direct response with response transform
5. Write integration tests
6. Validate end-to-end tests pass

### Phase 4 (Week 4): Forms & Meta Pages
1. Refactor form handlers
2. Refactor meta page handler
3. Implement custom error pages per gateway
4. Write integration tests

### Phase 5 (Week 5): Middleware & Routing
1. Implement middleware system
2. Implement first-match-wins routing with reserved names
3. Add routing tests for shadowed server names
4. Write integration tests

### Phase 6 (Week 6): Configuration & Polish
1. Implement new configuration format
2. Add hot-reloading support
3. Add load-time validation
4. Implement pluggable logging delegation
5. Update documentation
6. Final review and merge

## Notes for Implementation

### Critical Implementation Details

**No Caching Anywhere:**
- Transforms loaded fresh each time
- CIDs resolved fresh each time
- Templates loaded fresh each time (lazy)
- No connection pooling
- Simplifies code, ensures freshness

**No Sandboxing:**
- Transforms run with full Python access
- Can import any module
- Can access filesystem
- Can call any internal server
- Developer is responsible for security

**No Timeouts:**
- Gateway requests can run indefinitely
- Transform execution unlimited
- Target execution unlimited
- Developer handles performance

**Fatal Errors with Diagnostics:**
- All errors are fatal (no silent fallbacks)
- All errors logged
- All errors propagated
- Rich diagnostic information
- Per-gateway custom error pages

**Response Transform Always Runs:**
- Even for direct responses
- Response transform knows it was direct (is_direct_response flag)
- Can choose to return unmodified or transform further
- Provides consistency and flexibility

**First-Match-Wins Routing:**
- Routes checked in registration order
- More specific patterns registered before general patterns
- Reserved names (meta, request, response, test) have dedicated routes
- Servers with reserved names need aliases to be accessible
- Example: Server named "meta" must use alias like "meta-server" in gateway config
- All routing scoped to /gateway/ prefix only

### Edge Cases to Cover

1. Circular redirects in internal requests → Detect and error
2. Transform functions that return invalid types → Validate and error
3. CIDs that resolve to empty content → Allow (empty is valid)
4. Templates with undefined variables → Jinja will error
5. Concurrent modifications to gateway configs → Hot-reload handles
6. Very large responses → No limit, handle naturally
7. Binary content in text fields → Handle encoding
8. Malformed UTF-8 in responses → Handle with errors="replace"
9. Request/response cycles → No timeout
10. Database connection failures → Log and propagate

### Security Considerations (Revised)

**No Sandboxing:**
1. Transforms execute arbitrary Python code with full access
2. Developer is responsible for transform security
3. No restrictions on imports, filesystem, network
4. Suitable for trusted internal use, not user-supplied code

**Still Important:**
1. User input in paths needs sanitization (SQL injection, path traversal)
2. CID values from users need validation (prevent injection)
3. Template variables from users need escaping (XSS prevention)
4. Error messages should not leak secrets (sanitize diagnostics)

## Next Steps

1. ✅ ~~Answer all open questions~~ - **COMPLETE**
2. ✅ ~~Review proposed configuration format~~ - **APPROVED**
3. ✅ ~~Review middleware design~~ - **APPROVED**
4. **Create detailed task breakdown for Phase 1**
5. **Begin implementation** starting with pure function extraction

## Open Questions for Implementation

### Routing Implementation Details
**Question:** How should the pattern matching work internally?

The `GatewayRouter._match()` method needs implementation. Options:
- **A.** Simple string splitting and matching (fastest, most explicit)
- **B.** Regex-based matching (more flexible, standard approach)
- **C.** Use existing library like werkzeug.routing (less code, well-tested)

**Recommendation:** Start with option C (werkzeug.routing) unless there's a reason to avoid dependencies.

### Pluggable Logging Interface
**Question:** What interface should the gateway expect for logging delegation?

Since we're delegating to pluggable logging, we need to define what that interface looks like:

```python
# Option A: Standard Python logging
import logging
logger = logging.getLogger('gateway')
logger.info("Request", extra={"gateway": name, "path": path})

# Option B: Structured logging interface
class LoggingDelegate:
    def log_request(self, gateway: str, path: str, method: str):
        ...
    def log_error(self, gateway: str, error: Exception, context: dict):
        ...

# Option C: Simple callable
log_fn = context.get('log_gateway_event')
if log_fn:
    log_fn(event_type='request', gateway=name, path=path)
```

**Recommendation:** Start with Option A (standard Python logging with structured extras) - most flexible and integrates with existing logging infrastructure.

---

**Document Status**: **APPROVED v3.0** - Ready for implementation
**Last Updated**: 2026-01-09
**Owner**: Development Team
**All Design Decisions**: Complete (50/50 questions resolved)
