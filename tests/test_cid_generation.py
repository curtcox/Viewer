import hashlib
import os
import unittest

from cid_utils import (
    CID_LENGTH,
    CID_MIN_LENGTH,
    CID_NORMALIZED_PATTERN,
    DIRECT_CONTENT_EMBED_LIMIT,
    encode_cid_length,
    generate_cid,
    is_normalized_cid,
    is_probable_cid_component,
    is_strict_cid_candidate,
    parse_cid_components,
    split_cid_path,
)
from cid_utils import _base64url_encode


class TestCIDGeneration(unittest.TestCase):
    """Unit tests validating CID generation behaviour."""

    def _assert_round_trip(self, content: bytes) -> None:
        cid = generate_cid(content)
        length, payload = parse_cid_components(cid)

        self.assertEqual(length, len(content))
        if len(content) <= DIRECT_CONTENT_EMBED_LIMIT:
            self.assertEqual(payload, content)
            expected = encode_cid_length(len(content)) + _base64url_encode(content)
        else:
            self.assertEqual(payload, hashlib.sha512(content).digest())
            expected = encode_cid_length(len(content)) + _base64url_encode(payload)

        self.assertEqual(cid, expected)
        self.assertGreaterEqual(len(cid), CID_MIN_LENGTH)
        self.assertLessEqual(len(cid), CID_LENGTH)
        self.assertTrue(CID_NORMALIZED_PATTERN.fullmatch(cid))
        self.assertTrue(is_normalized_cid(cid))

    def test_direct_content_round_trip_all_lengths(self) -> None:
        """Exercise every direct-encoding length with multiple examples."""

        # Length 0 has only one representation.
        cid_zero = generate_cid(b"")
        self.assertEqual(cid_zero, "AAAAAAAA")
        self._assert_round_trip(b"")

        for length in range(1, DIRECT_CONTENT_EMBED_LIMIT + 1):
            example_one = bytes((index % 256 for index in range(length)))
            example_two = bytes(((index + 127) % 256 for index in range(length)))

            with self.subTest(length=length, case="sequential"):
                self._assert_round_trip(example_one)
            with self.subTest(length=length, case="offset"):
                self._assert_round_trip(example_two)

    def test_hashed_round_trip_examples(self) -> None:
        """Verify hashed CIDs behave like the legacy format."""

        for size in (DIRECT_CONTENT_EMBED_LIMIT + 1, 512, 1024 * 1024):
            content = os.urandom(size)
            with self.subTest(size=size):
                cid = generate_cid(content)
                length, payload = parse_cid_components(cid)
                self.assertEqual(length, size)
                self.assertEqual(len(cid), CID_LENGTH)
                self.assertEqual(payload, hashlib.sha512(content).digest())

    def test_helper_utilities_still_validate(self) -> None:
        """Ensure helper utilities recognise generated CIDs."""

        cid = generate_cid(b"helper utilities")

        self.assertTrue(is_probable_cid_component(cid))
        self.assertTrue(is_strict_cid_candidate(cid))
        self.assertTrue(is_normalized_cid(cid))

        # Validation should fail for malformed candidates.
        self.assertFalse(is_probable_cid_component("short"))
        self.assertFalse(is_normalized_cid(f"{cid}extra"))

        # Path splitting handles direct CIDs, extensions, and URL modifiers.
        self.assertEqual(split_cid_path(f"/{cid}"), (cid, None))
        self.assertEqual(split_cid_path(f"/{cid}.json"), (cid, "json"))
        self.assertEqual(split_cid_path(f"/{cid}.html?download=1"), (cid, "html"))
        self.assertEqual(split_cid_path(f"/{cid}.txt#section"), (cid, "txt"))
        self.assertIsNone(split_cid_path("/not/a/cid"))
        self.assertIsNone(split_cid_path(""))


if __name__ == "__main__":  # pragma: no cover - support manual execution
    unittest.main()
