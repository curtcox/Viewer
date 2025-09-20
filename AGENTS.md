# Workflow

- `./install`: Set up project dependencies and environment requirements.
- `./doctor`: Run diagnostic checks to verify that the environment is correctly configured.
- `./run`: Start the application using the standard runtime configuration.
- `./test`: Execute the project's automated test suite.
- `python run_coverage.py --xml --html`: (Optional) Run the test suite with coverage reporting, producing XML and HTML outputs for review.

Pytest automatically discovers and runs all `test_*.py` modules located under the repository root while skipping any directories listed in the `norecursedirs` setting of `pytest.ini`.
