#!/usr/bin/env python3
"""Simple demonstration of read-only mode functionality."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from db_config import DatabaseConfig, DatabaseMode
from readonly_config import ReadOnlyConfig


def demo_normal_mode():
    """Demonstrate normal mode allows state changes."""
    print("\n" + "=" * 60)
    print("DEMO: Normal Mode")
    print("=" * 60)
    
    DatabaseConfig.reset()
    ReadOnlyConfig.reset()
    DatabaseConfig.set_mode(DatabaseMode.MEMORY)
    
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    print("Testing POST request to create a server...")
    response = client.post("/servers/new", data={
        "name": "test_server",
        "definition": "def main(): pass"
    })
    
    print(f"Status code: {response.status_code}")
    if response.status_code == 405:
        print("❌ BLOCKED (unexpected in normal mode)")
    else:
        print("✅ ALLOWED (expected in normal mode)")


def demo_readonly_mode():
    """Demonstrate read-only mode blocks state changes."""
    print("\n" + "=" * 60)
    print("DEMO: Read-Only Mode")
    print("=" * 60)
    
    DatabaseConfig.reset()
    ReadOnlyConfig.reset()
    ReadOnlyConfig.set_read_only_mode(True)
    DatabaseConfig.set_mode(DatabaseMode.MEMORY)
    
    app = create_app({"TESTING": True})
    client = app.test_client()
    
    print("Testing POST request to create a server...")
    response = client.post("/servers/new", data={
        "name": "test_server",
        "definition": "def main(): pass"
    })
    
    print(f"Status code: {response.status_code}")
    if response.status_code == 405:
        print("✅ BLOCKED (expected in read-only mode)")
        if b"not allowed in read-only mode" in response.data.lower():
            print("✅ Correct error message")
    else:
        print("❌ ALLOWED (unexpected in read-only mode)")
    
    print("\nTesting GET request to list servers...")
    response = client.get("/servers")
    print(f"Status code: {response.status_code}")
    if response.status_code in (200, 302, 303):
        print("✅ ALLOWED (expected in read-only mode)")
    else:
        print("❌ BLOCKED (unexpected in read-only mode)")


def demo_memory_limits():
    """Demonstrate CID memory limits."""
    print("\n" + "=" * 60)
    print("DEMO: CID Memory Limits")
    print("=" * 60)
    
    DatabaseConfig.reset()
    ReadOnlyConfig.reset()
    ReadOnlyConfig.set_read_only_mode(True)
    ReadOnlyConfig.set_max_cid_memory(100)  # 100 bytes
    DatabaseConfig.set_mode(DatabaseMode.MEMORY)
    
    app = create_app({"TESTING": True})
    
    with app.app_context():
        from db_access.cids import create_cid_record
        from models import CID
        from werkzeug.exceptions import RequestEntityTooLarge
        
        print("Max CID memory: 100 bytes")
        
        print("\nCreating small CID (10 bytes)...")
        try:
            create_cid_record("AAAAAAAA", b"x" * 10)
            print("✅ Created successfully")
        except RequestEntityTooLarge:
            print("❌ Failed (unexpected)")
        
        print("\nCreating large CID (200 bytes, exceeds limit)...")
        try:
            create_cid_record("BBBBBBBB", b"x" * 200)
            print("❌ Created successfully (unexpected)")
        except RequestEntityTooLarge:
            print("✅ Rejected with 413 (expected)")
        
        print(f"\nTotal CIDs in memory: {CID.query.count()}")


def demo_readonly_config():
    """Demonstrate ReadOnlyConfig."""
    print("\n" + "=" * 60)
    print("DEMO: ReadOnlyConfig")
    print("=" * 60)
    
    ReadOnlyConfig.reset()
    
    print(f"Default read-only mode: {ReadOnlyConfig.is_read_only_mode()}")
    print(f"Default max memory: {ReadOnlyConfig.get_max_cid_memory():,} bytes")
    
    ReadOnlyConfig.set_read_only_mode(True)
    ReadOnlyConfig.set_max_cid_memory(512 * 1024 * 1024)
    
    print(f"\nAfter configuration:")
    print(f"Read-only mode: {ReadOnlyConfig.is_read_only_mode()}")
    print(f"Max memory: {ReadOnlyConfig.get_max_cid_memory():,} bytes (512MB)")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("READ-ONLY MODE DEMONSTRATION")
    print("=" * 60)
    
    try:
        demo_readonly_config()
        demo_normal_mode()
        demo_readonly_mode()
        demo_memory_limits()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
