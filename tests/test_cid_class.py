"""Tests for the CID class.

This module tests the CID class to ensure:
- Proper validation of CID strings
- Correct generation from bytes
- Accurate property values
- Expected behavior for all methods
- Proper error handling
"""

import unittest
from cid import CID
from cid_core import generate_cid


class TestCIDConstruction(unittest.TestCase):
    """Test CID construction and validation."""

    def test_construct_from_valid_cid_string(self):
        """Test creating CID from valid string."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid.value, "AAAAAAAA")

    def test_construct_from_valid_cid_with_leading_slash(self):
        """Test creating CID from string with leading slash."""
        cid = CID("/AAAAAAAA")
        self.assertEqual(cid.value, "AAAAAAAA")

    def test_construct_from_literal_cid(self):
        """Test creating CID with embedded content."""
        cid = CID("AAAAAAAFaGVsbG8")  # "hello"
        self.assertEqual(cid.value, "AAAAAAAFaGVsbG8")

    def test_construct_from_hashed_cid(self):
        """Test creating CID with hash-based content."""
        # Generate a CID for content > 64 bytes
        large_content = b"x" * 100
        cid_string = generate_cid(large_content)
        cid = CID(cid_string)
        self.assertEqual(cid.value, cid_string)
        self.assertEqual(len(cid.value), 94)  # Full length for hashed CID

    def test_construct_invalid_cid_raises_error(self):
        """Test that invalid CID strings raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            CID("invalid")
        self.assertIn("Invalid CID", str(ctx.exception))

    def test_construct_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            CID("")
        self.assertIn("Invalid CID", str(ctx.exception))

    def test_construct_with_dots_raises_error(self):
        """Test that CID with dots raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            CID("AAAAAAAA.txt")
        self.assertIn("Invalid CID", str(ctx.exception))

    def test_construct_with_slashes_in_middle_raises_error(self):
        """Test that CID with slashes in middle raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            CID("AAAA/AAAA")
        self.assertIn("Invalid CID", str(ctx.exception))

    def test_construct_too_short_raises_error(self):
        """Test that too-short string raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            CID("SHORT")
        self.assertIn("Invalid CID", str(ctx.exception))

    def test_construct_with_non_string_raises_type_error(self):
        """Test that non-string input raises TypeError."""
        with self.assertRaises(TypeError) as ctx:
            CID(123)
        self.assertIn("must be initialized with a string", str(ctx.exception))

        with self.assertRaises(TypeError):
            CID(None)

        with self.assertRaises(TypeError):
            CID(b"AAAAAAAA")


class TestCIDFromBytes(unittest.TestCase):
    """Test CID.from_bytes() class method."""

    def test_from_empty_bytes(self):
        """Test generating CID from empty content."""
        cid = CID.from_bytes(b"")
        self.assertEqual(cid.value, "AAAAAAAA")
        self.assertEqual(cid.content_length, 0)

    def test_from_small_content(self):
        """Test generating CID from small content."""
        cid = CID.from_bytes(b"hello")
        self.assertEqual(cid.value, "AAAAAAAFaGVsbG8")
        self.assertEqual(cid.content_length, 5)

    def test_from_exact_64_bytes(self):
        """Test generating CID from exactly 64 bytes (boundary case)."""
        content = b"x" * 64
        cid = CID.from_bytes(content)
        self.assertEqual(cid.content_length, 64)
        self.assertTrue(cid.is_literal)

    def test_from_65_bytes(self):
        """Test generating CID from 65 bytes (just over literal limit)."""
        content = b"x" * 65
        cid = CID.from_bytes(content)
        self.assertEqual(cid.content_length, 65)
        self.assertFalse(cid.is_literal)
        self.assertEqual(len(cid.value), 94)  # Full hashed CID

    def test_from_large_content(self):
        """Test generating CID from large content."""
        content = b"x" * 1000
        cid = CID.from_bytes(content)
        self.assertEqual(cid.content_length, 1000)
        self.assertFalse(cid.is_literal)
        self.assertEqual(len(cid.value), 94)

    def test_from_bytes_deterministic(self):
        """Test that same content produces same CID."""
        content = b"test content"
        cid1 = CID.from_bytes(content)
        cid2 = CID.from_bytes(content)
        self.assertEqual(cid1, cid2)
        self.assertEqual(cid1.value, cid2.value)


class TestCIDTryFromString(unittest.TestCase):
    """Test CID.try_from_string() class method."""

    def test_try_from_valid_string(self):
        """Test try_from_string with valid CID."""
        cid = CID.try_from_string("AAAAAAAA")
        self.assertIsNotNone(cid)
        self.assertEqual(cid.value, "AAAAAAAA")

    def test_try_from_invalid_string(self):
        """Test try_from_string with invalid CID."""
        cid = CID.try_from_string("invalid")
        self.assertIsNone(cid)

    def test_try_from_none(self):
        """Test try_from_string with None."""
        cid = CID.try_from_string(None)
        self.assertIsNone(cid)

    def test_try_from_empty_string(self):
        """Test try_from_string with empty string."""
        cid = CID.try_from_string("")
        self.assertIsNone(cid)


class TestCIDProperties(unittest.TestCase):
    """Test CID properties."""

    def test_value_property(self):
        """Test value property returns normalized CID."""
        cid = CID("/AAAAAAAA")
        self.assertEqual(cid.value, "AAAAAAAA")

    def test_content_length_for_empty(self):
        """Test content_length for empty content."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid.content_length, 0)

    def test_content_length_for_literal(self):
        """Test content_length for literal CID."""
        cid = CID.from_bytes(b"hello")
        self.assertEqual(cid.content_length, 5)

    def test_content_length_for_hashed(self):
        """Test content_length for hash-based CID."""
        content = b"x" * 100
        cid = CID.from_bytes(content)
        self.assertEqual(cid.content_length, 100)

    def test_is_literal_for_empty(self):
        """Test is_literal for empty content."""
        cid = CID("AAAAAAAA")
        self.assertTrue(cid.is_literal)

    def test_is_literal_for_small_content(self):
        """Test is_literal for small content."""
        cid = CID.from_bytes(b"hello")
        self.assertTrue(cid.is_literal)

    def test_is_literal_for_64_bytes(self):
        """Test is_literal for exactly 64 bytes."""
        cid = CID.from_bytes(b"x" * 64)
        self.assertTrue(cid.is_literal)

    def test_is_literal_for_65_bytes(self):
        """Test is_literal for 65 bytes."""
        cid = CID.from_bytes(b"x" * 65)
        self.assertFalse(cid.is_literal)

    def test_is_literal_for_large_content(self):
        """Test is_literal for large content."""
        cid = CID.from_bytes(b"x" * 1000)
        self.assertFalse(cid.is_literal)

    def test_payload_for_literal_cid(self):
        """Test payload property for literal CID."""
        content = b"hello"
        cid = CID.from_bytes(content)
        self.assertEqual(cid.payload, content)

    def test_payload_for_hashed_cid(self):
        """Test payload property for hash-based CID."""
        content = b"x" * 100
        cid = CID.from_bytes(content)
        # Payload should be the SHA-512 digest (64 bytes)
        self.assertEqual(len(cid.payload), 64)


class TestCIDMethods(unittest.TestCase):
    """Test CID methods."""

    def test_extract_literal_content_for_empty(self):
        """Test extracting content from empty CID."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid.extract_literal_content(), b"")

    def test_extract_literal_content_for_literal(self):
        """Test extracting content from literal CID."""
        cid = CID.from_bytes(b"hello")
        self.assertEqual(cid.extract_literal_content(), b"hello")

    def test_extract_literal_content_for_hashed(self):
        """Test extracting content from hash-based CID returns None."""
        cid = CID.from_bytes(b"x" * 100)
        self.assertIsNone(cid.extract_literal_content())

    def test_to_path_without_extension(self):
        """Test to_path without extension."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid.to_path(), "/AAAAAAAA")

    def test_to_path_with_extension(self):
        """Test to_path with extension."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid.to_path("txt"), "/AAAAAAAA.txt")
        self.assertEqual(cid.to_path("json"), "/AAAAAAAA.json")


class TestCIDStringConversion(unittest.TestCase):
    """Test CID string conversion and representation."""

    def test_str_conversion(self):
        """Test str() conversion."""
        cid = CID("AAAAAAAA")
        self.assertEqual(str(cid), "AAAAAAAA")

    def test_repr_conversion(self):
        """Test repr() conversion."""
        cid = CID("AAAAAAAA")
        self.assertEqual(repr(cid), "CID('AAAAAAAA')")

    def test_len(self):
        """Test len() returns CID string length."""
        cid = CID("AAAAAAAA")
        self.assertEqual(len(cid), 8)

        cid_large = CID.from_bytes(b"x" * 100)
        self.assertEqual(len(cid_large), 94)


class TestCIDEquality(unittest.TestCase):
    """Test CID equality comparisons."""

    def test_equality_with_same_cid(self):
        """Test equality between identical CIDs."""
        cid1 = CID("AAAAAAAA")
        cid2 = CID("AAAAAAAA")
        self.assertEqual(cid1, cid2)

    def test_equality_with_string(self):
        """Test equality between CID and string."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid, "AAAAAAAA")

    def test_equality_with_string_with_leading_slash(self):
        """Test equality between CID and string with leading slash."""
        cid = CID("AAAAAAAA")
        self.assertEqual(cid, "/AAAAAAAA")

    def test_inequality_with_different_cid(self):
        """Test inequality between different CIDs."""
        cid1 = CID("AAAAAAAA")
        cid2 = CID.from_bytes(b"hello")
        self.assertNotEqual(cid1, cid2)

    def test_inequality_with_different_string(self):
        """Test inequality between CID and different string."""
        cid = CID("AAAAAAAA")
        self.assertNotEqual(cid, "different")

    def test_inequality_with_invalid_type(self):
        """Test inequality with non-string, non-CID types."""
        cid = CID("AAAAAAAA")
        self.assertNotEqual(cid, 123)
        self.assertNotEqual(cid, None)
        self.assertNotEqual(cid, b"AAAAAAAA")


class TestCIDHashing(unittest.TestCase):
    """Test CID hashing for use in sets and dicts."""

    def test_hash_consistency(self):
        """Test that same CID produces same hash."""
        cid1 = CID("AAAAAAAA")
        cid2 = CID("AAAAAAAA")
        self.assertEqual(hash(cid1), hash(cid2))

    def test_hash_different_for_different_cids(self):
        """Test that different CIDs produce different hashes."""
        cid1 = CID("AAAAAAAA")
        cid2 = CID.from_bytes(b"hello")
        # Note: Hash collisions are possible but extremely unlikely
        self.assertNotEqual(hash(cid1), hash(cid2))

    def test_cid_in_set(self):
        """Test using CID in a set."""
        cid1 = CID("AAAAAAAA")
        cid2 = CID.from_bytes(b"hello")
        cid3 = CID("AAAAAAAA")

        cid_set = {cid1, cid2, cid3}
        self.assertEqual(len(cid_set), 2)  # cid1 and cid3 are the same
        self.assertIn(cid1, cid_set)
        self.assertIn(cid2, cid_set)

    def test_cid_as_dict_key(self):
        """Test using CID as dictionary key."""
        cid1 = CID("AAAAAAAA")
        cid2 = CID.from_bytes(b"hello")

        cid_dict = {cid1: "empty", cid2: "hello"}
        self.assertEqual(cid_dict[cid1], "empty")
        self.assertEqual(cid_dict[cid2], "hello")

        # Same CID should retrieve same value
        cid3 = CID("AAAAAAAA")
        self.assertEqual(cid_dict[cid3], "empty")


class TestCIDEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_whitespace_in_input(self):
        """Test that whitespace is properly handled."""
        cid = CID("  AAAAAAAA  ")
        self.assertEqual(cid.value, "AAAAAAAA")

    def test_boundary_at_64_bytes(self):
        """Test the boundary between literal and hashed CIDs."""
        content_64 = b"x" * 64
        content_65 = b"x" * 65

        cid_64 = CID.from_bytes(content_64)
        cid_65 = CID.from_bytes(content_65)

        self.assertTrue(cid_64.is_literal)
        self.assertFalse(cid_65.is_literal)

        self.assertEqual(cid_64.extract_literal_content(), content_64)
        self.assertIsNone(cid_65.extract_literal_content())

    def test_unicode_content(self):
        """Test generating CID from unicode content."""
        content = "Hello 世界! 🌍".encode("utf-8")
        cid = CID.from_bytes(content)
        self.assertEqual(cid.content_length, len(content))

    def test_binary_content(self):
        """Test generating CID from binary content."""
        content = bytes(range(256))  # All byte values
        cid = CID.from_bytes(content)
        self.assertEqual(cid.content_length, 256)
        self.assertFalse(cid.is_literal)


class TestCIDImmutability(unittest.TestCase):
    """Test that CID instances are effectively immutable."""

    def test_cannot_modify_value(self):
        """Test that CID value cannot be modified."""
        cid = CID("AAAAAAAA")
        with self.assertRaises(AttributeError):
            cid.value = "different"

    def test_cannot_modify_content_length(self):
        """Test that content_length cannot be modified."""
        cid = CID("AAAAAAAA")
        with self.assertRaises(AttributeError):
            cid.content_length = 100

    def test_cannot_add_attributes(self):
        """Test that new attributes cannot be added (due to __slots__)."""
        cid = CID("AAAAAAAA")
        with self.assertRaises(AttributeError):
            setattr(cid, "new_attribute", "value")


if __name__ == "__main__":
    unittest.main()
