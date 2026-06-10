"""Dependency-free text similarity helpers for lightweight analytics workflows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log, sqrt
import re
from typing import Iterable, Mapping, Sequence

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")

_DEFAULT_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "with",
    }
)

_DEFAULT_TOKEN_ALIASES: Mapping[str, str] = {
    "advance": "rise",
    "advanced": "rise",
    "advances": "rise",
    "advancing": "rise",
    "ai": "artificial_intelligence",
    "bearish": "negative",
    "bullish": "positive",
    "chip": "semiconductor",
    "chips": "semiconductor",
    "decline": "fall",
    "declined": "fall",
    "declines": "fall",
    "declining": "fall",
    "drop": "fall",
    "dropped": "fall",
    "dropping": "fall",
    "drops": "fall",
    "equities": "stock",
    "equity": "stock",
    "gain": "rise",
    "gained": "rise",
    "gaining": "rise",
    "gains": "rise",
    "optimism": "positive",
    "optimistic": "positive",
    "pessimism": "negative",
    "pessimistic": "negative",
    "rallied": "rise",
    "rallies": "rise",
    "rally": "rise",
    "rallying": "rise",
    "selloff": "fall",
    "selloffs": "fall",
    "share": "stock",
    "shares": "stock",
    "slid": "fall",
    "slide": "fall",
    "slides": "fall",
    "sliding": "fall",
    "stock": "stock",
    "stocks": "stock",
    "upbeat": "positive",
}


@dataclass(frozen=True)
class SimilarityMatch:
    """Ranked similarity result for a candidate text."""

    index: int
    text: str
    score: float


def tokenize(
    text: str,
    *,
    stop_words: Iterable[str] | None = _DEFAULT_STOP_WORDS,
    token_aliases: Mapping[str, str] | None = _DEFAULT_TOKEN_ALIASES,
) -> list[str]:
    """Normalize text into lowercase word tokens.

    Args:
        text: Text to tokenize.
        stop_words: Optional words to remove after lowercasing. Pass ``None`` to
            keep every token.
        token_aliases: Optional canonical aliases for common synonyms or domain
            terms. Pass ``None`` to keep tokens exactly as extracted.

    Returns:
        A list of normalized tokens in their original order.
    """
    normalized_stop_words = {word.lower() for word in stop_words} if stop_words else set()
    normalized_aliases = (
        {token.lower(): alias.lower() for token, alias in token_aliases.items()}
        if token_aliases
        else {}
    )

    tokens: list[str] = []
    for match in _WORD_RE.finditer(str(text)):
        token = match.group(0).lower()
        if token in normalized_stop_words:
            continue
        tokens.append(normalized_aliases.get(token, token))
    return tokens


def term_frequency(tokens: Iterable[str]) -> dict[str, float]:
    """Build a length-normalized term-frequency vector from tokens."""
    counts = Counter(tokens)
    total = sum(counts.values())
    if not total:
        return {}
    return {term: count / total for term, count in counts.items()}


def _inverse_document_frequency(documents: Sequence[Sequence[str]]) -> dict[str, float]:
    """Calculate smoothed inverse-document-frequency weights."""
    document_count = len(documents)
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(set(document))

    return {
        term: log((1 + document_count) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }


def _tf_idf_vector(tokens: Sequence[str], idf: dict[str, float]) -> dict[str, float]:
    """Create a TF-IDF vector for a tokenized document."""
    return {
        term: frequency * idf.get(term, 1.0)
        for term, frequency in term_frequency(tokens).items()
    }


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    """Return cosine similarity between two sparse vectors.

    The return value is in the range ``0.0`` to ``1.0`` for non-negative input
    vectors. Empty vectors return ``0.0``.
    """
    if not left or not right:
        return 0.0

    common_terms = set(left) & set(right)
    numerator = sum(left[term] * right[term] for term in common_terms)
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def semantic_similarity(
    left: str,
    right: str,
    *,
    stop_words: Iterable[str] | None = _DEFAULT_STOP_WORDS,
    token_aliases: Mapping[str, str] | None = _DEFAULT_TOKEN_ALIASES,
) -> float:
    """Score two texts using alias-normalized TF-IDF cosine similarity.

    This lightweight implementation is suitable for ranking similar headlines,
    notes, or short dashboard snippets without adding an embedding-model
    dependency. Scores closer to ``1.0`` indicate more similar text, while
    unrelated or empty text scores ``0.0``.
    """
    tokenized_documents = [
        tokenize(left, stop_words=stop_words, token_aliases=token_aliases),
        tokenize(right, stop_words=stop_words, token_aliases=token_aliases),
    ]
    idf = _inverse_document_frequency(tokenized_documents)
    return cosine_similarity(
        _tf_idf_vector(tokenized_documents[0], idf),
        _tf_idf_vector(tokenized_documents[1], idf),
    )


def rank_similar_texts(
    query: str,
    candidates: Sequence[str],
    *,
    limit: int | None = None,
    min_score: float = 0.0,
    stop_words: Iterable[str] | None = _DEFAULT_STOP_WORDS,
    token_aliases: Mapping[str, str] | None = _DEFAULT_TOKEN_ALIASES,
) -> list[SimilarityMatch]:
    """Rank candidate texts by similarity to a query.

    Args:
        query: Text to compare against every candidate.
        candidates: Candidate texts to rank.
        limit: Optional maximum number of matches to return.
        min_score: Drop matches below this score.
        stop_words: Optional words to remove during tokenization.
        token_aliases: Optional canonical aliases for common synonyms or domain
            terms. Pass ``None`` to disable alias normalization.

    Returns:
        Similarity matches sorted by descending score, preserving the original
        candidate index in each result.
    """
    if limit is not None and limit < 0:
        raise ValueError("limit cannot be negative")
    if min_score < 0:
        raise ValueError("min_score cannot be negative")

    tokenized_query = tokenize(
        query,
        stop_words=stop_words,
        token_aliases=token_aliases,
    )
    tokenized_candidates = [
        tokenize(candidate, stop_words=stop_words, token_aliases=token_aliases)
        for candidate in candidates
    ]
    idf = _inverse_document_frequency([tokenized_query, *tokenized_candidates])
    query_vector = _tf_idf_vector(tokenized_query, idf)

    matches = [
        SimilarityMatch(
            index=index,
            text=candidate,
            score=cosine_similarity(query_vector, _tf_idf_vector(tokens, idf)),
        )
        for index, (candidate, tokens) in enumerate(zip(candidates, tokenized_candidates))
    ]
    ranked_matches = sorted(
        (match for match in matches if match.score >= min_score),
        key=lambda match: (-match.score, match.index),
    )
    return ranked_matches if limit is None else ranked_matches[:limit]
