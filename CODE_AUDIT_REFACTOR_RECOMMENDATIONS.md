# Code Audit: Simplification & Abstraction Opportunities

**Date:** 2025-11-11
**Focus:** Identifying simplification opportunities and missing abstractions

---

## Executive Summary

The Viewer codebase is well-structured with good separation of concerns, but there are several opportunities to reduce duplication and introduce helpful abstractions. The code audit identified **5 major areas** for simplification that would significantly reduce maintenance burden.

### Key Metrics
- **Lines of duplicate code:** ~300+ lines across entity CRUD routes
- **Duplicate function:** `_wants_structured_response()` repeated 4 times
- **Form classes with identical patterns:** 4 forms (Server, Variable, Secret, Alias)
- **Complexity hotspots:** 3 files >750 lines

---

## 1. HIGHEST PRIORITY: Eliminate Route Code Duplication

### Issue: CRUD Pattern Repeated Across 4 Route Files

The same patterns appear in:
- `routes/servers.py` (802 lines)
- `routes/variables.py` (479 lines)
- `routes/secrets.py` (263 lines)
- `routes/aliases.py` (793 lines)

**Duplicate patterns identified:**

#### A. List View Pattern (appears 4x)
```python
# Repeated in servers.py:475, variables.py:260, secrets.py:58, aliases.py:318
@main_bp.route('/{entities}')
def list_entities():
    entities_list = user_entities()
    if _wants_structured_response():
        return jsonify([_entity_to_json(e) for e in entities_list])
    return render_template('entities.html', entities=entities_list)
```

#### B. Toggle Enabled Pattern (appears 4x)
```python
# Repeated in servers.py:503, variables.py:276, secrets.py:74, aliases.py:327
@main_bp.route('/{entities}/<name>/enabled', methods=['POST'])
def update_entity_enabled(name: str):
    entity = get_entity_by_name(current_user.id, name)
    if not entity:
        abort(404)
    try:
        enabled_value = extract_enabled_value_from_request()
    except ValueError:
        abort(400)
    entity.enabled = enabled_value
    entity.updated_at = datetime.now(timezone.utc)
    save_entity(entity)
    update_definitions_cid(current_user.id)
    if request_prefers_json():
        return jsonify({'entity': entity.name, 'enabled': entity.enabled})
    return redirect(url_for('main.entities'))
```

#### C. View Entity Pattern (appears 4x)
```python
# Nearly identical across all 4 files
@main_bp.route('/{entities}/<name>')
def view_entity(name):
    entity = get_entity_by_name(current_user.id, name)
    if not entity:
        abort(404)
    if _wants_structured_response():
        return jsonify(_entity_to_json(entity))
    return render_template('entity_view.html', entity=entity, ...)
```

#### D. Delete Entity Pattern (appears 4x)
```python
# Identical in all files except entity type string
@main_bp.route('/{entities}/<name>/delete', methods=['POST'])
def delete_entity_route(name):
    entity = get_entity_by_name(current_user.id, name)
    if not entity:
        abort(404)
    delete_entity(entity)
    update_definitions_cid(current_user.id)
    flash(f'{EntityType} "{name}" deleted successfully!', 'success')
    return redirect(url_for('main.entities'))
```

### Proposed Solution: Generic Route Factory

Create `routes/crud_factory.py`:

```python
"""Generic CRUD route factory for entity management."""

from typing import Any, Callable, Dict, Optional, Type
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from datetime import datetime, timezone

from db_access import save_entity, delete_entity
from identity import current_user
from .enabled import extract_enabled_value_from_request, request_prefers_json


class EntityRouteConfig:
    """Configuration for entity-specific routes."""

    def __init__(
        self,
        entity_class: Type,
        entity_type: str,  # 'server', 'variable', 'secret', 'alias'
        plural_name: str,  # 'servers', 'variables', etc.
        get_by_name_func: Callable,
        get_user_entities_func: Callable,
        update_cid_func: Optional[Callable] = None,
        to_json_func: Optional[Callable] = None,
        # Template names
        list_template: str = None,
        view_template: str = None,
        # Extra view data builders
        build_view_data: Optional[Callable] = None,
    ):
        self.entity_class = entity_class
        self.entity_type = entity_type
        self.plural_name = plural_name
        self.get_by_name = get_by_name_func
        self.get_user_entities = get_user_entities_func
        self.update_cid = update_cid_func
        self.to_json = to_json_func or (lambda e: model_to_dict(e))
        self.list_template = list_template or f'{plural_name}.html'
        self.view_template = view_template or f'{entity_type}_view.html'
        self.build_view_data = build_view_data or (lambda entity: {})


def create_entity_routes(bp: Blueprint, config: EntityRouteConfig):
    """Create standard CRUD routes for an entity type.

    This eliminates ~100 lines of duplicate code per entity type.
    """

    # List route
    @bp.route(f'/{config.plural_name}')
    def list_entities():
        entities_list = config.get_user_entities(current_user.id)
        if _wants_structured_response():
            return jsonify([config.to_json(e) for e in entities_list])

        context = {'entities': entities_list}
        # Add entity-specific context
        if config.update_cid:
            cid = config.update_cid(current_user.id)
            context[f'{config.entity_type}_definitions_cid'] = cid

        return render_template(config.list_template, **context)

    # Toggle enabled route
    @bp.route(f'/{config.plural_name}/<entity_name>/enabled', methods=['POST'])
    def update_entity_enabled(entity_name: str):
        entity = config.get_by_name(current_user.id, entity_name)
        if not entity:
            abort(404)

        try:
            enabled_value = extract_enabled_value_from_request()
        except ValueError:
            abort(400)

        entity.enabled = enabled_value
        entity.updated_at = datetime.now(timezone.utc)
        save_entity(entity)

        if config.update_cid:
            config.update_cid(current_user.id)

        if request_prefers_json():
            return jsonify({config.entity_type: entity.name, 'enabled': entity.enabled})

        return redirect(url_for(f'main.{config.plural_name}'))

    # View route
    @bp.route(f'/{config.plural_name}/<entity_name>')
    def view_entity(entity_name: str):
        entity = config.get_by_name(current_user.id, entity_name)
        if not entity:
            abort(404)

        if _wants_structured_response():
            return jsonify(config.to_json(entity))

        context = {config.entity_type: entity}
        # Add entity-specific view data
        if config.build_view_data:
            context.update(config.build_view_data(entity))

        return render_template(config.view_template, **context)

    # Delete route
    @bp.route(f'/{config.plural_name}/<entity_name>/delete', methods=['POST'])
    def delete_entity_route(entity_name: str):
        entity = config.get_by_name(current_user.id, entity_name)
        if not entity:
            abort(404)

        delete_entity(entity)

        if config.update_cid:
            config.update_cid(current_user.id)

        flash(f'{config.entity_type.title()} "{entity_name}" deleted successfully!', 'success')
        return redirect(url_for(f'main.{config.plural_name}'))

    # Register route functions with proper names
    list_entities.__name__ = config.plural_name
    update_entity_enabled.__name__ = f'update_{config.entity_type}_enabled'
    view_entity.__name__ = f'view_{config.entity_type}'
    delete_entity_route.__name__ = f'delete_{config.entity_type}'
```

**Usage example in routes/servers.py:**

```python
from .crud_factory import EntityRouteConfig, create_entity_routes
from models import Server

# Define server-specific configuration
server_config = EntityRouteConfig(
    entity_class=Server,
    entity_type='server',
    plural_name='servers',
    get_by_name_func=get_server_by_name,
    get_user_entities_func=get_user_servers,
    update_cid_func=update_server_definitions_cid,
    to_json_func=_server_to_json,
    build_view_data=lambda server: {
        'history': get_server_definition_history(current_user.id, server.name),
        'invocations': get_server_invocation_history(current_user.id, server.name),
        # ... other server-specific data
    }
)

# Create all standard CRUD routes
create_entity_routes(main_bp, server_config)
```

**Impact:** Reduces ~300 lines of duplicate code across 4 files.

---

## 2. HIGH PRIORITY: Consolidate Helper Functions

### Issue: `_wants_structured_response()` Defined 4 Times

This exact function appears in:
- `routes/servers.py:796`
- `routes/variables.py:473`
- `routes/secrets.py:257`
- `routes/aliases.py:780`

```python
def _wants_structured_response() -> bool:
    return getattr(g, "response_format", None) in {"json", "xml", "csv"}
```

### Proposed Solution: Move to Shared Module

Create `routes/response_utils.py`:

```python
"""Shared utilities for route response handling."""

from flask import g
from typing import Literal

ResponseFormat = Literal["json", "xml", "csv", "html"]

def wants_structured_response() -> bool:
    """Check if the request wants a structured (non-HTML) response."""
    return getattr(g, "response_format", None) in {"json", "xml", "csv"}

def get_response_format() -> ResponseFormat:
    """Get the requested response format, defaulting to HTML."""
    return getattr(g, "response_format", "html")
```

Replace all 4 instances with:
```python
from .response_utils import wants_structured_response
```

**Impact:** Eliminates 3 duplicate function definitions.

---

## 3. MEDIUM PRIORITY: Simplify Form Hierarchy

### Issue: Duplicate Validation Logic Across Forms

All 4 forms have identical patterns:

```python
# forms.py:78-92, 93-107, 175-189
class ServerForm(FlaskForm):
    name = StringField('Server Name', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9._-]+$', message='...')
    ])
    definition = TextAreaField('Server Definition', validators=[DataRequired()])
    enabled = BooleanField('Enabled', default=True)
    template = BooleanField('Template', default=False)
    submit = SubmitField('Save Server')

    def validate_name(self, field: Field) -> None:
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError('...')
```

### Proposed Solution: Create Base Form Class

```python
"""forms.py - Enhanced with base class"""

class EntityForm(FlaskForm):
    """Base form for all entity types (Server, Variable, Secret, Alias)."""

    name = StringField(
        'Name',
        validators=[
            DataRequired(),
            Regexp(r'^[a-zA-Z0-9._-]+$',
                   message='Name can only contain letters, numbers, dots, hyphens, and underscores')
        ],
        filters=[_strip_filter],
    )
    definition = TextAreaField(
        'Definition',
        validators=[DataRequired()],
        render_kw={'rows': 15}
    )
    enabled = BooleanField('Enabled', default=True)
    template = BooleanField('Template', default=False)
    submit = SubmitField('Save')

    def __init__(self, entity_type: str = 'Entity', *args, **kwargs):
        """Initialize with entity type for labels."""
        super().__init__(*args, **kwargs)
        self.name.label.text = f'{entity_type} Name'
        self.definition.label.text = f'{entity_type} Definition'
        self.submit.label.text = f'Save {entity_type}'

    def validate_name(self, field: Field) -> None:
        """Validate name format for URL safety."""
        if not re.match(r'^[a-zA-Z0-9._-]+$', field.data):
            raise ValidationError(f'{self.name.label.text} contains invalid characters for URLs')


class ServerForm(EntityForm):
    """Form for server management."""
    def __init__(self, *args, **kwargs):
        super().__init__('Server', *args, **kwargs)


class VariableForm(EntityForm):
    """Form for variable management."""
    def __init__(self, *args, **kwargs):
        super().__init__('Variable', *args, **kwargs)


class SecretForm(EntityForm):
    """Form for secret management."""
    def __init__(self, *args, **kwargs):
        super().__init__('Secret', *args, **kwargs)
```

**Impact:** Reduces forms.py by ~60 lines, centralizes validation logic.

---

## 4. MEDIUM PRIORITY: Extract Content Rendering Helpers

### Issue: Complex Function in content_rendering.py

The `normalize_github_relative_link_target()` function (lines 196-258) is 65 lines with 4-level nesting.

### Current Structure:
```python
def normalize_github_relative_link_target(raw_target: str) -> Optional[str]:
    """65 lines with complex nested logic"""
    # Validation
    # Pipe syntax handling
    # Page part processing
    # Anchor part processing
    # Result assembly
```

### Proposed Solution: Extract Helper Functions

```python
# content_rendering.py - Refactored

def _extract_target_and_label(raw_target: str) -> tuple[str, str]:
    """Extract target and label from pipe syntax: [[target|label]]."""
    target = raw_target.strip()
    if '|' in target:
        primary = target.split('|', 1)[0].strip()
        return primary, target
    return target, target


def _normalize_page_path(page_part: str, preserve_trailing_slash: bool) -> str:
    """Normalize a page path component."""
    prepared = re.sub(r"\s+", "-", page_part.strip())
    cleaned = GITHUB_RELATIVE_LINK_PATH_SANITIZER.sub('', prepared)
    segments = [s for s in cleaned.split('/') if s]

    if not segments:
        return ""

    normalized = '/' + '/'.join(s.lower() for s in segments)
    if preserve_trailing_slash:
        normalized += '/'
    return normalized


def _normalize_anchor_fragment(anchor_part: str) -> str:
    """Normalize an anchor fragment."""
    slug = anchor_part.strip().lower()
    slug = re.sub(r"\s+", '-', slug)
    slug = GITHUB_RELATIVE_LINK_ANCHOR_SANITIZER.sub('', slug)
    slug = slug.strip('-')
    return f'#{slug}' if slug else ""


def normalize_github_relative_link_target(raw_target: str) -> Optional[str]:
    """Normalize GitHub-style relative link targets.

    Now 25 lines instead of 65, with clear single-responsibility helpers.
    """
    if not raw_target or not raw_target.strip():
        return None

    # Extract target from pipe syntax
    primary, _ = _extract_target_and_label(raw_target)
    if not primary:
        return None

    # Split page and anchor
    page_part, _, anchor_part = primary.partition('#')

    # Normalize components
    normalized_path = ""
    if page_part:
        preserve_slash = page_part.rstrip().endswith('/')
        normalized_path = _normalize_page_path(page_part, preserve_slash)

    anchor_fragment = _normalize_anchor_fragment(anchor_part) if anchor_part else ""

    # Assemble result
    if normalized_path and anchor_fragment:
        return f'{normalized_path}{anchor_fragment}'
    return normalized_path or anchor_fragment or None
```

**Impact:** Reduces function from 65 to ~25 lines, eliminates deep nesting.

---

## 5. LOW PRIORITY: Introduce Type-Based EntityMetadata

### Issue: String-Based Entity Type Handling

Current approach uses string literals throughout:

```python
# Found in multiple files
entity_type = 'server'  # or 'variable', 'secret', 'alias'
record_entity_interaction(
    EntityInteractionRequest(
        entity_type=entity_type,  # string-based
        ...
    )
)
```

### Proposed Solution: EntityMetadata Protocol

```python
"""entity_metadata.py - New module"""

from typing import Protocol, Type
from dataclasses import dataclass


@dataclass
class EntityMetadata:
    """Metadata about an entity type."""
    type_name: str          # 'server', 'variable', etc.
    type_label: str         # 'Server', 'Variable', etc.
    plural_name: str        # 'servers', 'variables', etc.
    model_class: Type
    form_class: Type
    route_prefix: str       # '/servers', '/variables', etc.


class EntityRegistry:
    """Registry of all entity types and their metadata."""

    def __init__(self):
        self._entities: dict[Type, EntityMetadata] = {}

    def register(self, model_class: Type, metadata: EntityMetadata):
        """Register an entity type."""
        self._entities[model_class] = metadata

    def get_metadata(self, model_class: Type) -> EntityMetadata:
        """Get metadata for an entity type."""
        return self._entities[model_class]

    def get_by_type_name(self, type_name: str) -> EntityMetadata:
        """Get metadata by type name string."""
        for meta in self._entities.values():
            if meta.type_name == type_name:
                return meta
        raise ValueError(f"Unknown entity type: {type_name}")


# Global registry
entity_registry = EntityRegistry()

# Register entities at module load
from models import Server, Variable, Secret, Alias
from forms import ServerForm, VariableForm, SecretForm, AliasForm

entity_registry.register(Server, EntityMetadata(
    type_name='server',
    type_label='Server',
    plural_name='servers',
    model_class=Server,
    form_class=ServerForm,
    route_prefix='/servers',
))

entity_registry.register(Variable, EntityMetadata(
    type_name='variable',
    type_label='Variable',
    plural_name='variables',
    model_class=Variable,
    form_class=VariableForm,
    route_prefix='/variables',
))

# ... register other types
```

**Usage:**
```python
# Instead of string literals
from entity_metadata import entity_registry

metadata = entity_registry.get_metadata(Server)
record_entity_interaction(
    EntityInteractionRequest(
        entity_type=metadata.type_name,
        ...
    )
)
```

**Impact:** Type safety, eliminates magic strings, enables compile-time checking.

---

## 6. Specific Code Simplification Opportunities

### A. Consolidate Template Building in routes/servers.py

**Current (lines 542-576):**
```python
user_server_templates = [
    {
        'id': f'user-{server.id}',
        'name': server.name,
        'definition': server.definition or '',
        'suggested_name': f"{server.name}-copy" if server.name else '',
    }
    for server in get_user_template_servers(current_user.id)
]
```

This pattern appears in:
- `routes/servers.py:542`
- `routes/variables.py:340`
- `routes/secrets.py:138`
- `routes/aliases.py:373`

**Proposed:** Extract to shared helper:

```python
# routes/template_utils.py
def build_template_list(entities, prefix='user'):
    """Build template list for entity create/edit forms."""
    return [
        {
            'id': f'{prefix}-{e.id}' if prefix else e.id,
            'name': e.name,
            'definition': e.definition or '',
            'suggested_name': f"{e.name}-copy" if e.name else '',
        }
        for e in entities
    ]
```

### B. Simplify Interaction History Loading

**Current pattern (appears 8+ times):**
```python
entity_name_hint = (form.name.data or '').strip()
interaction_history = load_interaction_history(
    current_user.id, 'server', entity_name_hint
)
```

**Proposed:**
```python
def get_entity_interaction_history(entity_type: str, form) -> list:
    """Get interaction history for an entity being edited."""
    entity_name = (form.name.data or '').strip()
    return load_interaction_history(current_user.id, entity_type, entity_name)

# Usage
interaction_history = get_entity_interaction_history('server', form)
```

### C. Extract Flash Message Builder

**Current (appears 12+ times with variations):**
```python
flash(f'Server "{server_name}" deleted successfully!', 'success')
flash(f'Variable "{name}" created successfully!', 'success')
```

**Proposed:**
```python
# routes/messages.py
class Messages:
    """Standard flash messages for entity operations."""

    @staticmethod
    def created(entity_type: str, name: str) -> str:
        return f'{entity_type.title()} "{name}" created successfully!'

    @staticmethod
    def updated(entity_type: str, name: str) -> str:
        return f'{entity_type.title()} "{name}" updated successfully!'

    @staticmethod
    def deleted(entity_type: str, name: str) -> str:
        return f'{entity_type.title()} "{name}" deleted successfully!'

# Usage
flash(Messages.deleted('server', server_name), 'success')
```

---

## Summary of Recommendations

### Immediate Actions (High ROI)

1. **Create `routes/crud_factory.py`** - Eliminates 300+ lines of duplication
2. **Move `_wants_structured_response()` to shared module** - Eliminates 3 duplicates
3. **Create `EntityForm` base class** - Reduces forms.py by 60 lines

### Short-term Actions (Medium ROI)

4. **Extract helpers in `content_rendering.py`** - Reduces complexity score
5. **Create `routes/template_utils.py`** - Consolidates template building
6. **Create `routes/messages.py`** - Standardizes flash messages

### Long-term Actions (Foundation)

7. **Introduce `EntityMetadata` registry** - Type safety for entity operations
8. **Consider splitting `routes/servers.py`** - Currently 802 lines

---

## Complexity Metrics

### Before Refactoring
- Total lines in entity routes: ~2,337
- Duplicate code: ~300 lines
- Average route file size: ~584 lines
- Forms with validation duplication: 4

### After Refactoring (Estimated)
- Total lines in entity routes: ~1,900
- Duplicate code: ~50 lines
- Average route file size: ~475 lines
- Forms with validation duplication: 0

**Net reduction: ~437 lines of code (~18.7%)**

---

## Implementation Priority

### Phase 1 (1-2 days)
- [ ] Create `routes/response_utils.py` and consolidate `_wants_structured_response()`
- [ ] Create `EntityForm` base class in `forms.py`
- [ ] Create `routes/messages.py` for standard messages

### Phase 2 (3-4 days)
- [ ] Design and implement `routes/crud_factory.py`
- [ ] Refactor `routes/servers.py` to use factory
- [ ] Refactor `routes/variables.py` to use factory

### Phase 3 (2-3 days)
- [ ] Refactor `routes/secrets.py` to use factory
- [ ] Refactor `routes/aliases.py` to use factory (note: has more custom logic)
- [ ] Create `routes/template_utils.py`

### Phase 4 (2-3 days)
- [ ] Extract helpers in `content_rendering.py`
- [ ] Consider `EntityMetadata` registry for type safety

**Total estimated effort: 8-12 days**

---

## Risk Assessment

### Low Risk
- Moving `_wants_structured_response()` to shared module
- Creating base form class
- Extracting message builders

### Medium Risk
- Generic route factory (requires careful testing of all CRUD operations)
- Content rendering refactoring (markdown parsing is fragile)

### High Risk
- EntityMetadata registry (significant architectural change)

---

## Testing Strategy

For each refactoring:
1. Run existing test suite before changes
2. Implement refactoring
3. Run test suite again (should have same results)
4. Add integration tests for new abstractions
5. Manual testing of affected routes

---

## Conclusion

The codebase is already well-structured, but these refactorings would:
- **Reduce maintenance burden** by eliminating 300+ lines of duplication
- **Improve consistency** through shared abstractions
- **Enhance type safety** with proper entity metadata
- **Lower cognitive load** with clearer function responsibilities

The highest-impact changes (CRUD factory, consolidated helpers) can be implemented incrementally without disrupting existing functionality.
