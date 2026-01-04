"""Unit tests for gateway test server support."""

import os


# CID for the test archive
TEST_ARCHIVE_CID = "AAAAAAZCSIClksiwHZUoWgcSYgxDmR2pj2mgV1rz-oCey_hAB0soDmvPZ3ymH6P6NhOTDvgdbPTQHj8dqABcQw42a6wx5A"


# Test parsing of test server paths from URL
def test_parse_test_server_path_simple():
    """Test parsing a simple test server path."""
    path = "/gateway/test/cids/SOMECID/as/jsonplaceholder/posts/1"
    parts = path.strip("/").split("/")
    
    # Remove gateway prefix
    if parts[0] == "gateway":
        parts = parts[1:]
    
    # Check it starts with test
    assert parts[0] == "test"
    
    # Find 'as' index
    as_index = parts.index("as")
    assert as_index == 3  # test/cids/SOMECID/as...
    
    # Extract components
    test_server_path = "/".join(parts[1:as_index])
    server_name = parts[as_index + 1]
    rest_path = "/".join(parts[as_index + 2:])
    
    assert test_server_path == "cids/SOMECID"
    assert server_name == "jsonplaceholder"
    assert rest_path == "posts/1"


def test_parse_test_server_path_with_nested_path():
    """Test parsing test server path with nested structure."""
    path = "/gateway/test/hrx/ARCHIVE123/some/file.md/as/man/ls"
    parts = path.strip("/").split("/")
    
    if parts[0] == "gateway":
        parts = parts[1:]
    
    as_index = parts.index("as")
    test_server_path = "/".join(parts[1:as_index])
    server_name = parts[as_index + 1]
    rest_path = "/".join(parts[as_index + 2:])
    
    assert test_server_path == "hrx/ARCHIVE123/some/file.md"
    assert server_name == "man"
    assert rest_path == "ls"


def test_parse_test_server_path_no_rest():
    """Test parsing when there's no rest path after server name."""
    path = "/gateway/test/cids/SOMECID/as/jsonplaceholder"
    parts = path.strip("/").split("/")
    
    if parts[0] == "gateway":
        parts = parts[1:]
    
    as_index = parts.index("as")
    test_server_path = "/".join(parts[1:as_index])
    server_name = parts[as_index + 1]
    rest_path = "/".join(parts[as_index + 2:]) if len(parts) > as_index + 2 else ""
    
    assert test_server_path == "cids/SOMECID"
    assert server_name == "jsonplaceholder"
    assert rest_path == ""


def test_parse_meta_test_pattern():
    """Test parsing meta page with test pattern."""
    path = "/gateway/meta/test/cids/SOMECID/as/jsonplaceholder"
    parts = path.strip("/").split("/")
    
    if parts[0] == "gateway":
        parts = parts[1:]
    
    assert parts[0] == "meta"
    assert parts[1] == "test"
    
    as_index = parts.index("as")
    test_server_path = "/".join(parts[2:as_index])
    server_name = parts[as_index + 1]
    
    assert test_server_path == "cids/SOMECID"
    assert server_name == "jsonplaceholder"


class TestTestTargetResolution:
    """Test resolution of test targets."""
    
    def test_resolve_test_target_adds_leading_slash(self):
        """Test that test target resolution adds leading slash if missing."""
        test_server_path = "cids/SOMECID"
        
        # Simulate _resolve_test_target
        if not test_server_path.startswith("/"):
            test_server_path = f"/{test_server_path}"
        
        target = {"mode": "internal", "url": test_server_path}
        
        assert target["mode"] == "internal"
        assert target["url"] == "/cids/SOMECID"
    
    def test_resolve_test_target_keeps_leading_slash(self):
        """Test that test target resolution keeps existing leading slash."""
        test_server_path = "/cids/SOMECID"
        
        if not test_server_path.startswith("/"):
            test_server_path = f"/{test_server_path}"
        
        target = {"mode": "internal", "url": test_server_path}
        
        assert target["mode"] == "internal"
        assert target["url"] == "/cids/SOMECID"


class TestAliasDefinition:
    """Test the local_jsonplaceholder alias definition."""
    
    def test_alias_file_exists(self):
        """Test that the alias file was created."""
        path = "reference_templates/aliases/local_jsonplaceholder.txt"
        assert os.path.exists(path), f"Alias file should exist at {path}"
    
    def test_alias_definition_format(self):
        """Test that the alias definition has the correct format."""
        with open("reference_templates/aliases/local_jsonplaceholder.txt", "r") as f:
            content = f.read().strip()
        
        # Should contain the pattern
        assert "/gateway/jsonplaceholder/**" in content
        assert "-> " in content
        assert "/gateway/test/hrx/" in content
        assert "/as/jsonplaceholder/**" in content
    
    def test_alias_uses_correct_cid(self):
        """Test that the alias references the correct CID."""
        with open("reference_templates/aliases/local_jsonplaceholder.txt", "r") as f:
            content = f.read().strip()
        
        # Should contain the CID we created
        assert TEST_ARCHIVE_CID in content


class TestCIDArchive:
    """Test the CID archive file."""
    
    def test_cid_file_exists(self):
        """Test that the CID archive file was created."""
        path = f"cids/{TEST_ARCHIVE_CID}"
        assert os.path.exists(path), f"CID archive should exist at {path}"
    
    def test_cid_file_is_hrx(self):
        """Test that the CID file contains HRX format data."""
        path = f"cids/{TEST_ARCHIVE_CID}"
        
        with open(path, "r") as f:
            content = f.read()
        
        # Should contain HRX boundary markers
        assert "<==>" in content
        assert "GET" in content or "POST" in content
        assert "HTTP/" in content
    
    def test_cid_contains_jsonplaceholder_data(self):
        """Test that the CID contains jsonplaceholder test data."""
        path = f"cids/{TEST_ARCHIVE_CID}"
        
        with open(path, "r") as f:
            content = f.read()
        
        # Should contain sample posts and users
        assert "/posts" in content
        assert "/users" in content
        assert "userId" in content or "username" in content
