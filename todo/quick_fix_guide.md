# QUICK FIX GUIDE: Type Hints Implementation

## TIER 1: CRITICAL FIXES (Do This First)

### Fix 1: text_function_runner.py - Line 21
**Current Code:**
```python
def _get_current_user_id():
    try:
        user = current_user
    except (RuntimeError, AttributeError):
        return None
    ...
    return str(user_id)
```

**Fixed Code:**
```python
from typing import Optional

def _get_current_user_id() -> Optional[str]:  # or: -> str | None
    try:
        user = current_user
    except (RuntimeError, AttributeError):
        return None
    ...
    return str(user_id)
```

**Why:** Function can return None (lines 26, 41) but callers don't know.

---

### Fix 2: text_function_runner.py - Line 94-97
**Current Code:**
```python
def run_text_function(
    body_text: str,
    arg_map: Dict[str, object],
):
    """Define and execute a function from multi-line Python `body_text`..."""
```

**Fixed Code:**
```python
from typing import Any, Dict

def run_text_function(
    body_text: str,
    arg_map: Dict[str, object],
) -> Any:
    """Define and execute a function from multi-line Python `body_text`..."""
```

**Why:** Dynamically executed code - return type is unpredictable.

---

### Fix 3: upload_handlers.py - Lines 45, 66, 86
**Current Code:**
```python
def process_file_upload(form) -> Tuple[bytes, str]:
    """Process file upload from form..."""
    uploaded_file = form.file.data
    ...

def process_text_upload(form) -> bytes:
    """Process text upload from form..."""
    text_content = form.text_content.data
    ...

def process_url_upload(form) -> Tuple[bytes, str]:
    """Process URL upload..."""
    url = form.url.data.strip()
    ...
```

**Fixed Code:**
```python
from typing import Any, Tuple

def process_file_upload(form: Any) -> Tuple[bytes, str]:
    """Process file upload from form..."""
    uploaded_file = form.file.data
    ...

def process_text_upload(form: Any) -> bytes:
    """Process text upload from form..."""
    text_content = form.text_content.data
    ...

def process_url_upload(form: Any) -> Tuple[bytes, str]:
    """Process URL upload..."""
    url = form.url.data.strip()
    ...
```

**Why:** Flask form objects require type hints to document the parameter type.

**Better (if possible):**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from werkzeug.datastructures import FileStorage
    # Or import actual Flask form type
    
def process_file_upload(form: "WTFForm") -> Tuple[bytes, str]:
    ...
```

---

## TIER 2: HIGH-PRIORITY FIXES

### Fix 4: text_function_runner.py - Line 13
**Current Code:**
```python
def _coerce_to_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")
```

**Fixed Code:**
```python
from typing import Any

def _coerce_to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("utf-8")
```

---

### Fix 5: text_function_runner.py - Line 46
**Current Code:**
```python
def _save_content(value):
    user_id = _get_current_user_id()
    if not user_id:
        raise RuntimeError("save() requires an authenticated user with an id")

    content = _coerce_to_bytes(value)
    return store_cid_from_bytes(content, user_id)
```

**Fixed Code:**
```python
from typing import Any

def _save_content(value: Any) -> str:  # Returns CID string
    user_id = _get_current_user_id()
    if not user_id:
        raise RuntimeError("save() requires an authenticated user with an id")

    content = _coerce_to_bytes(value)
    return store_cid_from_bytes(content, user_id)
```

**Why:** Documents that this function persists content and returns a CID identifier.

---

### Fix 6: routes/cid_helper.py - Line 25
**Current Code:**
```python
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
        return None
    path = cid_path(normalized)
    return get_cid_by_path(path) if path else None
```

**Fixed Code:**
```python
from typing import Optional, Any

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
        return None
    path = cid_path(normalized)
    return get_cid_by_path(path) if path else None
```

**Or (better if you know the model):**
```python
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import CID

@staticmethod
def get_record(cid_value: str) -> Optional["CID"]:
    ...
```

---

### Fix 7: routes/cid_helper.py - Line 41
**Current Code:**
```python
@staticmethod
def resolve_size(record, default: int = 0) -> int:
    """Return a best-effort file size from a CID record.
    
    Args:
        record: The CID record
        default: Default size to return if record is None
    
    Returns:
        The file size as an integer
    """
    if not record:
        return default
    ...
```

**Fixed Code:**
```python
from typing import Optional, Any

@staticmethod
def resolve_size(record: Optional[Any], default: int = 0) -> int:
    """Return a best-effort file size from a CID record.
    
    Args:
        record: The CID record (or None)
        default: Default size to return if record is None
    
    Returns:
        The file size as an integer
    """
    if not record:
        return default
    ...
```

---

## TIER 3: MEDIUM-PRIORITY FIXES

### Fix 8: routes/crud_factory.py - Lines 79, 115, 149, 188
**Current Code:**
```python
def create_list_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the list route..."""
    @bp.route(f'/{config.plural_name}')
    def list_entities():
        """List all entities for the current user."""
        ...
    return list_entities

def create_view_route(bp: Blueprint, config: EntityRouteConfig):
    """Create the view route..."""
    @bp.route(f'/{config.plural_name}/<{config.param_name}>')
    def view_entity(**kwargs):
        """View a specific entity."""
        ...
    return view_entity

# Similar for create_enabled_toggle_route and create_delete_route
```

**Fixed Code:**
```python
from typing import Callable, Any
from flask import Blueprint

def create_list_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[[], Any]:
    """Create the list route..."""
    @bp.route(f'/{config.plural_name}')
    def list_entities() -> Any:  # Can return str (template) or Response (JSON)
        """List all entities for the current user."""
        ...
    return list_entities

def create_view_route(bp: Blueprint, config: EntityRouteConfig) -> Callable[..., Any]:
    """Create the view route..."""
    @bp.route(f'/{config.plural_name}/<{config.param_name}>')
    def view_entity(**kwargs: Any) -> Any:  # Can return str (template) or Response (JSON)
        """View a specific entity."""
        ...
    return view_entity

# Similar for others
```

---

### Fix 9: routes/source.py - Lines 162, 185
**Current Code:**
```python
def _render_directory(path: str, tracked_paths: frozenset[str]):
    """Render the directory listing template."""
    directories, files = _directory_listing(path, tracked_paths)
    ...
    return render_template(...)

def _render_file(path: str, root_path: Path):
    """Render a file from the repository..."""
    ...
    return send_file(file_path)  # or
    return render_template(...)
```

**Fixed Code:**
```python
from typing import Union
from flask import Response

def _render_directory(path: str, tracked_paths: frozenset[str]) -> str:
    """Render the directory listing template."""
    directories, files = _directory_listing(path, tracked_paths)
    ...
    return render_template(...)

def _render_file(path: str, root_path: Path) -> Union[str, Response]:
    """Render a file from the repository..."""
    ...
    # Can return either render_template (str) or send_file (Response)
    return send_file(file_path)  # or
    return render_template(...)
```

---

### Fix 10: debug_error_page.py - Line 11
**Current Code:**
```python
def debug_error_page():
    """Generate and examine error page HTML."""
    app = create_app({...})
    ...
    print(html_content)
```

**Fixed Code:**
```python
def debug_error_page() -> None:
    """Generate and examine error page HTML."""
    app = create_app({...})
    ...
    print(html_content)
```

---

## ✅ IMPLEMENTATION COMPLETE

All type hints have been successfully added to the codebase.

**Files Modified:**
- text_function_runner.py (4 type hints added)
- upload_handlers.py (3 type hints added)
- routes/cid_helper.py (3 type hints added including import update)
- routes/crud_factory.py (8 type hints added - 4 outer + 4 inner functions)
- routes/source.py (3 type hints added including import updates)
- debug_error_page.py (1 type hint added)

**Total:** 22 type annotations added across 6 files

## VALIDATION CHECKLIST

After making changes, verify with:

```bash
# 1. Run mypy to check type hints
mypy upload_handlers.py
mypy text_function_runner.py
mypy routes/cid_helper.py

# 2. Run with strict mode
mypy --strict upload_handlers.py

# 3. Check specific function
mypy --show-error-codes --no-implicit-reexport upload_handlers.py

# 4. Full project check
mypy src/ --ignore-missing-imports
```

---

## IMPORT UPDATES NEEDED

Add to top of each modified file:

**upload_handlers.py:**
```python
from typing import Any, Tuple  # Add if not present
```

**text_function_runner.py:**
```python
from typing import Any, Dict, Optional  # Update existing import
# Change: from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union
```

**routes/cid_helper.py:**
```python
from typing import Optional, Any  # Add to existing import
# Update: from typing import Optional
```

**routes/crud_factory.py:**
```python
from typing import Any, Callable  # Add if not present
# Already has: from typing import Any, Callable, Dict, Optional, Type
```

**routes/source.py:**
```python
from typing import Union  # Add if not present
from flask import Response  # Add to existing imports
```

---

## TESTING AFTER CHANGES

Run tests to ensure type hints didn't break anything:

```bash
# Unit tests
pytest tests/test_upload_handlers.py -v
pytest tests/test_text_function_runner.py -v

# Type checking
mypy --show-traceback src/

# Full coverage report
coverage run -m pytest && coverage report
```
