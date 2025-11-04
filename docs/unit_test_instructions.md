# Unit Test Execution Guide

These steps capture the minimal setup required to run the repository's unit-test suite in an isolated environment. They are adapted from hands-on verification of the helper scripts bundled with the project.

## 1. Install dependencies
Run the repository's bootstrap script once per environment to provision the virtual environment, install dependencies, and create a default `.env` file:

```bash
./install
```

The script is idempotent, so it is safe to rerun when dependencies or tooling change.
In sandboxed environments without outbound network access, pip may emit warnings about failing to reach the package index; the
script finishes successfully as long as the required wheels were previously cached.

## 2. Execute the unit-test wrapper
To run lint and the pytest-only unit-test selection without the Gauge specs or other integration checks, use:

```bash
./test unit
```

This command ensures the environment variables are configured and dispatches to the same pytest invocation used in CI for the unit tests.

## 3. Optional: call pytest directly
For finer-grained control, call the dedicated helper and pass pytest arguments after a `--` separator:

```bash
./test-unit -- --maxfail=1 --verbose
```

Add `--coverage` before the separator to generate coverage data via pytest-cov.

## 4. Testmon: Selective test execution for faster feedback

The project uses [pytest-testmon](https://testmon.org/) to run only tests affected by recent code changes. This dramatically speeds up the feedback loop during development.

### Using testmon locally

Run tests with testmon enabled:

```bash
./test-unit --testmon
```

This will:
- On the first run: execute all tests and build a dependency database
- On subsequent runs: only execute tests affected by your code changes

### Testmon with coverage

You can combine testmon with coverage reporting:

```bash
./test-unit --coverage --testmon
```

### Managing the testmon database

Clear the testmon cache to force all tests to run:

```bash
pytest --testmon-nocache
```

The testmon database is stored in `.testmondata` in the project root. This file should be excluded from version control (it's already in `.gitignore`).

### How testmon works

Testmon tracks which source files each test depends on. When you change a file, testmon knows which tests need to be re-run. This is particularly useful for:
- Quick feedback during TDD (Test-Driven Development)
- Running tests frequently without waiting for the full suite
- CI/CD pipelines where only changed code needs testing

### Testmon in CI

The CI workflow automatically uses testmon for unit tests, property tests, and integration tests. The testmon database is cached between CI runs to maximize the benefit of selective testing.

## 5. Gauge specs (known limitation)
The full `./test` wrapper also triggers Gauge browser specs that attempt to download a Chromium build. In offline or sandboxed environments the download fails, leading to a non-zero exit even though the unit tests pass. Run `./test` only when the environment allows outbound downloads.
