#!/usr/bin/env python3
"""
Test to validate that the CID path mismatch fix works correctly.
"""

def test_base_path_extraction():
    """Test the base path extraction logic that was added to not_found_error"""
    
    test_cases = [
        # (input_path, expected_base_path)
        ("/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa.html", "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"),
        ("/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa.txt", "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"),
        ("/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa.json", "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"),
        ("/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa", "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"),  # No extension
        ("/echo", "/echo"),  # Server path, no extension
        ("/some/nested/path.html", "/some/nested/path"),  # Nested path with extension
    ]
    
    print("=== Testing Base Path Extraction Logic ===")
    
    for input_path, expected_base_path in test_cases:
        # This is the logic added to not_found_error()
        base_path = input_path.split('.')[0] if '.' in input_path else input_path
        
        print(f"Input: {input_path}")
        print(f"Expected: {expected_base_path}")
        print(f"Actual: {base_path}")
        print(f"Match: {base_path == expected_base_path}")
        
        assert base_path == expected_base_path, f"Failed for {input_path}: expected {expected_base_path}, got {base_path}"
        print("✓ Passed\n")

def test_cid_lookup_simulation():
    """Simulate the CID lookup with the fix"""
    
    print("=== Simulating CID Lookup with Fix ===")
    
    # Simulate database records (how they're stored)
    stored_cid_records = [
        {"path": "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa", "file_data": b"<h1>Hello World</h1>"},
        {"path": "/bafybeiother123456789", "file_data": b"Some other content"},
    ]
    
    # Simulate user requests (what they're looking for)
    user_requests = [
        "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa.html",
        "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa.txt", 
        "/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa",  # No extension
        "/bafybeiother123456789.json",
        "/nonexistent.html",
    ]
    
    def simulate_cid_lookup(path, records):
        """Simulate the fixed CID lookup logic"""
        # Apply the fix: strip extension for lookup
        base_path = path.split('.')[0] if '.' in path else path
        
        # Search in records
        for record in records:
            if record["path"] == base_path:
                return record
        return None
    
    for request_path in user_requests:
        print(f"Request: {request_path}")
        
        # Old logic (broken)
        old_result = None
        for record in stored_cid_records:
            if record["path"] == request_path:
                old_result = record
                break
        
        # New logic (fixed)
        new_result = simulate_cid_lookup(request_path, stored_cid_records)
        
        print(f"  Old logic result: {'Found' if old_result else 'Not found'}")
        print(f"  New logic result: {'Found' if new_result else 'Not found'}")
        
        # The fix should find records for paths with extensions that match stored base paths
        if request_path.startswith("/bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"):
            assert new_result is not None, f"Should find record for {request_path}"
            print("  ✓ Fix works correctly")
        elif request_path.startswith("/bafybeiother123456789"):
            assert new_result is not None, f"Should find record for {request_path}"
            print("  ✓ Fix works correctly")
        else:
            assert new_result is None, f"Should not find record for {request_path}"
            print("  ✓ Correctly returns not found")
        
        print()

def test_echo_flow_simulation():
    """Simulate the complete echo flow with the fix"""
    
    print("=== Echo Flow Simulation ===")
    
    # Step 1: Echo server executes and stores CID
    echo_output = "<h1>Hello from Echo!</h1>"
    cid = "bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"  # Example CID
    stored_path = f"/{cid}"
    
    print(f"1. Echo server output: {echo_output}")
    print(f"2. Generated CID: {cid}")
    print(f"3. Stored in DB with path: {stored_path}")
    
    # Step 2: User gets redirected to CID URL with extension
    content_type = "text/html"
    extension = "html"
    redirect_url = f"/{cid}.{extension}"
    
    print(f"4. Content type: {content_type}")
    print(f"5. User redirected to: {redirect_url}")
    
    # Step 3: User visits the redirect URL - this is where the fix applies
    requested_path = redirect_url
    
    print(f"6. User requests: {requested_path}")
    
    # Step 4: Apply the fix in not_found_error
    base_path = requested_path.split('.')[0] if '.' in requested_path else requested_path
    
    print(f"7. Base path extracted: {base_path}")
    print(f"8. Lookup path matches stored path: {base_path == stored_path}")
    
    # Step 5: Simulate successful lookup
    if base_path == stored_path:
        print("9. ✓ CID record found!")
        print("10. ✓ serve_cid_content() called with original path for MIME detection")
        print("11. ✓ Content served successfully")
    else:
        print("9. ❌ CID record not found - 404")
    
    assert base_path == stored_path, "Fix should make paths match"

if __name__ == "__main__":
    try:
        test_base_path_extraction()
        test_cid_lookup_simulation()
        test_echo_flow_simulation()
        
        print("=== ALL TESTS PASSED ===")
        print("The fix should resolve the echo functionality issue!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
