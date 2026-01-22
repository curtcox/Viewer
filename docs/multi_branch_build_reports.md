# Multi-Branch Build Report Artifacts and GitHub Pages

## Overview

This implementation adds support for creating branch-specific build report archives and displaying a unified top-level index page that links to all branch reports with visual status indicators.

## Changes Made

### 1. New Script: `scripts/generate_branch_index.py`

A Python script that generates the top-level index page for GitHub Pages. It:
- Reads job status JSON files from all three branches (main, dev, test)
- Counts successful vs. total jobs for each branch
- Generates a clean HTML page with:
  - Color-coded status indicators (green for success, red for failures)
  - Visual check marks (✓) and X marks (✖)
  - Clickable links to each branch's detailed reports
  - Status summary showing "X out of Y jobs successful"

**Testing**: Comprehensive test suite in `tests/test_generate_branch_index.py` with 9 passing tests.

**Validation**: Passes both `ruff` (linter) and `mypy` (type checker).

### 2. Workflow Updates: `.github/workflows/full-checks.yml`

Added new steps to the `deploy-github-pages` job:

#### Build Report Archives
```yaml
- name: Create build report archive
  # Creates branch-specific zip archives (main_build_report.zip, dev_build_report.zip, test_build_report.zip)
  
- name: Upload build report archive
  # Uploads archives as GitHub Actions artifacts with 90-day retention
```

#### Top-Level Index Generation
```yaml
- name: Download job statuses from all branches
  # Extracts job-statuses.json from each branch's site content
  
- name: Generate top-level index
  # Runs generate_branch_index.py to create the unified landing page
```

### 3. Script Update: `scripts/ci/prepare_report_site.sh`

Modified to copy `job-statuses.json` into the site directory so it can be:
- Included in the branch-specific GitHub Pages artifacts
- Extracted later to generate the top-level index

## How It Works

### Workflow Execution

1. **Job runs on push to main, dev, or test branches**
   - All CI checks execute (linters, tests, etc.)
   - Job statuses are captured to `job-statuses.json`

2. **Site preparation**
   - `prepare_report_site.sh` builds the site content
   - Copies `job-statuses.json` into the site directory

3. **Archive creation**
   - Site content is zipped into `{branch}_build_report.zip`
   - Archive is uploaded as a GitHub Actions artifact

4. **Branch artifact creation**
   - Site content is uploaded as `github-pages-{branch}`
   - Used for combining all branches before deployment

5. **Combine and deploy**
   - Downloads artifacts from all three branches
   - Extracts `job-statuses.json` from each branch
   - Generates top-level `index.html` with branch summaries
   - Deploys combined site to GitHub Pages

### GitHub Pages Structure

```
https://curtcox.github.io/Viewer/
├── index.html              # Top-level index with branch summary
├── job-statuses.json       # Main branch job statuses
├── unit-tests-results/     # Main branch test results
├── gauge-specs/            # Main branch Gauge reports
├── ...                     # Other main branch reports
├── dev/
│   ├── index.html          # Dev branch landing page
│   ├── job-statuses.json   # Dev branch job statuses
│   ├── unit-tests-results/ # Dev branch test results
│   └── ...                 # Other dev branch reports
└── test/
    ├── index.html          # Test branch landing page
    ├── job-statuses.json   # Test branch job statuses
    ├── unit-tests-results/ # Test branch test results
    └── ...                 # Other test branch reports
```

### Artifacts Structure

GitHub Actions creates these artifacts for each branch:

1. **Build Report Archives** (90-day retention):
   - `main_build_report` (contains `main_build_report.zip`)
   - `dev_build_report` (contains `dev_build_report.zip`)
   - `test_build_report` (contains `test_build_report.zip`)

2. **GitHub Pages Artifacts** (90-day retention):
   - `github-pages-main`
   - `github-pages-dev`
   - `github-pages-test`

## User Experience

### Top-Level Index Page

When users visit `https://curtcox.github.io/Viewer/`, they see:

1. **Page Title**: "SecureApp CI Reports"
2. **Subtitle**: "Comprehensive test and quality reports across all active branches"
3. **Branch Cards**: Interactive cards for each branch showing:
   - Visual status indicator (✓ or ✖)
   - Branch name (clickable)
   - Job success rate ("X out of Y jobs successful")
   - Color coding (green for success, red for failures)

### Navigation Flow

```
User visits root page (index.html)
    ↓
Sees branch summary cards
    ↓
Clicks on a branch (e.g., "Dev Branch")
    ↓
Views dev branch landing page (dev/index.html)
    ↓
Can explore detailed reports (dev/unit-tests-results/, etc.)
```

## Benefits

1. **Better Visibility**: Single page shows status of all branches at a glance
2. **Downloadable Archives**: Build reports available as zip files
3. **Historical Access**: Artifacts retained for 90 days
4. **Clear Status Indicators**: Visual feedback (✓/✖) and color coding
5. **Easy Navigation**: Clear links to detailed reports for each branch
6. **Automated**: No manual intervention required

## Testing

Run tests locally:
```bash
source venv/bin/activate
python -m pytest tests/test_generate_branch_index.py -v
```

Generate a preview locally:
```bash
# Create sample status files
cat > /tmp/main-statuses.json << EOF
{"job1": "success", "job2": "failure", "job3": "success"}
EOF

# Generate index
python scripts/generate_branch_index.py \
  --output /tmp/preview/index.html \
  --main-statuses /tmp/main-statuses.json

# Open in browser
open /tmp/preview/index.html
```

## Future Enhancements

Possible improvements:
- Add timestamp of last update for each branch
- Show trends (improving/degrading)
- Add direct links to failing jobs
- Display commit SHA and message for each branch
- Add branch comparison features
