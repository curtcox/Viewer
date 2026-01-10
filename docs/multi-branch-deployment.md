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

### Content Merging (Overlay Approach)

**All branches now preserve content from other branches using an overlay approach:**

#### Main Branch Deployment
1. **Downloads existing GitHub Pages content**: Retrieves the current `gh-pages` branch
2. **Preserves all subdirectories**: Copies all existing content including `dev/` and `test/` subdirectories
3. **Updates root content**: Overwrites root-level files with new main branch reports
4. **Deploys merged content**: Uploads the complete site with main reports at root and preserved subdirectories

#### Dev/Test Branch Deployment
1. **Downloads existing GitHub Pages content**: Retrieves the current `gh-pages` branch
2. **Preserves other branch content**: Copies all content except the subdirectory being updated
3. **Updates branch subdirectory**: Places new reports in the appropriate subdirectory (`dev/` or `test/`)
4. **Deploys merged content**: Uploads the complete site with all branch reports preserved

**Key Difference from Previous Behavior**: The main branch now explicitly preserves the `dev/` and `test/` subdirectories instead of erasing them. This ensures that builds from any branch overlay and coexist with builds from other branches.

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
1. Check the workflow logs for the "Organize site for branch deployment" step
2. Verify the branch detection is working correctly
3. Ensure the `gh-pages` branch exists and is accessible

### Existing Content Being Overwritten

**This issue has been fixed in the current implementation.** All branches now preserve content from other branches:
- Main branch preserves `dev/` and `test/` subdirectories
- Dev branch preserves root content and `test/` subdirectory
- Test branch preserves root content and `dev/` subdirectory

If content is still being overwritten:
1. Check the "Download existing GitHub Pages" step runs for **all branches** (not just subdirectories)
2. Verify the rsync command uses the correct exclude logic:
   - Main: No exclusions (preserves all subdirectories)
   - Dev: Excludes only `dev/`
   - Test: Excludes only `test/`
3. Check that the merge logic in "Organize site for branch deployment" handles both main and branch deployments correctly

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
