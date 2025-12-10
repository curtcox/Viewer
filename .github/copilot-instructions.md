# GitHub Copilot Instructions for Viewer

## Project Overview

Viewer is a Flask-based web application focused on analyzing HTTP requests and presenting diagnostics. The project emphasizes content tooling and presentation, with authentication and subscriptions handled externally. The codebase prioritizes simplicity, clarity, and comprehensive testing.

## Quick Start Commands

```bash
./install   # Set up virtual environment and install dependencies
./doctor    # Verify environment configuration
./run       # Start development server on http://localhost:5000
./test      # Run full test suite (pytest + Gauge specs)
./test-unit # Run only pytest suite (add --coverage for coverage reports)
./test-gauge # Run only Gauge specs
```

## Development Workflow

### Process Principles

1. **Favor simplicity**: Choose the simplest implementation that satisfies requirements. Prioritize clarity over cleverness.
2. **Work incrementally**: Make small changes. Write or update tests first, implement minimal code to pass, then refactor.
3. **Keep tests focused**: Tests should be narrow yet meaningful, providing confidence that passing tests indicate working code.
4. **Use tests as permission to refactor**: When tests are green, improve code structure while maintaining behavior.
5. **Keep CI healthy**: Run `./doctor` and `./test` locally before pushing changes.

### Lightweight Workflow

1. Understand the user-visible behavior to change
2. Add or update the smallest high-value test that will fail without the change
3. Implement the simplest code necessary to turn the test green
4. With tests passing, refactor to improve clarity or structure
5. Run fast checks (`./doctor`, `./test`) before pushing

## Testing Strategy

### Test Organization

- **Unit tests**: Python `test_*.py` modules discovered automatically by pytest
- **Gauge specs**: Browser-based user flow tests in `specs/` directory
- **Integration tests**: Under `tests/integration/`, run with `scripts/run-integration.sh`
- **Test exclusions**: Configured in `pytest.ini` via `norecursedirs` setting

### Running Tests

```bash
# Fast unit tests only
./test-unit

# With coverage
./test-unit --coverage
python run_coverage.py --xml --html

# Selective testing with testmon (only affected tests)
./test-unit --testmon

# Specific test file
./test-unit -- tests/test_import_export.py -v

# Integration tests (mirrors CI)
scripts/run-integration.sh

# Full suite including Gauge specs
./test
```

### Test Best Practices

- Add or update tests alongside implementation changes
- Keep tests readable and focused on behavior
- Use testmon (`--testmon`) for faster feedback during development
- Run full suite before opening pull requests
- Integration tests are skipped by default; run explicitly when validating end-to-end behavior

## Code Style & Conventions

### UI Design Principles

- **Links for navigation**: If a UI element could link to something useful, make it a link
- **Buttons for actions**: Reserve buttons for operations that make changes
- **Make links obvious**: Ensure links look like links for immediate recognition

### Code Principles

- Avoid comments unless they match existing style or explain complex logic
- Use existing libraries; only add new dependencies when absolutely necessary
- Maintain consistency with existing code patterns
- Leave code simpler than you found it

## Environment & Configuration

### Environment Variables

- `DATABASE_URL`: Database connection (defaults to SQLite `secureapp.db`)
- `SESSION_SECRET`: Flask secret key for signing sessions
- `LOGFIRE_API_KEY`: Enable Logfire tracing
- `LOGFIRE_PROJECT_URL`: Link to Logfire project dashboard
- `LANGSMITH_API_KEY`: Enable LangSmith integration
- `LANGSMITH_PROJECT_URL`: Link to LangSmith project

### Setup

- Run `./install` to create `.env` from `.env.sample`
- Default: SQLite database (`secureapp.db`)
- PostgreSQL: Update `DATABASE_URL` and install `psycopg`

## Project Structure

### Key Directories

- `api/`: API route handlers
- `db_access/`: Database access layer
- `docs/`: Detailed documentation
- `routes/`: Flask route definitions
- `specs/`: Gauge specifications for behavior tests
- `static/`: Static assets (CSS, JavaScript)
- `templates/`: Jinja2 templates
- `tests/`: Test modules
- `tests/integration/`: Integration test suite
- `scripts/`: Helper scripts for CI and development

### Helper Scripts

- `install`: Create virtualenv and install packages
- `doctor`: Check for common installation issues
- `run`: Activate environment and start application
- `test-unit`: Execute pytest suite
- `test-gauge`: Run Gauge specifications
- `test`: Run both pytest and Gauge sequentially
- `scripts/run-integration.sh`: Run integration tests with logging
- `run_coverage.py`: Execute tests with coverage analysis
- `scripts/check-test-index.sh`: Verify TEST_INDEX.md is current
- `scripts/publish_integration_summary.py`: Generate CI integration summary
- `scripts/publish-coverage-summary.sh`: Generate CI coverage summary
- `scripts/build-report-site.py`: Build static report site from artifacts

## Special Considerations

### Authentication

Authentication is handled by external systems. This repository focuses on content tooling, not authentication flows.

### Gauge Specs

- Requires [Gauge CLI](https://docs.gauge.org/getting_started/installing-gauge.html)
- Install `python` and `html-report` plugins
- HTML reports at `reports/html-report/index.html`
- Accessible via app's source browser at `/source/reports/html-report/index.html`
- May fail in offline/sandboxed environments due to Chromium download requirement

### Observability

- Ships with Logfire support (including LangSmith instrumentation)
- Requires OpenTelemetry instrumentations (`opentelemetry-instrumentation-flask`, `opentelemetry-instrumentation-sqlalchemy`)
- Home page provides quick links to observability dashboards when configured

## Requirements

- Python 3.12 or newer
- Optional: PostgreSQL (if not using default SQLite)
- Optional: Gauge CLI for running Gauge specs

## CI/CD

- GitHub Actions workflows in `.github/workflows/`
- `full-checks.yml`: Complete test suite with coverage
- `quick-checks.yml`: Fast validation for PRs
- Published reports available at [GitHub Pages site](https://curtcox.github.io/Viewer/)

## Making Changes

1. Run `./install` to ensure environment is ready
2. Run `./doctor` to verify configuration
3. Make changes following the lightweight workflow
4. Run `./test-unit` frequently for fast feedback
5. Use `./test-unit --testmon` for even faster iteration
6. Run `./test` before opening PR
7. Re-run `./doctor` after changing configuration or dependencies

## Getting Help

- See `docs/unit_test_instructions.md` for detailed testing walkthrough
- See `AGENTS.md` for workflow and process principles
- See `README.md` for comprehensive project documentation
- Check `docs/` directory for specific topics (import/export formats, deployment, etc.)
