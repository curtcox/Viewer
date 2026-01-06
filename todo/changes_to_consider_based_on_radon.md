# Architectural Improvements Based on Radon Complexity Analysis

This document outlines structural improvements to consider based on Radon cyclomatic complexity analysis. The analysis identified several code areas with high complexity that could benefit from architectural refactoring.

## Executive Summary

The Radon analysis revealed three primary areas of concern:

1. **Server Definition `main()` Functions** - Complexity scores ranging from D (23) to F (58)
2. **Gateway Request Handlers** - Complexity scores of E (31) to F (42-43)
3. **Language Detection Logic** - Complexity score of E (31)

These issues share common anti-patterns: large monolithic functions, extensive if-elif chains, and mixed responsibilities.

---

## 1. Server Definition Architecture

### Current State

Most server definitions in `reference/templates/servers/definitions/` follow a pattern where the `main()` function handles everything:

```
main() complexity distribution:
- F (41-58): box.py, coda.py, squarespace.py, onedrive.py, meta_ads.py, wix.py
- E (31-34): aws_s3.py, apify.py, etsy.py, klaviyo.py, telegram.py, xero.py, etc.
- D (23-30): activecampaign.py, amplitude.py, asana.py, etc.
```

### Root Causes

1. **Operation Dispatch via If-Elif Chains**
   - Each `main()` function contains 10-20+ operation cases
   - Each branch includes validation, URL construction, and execution logic
   - Example: `box.py` has 12 operations with 250+ lines of branching

2. **URL Construction Duplication**
   - Same URLs built twice: once for preview, once for execution
   - Each operation builds URLs with nearly identical patterns

3. **Mixed Responsibilities**
   - Credential validation
   - Parameter validation
   - URL construction
   - HTTP method selection
   - Dry-run preview generation
   - API request execution
   - Response parsing

### Proposed Solutions

#### 1.1 Operation Registry Pattern

Replace if-elif chains with a declarative operation registry:

```python
# Proposed structure for server definitions
OPERATIONS = {
    "list_items": Operation(
        method="GET",
        url_template="/folders/{folder_id}/items",
        required_params=["folder_id"],
        defaults={"folder_id": "0"},
    ),
    "get_file": Operation(
        method="GET",
        url_template="/files/{file_id}",
        required_params=["file_id"],
    ),
    "delete_file": Operation(
        method="DELETE",
        url_template="/files/{file_id}",
        required_params=["file_id"],
    ),
    # ...
}

def main(**kwargs):
    return execute_operation(OPERATIONS, kwargs, base_url="https://api.box.com/2.0")
```

**Benefits:**
- Reduces `main()` from 200+ lines to ~10 lines
- Operations become data, not code paths
- Validation logic can be generalized
- Testing becomes trivial (test the registry data + the executor once)

#### 1.2 Leverage Existing `server_utils` Abstractions

The codebase already has under-utilized abstractions in `server_utils/external_api/`:

| Class | Purpose | Current Usage |
|-------|---------|---------------|
| `OperationValidator` | Validate operation names | Inconsistent |
| `ParameterValidator` | Validate required parameters | Inconsistent |
| `PreviewBuilder` | Build dry-run responses | Inconsistent |
| `ResponseHandler` | Handle API responses | Inconsistent |

**Recommendation:** Mandate use of these utilities across all server definitions to reduce duplication and complexity.

#### 1.3 Base Server Class

Create an abstract base class that handles common patterns:

```python
class ExternalApiServer:
    """Base class for external API server definitions."""

    base_url: str
    operations: Dict[str, Operation]
    auth_header_name: str = "Authorization"

    def main(self, operation: str, dry_run: bool = True, **params):
        # 1. Validate operation
        # 2. Validate required params
        # 3. Build request
        # 4. Return preview or execute
        pass
```

---

## 2. Gateway Request Handler Architecture

### Current State

`reference/templates/servers/definitions/gateway.py` (2250 lines) contains:

| Function | Complexity | Lines (approx) |
|----------|-----------|----------------|
| `_handle_gateway_test_request` | F (42) | ~200 |
| `_handle_gateway_request` | E (31) | ~200 |
| `main` | D (24) | ~150 |

### Root Causes

1. **Near-Identical Handler Functions**
   - `_handle_gateway_request` and `_handle_gateway_test_request` share 80% of their logic
   - Differences are only in test mode flag and server path resolution

2. **Deep Nesting**
   - Transform loading, validation, execution, error handling all nested
   - Each branch contains significant logic

3. **Inline Error Rendering**
   - `_render_error()` calls repeated with similar parameters throughout
   - Error context building duplicated

### Proposed Solutions

#### 2.1 Unified Request Handler

Extract common logic into a single handler with a mode parameter:

```python
def _handle_gateway_request_common(
    server_name: str,
    rest_path: str,
    gateways: dict,
    context: dict,
    *,
    test_mode: bool = False,
    test_server_path: str = None,
):
    """Unified gateway request handler."""
    pass
```

#### 2.2 Pipeline Architecture

Refactor request handling into discrete pipeline stages:

```python
class GatewayPipeline:
    """Process gateway requests through discrete stages."""

    def process(self, request: GatewayRequest) -> GatewayResponse:
        return (
            self.validate_gateway(request)
            .then(self.build_request_details)
            .then(self.apply_request_transform)
            .then(self.execute_server_call)
            .then(self.apply_response_transform)
            .then(self.build_response)
        )
```

**Each stage becomes a testable unit with single responsibility.**

#### 2.3 Error Context Builder

Extract error context building into a dedicated class:

```python
class GatewayErrorBuilder:
    def __init__(self, gateways: dict, archive: str = None, path: str = None):
        self.gateways = gateways
        self.archive = archive
        self.path = path

    def render(self, title: str, message: str, **extra) -> Response:
        return _render_error(
            title, message, self.gateways,
            gateway_archive=self.archive,
            gateway_path=self.path,
            **extra
        )
```

---

## 3. Language Detection Refactoring

### Current State

`server_execution/language_detection.py` has:
- `detect_server_language()` with complexity E (31)
- 6 sequential pattern-matching stages
- Multiple regex compilations per call

### Root Causes

1. **Sequential Pattern Matching**
   - Each language check is independent but sequentially ordered
   - Priority logic embedded in control flow

2. **Inline Regex Patterns**
   - Patterns defined inline and recompiled each call
   - Similar patterns grouped but not reusable

### Proposed Solutions

#### 3.1 Detector Registry Pattern

```python
@dataclass
class LanguageDetector:
    language: str
    priority: int
    patterns: List[re.Pattern]

    def matches(self, text: str) -> bool:
        return any(p.search(text) for p in self.patterns)

DETECTORS = [
    LanguageDetector("bash", 100, [re.compile(r"^@bash_command")]),
    LanguageDetector("python", 90, [re.compile(r"^\s*def\s+\w+\s*\(")]),
    # ...
]

def detect_server_language(definition: str) -> str:
    if not definition:
        return "python"

    for detector in sorted(DETECTORS, key=lambda d: -d.priority):
        if detector.matches(definition):
            return detector.language

    return "python"
```

**Benefits:**
- Pre-compiled regex patterns
- Explicit priority ordering
- Easy to add new languages
- Testable detector units

#### 3.2 Early Return Optimization

Restructure shebang detection to use early returns with a helper:

```python
def _detect_from_shebang(first_line: str) -> Optional[str]:
    """Detect language from shebang line."""
    if not first_line.startswith("#!"):
        return None

    shebang_map = {
        "python": ["python"],
        "bash": ["bash", "/sh", "sh "],
        "typescript": ["deno", "ts-node", "typescript"],
        "clojure": ["clojure", "bb", "babashka"],
    }

    for language, markers in shebang_map.items():
        if any(m in first_line for m in markers):
            return language

    return None
```

---

## 4. Cross-Cutting Improvements

### 4.1 Reduce Duplication Across Server Definitions

Analysis shows significant code duplication across 100+ server definition files:

| Pattern | Occurrences | Lines Each |
|---------|-------------|------------|
| Operation validation | 100+ | 5-10 |
| Credential checking | 100+ | 3-5 |
| Dry-run preview building | 100+ | 10-20 |
| Response error handling | 100+ | 10-15 |

**Recommendation:** Create a `ServerDefinitionTemplate` that generates server definitions from declarative configurations.

### 4.2 Extract Common Patterns to Mixins

```python
class CredentialValidationMixin:
    """Mixin for credential validation."""

    def validate_credentials(self, **credentials) -> Optional[Dict]:
        for name, value in credentials.items():
            if name.isupper() and not value:
                return missing_secret_error(name)
        return None

class OperationDispatchMixin:
    """Mixin for operation dispatch."""

    operations: Dict[str, Operation]

    def dispatch(self, operation: str, **params) -> Dict:
        if operation not in self.operations:
            return validation_error("Invalid operation", field="operation")
        return self.operations[operation].execute(**params)
```

### 4.3 Introduce Strategy Pattern for URL Building

Many servers build URLs with similar patterns but different base URLs:

```python
class UrlBuilder:
    """Build URLs for API requests."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def build(self, template: str, **params) -> str:
        path = template.format(**params)
        return f"{self.base_url}/{path.lstrip('/')}"
```

---

## 5. Implementation Priority

### High Priority (Significant Complexity Reduction)

1. **Unified Gateway Handler** - Reduces gateway.py complexity by ~40%
2. **Operation Registry for Server Definitions** - Reduces average server definition complexity by ~60%
3. **Consistent Use of `server_utils` Abstractions** - Reduces duplication significantly

### Medium Priority (Maintainability Improvements)

4. **Language Detector Registry** - Reduces `detect_server_language` from E to A/B
5. **Base Server Class** - Standardizes all server definitions
6. **Pipeline Architecture for Gateway** - Improves testability

### Low Priority (Polish)

7. **URL Builder Strategy** - Minor duplication reduction
8. **Error Context Builder** - Code organization improvement

---

## 6. Metrics Targets

| Metric | Current | Target |
|--------|---------|--------|
| Average server `main()` complexity | D (25) | B (8) |
| Gateway handler complexity | E-F (31-42) | C (15) |
| Language detection complexity | E (31) | B (8) |
| Server definitions using `server_utils` | ~20% | 100% |
| Average lines per server definition | 250 | 100 |

---

## 7. Migration Strategy

### Phase 1: Foundation (Low Risk)

1. Ensure all `server_utils` abstractions are well-tested
2. Create `Operation` and `OperationRegistry` classes
3. Create `ExternalApiServer` base class

### Phase 2: Pilot Migration

1. Migrate 3-5 simple server definitions to new pattern
2. Validate that behavior is unchanged
3. Measure complexity reduction

### Phase 3: Systematic Migration

1. Generate migration scripts to convert server definitions
2. Migrate servers in batches of 10-15
3. Run full test suite after each batch

### Phase 4: Gateway Refactoring

1. Extract unified handler function
2. Implement pipeline architecture
3. Comprehensive gateway testing

---

## 8. Testing Considerations

### Current Test Coverage Concerns

- Server definitions have limited unit tests
- Gateway handlers tested primarily through integration tests
- Language detection has good unit test coverage

### Recommended Testing Approach

1. **Operation Registry**: Unit test each operation configuration
2. **Base Server Class**: Comprehensive unit tests for the executor
3. **Gateway Pipeline**: Unit test each pipeline stage independently
4. **Property-Based Testing**: Use Hypothesis for input validation

---

## Appendix: Complexity Reference

### Radon Complexity Grades

| Grade | Complexity | Risk |
|-------|-----------|------|
| A | 1-5 | Low - simple block |
| B | 6-10 | Low - well structured |
| C | 11-20 | Moderate - slightly complex |
| D | 21-30 | More than moderate - more complex |
| E | 31-40 | High - complex, alarming |
| F | 41+ | Very high - error-prone, untestable |

### Files Requiring Immediate Attention

| File | Function | Complexity | Grade |
|------|----------|------------|-------|
| gateway.py | `_handle_gateway_test_request` | 42 | F |
| box.py | `main` | 58 | F |
| coda.py | `main` | 51 | F |
| squarespace.py | `main` | 50 | F |
| onedrive.py | `main` | 44 | F |
| meta_ads.py | `main` | 44 | F |
| wix.py | `main` | 44 | F |
| language_detection.py | `detect_server_language` | 31 | E |
