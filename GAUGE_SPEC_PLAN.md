# Gauge spec execution status

## Why results are currently unavailable

The Gauge specs in this repository depend on the Gauge command-line interface and its Python plugin.  Our execution environment does not provide the `gauge` binary, and the Python plugin (`getgauge`) is also absent, so invoking `gauge run` cannot discover or execute the specs.  The fallback runner (`python run_specs.py`) lets us exercise the steps manually, but it does not generate the standard Gauge reports that confirm a full Gauge execution succeeded.  As a result we cannot inspect the canonical Gauge output to prove the specs passed.

## Why CI is currently failing

The latest CI run executes the real Gauge CLI, which surfaces two distinct issues:

* `specs/gauge_task_list.md` is no longer a valid Gauge spec.  We replaced the file contents with a backlog description, so Gauge now reports a `ParseError` because the document does not contain any scenarios or steps.
* The screenshot spec uses parameterised steps such as `When I request /_screenshot/cid-demo with screenshot mode enabled`.  Gauge’s Python runner expects quoted parameters (for example `"/_screenshot/cid-demo"`), so the unquoted version is ignored and Gauge raises `Step implementation not found` for each scenario.

## Recovery plan

1. **Move the backlog out of the spec runner.** Relocate the task list to `docs/gauge_backlog.md` (or similar) and restore `specs/gauge_task_list.spec` with at least one real scenario so the CLI parser succeeds.
2. **Align the screenshot spec with Gauge syntax.** Update `specs/screenshot_mode.spec` to quote the dynamic path segment and keep `step_impl/source_steps.py` accepting a `<path>` parameter.  Verify that both `gauge run specs` and `python run_specs.py` recognise the updated wording.
3. **Keep the compatibility runner honest.** Extend `test_run_specs_script.py` with a regression test that exercises a quoted placeholder so our shim mirrors Gauge’s behaviour.
4. **Re-run CI.** Once the specs parse and the steps bind correctly, the Gauge job should pass again and produce the expected HTML report.

Completing these steps addresses the immediate CI failure while continuing the longer-term effort to make Gauge results visible in every environment.
