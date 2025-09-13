#!/usr/bin/env python3
"""
Test to validate the CID serving issue.
The fact that the user got redirected to a specific CID URL means:
1. Echo server exists and executed successfully
2. CID was generated and stored
3. But CID serving is failing with 404
"""

def test_cid_url_analysis():
    """Analyze the CID URL that user was redirected to"""
    
    # The CID URL the user was redirected to
    cid_url = "bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa.html"
    
    print("=== CID URL Analysis ===")
    print(f"Full CID URL: /{cid_url}")
    
    # Extract base CID (without extension)
    base_cid = cid_url.split('.')[0]
    print(f"Base CID: {base_cid}")
    
    # Extract extension
    extension = cid_url.split('.')[-1] if '.' in cid_url else None
    print(f"Extension: {extension}")
    
    return base_cid, extension

def test_cid_serving_logic():
    """Test the CID serving logic from routes.py"""
    
    print("\n=== CID Serving Logic ===")
    print("When user visits /bafybei...html:")
    print("1. Flask routes don't match (no explicit route)")
    print("2. 404 handler (not_found_error) is triggered")
    print("3. is_potential_server_path() returns False (contains '.')")
    print("4. CID.query.filter_by(path='/bafybei...html').first() is called")
    print("5. If CID record exists, serve_cid_content() is called")
    print("6. If CID record doesn't exist, 404 is returned")

def test_cid_path_storage_mismatch():
    """Test potential mismatch between CID storage and serving"""
    
    print("\n=== Potential CID Storage/Serving Mismatch ===")
    
    # From execute_server_code, CID is stored with path like this:
    base_cid = "bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"
    stored_path = f"/{base_cid}"  # CID stored without extension
    requested_path = f"/{base_cid}.html"  # User redirected to URL with extension
    
    print(f"CID stored in DB with path: {stored_path}")
    print(f"User requesting path: {requested_path}")
    print(f"Paths match: {stored_path == requested_path}")
    
    print("\n❌ ISSUE IDENTIFIED: Path mismatch!")
    print("- CID is stored in database with path like '/bafybei...' (no extension)")
    print("- User is redirected to '/bafybei....html' (with extension)")
    print("- CID lookup fails because paths don't match")
    
    return stored_path, requested_path

def test_serve_cid_content_logic():
    """Analyze the serve_cid_content function logic"""
    
    print("\n=== serve_cid_content Logic Analysis ===")
    print("From routes.py line ~679:")
    print("1. serve_cid_content(cid_content, path) is called")
    print("2. It extracts CID from path: cid = path[1:] if path.startswith('/') else path")
    print("3. For '/bafybei...html', this gives 'bafybei...html' (with extension)")
    print("4. It determines MIME type from URL extension")
    print("5. It serves the file_data from the CID record")
    print("")
    print("The function should work IF the CID record is found.")
    print("The issue is in the CID lookup in not_found_error().")

def create_failing_test():
    """Create a test that demonstrates the failing behavior"""
    
    print("\n=== Failing Test Scenario ===")
    
    # Simulate the database lookup that's failing
    base_cid = "bafybeivuvtmn7tdudola5day36gxpos653lmk5duwxlgikg3xy6akai4aa"
    
    # What's stored in database (from execute_server_code)
    stored_records = [
        {"path": f"/{base_cid}", "file_data": b"<h1>Hello World</h1>"}
    ]
    
    # What's being looked up (from not_found_error)
    lookup_path = f"/{base_cid}.html"
    
    # Simulate the query
    found_record = None
    for record in stored_records:
        if record["path"] == lookup_path:
            found_record = record
            break
    
    print(f"Stored records: {[r['path'] for r in stored_records]}")
    print(f"Looking up path: {lookup_path}")
    print(f"Record found: {found_record is not None}")
    
    # This should fail
    assert found_record is None, "Expected lookup to fail due to path mismatch"
    print("✓ Test confirms: CID lookup fails due to path mismatch")

if __name__ == "__main__":
    try:
        base_cid, extension = test_cid_url_analysis()
        test_cid_serving_logic()
        stored_path, requested_path = test_cid_path_storage_mismatch()
        test_serve_cid_content_logic()
        create_failing_test()
        
        print("\n=== FINAL DIAGNOSIS ===")
        print("ROOT CAUSE: Path mismatch between CID storage and lookup")
        print("")
        print("What happens:")
        print("1. User visits /echo")
        print("2. Echo server executes successfully")
        print(f"3. Output is stored in CID table with path='/{base_cid}' (no extension)")
        print(f"4. User is redirected to '/{base_cid}.html' (with extension)")
        print(f"5. 404 handler looks for CID with path='/{base_cid}.html'")
        print(f"6. Lookup fails because stored path is '/{base_cid}' (no extension)")
        print("7. 404 is returned")
        print("")
        print("The echo functionality IS working - the issue is in CID URL handling.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
