# SecureApp

SecureApp is a Flask based web application that demonstrates multi layer access control and integrates with OAuth providers.  
The project includes simple helper scripts so you can get up and running quickly.

## Quick start

```bash
./install   # set up a virtual environment and install dependencies
./doctor    # verify your environment
./run       # start the development server on http://localhost:5000
```

The `install` script copies `.env.sample` to `.env` if it does not exist.  By default the application uses a local SQLite
file called `secureapp.db`.  Edit `.env` to change the configuration or to point at a PostgreSQL instance for production use.

## Scripts

* `install` – create a virtual environment and install the required Python packages.
* `run` – activate the environment and run the application.
* `doctor` – check for common installation issues and suggest how to fix them.

## Requirements

* Python 3.8 or newer
* Optional: PostgreSQL if you do not want to use the default SQLite database

## Developing

After changing the configuration or dependencies re‑run `./doctor` to ensure your setup is healthy.  Use `Ctrl+C` to stop
 the development server started with `./run`.
