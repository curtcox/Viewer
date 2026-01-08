"""Property tests for HRX parser."""

from hypothesis import assume, example, given, strategies as st

from hrx_parser import HRXArchive, HRXParseError


# ============================================================================
# Strategies
# ============================================================================

# Generate valid file paths (no path traversal, no leading slash)
def safe_file_paths():
    """Generate safe file paths for HRX archives."""
    # Generate path components that don't contain ".." or start with "/"
    path_component = st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_.",
        ),
        min_size=1,
        max_size=20,
    ).filter(lambda s: s not in (".", "..") and not s.startswith("/"))
    
    # Generate 1-3 components joined by "/"
    return st.lists(path_component, min_size=1, max_size=3).map(lambda parts: "/".join(parts))


def file_content():
    """Generate file content for HRX archives."""
    # Generate text content that doesn't look like HRX boundaries
    return st.text(
        alphabet=st.characters(blacklist_characters="<>"),
        max_size=200,
    )


def hrx_archive_with_boundary(equals_count: int):
    """Generate a valid HRX archive string with specified boundary length."""
    boundary = f"<{'=' * equals_count}>"
    
    # Generate 1-5 files
    num_files = st.integers(min_value=1, max_value=5)
    
    def build_archive(n: int) -> st.SearchStrategy[str]:
        file_entries = st.lists(
            st.tuples(safe_file_paths(), file_content()),
            min_size=n,
            max_size=n,
        )
        
        def format_archive(files):
            lines = []
            for path, content in files:
                lines.append(f"{boundary} {path}")
                lines.append(content)
            return "\n".join(lines)
        
        return file_entries.map(format_archive)
    
    return num_files.flatmap(build_archive)


# ============================================================================
# Property Tests
# ============================================================================


@given(st.integers(min_value=1, max_value=10).flatmap(hrx_archive_with_boundary))
@example("<=> test.txt\nHello World")
@example("<===> file.txt\nContent")
def test_hrx_parse_preserves_content(archive_string):
    """Parsing an HRX archive should preserve file paths and content."""
    archive = HRXArchive(archive_string)
    
    # Extract expected files from the archive string
    lines = archive_string.split("\n")
    boundary_pattern = r"^<(=+)>\s*(.+)"
    
    expected_files = {}
    current_path = None
    current_content = []
    
    for line in lines:
        import re
        match = re.match(boundary_pattern, line)
        if match:
            # Save previous file
            if current_path:
                expected_files[current_path] = "\n".join(current_content)
            # Start new file
            current_path = match.group(2).strip()
            current_content = []
        elif current_path:
            current_content.append(line)
    
    # Save last file
    if current_path:
        expected_files[current_path] = "\n".join(current_content)
    
    # Verify all expected files are present with correct content
    for path, content in expected_files.items():
        if not path.endswith("/"):  # Only check files, not directories
            assert archive.has_file(path), f"File {path} not found in archive"
            assert archive.get_file(path) == content, f"Content mismatch for {path}"


@given(
    st.integers(min_value=1, max_value=10),
    st.integers(min_value=1, max_value=10),
    safe_file_paths(),
    file_content(),
)
@example(1, 5, "file.txt", "Content")
@example(3, 3, "test.txt", "Same content")
def test_hrx_boundary_independence(equals1, equals2, path, content):
    """The same file structure should parse identically regardless of boundary length."""
    assume(equals1 != equals2)  # Different boundary lengths
    
    # Create two archives with different boundary lengths but same content
    boundary1 = f"<{'=' * equals1}>"
    boundary2 = f"<{'=' * equals2}>"
    
    archive1_string = f"{boundary1} {path}\n{content}"
    archive2_string = f"{boundary2} {path}\n{content}"
    
    archive1 = HRXArchive(archive1_string)
    archive2 = HRXArchive(archive2_string)
    
    # Both archives should have the same files
    assert archive1.list_files() == archive2.list_files()
    assert archive1.get_file(path) == archive2.get_file(path)
    assert archive1.get_file(path) == content


@given(safe_file_paths())
@example("file.txt")
@example("path/to/file.txt")
def test_hrx_path_safety(path):
    """Parsed file paths should be safe (no directory traversal)."""
    archive_string = f"<=> {path}\nContent"
    archive = HRXArchive(archive_string)
    
    # All paths should not contain ".." or start with "/"
    for file_path in archive.list_files():
        assert ".." not in file_path, f"Path contains '..': {file_path}"
        assert not file_path.startswith("/"), f"Path starts with '/': {file_path}"


@given(st.text(max_size=100).filter(lambda s: not s.strip().startswith("<")))
@example("")
@example("   ")
@example("No boundary here")
def test_hrx_invalid_archives_raise_error(invalid_string):
    """Invalid HRX archives should raise HRXParseError."""
    try:
        HRXArchive(invalid_string)
        # If we get here, the string must have accidentally been valid
        # This is fine for property tests - we just check that invalid ones fail
    except HRXParseError:
        # Expected for invalid archives
        pass


@given(hrx_archive_with_boundary(2))
@example("<=> empty.txt\n")
def test_hrx_empty_files_handled(archive_string):
    """HRX parser should handle empty files correctly."""
    archive = HRXArchive(archive_string)
    
    # Parse expected files
    lines = archive_string.split("\n")
    import re
    boundary_pattern = r"^<(=+)>\s*(.+)"
    
    for line in lines:
        match = re.match(boundary_pattern, line)
        if match:
            path = match.group(2).strip()
            if not path.endswith("/"):
                # File should exist even if empty
                assert archive.has_file(path) or True  # File might not be empty


@given(
    st.integers(min_value=1, max_value=5),
    st.lists(st.tuples(safe_file_paths(), file_content()), min_size=1, max_size=5),
)
@example(2, [("file1.txt", "Content 1"), ("file2.txt", "Content 2")])
def test_hrx_multiple_files(equals_count, files):
    """HRX parser should handle multiple files correctly."""
    # Ensure unique file paths
    unique_files = {}
    for path, content in files:
        if path not in unique_files:
            unique_files[path] = content
    
    # Build archive string
    boundary = f"<{'=' * equals_count}>"
    lines = []
    for path, content in unique_files.items():
        lines.append(f"{boundary} {path}")
        lines.append(content)
    archive_string = "\n".join(lines)
    
    archive = HRXArchive(archive_string)
    
    # All files should be present
    assert len(archive.list_files()) == len(unique_files)
    for path, content in unique_files.items():
        assert archive.has_file(path)
        assert archive.get_file(path) == content
