# Viewer

[![CI](https://github.com/curtcox/Viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/curtcox/Viewer/actions/workflows/ci.yml)

Viewer is a Flask based web application that focuses on analysing HTTP requests and presenting diagnostics.
Authentication, subscriptions, and OAuth flows are now handled externally so this project concentrates on content tooling.
The project includes simple helper scripts so you can get up and running quickly.
Visit the [published GitHub Pages site](https://curtcox.github.io/Viewer/) for the latest CI test and spec reports.

## Quick start

```bash
./install   # set up a virtual environment and install dependencies
./doctor    # verify your environment
./run       # start the development server on http://localhost:5000
./test      # run the full test suite (pytest + Gauge specs)
./test-unit  # run only the pytest suite (add --coverage for coverage reports)
./test-gauge # run only the Gauge specs
python run_integration_tests.py  # run the dedicated integration test suite
python run_coverage.py --xml --html  # run tests with coverage reports (optional)
```

> **Note:** The automated tests require the [Markdown](https://python-markdown.github.io/) package. Run `./install` (or
> `pip install -r requirements.txt`) before invoking the test suite so the dependency is available.

## Environment

* Running `./install` copies `.env.sample` to `.env` the first time so you have a starting point for local configuration.
* The default configuration uses a SQLite database stored in `secureapp.db` in the project root so you can test without
  additional services.
* To switch to PostgreSQL, update `DATABASE_URL` in `.env` to point at your PostgreSQL instance (for example,
  `postgresql://username:password@localhost/database_name`) and install the appropriate driver such as `psycopg`.
* Useful environment variables for local development include:
  * `DATABASE_URL` – controls the database connection string.  Defaults to the bundled SQLite file but can target
    PostgreSQL or another database supported by SQLAlchemy.
  * `SESSION_SECRET` – Flask's secret key used to sign sessions.  Replace the sample value with a secure random string
    for any shared or production deployment.
  * `LOGFIRE_API_KEY` – enables Logfire tracing and activates a link to the configured project on the home page.
  * `LOGFIRE_PROJECT_URL` – the share link to your Logfire project so the home page can deep-link directly to it.
  * `LANGSMITH_API_KEY` – enables Logfire's LangSmith bridge so language workflows are captured automatically.
  * `LANGSMITH_PROJECT_URL` – optional link shown on the home page when the LangSmith integration is active.
## Scripts

* `install` – create a virtual environment and install the required Python packages.
* `run` – activate the environment and run the application.
* `doctor` – check for common installation issues and suggest how to fix them.
* `test-unit` – execute the pytest suite (`--coverage` forwards to `run_coverage.py`).
* `test-gauge` – run the Gauge specifications.
* `test` – invoke both `test-unit` and `test-gauge` sequentially.
* `run_integration_tests.py` – execute only the integration tests under `tests/integration`.
* `run_coverage.py` – execute the test suite with coverage analysis and optional HTML/XML reports.
* `scripts/check-test-index.sh` – verify `TEST_INDEX.md` matches the output of `python generate_test_index.py` so you can catch
  drift locally before pushing changes.

### Gauge specs

Gauge specs exercise key user flows alongside the pytest suite. Install the
[Gauge CLI](https://docs.gauge.org/getting_started/installing-gauge.html) and the
`python` and `html-report` plugins, then run `./test-gauge` to execute just Gauge or `./test` to run both pytest and
Gauge. The HTML report generated at `reports/html-report/index.html` is available
through the running app's source browser at `/source/reports/html-report/index.html`,
alongside unit test and coverage results. A build is only considered passing when
both the pytest suite and the Gauge specs succeed.

## Requirements

* Python 3.12 or newer
* Optional: PostgreSQL if you do not want to use the default SQLite database

## Developing

After changing the configuration or dependencies re‑run `./doctor` to ensure your setup is healthy.  Use `Ctrl+C` to stop
 the development server started with `./run`.

Run `pytest` (or the `./test` wrapper) before opening a pull request so you catch regressions locally.  Integration scenarios
live under `tests/integration` and are skipped by default; run `python run_integration_tests.py` when you need to validate
end-to-end behaviour.

### Observability

Viewer now ships with Logfire support (including LangSmith instrumentation) so local development mirrors production
tracing.  Install dependencies with `./install`, set your `LOGFIRE_*` and `LANGSMITH_*` values in `.env`, and then use `./run`
to start the server.  The `./install` script installs the required OpenTelemetry instrumentations (`opentelemetry-
instrumentation-flask` and `opentelemetry-instrumentation-sqlalchemy`) so Logfire can attach to the framework automatically.
When keys are present, the home page provides quick links to both observability dashboards; otherwise the buttons note that
the integrations are disabled.  Detailed reasons for any disabled integration appear in the application log at startup.
