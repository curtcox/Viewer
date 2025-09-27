#!/usr/bin/env python3
"""Debug script to examine actual error page HTML output."""

from app import create_app
from database import db

def debug_error_page():
    """Generate and examine error page HTML."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
    })
    
    with app.app_context():
        db.create_all()
        
        with app.test_request_context('/debug-error'):
            try:
                # Import some project modules to get them in traceback
                from routes.core import _build_stack_trace
                from routes.source import _get_comprehensive_paths
                from routes.aliases import _alias_name_conflicts_with_routes
                
                # Create an error with a good traceback
                raise RuntimeError('Debug error for examining HTML output')
            except RuntimeError as exc:
                from routes.core import internal_error
                html_content, status_code = internal_error(exc)
                
                print(f"Status Code: {status_code}")
                print("=" * 80)
                print("HTML Content:")
                print("=" * 80)
                print(html_content)
                print("=" * 80)
                
                # Check for specific elements
                print("\nChecking for specific elements:")
                print(f"Contains 'RuntimeError': {'RuntimeError' in html_content}")
                print(f"Contains 'Debug error': {'Debug error' in html_content}")
                print(f"Contains 'href=\"/source/': {'href=\"/source/' in html_content}")
                print(f"Contains '>>>': {'>>>' in html_content}")
                print(f"Contains 'Stack trace': {'Stack trace' in html_content}")
                print(f"Contains 'target=\"_blank\"': {'target=\"_blank\"' in html_content}")
                
                # Look for source links
                import re
                source_links = re.findall(r'href="/source/([^"]+)"', html_content)
                print(f"\nFound {len(source_links)} source links:")
                for link in source_links:
                    print(f"  - /source/{link}")

if __name__ == '__main__':
    debug_error_page()
