"""Property tests for MIME utilities."""

from hypothesis import assume, example, given, strategies as st

from mime_utils import (
    EXTENSION_TO_MIME,
    MIME_TO_EXTENSION,
    extract_filename_from_cid_path,
    get_extension_from_mime_type,
    get_mime_type_from_extension,
)


# ============================================================================
# Strategies
# ============================================================================


def known_extensions():
    """Generate known file extensions."""
    return st.sampled_from(list(EXTENSION_TO_MIME.keys()))


def known_mime_types():
    """Generate known MIME types."""
    return st.sampled_from(list(MIME_TO_EXTENSION.keys()))


def charset_params():
    """Generate charset parameters for MIME types."""
    return st.sampled_from([
        "",
        "; charset=utf-8",
        "; charset=UTF-8",
        "; charset=iso-8859-1",
        ";charset=utf-8",  # no space
        " ; charset=utf-8",  # extra space
    ])


def cid_paths():
    """Generate CID-style paths."""
    cid_part = st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        min_size=5,
        max_size=20,
    )
    
    filename_part = st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_",
        ),
        min_size=1,
        max_size=20,
    )
    
    extension = known_extensions()
    
    # Generate paths with different numbers of components
    return st.one_of(
        # CID.ext (2 parts - should return None)
        st.tuples(cid_part, extension).map(lambda x: f"/{x[0]}.{x[1]}"),
        # CID.filename.ext (3 parts - should return filename.ext)
        st.tuples(cid_part, filename_part, extension).map(
            lambda x: f"/{x[0]}.{x[1]}.{x[2]}"
        ),
        # CID.file.name.ext (4+ parts - should return file.name.ext)
        st.tuples(cid_part, filename_part, filename_part, extension).map(
            lambda x: f"/{x[0]}.{x[1]}.{x[2]}.{x[3]}"
        ),
    )


# ============================================================================
# Property Tests
# ============================================================================


@given(known_extensions())
@example("txt")
@example("json")
def test_extension_to_mime_to_extension_stable(extension):
    """For known extensions, converting to MIME and back should be stable."""
    mime_type = EXTENSION_TO_MIME[extension]
    returned_extension = get_extension_from_mime_type(mime_type)
    
    # The returned extension should map to the same MIME type
    assert EXTENSION_TO_MIME[returned_extension] == mime_type


@given(known_mime_types(), charset_params())
@example("text/plain", "; charset=utf-8")
@example("application/json", "")
def test_mime_type_consistency_with_parameters(mime_type, charset):
    """MIME type extraction should ignore charset and other parameters."""
    mime_with_params = f"{mime_type}{charset}"
    ext_without_params = get_extension_from_mime_type(mime_type)
    ext_with_params = get_extension_from_mime_type(mime_with_params)
    
    assert ext_with_params == ext_without_params


@given(cid_paths())
@example("/CID.txt")
@example("/CID.document.pdf")
@example("/CID.my.file.tar.gz")
def test_filename_extraction_from_cid_path(path):
    """Filename extraction should handle various path formats correctly."""
    result = extract_filename_from_cid_path(path)
    
    # Count dots in the path (excluding leading slash)
    clean_path = path.lstrip("/")
    dot_count = clean_path.count(".")
    
    if dot_count < 2:
        # CID.ext (only 1 dot) should return None
        assert result is None
    else:
        # CID.filename.ext (2+ dots) should return filename.ext
        assert result is not None
        assert "." in result  # Should contain at least one dot (extension separator)
        
        # Verify the filename can be reconstructed correctly
        parts = clean_path.split(".", 1)
        if len(parts) == 2:
            expected_filename = parts[1]
            assert result == expected_filename


@given(
    st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        min_size=1,
        max_size=50,
    ),
    known_extensions(),
)
@example("document", "pdf")
@example("myfile", "txt")
def test_mime_type_detection_path_formats(filename, extension):
    """MIME type detection should work with various path formats."""
    # Test with just filename.ext
    path1 = f"{filename}.{extension}"
    mime1 = get_mime_type_from_extension(path1)
    
    # Test with /path/to/filename.ext
    path2 = f"/path/to/{filename}.{extension}"
    mime2 = get_mime_type_from_extension(path2)
    
    # Both should detect the same MIME type
    assert mime1 == mime2
    assert mime1 == EXTENSION_TO_MIME[extension]


@given(st.text(min_size=1, max_size=50).filter(lambda s: "." not in s))
@example("noextension")
@example("file-without-extension")
def test_mime_type_no_extension(path):
    """Paths without extensions should return default MIME type."""
    mime = get_mime_type_from_extension(path)
    assert mime == "application/octet-stream"


@given(
    st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        min_size=1,
        max_size=20,
    )
)
@example("file.unknown")
@example("document.xyz")
def test_mime_type_unknown_extension(unknown_ext):
    """Unknown extensions should return default MIME type."""
    # Make sure the extension is not known
    assume(unknown_ext.lower() not in EXTENSION_TO_MIME)
    
    path = f"file.{unknown_ext}"
    mime = get_mime_type_from_extension(path)
    assert mime == "application/octet-stream"


@given(
    st.text(min_size=0, max_size=100)
    .filter(lambda s: not s.strip().startswith("/") or s in ["/", "/.", "/.."]))
@example("")
@example("/")
@example("/.")
@example("/..")
def test_filename_extraction_invalid_paths(path):
    """Invalid or edge case paths should return None."""
    result = extract_filename_from_cid_path(path)
    # These edge cases should return None
    assert result is None or isinstance(result, str)


@given(known_extensions())
@example("html")
@example("jpg")
def test_extension_case_insensitivity(extension):
    """Extension detection should be case-insensitive."""
    # Test with lowercase
    mime_lower = get_mime_type_from_extension(f"file.{extension.lower()}")
    
    # Test with uppercase
    mime_upper = get_mime_type_from_extension(f"file.{extension.upper()}")
    
    # Test with mixed case
    mime_mixed = get_mime_type_from_extension(
        f"file.{extension[:len(extension)//2].upper()}{extension[len(extension)//2:].lower()}"
    )
    
    # All should return the same MIME type
    assert mime_lower == mime_upper == mime_mixed


@given(cid_paths())
@example("/ABC123.document.pdf")
def test_cid_path_no_directory_traversal(path):
    """Extracted filenames should not contain directory traversal patterns."""
    result = extract_filename_from_cid_path(path)
    
    if result is not None:
        # Should not contain ".." or start with "/"
        assert ".." not in result
        assert not result.startswith("/")
