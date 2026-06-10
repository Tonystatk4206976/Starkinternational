"""Tests for semantic similarity helpers."""

from __future__ import annotations

import unittest

from semantic_similarity import rank_similar_texts, semantic_similarity, tokenize


class SemanticSimilarityTests(unittest.TestCase):
    def test_tokenize_applies_stop_words_and_aliases(self) -> None:
        self.assertEqual(
            tokenize("The chip stocks rally"),
            ["semiconductor", "stock", "rise"],
        )

    def test_semantic_similarity_uses_aliases_by_default(self) -> None:
        score = semantic_similarity(
            "Chip stocks rally after upbeat AI demand",
            "Semiconductor shares rise on positive artificial intelligence demand",
        )
        lexical_only_score = semantic_similarity(
            "Chip stocks rally after upbeat AI demand",
            "Semiconductor shares rise on positive artificial intelligence demand",
            token_aliases=None,
        )

        self.assertGreater(score, lexical_only_score)
        self.assertGreater(score, 0.5)

    def test_rank_similar_texts_filters_and_preserves_index(self) -> None:
        matches = rank_similar_texts(
            "defensive stock rally",
            [
                "cash parking while volatility is elevated",
                "shares advance in broad market rally",
                "unrelated weather forecast",
            ],
            limit=1,
            min_score=0.1,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].index, 1)
        self.assertGreater(matches[0].score, 0.1)

    def test_invalid_options_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            rank_similar_texts("query", ["candidate"], limit=-1)
        with self.assertRaises(ValueError):
            rank_similar_texts("query", ["candidate"], min_score=-0.1)


if __name__ == "__main__":
    unittest.main()
