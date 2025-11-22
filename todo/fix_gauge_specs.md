# Fix Gauge Specs Failures

## Overview

The full-checks.yml workflow includes Gauge spec execution that is currently showing failures. This document outlines the investigation and fixes needed for the Gauge end-to-end test suite.

## Current Status

- **Check Name**: `gauge-specs` in `.github/workflows/full-checks.yml`
- **Status**: Failing
- **Location**: Specs in `specs/` directory, step implementations in `step_impl/`
- **CI URL**: https://curtcox.github.io/Viewer/ (reports published)

## Background

Gauge is an end-to-end testing framework that:
- Uses markdown-style spec files (`*.spec`) to define test scenarios
- Requires Python step implementations in `step_impl/`
- Uses pyppeteer (Chromium) for browser automation
- Tests the full application stack including UI interactions

## Spec Files

Current spec files in the repository:
- `specs/alias_management.spec` - Alias CRUD operations
- `specs/alias_view.spec` - Alias viewing functionality
- `specs/content_negotiation.spec` - Content type handling
- `specs/import_export.spec` - Import/export workflows
- `specs/meta_navigation.spec` - Navigation UI
- `specs/profile.spec` - User profile
- `specs/routes_overview.spec` - Route listings
- `specs/search.spec` - Search functionality
- `specs/secret_form.spec` - Secret form UI
- `specs/secrets.spec` - Secret management
- `specs/server_events.spec` - Server event tracking
- `specs/server_form.spec` - Server form UI
- `specs/server_view.spec` - Server viewing
- `specs/settings.spec` - Settings page
- `specs/source_browser.spec` - Source code browsing
- `specs/upload_templates.spec` - Template uploads

## Investigation Steps

### 1. Identify Failing Specs

To determine which specs are failing:

```bash
# Install Gauge (if not already installed)
# See: https://docs.gauge.org/getting_started/installing-gauge.html

# Run gauge specs locally
./test-gauge

# Or run with verbose output
gauge run specs/ --verbose

# Run specific spec file
gauge run specs/alias_management.spec
```

### 2. Review CI Logs

Check the GitHub Actions logs for the `gauge-specs` job:
- Look at the `reports/html-report/` artifacts
- Check the `gauge-execution.log` for detailed error messages
- Review the published reports at https://curtcox.github.io/Viewer/gauge-specs/

### 3. Common Gauge Failure Causes

Common issues to investigate:
- **Chromium startup failures**: pyppeteer may fail to launch browser in CI
- **Timing issues**: Race conditions in async operations
- **Selector changes**: UI selectors may have changed
- **Step implementation bugs**: Python code in `step_impl/` may have errors
- **Environment setup**: Missing environment variables or configuration
- **Database state**: Tests may depend on specific database state
- **Authentication**: OAuth/login flows may be failing

## Proposed Investigation Tasks

### Task 1: Local Gauge Setup
- [ ] Install Gauge CLI locally
- [ ] Install required Gauge plugins (Python, HTML report)
- [ ] Run full spec suite locally to reproduce failures
- [ ] Document local setup process

### Task 2: Categorize Failures
- [ ] Run each spec file individually
- [ ] Categorize failures by type:
  - Setup/teardown failures
  - Browser automation failures
  - Assertion failures
  - Timeout failures
- [ ] Document specific error messages for each failure

### Task 3: Fix High-Priority Failures
- [ ] Fix any spec files with 100% failure rate (setup issues)
- [ ] Fix critical path specs (e.g., authentication, core CRUD)
- [ ] Fix browser automation issues (selectors, timing)

### Task 4: Improve Reliability
- [ ] Add explicit waits for async operations
- [ ] Use more robust selectors (data-test-id attributes)
- [ ] Add retry logic for flaky steps
- [ ] Improve error messages in step implementations

### Task 5: CI Debugging
- [ ] Add more verbose logging in CI
- [ ] Capture screenshots on failure
- [ ] Save browser console logs
- [ ] Document any CI-specific issues

## Files to Review

### Step Implementation Files
- `step_impl/web_steps.py` - Web interaction steps (largest file, 30KB)
- `step_impl/alias_steps.py` - Alias-specific steps
- `step_impl/import_export_steps.py` - Import/export steps
- `step_impl/source_steps.py` - Source browsing steps
- `step_impl/artifacts.py` - Artifact handling
- `step_impl/shared_app.py` - Shared app setup
- `step_impl/shared_state.py` - Shared test state

### CI Configuration
- `.github/workflows/full-checks.yml` (lines 483-531) - Gauge job definition
- `scripts/checks/run_gauge_specs.sh` - Gauge execution script
- `scripts/publish_gauge_summary.py` - Report publishing
- `scripts/ci/verify_chromium_installation.sh` - Chromium setup
- `scripts/ci/check_chromium_dependencies.sh` - Dependency checks
- `scripts/ci/test_chromium_binary.sh` - Browser testing

### Test Scripts
- `./test-gauge` - Main Gauge test runner
- `./gauge` - Gauge wrapper script
- `scripts/test-browser-launch.py` - Browser launch testing

## Potential Quick Wins

1. **Update pyppeteer**: Check if upgrading fixes Chromium issues
2. **Increase timeouts**: Some specs may just need more time
3. **Skip flaky specs**: Temporarily skip unstable specs to green the build
4. **Fix obvious bugs**: Review step implementations for clear errors

## Success Criteria

- [ ] All Gauge specs pass in CI
- [ ] Gauge HTML report shows 100% pass rate
- [ ] No timeout or browser launch failures
- [ ] Reports published correctly to GitHub Pages

## Timeline Estimate

Based on typical Gauge debugging:
- **Quick assessment**: 1-2 hours (identify failing specs)
- **Basic fixes**: 4-8 hours (fix obvious issues)
- **Comprehensive fix**: 2-3 days (fix all specs, improve reliability)
- **Polish and documentation**: 1 day

**Total**: Approximately 1-2 weeks for complete resolution

## Notes

- Gauge specs are end-to-end tests and naturally more brittle than unit tests
- CI environment may behave differently than local (headless browser, timing)
- Consider whether all specs are still relevant or if some should be archived
- May need to update selectors if UI has changed significantly

## References

- [Gauge Documentation](https://docs.gauge.org/)
- [Gauge Python Plugin](https://gauge-python.readthedocs.io/)
- [pyppeteer Documentation](https://miyakogi.github.io/pyppeteer/)
- [GitHub Actions workflow](.github/workflows/full-checks.yml)
- [CI Reports](https://curtcox.github.io/Viewer/)

## Related Issues

This work may uncover or be related to:
- UI changes that broke selectors
- Performance regressions causing timeouts
- Browser compatibility issues
- CI infrastructure problems
