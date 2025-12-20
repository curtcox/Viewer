"""Unit tests for cid_core module."""

import unittest

from cid_core import (
    CID_LENGTH,
    CID_MIN_LENGTH,
    DIRECT_CONTENT_EMBED_LIMIT,
    MAX_CONTENT_LENGTH,
    base64url_decode,
    base64url_encode,
    encode_cid_length,
    generate_cid,
    is_normalized_cid,
    is_probable_cid_component,
    is_strict_cid_candidate,
    normalize_component,
    parse_cid_components,
    split_cid_path,
)


class TestBase64UrlEncoding(unittest.TestCase):
    """Tests for base64url encoding/decoding functions."""

    def test_base64url_encode_empty(self):
        """Test encoding empty bytes."""
        result = base64url_encode(b"")
        self.assertEqual(result, "")

    def test_base64url_encode_simple(self):
        """Test encoding simple data."""
        result = base64url_encode(b"hello")
        self.assertEqual(result, "aGVsbG8")

    def test_base64url_decode_simple(self):
        """Test decoding simple data."""
        result = base64url_decode("aGVsbG8")
        self.assertEqual(result, b"hello")

    def test_base64url_roundtrip(self):
        """Test encoding and decoding roundtrip."""
        data = b"test data with special chars: !@#$%"
        encoded = base64url_encode(data)
        decoded = base64url_decode(encoded)
        self.assertEqual(decoded, data)


class TestNormalizeComponent(unittest.TestCase):
    """Tests for normalize_component function."""

    def test_normalize_none(self):
        """Test normalizing None."""
        self.assertEqual(normalize_component(None), "")

    def test_normalize_empty(self):
        """Test normalizing empty string."""
        self.assertEqual(normalize_component(""), "")
        self.assertEqual(normalize_component("   "), "")

    def test_normalize_with_leading_slash(self):
        """Test normalizing string with leading slash."""
        self.assertEqual(normalize_component("/abc123"), "abc123")

    def test_normalize_with_spaces(self):
        """Test normalizing string with whitespace."""
        self.assertEqual(normalize_component("  abc123  "), "abc123")

    def test_normalize_with_internal_slash(self):
        """Test normalizing string with internal slash returns empty."""
        self.assertEqual(normalize_component("abc/def"), "")


class TestCIDValidation(unittest.TestCase):
    """Tests for CID validation functions."""

    def test_is_probable_cid_component_valid(self):
        """Test probable CID component detection with valid inputs."""
        self.assertTrue(is_probable_cid_component("AAAAAAAA"))
        self.assertTrue(is_probable_cid_component("abc123"))

    def test_is_probable_cid_component_invalid(self):
        """Test probable CID component detection with invalid inputs."""
        self.assertFalse(is_probable_cid_component("short"))  # Too short
        self.assertFalse(is_probable_cid_component("abc.txt"))  # Has dot
        self.assertFalse(is_probable_cid_component(None))
        self.assertFalse(is_probable_cid_component(""))

    def test_is_strict_cid_candidate_valid(self):
        """Test strict CID candidate detection."""
        self.assertTrue(is_strict_cid_candidate("AAAAAAAA"))

    def test_is_strict_cid_candidate_invalid(self):
        """Test strict CID candidate with invalid inputs."""
        self.assertFalse(is_strict_cid_candidate("short"))
        self.assertFalse(is_strict_cid_candidate("abc.txt"))

    def test_is_normalized_cid_valid(self):
        """Test normalized CID detection with valid CIDs."""
        cid = generate_cid(b"test")
        self.assertTrue(is_normalized_cid(cid))

    def test_is_normalized_cid_invalid(self):
        """Test normalized CID detection with invalid inputs."""
        self.assertFalse(is_normalized_cid("invalid"))
        self.assertFalse(is_normalized_cid("AAAAAAA"))  # Too short


class TestSplitCIDPath(unittest.TestCase):
    """Tests for split_cid_path function."""

    def test_split_cid_path_simple(self):
        """Test splitting simple CID path."""
        cid = generate_cid(b"test")
        result = split_cid_path(f"/{cid}")
        self.assertEqual(result, (cid, None))

    def test_split_cid_path_with_extension(self):
        """Test splitting CID path with extension."""
        cid = generate_cid(b"test")
        result = split_cid_path(f"/{cid}.txt")
        self.assertEqual(result, (cid, "txt"))

    def test_split_cid_path_with_query(self):
        """Test splitting CID path with query parameters."""
        cid = generate_cid(b"test")
        result = split_cid_path(f"/{cid}.txt?download=1")
        self.assertEqual(result, (cid, "txt"))

    def test_split_cid_path_with_anchor(self):
        """Test splitting CID path with anchor."""
        cid = generate_cid(b"test")
        result = split_cid_path(f"/{cid}.html#section")
        self.assertEqual(result, (cid, "html"))

    def test_split_cid_path_invalid(self):
        """Test splitting invalid paths."""
        self.assertIsNone(split_cid_path(None))
        self.assertIsNone(split_cid_path(""))
        self.assertIsNone(split_cid_path("/not/a/cid"))


class TestEncodeCIDLength(unittest.TestCase):
    """Tests for encode_cid_length function."""

    def test_encode_length_zero(self):
        """Test encoding length 0."""
        result = encode_cid_length(0)
        self.assertEqual(result, "AAAAAAAA")
        self.assertEqual(len(result), 8)

    def test_encode_length_positive(self):
        """Test encoding positive lengths."""
        result = encode_cid_length(42)
        self.assertEqual(len(result), 8)

    def test_encode_length_max(self):
        """Test encoding maximum length."""
        result = encode_cid_length(MAX_CONTENT_LENGTH)
        self.assertEqual(len(result), 8)

    def test_encode_length_negative(self):
        """Test encoding negative length raises error."""
        with self.assertRaises(ValueError):
            encode_cid_length(-1)

    def test_encode_length_too_large(self):
        """Test encoding too large length raises error."""
        with self.assertRaises(ValueError):
            encode_cid_length(MAX_CONTENT_LENGTH + 1)


class TestParseCIDComponents(unittest.TestCase):
    """Tests for parse_cid_components function."""

    def test_parse_empty_cid(self):
        """Test parsing CID for empty content."""
        cid = "AAAAAAAA"
        length, payload = parse_cid_components(cid)
        self.assertEqual(length, 0)
        self.assertEqual(payload, b"")

    def test_parse_direct_embed_cid(self):
        """Test parsing CID with direct content embedding."""
        cid = generate_cid(b"hello")
        length, payload = parse_cid_components(cid)
        self.assertEqual(length, 5)
        self.assertEqual(payload, b"hello")

    def test_parse_hashed_cid(self):
        """Test parsing CID with hashed content."""
        content = b"x" * 100  # Larger than DIRECT_CONTENT_EMBED_LIMIT
        cid = generate_cid(content)
        length, payload = parse_cid_components(cid)
        self.assertEqual(length, 100)
        self.assertEqual(len(payload), 64)  # SHA-512 digest size

    def test_parse_invalid_cid_too_short(self):
        """Test parsing too short CID raises error."""
        with self.assertRaises(ValueError):
            parse_cid_components("SHORT")

    def test_parse_invalid_cid_bad_base64(self):
        """Test parsing CID with invalid base64 raises error."""
        with self.assertRaises(ValueError):
            parse_cid_components("AAAAAAAA!!!!")


class TestGenerateCID(unittest.TestCase):
    """Tests for generate_cid function."""

    def test_generate_empty(self):
        """Test generating CID for empty content."""
        cid = generate_cid(b"")
        self.assertEqual(cid, "AAAAAAAA")

    def test_generate_small_content(self):
        """Test generating CID for small content (direct embed)."""
        cid = generate_cid(b"hello")
        self.assertEqual(len(cid), CID_MIN_LENGTH + len(base64url_encode(b"hello")))

    def test_generate_large_content(self):
        """Test generating CID for large content (hashed)."""
        content = b"x" * 100
        cid = generate_cid(content)
        self.assertEqual(len(cid), CID_LENGTH)

    def test_generate_roundtrip_small(self):
        """Test generating and parsing small content roundtrip."""
        content = b"test data"
        cid = generate_cid(content)
        length, payload = parse_cid_components(cid)
        self.assertEqual(length, len(content))
        self.assertEqual(payload, content)

    def test_generate_at_boundary(self):
        """Test generating CID at DIRECT_CONTENT_EMBED_LIMIT boundary."""
        content = b"x" * DIRECT_CONTENT_EMBED_LIMIT
        cid = generate_cid(content)
        length, payload = parse_cid_components(cid)
        self.assertEqual(length, DIRECT_CONTENT_EMBED_LIMIT)
        self.assertEqual(payload, content)

    def test_generate_above_boundary(self):
        """Test generating CID just above DIRECT_CONTENT_EMBED_LIMIT."""
        content = b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 1)
        cid = generate_cid(content)
        self.assertEqual(len(cid), CID_LENGTH)
        length, payload = parse_cid_components(cid)
        self.assertEqual(length, DIRECT_CONTENT_EMBED_LIMIT + 1)
        self.assertEqual(len(payload), 64)  # SHA-512 digest


class TestIsLiteralCID(unittest.TestCase):
    """Tests for is_literal_cid function."""

    def test_empty_cid_is_literal(self):
        """Test that empty content CID is literal."""
        from cid_core import is_literal_cid

        cid = generate_cid(b"")
        self.assertTrue(is_literal_cid(cid))

    def test_small_content_is_literal(self):
        """Test that small content (<=64 bytes) is literal."""
        from cid_core import is_literal_cid

        cid = generate_cid(b"hello")
        self.assertTrue(is_literal_cid(cid))

    def test_boundary_content_is_literal(self):
        """Test that content exactly at 64 bytes is literal."""
        from cid_core import is_literal_cid

        cid = generate_cid(b"x" * DIRECT_CONTENT_EMBED_LIMIT)
        self.assertTrue(is_literal_cid(cid))

    def test_large_content_is_not_literal(self):
        """Test that content > 64 bytes is not literal."""
        from cid_core import is_literal_cid

        cid = generate_cid(b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 1))
        self.assertFalse(is_literal_cid(cid))

    def test_works_with_leading_slash(self):
        """Test that function works with leading slash."""
        from cid_core import is_literal_cid

        cid = generate_cid(b"hello")
        self.assertTrue(is_literal_cid(f"/{cid}"))

    def test_invalid_cid_returns_false(self):
        """Test that invalid CID returns False."""
        from cid_core import is_literal_cid

        self.assertFalse(is_literal_cid("invalid"))
        self.assertFalse(is_literal_cid(""))
        self.assertFalse(is_literal_cid(None))


class TestExtractLiteralContent(unittest.TestCase):
    """Tests for extract_literal_content function."""

    def test_extract_empty_content(self):
        """Test extracting empty content."""
        from cid_core import extract_literal_content

        cid = generate_cid(b"")
        self.assertEqual(extract_literal_content(cid), b"")

    def test_extract_small_content(self):
        """Test extracting small content."""
        from cid_core import extract_literal_content

        content = b"hello world"
        cid = generate_cid(content)
        self.assertEqual(extract_literal_content(cid), content)

    def test_extract_boundary_content(self):
        """Test extracting content at 64-byte boundary."""
        from cid_core import extract_literal_content

        content = b"x" * DIRECT_CONTENT_EMBED_LIMIT
        cid = generate_cid(content)
        self.assertEqual(extract_literal_content(cid), content)

    def test_hash_based_cid_returns_none(self):
        """Test that hash-based CID returns None."""
        from cid_core import extract_literal_content

        content = b"x" * (DIRECT_CONTENT_EMBED_LIMIT + 1)
        cid = generate_cid(content)
        self.assertIsNone(extract_literal_content(cid))

    def test_works_with_leading_slash(self):
        """Test that function works with leading slash."""
        from cid_core import extract_literal_content

        content = b"hello"
        cid = generate_cid(content)
        self.assertEqual(extract_literal_content(f"/{cid}"), content)

    def test_invalid_cid_returns_none(self):
        """Test that invalid CID returns None."""
        from cid_core import extract_literal_content

        self.assertIsNone(extract_literal_content("invalid"))
        self.assertIsNone(extract_literal_content(""))
        self.assertIsNone(extract_literal_content(None))


if __name__ == "__main__":
    unittest.main()
