# Eliminate `SESSION_SECRET`

## Goal
Stop using the custom environment variable `SESSION_SECRET` and rely on Flask’s standard `SECRET_KEY` configuration instead.

Today the app maps `SESSION_SECRET` -> `app.config["SECRET_KEY"]`.

## Current usage (what depends on it)
`SESSION_SECRET` is read in `app.py` and becomes Flask’s `SECRET_KEY`:

- `app.py`
  - `flask_app.config.update(SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret"), ...)`

Once set, Flask/Werkzeug and Flask extensions use `SECRET_KEY` for:

- **Session cookies**: signing the session cookie backing `flask.session`.
  - Example of code relying on a working session secret:
    - `analytics.py`: `make_session_permanent()` sets `session.permanent = True` and is registered as a `before_request` hook.
- **CSRF tokens (when enabled)**: Flask-WTF uses `SECRET_KEY` (or `WTF_CSRF_SECRET_KEY`) to generate/validate CSRF tokens.
  - In integration tests, CSRF is explicitly disabled via `WTF_CSRF_ENABLED = False`, but in normal runtime CSRF may be enabled depending on environment/config.
- **Flashed messages**: Flask’s `flash()` stores messages in the session.

### User-visible functionality that depends on it now
If `SESSION_SECRET`/`SECRET_KEY` is missing or inconsistent:

- **Any feature that relies on sessions becomes unreliable**.
  - Symptoms:
    - Users may appear to “lose state” between requests.
    - Flash messages may not persist.
- **Forms may fail CSRF validation** (if CSRF is enabled).
  - Symptoms:
    - POSTs to form endpoints can fail with 400 CSRF errors.
- **Changing the secret logs everyone out / clears session state**.
  - This is expected for signed-cookie sessions: rotating the key invalidates existing cookies.

## Required code changes

### 1) Change the app to stop reading `SESSION_SECRET`
In `app.py`, replace:

- `SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret")`

with something that does not depend on `SESSION_SECRET`. Recommended options:

- **Preferred (standard Flask env var name):**
  - `SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret")`

Optionally (recommended for production safety), also:

- Fail fast if `SECRET_KEY` is not set in non-testing environments.
  - This prevents accidentally deploying with the insecure `"dev-secret"` fallback.

### 2) Update env files
- `.env`
  - Remove `SESSION_SECRET=...`
  - Add `SECRET_KEY=...`
- `.env.sample`
  - Replace the `SESSION_SECRET` example with `SECRET_KEY`

### 3) Update scripts/tests that set `SESSION_SECRET`
Search for `os.environ.setdefault("SESSION_SECRET", ...)` and change to `SECRET_KEY`:

- `tests/integration/conftest.py`
  - Replace `os.environ.setdefault("SESSION_SECRET", "integration-secret-key")`
  - With `os.environ.setdefault("SECRET_KEY", "integration-secret-key")`

- `migrate_remove_template_columns.py`
  - Replace `os.environ.setdefault('SESSION_SECRET', 'migration-secret-key')`
  - With `os.environ.setdefault('SECRET_KEY', 'migration-secret-key')`

Other locations in the repo (docs/CI/scripts) that mention `SESSION_SECRET` should be updated similarly.

### 4) (Optional) Consider explicit CSRF secret
If you want CSRF secrets to be rotated/managed independently of session signing:

- Configure `WTF_CSRF_SECRET_KEY` via environment
- Keep `SECRET_KEY` for session signing

This is optional; Flask-WTF works fine with only `SECRET_KEY`.

## Compatibility / rollout notes

- **Breaking change:** any deployment tooling or hosting (e.g., Vercel env vars) currently setting `SESSION_SECRET` must be updated to set `SECRET_KEY`.
- **Session invalidation:** rotating `SECRET_KEY` will invalidate all existing session cookies.
  - Plan the rollout accordingly if you care about preserving sessions.

## Verification checklist
- Update the code and env var names.
- Run `./doctor` and `./test`.
- Start the app (`./run`) and verify:
  - Page loads
  - POST forms still work (if CSRF enabled)
  - Flash messages/session behavior works as expected

## Suggested follow-up (cleanup)
After migration, consider adding a temporary startup warning for one release if `SESSION_SECRET` is present, e.g.:

- If `SESSION_SECRET` is set but `SECRET_KEY` is not:
  - log a warning explaining the rename.

Then remove that warning once all deployments are updated.
