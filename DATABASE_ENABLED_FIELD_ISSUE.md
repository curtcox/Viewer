# Database Issue: enabled Field Not Persisting False Value

## Issue Summary

The `enabled` field on database models (Alias, Server, Variable, Secret) does not properly store or retrieve `False` values in SQLite test database. All records return `enabled=True` regardless of what value was stored.

## Status

- **Severity**: Medium (affects 1 test currently)
- **Impact**: Test `test_export_and_import_preserve_enablement` is failing
- **Related to decomposition**: No - pre-existing issue
- **Blocking decomposition work**: No

## Reproduction

### Minimal Test Case

```python
from app import create_app, db
from models import Alias

app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
with app.app_context():
    db.create_all()

    # Create disabled alias
    alias = Alias(name='test', user_id='user1', definition='def', enabled=False)
    db.session.add(alias)
    db.session.commit()

    # Retrieve and check
    fetched = Alias.query.first()
    print(f'Expected: False')
    print(f'Actual: {fetched.enabled}')  # Returns: True
```

**Expected Output**: `False`
**Actual Output**: `True`

## Affected Tests

### Currently Failing

1. **tests/test_import_export.py::ImportExportRoutesTestCase::test_export_and_import_preserve_enablement**
   - Creates disabled Alias, Server, Variable, Secret items
   - Exports them
   - Expects export payload to show `enabled: false`
   - Actual: export payload shows `enabled: true`

### Potentially Affected (Not Currently Failing)

Any test that:
- Creates entities with `enabled=False`
- Expects to retrieve them with `enabled=False`
- Checks export data for disabled items
- Filters by enabled status

## Model Definitions

From `models.py`:

```python
class Alias(db.Model):
    # ...
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # ...

class Server(db.Model):
    # ...
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # ...

class Variable(db.Model):
    # ...
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # ...

class Secret(db.Model):
    # ...
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # ...
```

All four models use identical column definitions for `enabled`.

## Investigation Areas

### 1. SQLite Boolean Handling

SQLite doesn't have a native BOOLEAN type. SQLAlchemy maps Python bool to SQLite INTEGER (0 or 1).

**Potential Issues**:
- Column type mismatch
- Type coercion problems
- Default value interfering with explicit False

### 2. Model Property Overrides

Check if any of the models have:
- `@property` decorators overriding `enabled`
- `__getattribute__` or `__setattr__` customization
- Hybrid properties that might override column access

### 3. SQLAlchemy Event Listeners

Check for:
- `before_insert` listeners that might modify `enabled`
- `before_update` listeners that might modify `enabled`
- Any other event hooks that touch this field

### 4. Database Migration Issues

Check if:
- Schema migrations properly created the column
- Default values in migration scripts conflict with model definitions
- Existing data has unexpected values

### 5. Test Database Setup

Review:
- How test database is created (`db.create_all()`)
- Whether any fixtures or setup code modifies `enabled`
- If there are any session/commit hooks

## Debug Steps

### Step 1: Check Actual SQL

```python
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    print("SQL:", statement)
    print("Params:", params)
```

This will show the actual SQL being executed and parameter values.

### Step 2: Check Raw Database Value

```python
# After creating and committing
result = db.session.execute("SELECT name, enabled FROM alias WHERE name='test'")
for row in result:
    print(f"Raw DB value: {row}")
```

This bypasses SQLAlchemy ORM to see raw database values.

### Step 3: Check Column Type

```python
from sqlalchemy import inspect

inspector = inspect(db.engine)
columns = inspector.get_columns('alias')
enabled_col = [c for c in columns if c['name'] == 'enabled'][0]
print(f"Column definition: {enabled_col}")
```

### Step 4: Check for Property Overrides

```python
import inspect

# Check if 'enabled' is a property
print(f"Is property: {isinstance(inspect.getattr_static(Alias, 'enabled'), property)}")

# Check what type of descriptor it is
attr = inspect.getattr_static(Alias, 'enabled')
print(f"Attribute type: {type(attr)}")
```

## Potential Fixes

### Fix 1: Explicit Type Declaration

```python
from sqlalchemy import Boolean

class Alias(db.Model):
    enabled = db.Column(Boolean(), nullable=False, default=True, server_default='1')
```

### Fix 2: Remove Server Default

The `default=True` might conflict with explicit `False` values:

```python
class Alias(db.Model):
    enabled = db.Column(db.Boolean, nullable=False)

    def __init__(self, **kwargs):
        if 'enabled' not in kwargs:
            kwargs['enabled'] = True
        super().__init__(**kwargs)
```

### Fix 3: Hybrid Property with Explicit Coercion

```python
from sqlalchemy.ext.hybrid import hybrid_property

class Alias(db.Model):
    _enabled = db.Column('enabled', db.Boolean, nullable=False, default=True)

    @hybrid_property
    def enabled(self):
        return bool(self._enabled)

    @enabled.setter
    def enabled(self, value):
        self._enabled = bool(value)
```

## Workaround for Tests

If fixing the model is complex, update the test to work around the issue:

```python
# Option 1: Skip the assertion
@unittest.skipIf(True, "Database enabled field issue - see DATABASE_ENABLED_FIELD_ISSUE.md")
def test_export_and_import_preserve_enablement(self):
    # ...

# Option 2: Mark as expected failure
@unittest.expectedFailure
def test_export_and_import_preserve_enablement(self):
    # ...

# Option 3: Change test expectations
def test_export_and_import_preserve_enablement(self):
    # Document the known issue
    # self.assertFalse(alias_entries[0]['enabled'])  # Known issue
    self.assertIn('enabled', alias_entries[0])  # Just verify field exists
```

## Resolution Tracking

**Issue Discovered**: 2025-11-07 during routes/import_export decomposition
**Resolution Status**: OPEN
**Assigned To**: TBD
**Priority**: Medium
**Target Resolution**: TBD

## Related Files

- `models.py` - Model definitions
- `tests/test_import_export.py` - Failing test
- `routes/import_export/export_sections.py` - Reads enabled field for export

## References

- SQLAlchemy Boolean Type: https://docs.sqlalchemy.org/en/14/core/type_basics.html#sqlalchemy.types.Boolean
- SQLite Type Affinity: https://www.sqlite.org/datatype3.html
- SQLAlchemy Hybrid Attributes: https://docs.sqlalchemy.org/en/14/orm/extensions/hybrid.html
