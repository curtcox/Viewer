#!/usr/bin/env python3
"""
Demonstration script for JSON API Gateway functionality.

This script shows how the JSON API Gateway transforms JSON responses
into HTML with syntax highlighting and clickable links.
"""

import json
from reference_templates.gateways.transforms.json_api_response import (
    _format_json_with_links,
    _detect_id_reference_link,
    _detect_full_url_link,
    _build_breadcrumb
)


def demo_basic_json_rendering():
    """Demonstrate basic JSON rendering with syntax highlighting."""
    print("=" * 60)
    print("DEMO 1: Basic JSON Rendering")
    print("=" * 60)
    
    test_json = {
        "id": 1,
        "name": "Test User",
        "age": 30,
        "active": True,
        "notes": None
    }
    
    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {"enabled": False}
    }
    
    formatted = _format_json_with_links(test_json, link_config, "", 0)
    print("\nInput JSON:")
    print(json.dumps(test_json, indent=2))
    print("\nFormatted HTML (excerpt):")
    print(formatted[:500] + "...")
    print()


def demo_id_reference_detection():
    """Demonstrate ID reference detection and linking."""
    print("=" * 60)
    print("DEMO 2: ID Reference Detection")
    print("=" * 60)
    
    link_config = {
        "full_url": {"enabled": False},
        "id_reference": {
            "enabled": True,
            "patterns": {
                "userId": "/gateway/json_api/users/{id}",
                "postId": "/gateway/json_api/posts/{id}",
                "albumId": "/gateway/json_api/albums/{id}"
            }
        }
    }
    
    test_json = {
        "id": 1,
        "title": "My First Post",
        "userId": 5,
        "body": "This is a test post",
        "postId": 10
    }
    
    formatted = _format_json_with_links(test_json, link_config, "", 0)
    print("\nInput JSON:")
    print(json.dumps(test_json, indent=2))
    print("\nDetected Links:")
    print("- userId (5) → /gateway/json_api/users/5")
    print("- postId (10) → /gateway/json_api/posts/10")
    print()


def demo_full_url_detection():
    """Demonstrate full URL detection with base stripping."""
    print("=" * 60)
    print("DEMO 3: Full URL Detection")
    print("=" * 60)
    
    link_config = {
        "full_url": {
            "enabled": True,
            "base_url_strip": "https://jsonplaceholder.typicode.com",
            "gateway_prefix": "/gateway/json_api"
        },
        "id_reference": {"enabled": False}
    }
    
    test_json = {
        "id": 1,
        "name": "Test User",
        "profile_url": "https://jsonplaceholder.typicode.com/users/1/profile",
        "avatar_url": "https://example.com/avatars/user1.jpg"
    }
    
    formatted = _format_json_with_links(test_json, link_config, "", 0)
    print("\nInput JSON:")
    print(json.dumps(test_json, indent=2))
    print("\nDetected Links:")
    print("- profile_url → /gateway/json_api/users/1/profile (base stripped)")
    print("- avatar_url → https://example.com/avatars/user1.jpg (external URL)")
    print()


def demo_combined_detection():
    """Demonstrate combined ID and URL detection."""
    print("=" * 60)
    print("DEMO 4: Combined Detection (IDs + URLs)")
    print("=" * 60)
    
    link_config = {
        "full_url": {
            "enabled": True,
            "base_url_strip": "https://api.example.com",
            "gateway_prefix": "/gateway/json_api"
        },
        "id_reference": {
            "enabled": True,
            "patterns": {
                "userId": "/gateway/json_api/users/{id}",
                "postId": "/gateway/json_api/posts/{id}"
            }
        }
    }
    
    test_json = {
        "id": 42,
        "title": "My Post",
        "userId": 7,
        "author_url": "https://api.example.com/users/7",
        "comments_url": "https://api.example.com/posts/42/comments"
    }
    
    formatted = _format_json_with_links(test_json, link_config, "", 0)
    print("\nInput JSON:")
    print(json.dumps(test_json, indent=2))
    print("\nDetected Links:")
    print("- userId (7) → /gateway/json_api/users/7")
    print("- author_url → /gateway/json_api/users/7")
    print("- comments_url → /gateway/json_api/posts/42/comments")
    print()


def demo_breadcrumb():
    """Demonstrate breadcrumb generation."""
    print("=" * 60)
    print("DEMO 5: Breadcrumb Navigation")
    print("=" * 60)
    
    examples = [
        ("", "Root path"),
        ("posts", "Single level"),
        ("posts/1", "Two levels"),
        ("users/1/posts/5", "Multiple levels"),
    ]
    
    for path, description in examples:
        breadcrumb = _build_breadcrumb(path, "json_api")
        print(f"\nPath: /{path} ({description})")
        print(f"Breadcrumb HTML: {breadcrumb}")
    print()


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         JSON API Gateway Demonstration                   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    
    demo_basic_json_rendering()
    demo_id_reference_detection()
    demo_full_url_detection()
    demo_combined_detection()
    demo_breadcrumb()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\nThe JSON API Gateway provides:")
    print("✓ Syntax highlighting for JSON responses")
    print("✓ Automatic detection and linking of ID references")
    print("✓ Full URL detection with base URL stripping")
    print("✓ Breadcrumb navigation")
    print("✓ Support for nested objects and arrays")
    print("✓ Configurable link detection patterns")
    print()
    print("Configuration is done via gateways.source.json")
    print("See tests/test_json_api_gateway.py for more examples")
    print()


if __name__ == "__main__":
    main()
