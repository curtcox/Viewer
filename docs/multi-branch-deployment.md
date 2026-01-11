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

### Content Preservation with peaceiris/actions-gh-pages

The workflow uses [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages) with the `keep_files: true` option to preserve content from other branches:

#### How It Works
1. **Main branch**: Deploys reports to the root of the `gh-pages` branch
2. **Dev/Test branches**: Deploy reports to their respective subdirectories using `destination_dir`
3. **Preservation**: The `keep_files: true` option ensures existing files are not deleted, only updated

#### Key Features
- **Automatic content preservation**: The action handles merging automatically by only updating files in the target directory
- **No manual downloading**: Unlike previous approaches, no need to download and merge existing content
- **Atomic updates**: Each branch only touches its own directory, preventing conflicts

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
1. Check the workflow logs for the "Deploy to GitHub Pages" step
2. Verify the branch detection is working correctly in the "Determine deployment path" step
3. Ensure the `gh-pages` branch exists (the action will create it on first deployment)

### Existing Content Being Overwritten

The `peaceiris/actions-gh-pages` action with `keep_files: true` should preserve content from other branches. If content is still being overwritten:
1. Verify `keep_files: true` is set in the deployment step
2. Check that `destination_dir` is correctly set for dev/test branches
3. Ensure the concurrency control (`group: github-pages`) is preventing race conditions

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
