#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from unittest import TestCase

from kipp.utils.dfa_filters import DFAFilter


class DFAFilterBuildChainsTestCase(TestCase):
    """Tests for DFAFilter.build_chains."""

    def test_build_chains_creates_trie(self):
        f = DFAFilter()
        f.build_chains({"abc"})
        self.assertIn("a", f._chains)
        self.assertIn("b", f._chains["a"])
        self.assertIn("c", f._chains["a"]["b"])
        self.assertEqual(f._chains["a"]["b"]["c"], {})

    def test_build_chains_empty_set(self):
        f = DFAFilter()
        f.build_chains(set())
        self.assertEqual(f._chains, {})

    def test_build_chains_multiple_keywords_share_prefix(self):
        f = DFAFilter()
        f.build_chains({"ab", "abc"})
        self.assertIn("a", f._chains)
        self.assertIn("b", f._chains["a"])
        # "abc" adds 'c' to b's dict, so b is no longer an empty leaf
        self.assertIn("c", f._chains["a"]["b"])

    def test_build_chains_disjoint_keywords(self):
        f = DFAFilter()
        f.build_chains({"abc", "xyz"})
        self.assertIn("a", f._chains)
        self.assertIn("x", f._chains)
        self.assertEqual(len(f._chains), 2)

    def test_build_chains_single_char_keyword(self):
        f = DFAFilter()
        f.build_chains({"a"})
        self.assertIn("a", f._chains)
        self.assertEqual(f._chains["a"], {})

    def test_build_chains_unicode_keywords(self):
        f = DFAFilter()
        f.build_chains({"你好"})
        self.assertIn("你", f._chains)
        self.assertIn("好", f._chains["你"])
        self.assertEqual(f._chains["你"]["好"], {})

    def test_build_chains_overwrites_previous(self):
        f = DFAFilter()
        f.build_chains({"abc"})
        f.build_chains({"xyz"})
        self.assertNotIn("a", f._chains)
        self.assertIn("x", f._chains)

    def test_build_chains_shared_prefix_three_keywords(self):
        f = DFAFilter()
        f.build_chains({"a", "ab", "abc"})
        # 'a' node has child 'b', so it is not empty -- 'a' alone won't match
        self.assertIn("b", f._chains["a"])
        self.assertIn("c", f._chains["a"]["b"])
        self.assertEqual(f._chains["a"]["b"]["c"], {})


class DFAFilterLoadKeywordsTestCase(TestCase):
    """Tests for DFAFilter.load_keywords."""

    def test_load_keywords_without_build_chains_asserts(self):
        f = DFAFilter()
        with self.assertRaises(AssertionError):
            f.load_keywords("some text")

    def test_empty_keywords_no_matches(self):
        f = DFAFilter()
        f.build_chains(set())
        # Empty chains dict is falsy, so assertion fires
        with self.assertRaises(AssertionError):
            f.load_keywords("some text")

    def test_no_matches_found(self):
        f = DFAFilter()
        f.build_chains({"xyz"})
        result = f.load_keywords("hello world")
        self.assertEqual(result, set())

    def test_single_match(self):
        f = DFAFilter()
        f.build_chains({"hello"})
        result = f.load_keywords("say hello there")
        self.assertEqual(result, {"hello"})

    def test_multiple_matches(self):
        f = DFAFilter()
        f.build_chains({"cat", "dog"})
        result = f.load_keywords("I have a cat and a dog")
        self.assertEqual(result, {"cat", "dog"})

    def test_keyword_at_start(self):
        f = DFAFilter()
        f.build_chains({"abc"})
        result = f.load_keywords("abcdef")
        self.assertEqual(result, {"abc"})

    def test_keyword_at_end(self):
        f = DFAFilter()
        f.build_chains({"def"})
        result = f.load_keywords("abcdef")
        self.assertEqual(result, {"def"})

    def test_keyword_in_middle(self):
        f = DFAFilter()
        f.build_chains({"bcd"})
        result = f.load_keywords("abcde")
        self.assertEqual(result, {"bcd"})

    def test_overlapping_keywords_longer_wins(self):
        # When "ab" and "abc" share a prefix, the trie node for 'b' is not
        # empty (it has child 'c'), so "ab" cannot match. Only "abc" matches.
        f = DFAFilter()
        f.build_chains({"ab", "abc"})
        result = f.load_keywords("abcdef")
        self.assertEqual(result, {"abc"})

    def test_overlapping_keywords_shorter_cannot_match_alone(self):
        # "ab" won't match because node b has child 'c' (not empty),
        # and 'x' is not in b's children, so the walk fails.
        f = DFAFilter()
        f.build_chains({"ab", "abc"})
        result = f.load_keywords("abx")
        self.assertEqual(result, set())

    def test_overlapping_keywords_both_in_text_separately(self):
        # "ab" alone won't match due to trie structure, even at a separate position
        f = DFAFilter()
        f.build_chains({"ab", "abc"})
        result = f.load_keywords("abc ab")
        self.assertEqual(result, {"abc"})

    def test_single_character_keywords(self):
        f = DFAFilter()
        f.build_chains({"a", "b"})
        result = f.load_keywords("a test b here")
        self.assertEqual(result, {"a", "b"})

    def test_single_char_keyword_shadowed_by_longer(self):
        # "a" has child 'b' in the trie, so standalone "a" won't match
        f = DFAFilter()
        f.build_chains({"a", "ab"})
        result = f.load_keywords("a")
        self.assertEqual(result, set())

    def test_single_char_keyword_not_shadowed(self):
        # If "a" is the only keyword, it matches fine
        f = DFAFilter()
        f.build_chains({"a"})
        result = f.load_keywords("a")
        self.assertEqual(result, {"a"})

    def test_unicode_chinese_characters(self):
        f = DFAFilter()
        keywords = {"你好", "世界"}
        f.build_chains(keywords)
        result = f.load_keywords("你好世界欢迎")
        self.assertEqual(result, {"你好", "世界"})

    def test_unicode_mixed_with_ascii(self):
        f = DFAFilter()
        f.build_chains({"hello", "你好"})
        result = f.load_keywords("say hello and 你好")
        self.assertEqual(result, {"hello", "你好"})

    def test_repeated_keywords_in_text(self):
        f = DFAFilter()
        f.build_chains({"ab"})
        result = f.load_keywords("ababab")
        # Returns a set, so duplicates are collapsed
        self.assertEqual(result, {"ab"})

    def test_large_keyword_set(self):
        f = DFAFilter()
        keywords = {"kw_{:04d}".format(i) for i in range(1000)}
        f.build_chains(keywords)
        result = f.load_keywords("this text contains kw_0042 and kw_0999")
        self.assertEqual(result, {"kw_0042", "kw_0999"})

    def test_large_keyword_set_no_match(self):
        f = DFAFilter()
        keywords = {"kw_{:04d}".format(i) for i in range(1000)}
        f.build_chains(keywords)
        result = f.load_keywords("nothing here matches")
        self.assertEqual(result, set())

    def test_keyword_is_entire_text(self):
        f = DFAFilter()
        f.build_chains({"hello"})
        result = f.load_keywords("hello")
        self.assertEqual(result, {"hello"})

    def test_empty_text(self):
        f = DFAFilter()
        f.build_chains({"hello"})
        result = f.load_keywords("")
        self.assertEqual(result, set())

    def test_keyword_with_spaces(self):
        f = DFAFilter()
        f.build_chains({"hello world"})
        result = f.load_keywords("say hello world now")
        self.assertEqual(result, {"hello world"})

    def test_keyword_with_special_characters(self):
        f = DFAFilter()
        f.build_chains({"a+b", "x*y"})
        result = f.load_keywords("compute a+b and x*y")
        self.assertEqual(result, {"a+b", "x*y"})

    def test_adjacent_keywords_no_overlap(self):
        f = DFAFilter()
        f.build_chains({"ab", "cd"})
        result = f.load_keywords("abcd")
        self.assertEqual(result, {"ab", "cd"})

    def test_keyword_longer_than_text(self):
        f = DFAFilter()
        f.build_chains({"abcdefghij"})
        result = f.load_keywords("abc")
        self.assertEqual(result, set())

    def test_many_single_char_keywords(self):
        f = DFAFilter()
        f.build_chains({"a", "b", "c", "d", "e"})
        result = f.load_keywords("abcde")
        self.assertEqual(result, {"a", "b", "c", "d", "e"})

    def test_text_with_only_non_keyword_chars(self):
        f = DFAFilter()
        f.build_chains({"abc"})
        result = f.load_keywords("xyz xyz xyz")
        self.assertEqual(result, set())

    def test_multiple_occurrences_different_keywords(self):
        f = DFAFilter()
        f.build_chains({"foo", "bar"})
        result = f.load_keywords("foo bar foo bar")
        self.assertEqual(result, {"foo", "bar"})


class DFAFilterIsWordInChainsTestCase(TestCase):
    """Tests for DFAFilter.is_word_in_chains."""

    def test_returns_end_index_on_match(self):
        f = DFAFilter()
        f.build_chains({"abc"})
        result = f.is_word_in_chains(f._chains, "abcde", 5, 0)
        self.assertEqual(result, 2)

    def test_returns_none_on_no_match(self):
        f = DFAFilter()
        f.build_chains({"xyz"})
        result = f.is_word_in_chains(f._chains, "abcde", 5, 0)
        self.assertIsNone(result)

    def test_returns_none_when_text_ends_before_keyword(self):
        f = DFAFilter()
        f.build_chains({"abcdef"})
        result = f.is_word_in_chains(f._chains, "abc", 3, 0)
        self.assertIsNone(result)

    def test_match_starting_at_nonzero_index(self):
        f = DFAFilter()
        f.build_chains({"cd"})
        result = f.is_word_in_chains(f._chains, "abcde", 5, 2)
        self.assertEqual(result, 3)

    def test_match_single_char_at_end_of_text(self):
        f = DFAFilter()
        f.build_chains({"e"})
        result = f.is_word_in_chains(f._chains, "abcde", 5, 4)
        self.assertEqual(result, 4)

    def test_no_match_single_char_not_in_text(self):
        f = DFAFilter()
        f.build_chains({"z"})
        result = f.is_word_in_chains(f._chains, "abcde", 5, 0)
        self.assertIsNone(result)

    def test_partial_match_returns_none(self):
        # "abc" keyword but text only has "ab" starting at position 0
        f = DFAFilter()
        f.build_chains({"abc"})
        result = f.is_word_in_chains(f._chains, "ab", 2, 0)
        self.assertIsNone(result)


class DFAFilterFilterKeywordTestCase(TestCase):
    """Tests for DFAFilter.filter_keyword directly."""

    def test_returns_set(self):
        f = DFAFilter()
        f.build_chains({"test"})
        result = f.filter_keyword("a test string")
        self.assertIsInstance(result, set)

    def test_empty_text_returns_empty_set(self):
        f = DFAFilter()
        f.build_chains({"test"})
        result = f.filter_keyword("")
        self.assertEqual(result, set())

    def test_multiple_keywords_found(self):
        f = DFAFilter()
        f.build_chains({"one", "two", "three"})
        result = f.filter_keyword("one and two and three")
        self.assertEqual(result, {"one", "two", "three"})

    def test_no_keywords_found(self):
        f = DFAFilter()
        f.build_chains({"missing"})
        result = f.filter_keyword("nothing here")
        self.assertEqual(result, set())
