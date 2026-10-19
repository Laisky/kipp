"""Preserve legacy xxh32 cache keys while qualifying newer dependency releases."""

import unittest
from unittest.mock import patch

from kipp.decorator import calculate_args_hash, timeout_cache


class HashCompatibilityTests(unittest.TestCase):
    """HashCompatibilityTests protects stable keys, cache hits and expiry."""

    def test_legacy_keys_are_identical_for_supported_hash_versions(self):
        """test_legacy_keys_are_identical_for_supported_hash_versions checks frozen xxhash 1.4.4 vectors."""
        vectors = [
            ((), {}, "a892f6cd"),
            ((1, 2, 3), {}, "e149b888"),
            (("中文",), {}, "6a6de4fa"),
            ((b"bytes", None, True), {}, "1784ebf9"),
            ((1,), {"name": "alpha"}, "2707ef6a"),
            ((1,), {"name": "beta"}, "22a86dc1"),
            ((), {"a": 1, "b": 2}, "dbeaf971"),
        ]
        for args, kwargs, expected in vectors:
            with self.subTest(args=args, kwargs=kwargs):
                self.assertEqual(calculate_args_hash(*args, **kwargs), expected)

    def test_cache_hit_separation_and_expiry_remain_compatible(self):
        """test_cache_hit_separation_and_expiry_remain_compatible verifies actual decorated calls."""
        clock = {"now": 0.0}
        calls = []

        @timeout_cache(expires_sec=30)
        def cached(value, name="alpha"):
            """cached returns an invocation marker when its entry is absent or stale."""
            calls.append((value, name))
            return len(calls)

        with patch("kipp.decorator.time", side_effect=lambda: clock["now"]):
            self.assertEqual(cached("中文", name="alpha"), 1)
            self.assertEqual(cached("中文", name="alpha"), 1)
            self.assertEqual(cached("中文", name="beta"), 2)
            clock["now"] = 31.0
            self.assertEqual(cached("中文", name="alpha"), 3)
        self.assertEqual(
            calls, [("中文", "alpha"), ("中文", "beta"), ("中文", "alpha")]
        )


if __name__ == "__main__":
    unittest.main()
