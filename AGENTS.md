# Workflow

- `./install`: Set up project dependencies and environment requirements.
- `./doctor`: Run diagnostic checks to verify that the environment is correctly configured.
- `./run`: Start the application using the standard runtime configuration.
- `./test`: Execute the project's automated test suite.
- `python run_coverage.py --xml --html`: (Optional) Run the test suite with coverage reporting, producing XML and HTML outputs for review.

Pytest automatically discovers and runs all `test_*.py` modules located under the repository root while skipping any directories listed in the `norecursedirs` setting of `pytest.ini`.

## Authentication tests

- `run_auth_tests.py` executes the authentication-specific suites (`test_auth_providers`, `test_local_auth`, `test_auth_integration`, and `test_auth_templates`) outside of the standard pytest run so Flask-Login initialization does not interfere with unrelated tests.
- The runner configures an in-memory SQLite database (`DATABASE_URL=sqlite:///:memory:`) and sets a deterministic `SESSION_SECRET=test-secret-key`. Mirror these environment variables if you need to reproduce the segregated authentication setup manually.
