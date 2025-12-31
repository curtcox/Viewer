# HRX Gateway Template Externalization Plan

## Overview

The HRX gateway is the last gateway requiring template externalization. It presents unique challenges due to its multi-format rendering capabilities (HTML, markdown, CSS, directory listings, text files). This document outlines a focused plan to externalize HRX templates while maintaining its sophisticated rendering features.

## Current State

**File:** `reference_templates/gateways/transforms/hrx_response.py` (311 lines)

**Rendering Functions:**
1. `_render_error_page()` - Error pages for 404s and failures
2. `_render_directory()` - Directory/file listing navigation
3. `_render_markdown()` - Markdown files converted to styled HTML
4. `_render_text_file()` - Plain text/code files in viewer

**Helper Functions:**
1. `_fix_relative_urls()` - Fixes relative URLs in HTML files
2. `_fix_css_urls()` - Fixes relative URLs in CSS files
3. `_parse_file_list()` - Parses file list text into structured data
4. `_get_parent_path()` - Navigation helper

## Challenges

1. **Multi-format Output**: Unlike other gateways which produce single output formats, HRX produces:
   - HTML pages (error, directory, markdown viewer, text viewer)
   - Raw CSS (with URL fixing)
   - Raw HTML (with URL fixing)
   - Binary passthrough

2. **Complex URL Rewriting**: Relative URLs must be rewritten to absolute paths including the archive CID

3. **Markdown Rendering**: Uses external Markdown library with custom styling

4. **Syntax Highlighting**: Text file viewer may benefit from syntax highlighting

## Proposed Approach

### Phase 1: Extract Templates (2-3 hours)

Create 4 external Jinja2 templates:

**1. hrx_error.html**
```
Error page template with:
- Archive CID and file path context
- Error message display
- Navigation back to archive root
- Consistent styling with gateway theme
```

**2. hrx_directory.html**
```
Directory listing template with:
- Current path breadcrumb navigation
- File/folder list with icons
- Parent directory link
- File size and type indicators
```

**3. hrx_markdown.html**
```
Markdown viewer template with:
- Rendered markdown content
- Archive navigation
- Syntax highlighting for code blocks
- GitHub-flavored markdown styling
```

**4. hrx_text.html**
```
Text/code file viewer template with:
- Syntax-highlighted code display
- Line numbers
- Archive navigation
- Download/raw view links
```

### Phase 2: Refactor Transform (2-3 hours)

**Update `hrx_response.py`:**

1. Add resolve_template calls at top of each render function
2. Move inline HTML to template variables
3. Preserve all URL fixing logic (keep as helper functions)
4. Maintain binary/CSS/raw HTML passthrough unchanged

**Example Pattern:**
```python
def _render_error_page(archive_cid: str, file_path: str, message: str, context: dict) -> str:
    resolve_template = context.get("resolve_template")
    if not resolve_template:
        raise RuntimeError("resolve_template not available - templates must be configured")
    
    template = resolve_template("hrx_error.html")
    return template.render(
        archive_cid=archive_cid,
        file_path=file_path,
        message=message,
    )
```

### Phase 3: Update Configuration (30 minutes)

**Update `gateways.json`:**
```json
{
  "hrx": {
    "description": "HRX archive viewer with markdown and code highlighting",
    "response_transform_cid": "AAAAA...",
    "templates": {
      "hrx_error.html": "AAAAA...",
      "hrx_directory.html": "AAAAA...",
      "hrx_markdown.html": "AAAAA...",
      "hrx_text.html": "AAAAA..."
    }
  }
}
```

### Phase 4: Testing (1-2 hours)

**Unit Tests:**
```python
def test_hrx_transform_uses_external_templates():
    """HRX transform should load templates via resolve_template."""
    # Verify each template is loaded and rendered correctly
    pass

def test_hrx_transform_requires_templates():
    """HRX transform should raise error if templates not configured."""
    pass

def test_hrx_url_fixing_preserved():
    """URL fixing logic should work with external templates."""
    pass

def test_hrx_markdown_rendering():
    """Markdown rendering should work with external template."""
    pass
```

**Integration Tests:**
```python
def test_hrx_gateway_end_to_end():
    """Full integration test for HRX gateway with templates."""
    # Test directory listing, markdown file, text file, error page
    pass
```

**Manual Testing Checklist:**
- [ ] Visit HRX archive directory listing
- [ ] View markdown file in archive
- [ ] View HTML file with relative URLs
- [ ] View CSS file with relative URLs
- [ ] View text/code file
- [ ] Trigger 404 error
- [ ] Verify all navigation works
- [ ] Check URL fixing in HTML/CSS

## Implementation Strategy

### Conservative Approach (Recommended)

1. **Start with error template**: Simplest case, lowest risk
2. **Move to directory template**: More complex but isolated
3. **Handle text viewer**: Moderate complexity
4. **Finish with markdown**: Most complex due to Markdown library integration

### Key Principles

- **Preserve all existing functionality**: No feature regressions
- **Maintain URL fixing logic**: Keep as helper functions, pass results to templates
- **Test incrementally**: After each template extraction
- **Keep templates focused**: One template per rendering mode

## Complexity Assessment

**Estimated Effort:** 6-8 hours total development time

**Risk Factors:**
- Medium: URL rewriting logic must work with external templates
- Low: Markdown rendering already uses library, just needs template wrapper
- Low: Template structure is well-established from other gateways

**Why This Warrants a Separate Plan:**
1. Multi-format rendering (4 different output types)
2. Complex URL rewriting requirements
3. Integration with external Markdown library
4. Largest transform codebase (311 lines)
5. Most sophisticated gateway in the system

## Success Criteria

- [ ] All 4 HRX templates externalized to separate files
- [ ] All templates stored in CID storage and referenced in config
- [ ] URL fixing logic preserved and working
- [ ] Markdown rendering quality unchanged
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Manual testing checklist complete
- [ ] No performance regressions
- [ ] Meta page shows HRX template information correctly

## Timeline

- **Phase 1**: 2-3 hours (template creation)
- **Phase 2**: 2-3 hours (transform refactoring)
- **Phase 3**: 30 minutes (configuration)
- **Phase 4**: 1-2 hours (testing)
- **Total**: 6-8 hours for complete implementation

## Dependencies

- Existing template infrastructure (from Phases 1-3) ✅
- Template resolver function ✅
- Meta page template validation ✅
- No new dependencies required

## Notes

This work was deferred from the main gateway enhancement effort due to its complexity. The infrastructure built in Phases 1-3 makes this externalization straightforward, but the multi-format nature and URL rewriting requirements warrant careful attention and dedicated focus.

The plan can be executed as a standalone task or broken into smaller incremental steps (one template at a time) for easier review and validation.
