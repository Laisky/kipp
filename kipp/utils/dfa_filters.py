#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any


class DFAFilter:
    """Deterministic Finite Automaton based keyword filter.

    Builds a trie (prefix tree) from a set of keywords, then scans input text
    to find all occurrences of those keywords in O(n) time per character.

    Examples:
    ::
        dfa_filter = DFAFilter()
        dfa_filter.build_chains(keywords_set)
        dfa_filter.load_keywords(raw_text)
    """

    _chains: dict[str, Any]

    def load_keywords(self, raw_text: str) -> set[str]:
        """Scan raw_text and return all keywords found within it.

        Args:
            raw_text: text to scan for keyword matches

        Returns:
            Set of matched keywords found in raw_text
        """
        assert getattr(self, "_chains", None), "Should invoke build_chains first"
        return self.filter_keyword(raw_text)

    def build_chains(self, keywords: set[str]) -> None:
        """Construct the trie from a keyword lexicon.

        Each keyword is decomposed character-by-character into nested dicts.
        A leaf node is represented by an empty dict, signaling end-of-word.

        Args:
            keywords: lexicon of keywords to search for
        """
        chains: dict[str, Any] = {}
        for word in keywords:
            node = chains
            for char in word:
                if char not in node:
                    node[char] = {}

                node = node[char]

        self._chains = chains

    def is_word_in_chains(
        self, chains: dict[str, Any], raw_text: str, n_len: int, i: int
    ) -> int | None:
        """Recursively walk the trie to check if a keyword starts at position i.

        Returns the end index (inclusive) of the matched keyword, or None if
        no complete keyword is found along this path.
        """
        if raw_text[i] not in chains:
            return None

        # Empty dict at this node means we reached a leaf -- keyword ends here
        if not chains[raw_text[i]]:
            return i

        # Reached end of text without completing a keyword path
        if i == n_len - 1:
            return None

        return self.is_word_in_chains(
            chains=chains[raw_text[i]], raw_text=raw_text, n_len=n_len, i=i + 1
        )

    def filter_keyword(self, raw_text: str) -> set[str]:
        """Scan text against the trie and collect all matched keywords."""
        result_keywords: set[str] = set()
        i, n_len = 0, len(raw_text)
        for i in range(n_len):
            li = self.is_word_in_chains(self._chains, raw_text, n_len, i)
            if li is not None:
                result_keywords.add(raw_text[i : li + 1])

        return result_keywords
