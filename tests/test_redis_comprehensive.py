#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock

from kipp.redis.utils import RedisUtils, WAIT_DB_KEY_DURATION


class RedisUtilsGetItemTestCase(TestCase):
    """Tests for RedisUtils.get_item."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_get_item_returns_decoded_string(self):
        self.mock_client.get.return_value = b"hello"
        result = self.utils.get_item("mykey")
        self.assertEqual(result, "hello")
        self.mock_client.get.assert_called_once_with("mykey")

    def test_get_item_returns_str_directly(self):
        self.mock_client.get.return_value = "already_str"
        result = self.utils.get_item("mykey")
        self.assertEqual(result, "already_str")

    def test_get_item_returns_empty_string_for_missing_key(self):
        self.mock_client.get.return_value = None
        result = self.utils.get_item("missing")
        self.assertEqual(result, "")


class RedisUtilsSetItemTestCase(TestCase):
    """Tests for RedisUtils.set_item."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_set_item_calls_client_set(self):
        self.utils.set_item("key", "val", 300)
        self.mock_client.set.assert_called_once_with("key", "val", ex=300)

    def test_set_item_with_different_expiry(self):
        self.utils.set_item("k", "v", 60)
        self.mock_client.set.assert_called_once_with("k", "v", ex=60)


class RedisUtilsGetItemWithPrefixTestCase(TestCase):
    """Tests for RedisUtils.get_item_with_prefix."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_returns_dict_of_matching_keys(self):
        self.mock_client.scan_iter.return_value = [b"prefix:a", b"prefix:b"]
        self.mock_client.mget.return_value = [b"val_a", b"val_b"]
        result = self.utils.get_item_with_prefix("prefix:")
        self.assertEqual(result, {"prefix:a": "val_a", "prefix:b": "val_b"})

    def test_returns_empty_dict_when_no_keys(self):
        self.mock_client.scan_iter.return_value = []
        result = self.utils.get_item_with_prefix("nokeys:")
        self.assertEqual(result, {})

    def test_raises_value_error_for_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.utils.get_item_with_prefix("")

    def test_skips_none_values(self):
        self.mock_client.scan_iter.return_value = [b"p:a", b"p:b", b"p:c"]
        self.mock_client.mget.return_value = [b"val_a", None, b"val_c"]
        result = self.utils.get_item_with_prefix("p:")
        self.assertEqual(result, {"p:a": "val_a", "p:c": "val_c"})

    def test_scan_iter_called_with_correct_pattern(self):
        self.mock_client.scan_iter.return_value = []
        self.utils.get_item_with_prefix("test_")
        self.mock_client.scan_iter.assert_called_once_with(match="test_*", count=10)


class RedisUtilsRpushTestCase(TestCase):
    """Tests for RedisUtils.rpush."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_rpush_calls_client_rpush(self):
        with patch("kipp.redis.utils.random") as mock_random:
            mock_random.randint.return_value = 50  # won't trigger llen check
            self.utils.rpush("mylist", "val1", "val2")
        self.mock_client.rpush.assert_called_once_with("mylist", "val1", "val2")

    def test_rpush_trims_when_too_long(self):
        """When random check triggers and list is >= 100, should trim."""
        with patch("kipp.redis.utils.random") as mock_random:
            mock_random.randint.return_value = 0  # triggers llen check
            self.mock_client.llen.return_value = 150
            self.utils.rpush("mylist", "val")

        self.mock_client.llen.assert_called_once_with("mylist")
        self.mock_client.ltrim.assert_called_once_with("mylist", -10, -1)
        self.mock_client.rpush.assert_called_once_with("mylist", "val")

    def test_rpush_no_trim_when_short(self):
        """When random check triggers but list is short, no trim."""
        with patch("kipp.redis.utils.random") as mock_random:
            mock_random.randint.return_value = 0
            self.mock_client.llen.return_value = 50
            self.utils.rpush("mylist", "val")

        self.mock_client.llen.assert_called_once_with("mylist")
        self.mock_client.ltrim.assert_not_called()

    def test_rpush_no_llen_check_most_of_time(self):
        """When random != 0, llen should not be called."""
        with patch("kipp.redis.utils.random") as mock_random:
            mock_random.randint.return_value = 42
            self.utils.rpush("mylist", "val")

        self.mock_client.llen.assert_not_called()
        self.mock_client.ltrim.assert_not_called()


class RedisUtilsLpopKeysBlockingTestCase(TestCase):
    """Tests for RedisUtils.lpop_keys_blocking."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_returns_first_available_value(self):
        self.mock_client.lpop.side_effect = [None, b"value"]
        with patch("kipp.redis.utils.time"):
            key, val = self.utils.lpop_keys_blocking(["q1", "q2"])
        self.assertEqual(key, "q2")
        self.assertEqual(val, "value")

    def test_polls_until_value_found(self):
        """Returns after a few rounds of None."""
        # First full round: all None. Second round: q1 has value.
        self.mock_client.lpop.side_effect = [None, None, b"found"]
        with patch("kipp.redis.utils.time"):
            key, val = self.utils.lpop_keys_blocking(["q1", "q2"])
        self.assertEqual(key, "q1")
        self.assertEqual(val, "found")

    def test_decodes_bytes(self):
        self.mock_client.lpop.return_value = b"bytes_val"
        with patch("kipp.redis.utils.time"):
            key, val = self.utils.lpop_keys_blocking(["q"])
        self.assertEqual(val, "bytes_val")


class RedisUtilsGetItemBlockingTestCase(TestCase):
    """Tests for RedisUtils.get_item_blocking."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_get_item_blocking_no_delete(self):
        """With delete=False, just polls until key exists."""
        self.mock_client.get.side_effect = [None, None, b"found"]
        with patch("kipp.redis.utils.time"):
            result = self.utils.get_item_blocking("mykey", delete=False)
        self.assertEqual(result, "found")

    def test_get_item_blocking_with_delete(self):
        """With delete=True (default), uses pipeline with watch."""
        mock_pipe = MagicMock()
        mock_pipe.__enter__ = MagicMock(return_value=mock_pipe)
        mock_pipe.__exit__ = MagicMock(return_value=False)
        mock_pipe.get.return_value = b"data"
        self.mock_client.pipeline.return_value = mock_pipe

        with patch("kipp.redis.utils.time"):
            result = self.utils.get_item_blocking("mykey", delete=True)

        self.assertEqual(result, "data")
        mock_pipe.watch.assert_called_with("mykey")
        mock_pipe.multi.assert_called()
        mock_pipe.delete.assert_called_with("mykey")
        mock_pipe.execute.assert_called()


class RedisUtilsDecodeTestCase(TestCase):
    """Tests for RedisUtils._decode."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.utils = RedisUtils(client=self.mock_client)

    def test_decode_bytes(self):
        self.assertEqual(self.utils._decode(b"hello"), "hello")

    def test_decode_str(self):
        self.assertEqual(self.utils._decode("hello"), "hello")

    def test_decode_utf8(self):
        self.assertEqual(self.utils._decode("你好".encode("utf-8")), "你好")
