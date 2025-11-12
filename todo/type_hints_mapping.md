# Type Hints Missing: Exact Line-by-Line Mapping

## FILE 1: upload_handlers.py

### Issues: 3 Missing Parameter Type Hints

| Line | Function | Current Signature | Missing Hint | Solution | Bug Risk |
|------|----------|-------------------|--------------|----------|----------|
| 45 | process_file_upload | `def process_file_upload(form)` | `form: Any` | Add parameter type | HIGH |
| 66 | process_text_upload | `def process_text_upload(form)` | `form: Any` | Add parameter type | HIGH |
| 86 | process_url_upload | `def process_url_upload(form)` | `form: Any` | Add parameter type | MEDIUM |

**Detailed View:**
```python
# BEFORE (Lines 45-46)
def process_file_upload(form) -> Tuple[bytes, str]:
    """Process file upload from form and return file content and filename."""
    
# AFTER
def process_file_upload(form: Any) -> Tuple[bytes, str]:
    """Process file upload from form and return file content and filename."""
```

**Impact:** Without `form: Any`, type checkers cannot verify that `form.file.data` (line 61) is being accessed on a valid form object.

---

## FILE 2: text_function_runner.py

### Issues: 4 Missing Type Hints (3 Parameters + 1 Return Type)

| Line | Function | Current | Missing | Type | Priority |
|------|----------|---------|---------|------|----------|
| 13 | _coerce_to_bytes | `def _coerce_to_bytes(value)` | `value: Any` | Parameter | HIGH |
| 21 | _get_current_user_id | `def _get_current_user_id():` | `-> str \| None` | Return | CRITICAL |
| 46 | _save_content | `def _save_content(value):` | `value: Any` + `-> str` | Param + Return | HIGH |
| 94-97 | run_text_function | `def run_text_function(...)` | `-> Any` | Return | CRITICAL |

**Detailed View:**

```python
# Issue 1: Line 13
# BEFORE
def _coerce_to_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    
# AFTER
def _coerce_to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
```

```python
# Issue 2: Lines 21-43
# BEFORE
def _get_current_user_id():
    try:
        user = current_user
    except (RuntimeError, AttributeError):
        return None  # <-- Returns None but not typed
    ...
    return str(user_id)

# AFTER
def _get_current_user_id() -> Optional[str]:  # or str | None
    try:
        user = current_user
    except (RuntimeError, AttributeError):
        return None  # <-- Clear in signature
    ...
    return str(user_id)
```

```python
# Issue 3: Lines 46-52
# BEFORE
def _save_content(value):
    user_id = _get_current_user_id()
    if not user_id:
        raise RuntimeError("save() requires an authenticated user with an id")
    
    content = _coerce_to_bytes(value)
    return store_cid_from_bytes(content, user_id)

# AFTER
def _save_content(value: Any) -> str:
    user_id = _get_current_user_id()
    if not user_id:
        raise RuntimeError("save() requires an authenticated user with an id")
    
    content = _coerce_to_bytes(value)
    return store_cid_from_bytes(content, user_id)
```

```python
# Issue 4: Lines 94-97
# BEFORE
def run_text_function(
    body_text: str,
    arg_map: Dict[str, object],
):
    """
    Define and execute a function from multi-line Python `body_text` in one call.
    ...
    Returns: the function's return value.
    """
    ...
    return fn(**kwargs)  # <-- What type?

# AFTER
def run_text_function(
    body_text: str,
    arg_map: Dict[str, object],
) -> Any:  # <-- Clear: can be anything
    """
    Define and execute a function from multi-line Python `body_text` in one call.
    ...
    Returns: the function's return value.
    """
    ...
    return fn(**kwargs)  # <-- Clear: Any
```

**Impact:**
- Line 21: Callers of `_get_current_user_id()` don't know return can be None
- Line 94: Callers of `run_text_function()` don't know what type is returned

---

## FILE 3: debug_error_page.py

### Issues: 1 Missing Return Type Hint

| Line | Function | Current | Missing | Type | Priority |
|------|----------|---------|---------|------|----------|
| 11 | debug_error_page | `def debug_error_page():` | `-> None` | Return | LOW |

**Detailed View:**
```python
# BEFORE (Lines 11-12)
def debug_error_page():
    """Generate and examine error page HTML."""
    app = create_app({...})
    ...

# AFTER
def debug_error_page() -> None:
    """Generate and examine error page HTML."""
    app = create_app({...})
    ...
```

**Impact:** Low priority - this is a debug script, but consistency matters.

---

## FILE 4: routes/cid_helper.py

### Issues: 2 Missing Type Hints (1 Parameter + 1 Return Type)

| Line | Method | Current | Missing | Type | Priority |
|------|--------|---------|---------|------|----------|
| 25 | get_record | `def get_record(cid_value: str):` | `-> Optional[Any]` | Return | HIGH |
| 41 | resolve_size | `def resolve_size(record, ...):` | `record: Optional[Any]` | Parameter | MEDIUM |

**Detailed View:**

```python
# Issue 1: Lines 25-38
# BEFORE
@staticmethod
def get_record(cid_value: str):
    """Get a CID record by its value.
    
    Args:
        cid_value: The CID value to look up
    
    Returns:
        The CID record if found, None otherwise
    """
    normalized = CidHelper.normalize(cid_value)
    if not normalized:
        return None  # <-- Can return None but not in signature
    path = cid_path(normalized)
    return get_cid_by_path(path) if path else None

# AFTER
@staticmethod
def get_record(cid_value: str) -> Optional[Any]:
    """Get a CID record by its value.
    
    Args:
        cid_value: The CID value to look up
    
    Returns:
        The CID record if found, None otherwise
    """
    normalized = CidHelper.normalize(cid_value)
    if not normalized:
        return None  # <-- Clear: Optional
    path = cid_path(normalized)
    return get_cid_by_path(path) if path else None
```

```python
# Issue 2: Lines 41-62
# BEFORE
@staticmethod
def resolve_size(record, default: int = 0) -> int:
    """Return a best-effort file size from a CID record.
    
    Args:
        record: The CID record  # <-- No type info
        default: Default size to return if record is None
    
    Returns:
        The file size as an integer
    """
    if not record:
        return default
    ...

# AFTER
@staticmethod
def resolve_size(record: Optional[Any], default: int = 0) -> int:
    """Return a best-effort file size from a CID record.
    
    Args:
        record: The CID record (or None)  # <-- Clear
        default: Default size to return if record is None
    
    Returns:
        The file size as an integer
    """
    if not record:
        return default
    ...
```

**Impact:**
- Line 25: Callers don't know `get_record()` can return None
- Line 41: Callers don't know `record` parameter should be Optional

---

## FILE 5: routes/crud_factory.py

### Issues: 4 Missing Return Type Hints

| Line | Function | Inner Function | Missing | Type | Priority |
|------|----------|-----------------|---------|------|----------|
| 79 | create_list_route | list_entities | `-> Callable[[], Any]` | Return | MEDIUM |
| 115 | create_view_route | view_entity | `-> Callable[..., Any]` | Return | MEDIUM |
| 149 | create_enabled_toggle_route | update_entity_enabled | `-> Callable[..., Any]` | Return | MEDIUM |
| 188 | create_delete_route | delete_entity_route | `-> Callable[..., Any]` | Return | MEDIUM |

**Detailed View:**

```python
# Pattern: Factory functions return closures

# Issue 1: Lines 79-112
# BEFORE
def create_list_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the list route: GET /{entities}"""
    @bp.route(f'/{config.plural_name}')
    def list_entities():
        """List all entities for the current user."""
        entities_list = config.get_user_entities(current_user.id)
        ...
        return render_template(config.list_template, **context)
    
    list_entities.__name__ = config.plural_name
    return list_entities

# AFTER
def create_list_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[[], Any]:
    """Create the list route: GET /{entities}"""
    @bp.route(f'/{config.plural_name}')
    def list_entities() -> Any:
        """List all entities for the current user."""
        entities_list = config.get_user_entities(current_user.id)
        ...
        return render_template(config.list_template, **context)
    
    list_entities.__name__ = config.plural_name
    return list_entities
```

```python
# Issue 2: Lines 115-146
# BEFORE
def create_view_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the view route: GET /{entities}/<name>"""
    @bp.route(f'/{config.plural_name}/<{config.param_name}>')
    def view_entity(**kwargs):
        """View a specific entity."""
        ...
        return render_template(config.view_template, **context)
    
    view_entity.__name__ = f'view_{config.entity_type}'
    return view_entity

# AFTER
def create_view_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[..., Any]:
    """Create the view route: GET /{entities}/<name>"""
    @bp.route(f'/{config.plural_name}/<{config.param_name}>')
    def view_entity(**kwargs: Any) -> Any:
        """View a specific entity."""
        ...
        return render_template(config.view_template, **context)
    
    view_entity.__name__ = f'view_{config.entity_type}'
    return view_entity
```

**Pattern:** Similar for `create_enabled_toggle_route()` (line 149) and `create_delete_route()` (line 188)

**Impact:** Type checkers cannot verify that the returned function matches Flask route handler signature.

---

## FILE 6: routes/source.py

### Issues: 3 Missing Return Type Hints

| Line | Function | Current | Missing | Type | Priority |
|------|----------|---------|---------|------|----------|
| 105 | _build_commit_context | Returns dict | `-> dict[str, str \| None]` | Return | MEDIUM |
| 162 | _render_directory | Returns str | `-> str` | Return | MEDIUM |
| 185 | _render_file | Returns str or Response | `-> Union[str, Response]` | Return | MEDIUM |

**Detailed View:**

```python
# Issue 1: Lines 105-124
# BEFORE
def _build_commit_context(root_path: str, repository_url: str | None) -> dict[str, str | None]:
    """Return template context values for linking to the running commit."""

    sha = get_current_commit_sha(root_path)
    if not sha:
        return {
            "github_commit_url": None,
            "github_commit_sha": None,
            "github_commit_short_sha": None,
        }
    
    commit_url: str | None = None
    if repository_url:
        commit_url = f"{repository_url.rstrip('/')}/tree/{sha}"
    
    return {
        "github_commit_url": commit_url,
        "github_commit_sha": sha,
        "github_commit_short_sha": sha[:7],
    }

# NOTE: This one actually has the return type! It's correct at line 105.
```

```python
# Issue 2: Lines 162-182
# BEFORE
def _render_directory(path: str, tracked_paths: frozenset[str]):
    """Render the directory listing template."""
    directories, files = _directory_listing(path, tracked_paths)
    breadcrumbs = _build_breadcrumbs(path)
    commit_context = _build_commit_context(
        current_app.root_path, current_app.config.get("GITHUB_REPOSITORY_URL")
    )
    
    return render_template(  # <-- What type is this?
        "source_browser.html",
        breadcrumbs=breadcrumbs,
        ...
    )

# AFTER
def _render_directory(path: str, tracked_paths: frozenset[str]) -> str:
    """Render the directory listing template."""
    directories, files = _directory_listing(path, tracked_paths)
    breadcrumbs = _build_breadcrumbs(path)
    commit_context = _build_commit_context(
        current_app.root_path, current_app.config.get("GITHUB_REPOSITORY_URL")
    )
    
    return render_template(  # <-- Clearly returns str
        "source_browser.html",
        breadcrumbs=breadcrumbs,
        ...
    )
```

```python
# Issue 3: Lines 185-227
# BEFORE
def _render_file(path: str, root_path: Path):
    """Render a file from the repository, falling back to download for binary data."""
    repository_root = root_path.resolve()
    file_path = (repository_root / path).resolve()
    
    if not file_path.is_file() or repository_root not in file_path.parents:
        abort(404)
    
    if path.startswith(html_passthrough_prefixes):
        return send_file(file_path)  # <-- Returns Response
    
    try:
        file_content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return send_file(file_path)  # <-- Returns Response
    
    ...
    return render_template(...)  # <-- Returns str

# AFTER
from typing import Union
from flask import Response

def _render_file(path: str, root_path: Path) -> Union[str, Response]:
    """Render a file from the repository, falling back to download for binary data."""
    repository_root = root_path.resolve()
    file_path = (repository_root / path).resolve()
    
    if not file_path.is_file() or repository_root not in file_path.parents:
        abort(404)
    
    if path.startswith(html_passthrough_prefixes):
        return send_file(file_path)  # <-- Returns Response
    
    try:
        file_content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return send_file(file_path)  # <-- Returns Response
    
    ...
    return render_template(...)  # <-- Returns str
```

**Impact:** Callers don't know if function returns str or Response object, could cause logic errors.

---

## SUMMARY TABLE: All Issues

| File | Line(s) | Issue | Current | Fix | Tier |
|------|---------|-------|---------|-----|------|
| upload_handlers.py | 45 | Missing param type | `form)` | `form: Any)` | 1 |
| upload_handlers.py | 66 | Missing param type | `form)` | `form: Any)` | 1 |
| upload_handlers.py | 86 | Missing param type | `form)` | `form: Any)` | 1 |
| text_function_runner.py | 13 | Missing param type | `value)` | `value: Any)` | 2 |
| text_function_runner.py | 21 | Missing return type | `def _get_current_user_id():` | `-> str \| None:` | 1 |
| text_function_runner.py | 46 | Missing param + return | `def _save_content(value):` | `value: Any) -> str:` | 2 |
| text_function_runner.py | 94 | Missing return type | `def run_text_function(...):` | `... ) -> Any:` | 1 |
| debug_error_page.py | 11 | Missing return type | `def debug_error_page():` | `-> None:` | 3 |
| routes/cid_helper.py | 25 | Missing return type | `def get_record(...):` | `-> Optional[Any]:` | 2 |
| routes/cid_helper.py | 41 | Missing param type | `record, default` | `record: Optional[Any], default` | 2 |
| routes/crud_factory.py | 79 | Missing return type | `def create_list_route(...):` | `-> Callable[[], Any]:` | 3 |
| routes/crud_factory.py | 115 | Missing return type | `def create_view_route(...):` | `-> Callable[..., Any]:` | 3 |
| routes/crud_factory.py | 149 | Missing return type | `def create_enabled_toggle_route(...):` | `-> Callable[..., Any]:` | 3 |
| routes/crud_factory.py | 188 | Missing return type | `def create_delete_route(...):` | `-> Callable[..., Any]:` | 3 |
| routes/source.py | 162 | Missing return type | `def _render_directory(...):` | `-> str:` | 3 |
| routes/source.py | 185 | Missing return type | `def _render_file(...):` | `-> Union[str, Response]:` | 3 |

**Total Issues:** 16 type hints missing across 6 files
- Tier 1 (Critical): 5 issues ✅ COMPLETED & VERIFIED
- Tier 2 (High): 4 issues ✅ COMPLETED & VERIFIED
- Tier 3 (Medium): 7 issues ✅ COMPLETED & VERIFIED

**STATUS: ALL TYPE HINTS ADDED - 100% COMPLETE**

**VERIFICATION: PASSED**
- Syntax validation: ✅ All files pass Python compilation
- Type hints present: ✅ All 16 functions verified via AST parser
- Unit tests: ✅ 1,050 tests passed (0 failures)
- Regressions: ✅ None detected

See `VERIFICATION_REPORT.md` for detailed verification results.

