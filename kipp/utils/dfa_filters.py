#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class DFAFilter:
    """
    Examples:
    ::
        dfa_filter = DFAFilter()
        dfa_filter.build_chains(keywords_set)
        dfa_filter.load_keywords(raw_text)
    """

    def load_keywords(self, raw_text):
        """
        Args:
            raw_text (str):

        Returns:
            set: keywords that in raw_text
        """
        assert getattr(self, '_chains', None), 'Should invoke build_chains first'
        return self.filter_keyword(raw_text)

    def build_chains(self, keywords):
        """
        Args:
            keywords (set): lexicon of keywords
        """
        chains = {}
        for word in keywords:
            node = chains
            for char in word:
                if char not in node:
                    node[char] = {}

                node = node[char]

        self._chains = chains

    def is_word_in_chains(self, chains, raw_text, n_len, i):
        if raw_text[i] not in chains:
            return None

        if not chains[raw_text[i]]:
            return i

        if i == n_len - 1:
            return None

        return self.is_word_in_chains(chains=chains[raw_text[i]],
                                      raw_text=raw_text,
                                      n_len=n_len,
                                      i=i+1)

    def filter_keyword(self, raw_text):
        result_keywords = set()
        i, n_len = 0, len(raw_text)
        for i in range(n_len):
            li = self.is_word_in_chains(self._chains, raw_text, n_len, i)
            if li is not None:
                result_keywords.add(raw_text[i: li+1])

        return result_keywords
