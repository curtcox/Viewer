# Multi-Branch Deployment for GitHub Pages

This document explains how the GitHub Pages deployment workflow supports dev, test, and production (main) branches.

## Overview

The `full-checks.yml` workflow now publishes test reports to GitHub Pages for three branches:
- **main** (production): Reports published to the root of the GitHub Pages site
- **dev** (development): Reports published to `/dev` subdirectory
- **test** (testing): Reports published to `/test` subdirectory

## How It Works

### Workflow Triggers

The workflow runs on pushes to:
```yaml
branches:
  - main
  - master
  - dev
  - test
```

### Branch Detection

The `Determine deployment path` step identifies the current branch and sets:
- `branch_subdir`: The subdirectory for non-main branches (empty for main)
- `public_base_url`: The full URL where reports will be accessible

```bash
if [ "${{ github.ref }}" = "refs/heads/dev" ]; then
  echo "branch_subdir=dev"
  echo "public_base_url=https://curtcox.github.io/Viewer/dev"
elif [ "${{ github.ref }}" = "refs/heads/test" ]; then
  echo "branch_subdir=test"
  echo "public_base_url=https://curtcox.github.io/Viewer/test"
else
  echo "branch_subdir="
  echo "public_base_url=https://curtcox.github.io/Viewer"
fi
```

### Artifact-Based Content Preservation

The workflow uses branch-specific artifacts to ensure content from all branches is preserved:

#### How It Works
1. **Upload branch artifact**: Each branch uploads its reports as a named artifact (`github-pages-main`, `github-pages-dev`, or `github-pages-test`)
2. **Download all artifacts**: Before deploying, the workflow downloads the latest artifacts from all branches using `dawidd6/action-download-artifact`
3. **Combine artifacts**: All artifacts are combined into a single site structure:
   - Main branch content at root
   - Dev branch content in `/dev/`
   - Test branch content in `/test/`
4. **Deploy combined site**: The complete site is deployed to GitHub Pages

#### Key Features
- **Artifact persistence**: Branch artifacts are retained for 90 days, ensuring content survives even if a branch hasn't been built recently
- **Cross-run downloads**: Uses `dawidd6/action-download-artifact` to fetch artifacts from previous workflow runs on other branches
- **Current branch priority**: The current branch's content always takes precedence over downloaded artifacts
- **Graceful degradation**: Missing artifacts are ignored, allowing the first builds to succeed

### URL Structure

After deployment, reports are accessible at:
- Production: `https://curtcox.github.io/Viewer/`
- Development: `https://curtcox.github.io/Viewer/dev/`
- Testing: `https://curtcox.github.io/Viewer/test/`

Each URL provides the full test report site with all checks, coverage, and test results for that branch.

## Internal Links

The `public_base_url` parameter is passed to `build-report-site.py`, which uses it to generate correct internal links within reports (e.g., for Gauge screenshots and artifacts).

## Deployment Conditions

Reports are only deployed when:
- The workflow completes (all jobs run, even if some fail)
- The event is a push (not a pull request or manual trigger)
- The branch is one of: `main`, `dev`, or `test`

## Testing the Setup

To test this setup:

1. Create the `dev` and `test` branches if they don't exist:
   ```bash
   git checkout -b dev
   git push origin dev
   
   git checkout -b test
   git push origin test
   ```

2. Push changes to each branch:
   ```bash
   # Make changes and push to dev
   git checkout dev
   # ... make changes ...
   git push origin dev
   
   # Make changes and push to test
   git checkout test
   # ... make changes ...
   git push origin test
   
   # Make changes and push to main
   git checkout main
   # ... make changes ...
   git push origin main
   ```

3. Monitor the Actions tab to see the workflow run for each branch

4. Once deployed, verify the reports at:
   - https://curtcox.github.io/Viewer/
   - https://curtcox.github.io/Viewer/dev/
   - https://curtcox.github.io/Viewer/test/

## Troubleshooting

### Reports Not Appearing in Subdirectory

If dev/test reports don't appear in their subdirectories:
1. Check the workflow logs for the "Download dev/test branch artifact" steps
2. Verify the branch has been built at least once to create its artifact
3. Check that the artifact name matches (`github-pages-dev` or `github-pages-test`)

### Existing Content Being Overwritten

If content from other branches is being lost:
1. Check the "Download main/dev/test branch artifact" steps in the workflow logs
2. Verify artifacts exist in the Actions tab under the respective branch's workflow runs
3. Ensure the concurrency control (`group: github-pages`) is preventing race conditions
4. Check the "Verify combined site content" step to see what content was included

### Artifacts Not Found

If artifact downloads are failing:
1. The branch may not have been built yet - push a change to trigger a build
2. Artifacts expire after 90 days - rebuild the branch if artifacts have expired
3. Check that the workflow name in `dawidd6/action-download-artifact` matches (`full-checks.yml`)

### Links Not Working

If internal links in reports are broken:
1. Verify the `PUBLIC_BASE_URL` environment variable is set correctly
2. Check that `build-report-site.py` is using the `--public-base-url` parameter
3. Review the generated HTML to ensure paths are correct

## Future Enhancements

Potential improvements to this setup:
- Add a landing page with links to all branch reports
- Include branch name and last update time in reports
- Add cleanup logic to remove reports from deleted branches
- Support additional environment branches (staging, qa, etc.)
