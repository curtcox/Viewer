#!/usr/bin/env python3
"""Generate HTML reports for AI evaluation tests.

This script reads AI interaction JSON files and test source files,
then generates an index page and detail pages for each test.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer


# Constants
MAX_DOC_LENGTH = 100  # Maximum length for test description in index page


def load_interaction_file(json_path: Path) -> Optional[Dict]:
    """Load and parse an AI interaction JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load {json_path}: {e}", file=sys.stderr)
        return None


def load_test_source(test_file_path: str) -> Optional[str]:
    """Load the source code of a test file."""
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        print(f"Warning: Could not load test source {test_file_path}: {e}", file=sys.stderr)
        return None


def highlight_python_code(code: str) -> tuple[str, str]:
    """Return syntax-highlighted HTML and CSS for Python code."""
    formatter = HtmlFormatter(style='friendly', linenos='inline', cssclass='source')
    highlighted = highlight(code, PythonLexer(), formatter)
    css = formatter.get_style_defs('.source')
    return highlighted, css


def format_json(data: dict, max_length: int = 1000) -> str:
    """Format JSON data for display, with truncation if too long."""
    formatted = json.dumps(data, indent=2)
    if len(formatted) > max_length:
        formatted = formatted[:max_length] + '\n... (truncated)'
    return formatted


def generate_detail_page(interaction_data: Dict, output_path: Path) -> None:
    """Generate a detail page for a single test."""
    test_name = interaction_data.get('test_name', 'Unknown')
    test_doc = interaction_data.get('test_doc', '')
    test_file_path = interaction_data.get('test_file_path', '')
    interactions = interaction_data.get('interactions', [])
    passed = interaction_data.get('passed', False)
    failed = interaction_data.get('failed', False)
    
    # Load and highlight test source
    source_code = load_test_source(test_file_path) if test_file_path else None
    if source_code:
        highlighted_source, syntax_css = highlight_python_code(source_code)
    else:
        highlighted_source, syntax_css = None, None
    
    # Determine status badge
    if passed:
        status_badge = '<span class="badge badge-success">✓ PASSED</span>'
    elif failed:
        status_badge = '<span class="badge badge-failed">✗ FAILED</span>'
    else:
        status_badge = '<span class="badge badge-unknown">? UNKNOWN</span>'
    
    # Build interactions HTML
    interactions_html = []
    for idx, interaction in enumerate(interactions, 1):
        request = interaction.get('request', {})
        response = interaction.get('response', {})
        status = interaction.get('status', 'N/A')
        timestamp = interaction.get('timestamp', 'N/A')
        
        # Format request
        request_text = request.get('request_text', '')
        original_text = request.get('original_text', '')
        target_label = request.get('target_label', '')
        
        # Format response
        updated_text = response.get('updated_text', '')
        error = response.get('error', '')
        
        interaction_html = f"""
        <div class="interaction">
            <h3>Interaction {idx}</h3>
            <p class="timestamp">Timestamp: {timestamp}</p>
            <p class="status">HTTP Status: {status}</p>
            
            <h4>Request</h4>
            <div class="request-details">
                <p><strong>Target:</strong> {target_label}</p>
                <p><strong>Request Text:</strong></p>
                <pre class="request-text">{request_text}</pre>
                {f'<p><strong>Original Text:</strong></p><pre class="original-text">{original_text}</pre>' if original_text else ''}
            </div>
            
            <h4>Response</h4>
            <div class="response-details">
                {f'<p class="error"><strong>Error:</strong> {error}</p>' if error else ''}
                {f'<p><strong>Updated Text:</strong></p><pre class="updated-text">{updated_text}</pre>' if updated_text else ''}
            </div>
        </div>
        """
        interactions_html.append(interaction_html)
    
    interactions_section = '\n'.join(interactions_html) if interactions_html else '<p class="no-interactions">No interactions recorded</p>'
    
    # Generate HTML page
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{test_name} - AI Eval Test</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; line-height: 1.6; background: #f6f8fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h1 {{ color: #24292e; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #24292e; margin-top: 30px; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; }}
        h3 {{ color: #586069; margin-top: 20px; }}
        h4 {{ color: #6a737d; margin-top: 15px; margin-bottom: 10px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 14px; font-weight: 600; }}
        .badge-success {{ background: #28a745; color: white; }}
        .badge-failed {{ background: #d73a49; color: white; }}
        .badge-unknown {{ background: #6a737d; color: white; }}
        .test-info {{ background: #f6f8fa; padding: 15px; border-radius: 6px; margin: 20px 0; }}
        .test-info p {{ margin: 5px 0; }}
        .back-link {{ display: inline-block; margin-bottom: 20px; color: #0366d6; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
        pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; border: 1px solid #e1e4e8; }}
        .source {{ background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 10px; margin: 15px 0; overflow-x: auto; }}
        .interaction {{ background: #ffffff; border: 1px solid #e1e4e8; border-radius: 6px; padding: 20px; margin: 20px 0; }}
        .request-details, .response-details {{ margin: 10px 0; }}
        .request-text, .original-text, .updated-text {{ background: #f6f8fa; padding: 10px; border-left: 3px solid #0366d6; }}
        .error {{ color: #d73a49; font-weight: 600; }}
        .timestamp, .status {{ color: #586069; font-size: 14px; }}
        .no-interactions {{ color: #6a737d; font-style: italic; padding: 20px; text-align: center; }}
        {syntax_css if syntax_css else ''}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">← Back to Index</a>
        
        <h1>{test_name} {status_badge}</h1>
        
        {f'<div class="test-info"><p><strong>Description:</strong> {test_doc}</p></div>' if test_doc else ''}
        
        <h2>Test Source Code</h2>
        {highlighted_source if highlighted_source else '<p class="no-interactions">Source code not available</p>'}
        
        <h2>AI Interactions</h2>
        {interactions_section}
    </div>
</body>
</html>"""
    
    # Write the HTML file
    output_path.write_text(html, encoding='utf-8')
    print(f"Generated detail page: {output_path}")


def generate_index_page(interaction_files: List[Path], output_path: Path) -> None:
    """Generate the index page listing all AI eval tests."""
    
    # Load all interaction data
    tests = []
    for json_file in sorted(interaction_files):
        data = load_interaction_file(json_file)
        if data:
            tests.append({
                'name': data.get('test_name', json_file.stem),
                'doc': data.get('test_doc', ''),
                'file': data.get('test_file', ''),
                'passed': data.get('passed', False),
                'failed': data.get('failed', False),
                'detail_page': f"{json_file.stem}.html"
            })
    
    # Build test list HTML
    test_items = []
    for test in tests:
        if test['passed']:
            status_icon = '✓'
            status_class = 'status-pass'
        elif test['failed']:
            status_icon = '✗'
            status_class = 'status-fail'
        else:
            status_icon = '?'
            status_class = 'status-unknown'
        
        doc_text = test['doc'][:MAX_DOC_LENGTH] + '...' if len(test['doc']) > MAX_DOC_LENGTH else test['doc']
        
        test_item = f"""
        <li class="test-item">
            <span class="status-icon {status_class}">{status_icon}</span>
            <div class="test-details">
                <a href="{test['detail_page']}" class="test-name">{test['name']}</a>
                {f'<p class="test-description">{doc_text}</p>' if doc_text else ''}
            </div>
        </li>
        """
        test_items.append(test_item)
    
    test_list = '\n'.join(test_items) if test_items else '<p class="no-tests">No tests found</p>'
    
    # Count stats
    total = len(tests)
    passed = sum(1 for t in tests if t['passed'])
    failed = sum(1 for t in tests if t['failed'])
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>AI Eval Tests - Index</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; line-height: 1.6; background: #f6f8fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h1 {{ color: #24292e; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ background: #f6f8fa; padding: 15px 20px; border-radius: 6px; flex: 1; text-align: center; }}
        .stat-number {{ font-size: 32px; font-weight: bold; }}
        .stat-label {{ color: #586069; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .stat-pass .stat-number {{ color: #28a745; }}
        .stat-fail .stat-number {{ color: #d73a49; }}
        .stat-total .stat-number {{ color: #0366d6; }}
        .test-list {{ list-style: none; padding: 0; margin: 20px 0; }}
        .test-item {{ display: flex; align-items: center; gap: 15px; padding: 15px; margin: 10px 0; background: #f6f8fa; border-radius: 6px; border-left: 4px solid #e1e4e8; }}
        .test-item:hover {{ background: #e1e4e8; }}
        .status-icon {{ font-size: 24px; font-weight: bold; width: 30px; text-align: center; }}
        .status-pass {{ color: #28a745; }}
        .status-fail {{ color: #d73a49; }}
        .status-unknown {{ color: #6a737d; }}
        .test-details {{ flex: 1; }}
        .test-name {{ color: #0366d6; text-decoration: none; font-weight: 600; font-size: 16px; }}
        .test-name:hover {{ text-decoration: underline; }}
        .test-description {{ color: #586069; font-size: 14px; margin: 5px 0 0 0; }}
        .no-tests {{ text-align: center; padding: 40px; color: #6a737d; font-style: italic; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Evaluation Tests</h1>
        
        <div class="stats">
            <div class="stat stat-total">
                <div class="stat-number">{total}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat stat-pass">
                <div class="stat-number">{passed}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat stat-fail">
                <div class="stat-number">{failed}</div>
                <div class="stat-label">Failed</div>
            </div>
        </div>
        
        <h2>Test Cases</h2>
        <ul class="test-list">
            {test_list}
        </ul>
    </div>
</body>
</html>"""
    
    # Write the HTML file
    output_path.write_text(html, encoding='utf-8')
    print(f"Generated index page: {output_path}")


def main():
    """Main entry point for the script."""
    # Paths
    interactions_dir = Path('test-results/ai-interactions')
    output_dir = Path('test-results/ai-eval-reports')
    
    # Check if interactions directory exists
    if not interactions_dir.exists():
        print(f"Error: Interactions directory not found: {interactions_dir}", file=sys.stderr)
        print("Run the AI eval tests first to generate interaction data.", file=sys.stderr)
        return 1
    
    # Find all interaction JSON files
    json_files = list(interactions_dir.glob('*.json'))
    if not json_files:
        print(f"Warning: No interaction JSON files found in {interactions_dir}", file=sys.stderr)
        return 1
    
    print(f"Found {len(json_files)} test interaction files")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate detail pages for each test
    for json_file in json_files:
        interaction_data = load_interaction_file(json_file)
        if interaction_data:
            detail_page = output_dir / f"{json_file.stem}.html"
            generate_detail_page(interaction_data, detail_page)
    
    # Generate index page
    index_page = output_dir / 'index.html'
    generate_index_page(json_files, index_page)
    
    print("\n✓ Report generation complete!")
    print(f"  Index: {index_page}")
    print("  View via source browser at: /source/test-results/ai-eval-reports/index.html")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
