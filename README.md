# SecureApp

SecureApp is a Flask based web application that demonstrates multi layer access control and integrates with OAuth providers.  
The project includes simple helper scripts so you can get up and running quickly.

## Quick start

```bash
./install   # set up a virtual environment and install dependencies
./doctor    # verify your environment
./run       # start the development server on http://localhost:5000
./test      # run the full test suite
python run_coverage.py --xml --html  # run tests with coverage reports (optional)
```

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

## Scripts

* `install` – create a virtual environment and install the required Python packages.
* `run` – activate the environment and run the application.
* `doctor` – check for common installation issues and suggest how to fix them.
* `test` – execute the automated test suite via pytest.
* `run_coverage.py` – execute the test suite with coverage analysis and optional HTML/XML reports.

## Requirements

* Python 3.12 or newer
* Optional: PostgreSQL if you do not want to use the default SQLite database

## Developing

After changing the configuration or dependencies re‑run `./doctor` to ensure your setup is healthy.  Use `Ctrl+C` to stop
 the development server started with `./run`.

Run `pytest` (or the `./test` wrapper) before opening a pull request so you catch regressions locally.  The test runner will
 execute every `test_*.py` module in the repository.
