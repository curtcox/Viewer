# Gauge spec execution status

## Why results are currently unavailable

The Gauge specs in this repository depend on the Gauge command-line interface and its Python plugin.  Our execution environment does not provide the `gauge` binary, and the Python plugin (`getgauge`) is also absent, so invoking `gauge run` cannot discover or execute the specs.  The fallback runner (`python run_specs.py`) lets us exercise the steps manually, but it does not generate the standard Gauge reports that confirm a full Gauge execution succeeded.  As a result we cannot inspect the canonical Gauge output to prove the specs passed.

## Plan to regain Gauge visibility

1. **Bundle the Gauge CLI.** Extend the `./install` script to download the official Gauge release for Linux x86_64, verify its checksum, and place the executable under `./env/bin/gauge` so the rest of the tooling can rely on it without needing global installation rights.
2. **Install the Gauge Python plugin offline.** Vendor the Gauge Python plugin archive alongside the repository, adjust `./install` to unpack it into `env/gauge/plugins/python`, and set `GAUGE_PYTHON_COMMAND` so the CLI can invoke our virtualenv's interpreter.
3. **Re-enable native Gauge runs.** Update the `./test` wrapper to prefer the bundled Gauge binary, ensuring CI and local runs execute `gauge run specs` before falling back to `python run_specs.py`.  Add a smoke test in `test_run_specs_script.py` that shells out to the new binary so regressions surface quickly.
4. **Surface HTML and console reports.** Once the CLI is working, commit to publishing the HTML report under `reports/html-report/` and teach `README.md` how to open it so we can review the official Gauge output alongside pytest results.

Completing these steps will let us run the true Gauge workflow end-to-end and inspect its success reports instead of relying solely on the lightweight interpreter.
