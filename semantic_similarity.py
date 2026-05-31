"""Hugging Face sentence-similarity helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

DEFAULT_SENTENCE_SIMILARITY_MODEL = "sentence-transformers/multi-qa-mpnet-base-dot-v1"
DEFAULT_INFERENCE_PROVIDER = "hf-inference"


@dataclass(frozen=True)
class SentenceSimilarityResult:
    """Similarity scores for a source sentence against candidate sentences."""

    source_sentence: str
    sentences: tuple[str, ...]
    scores: tuple[float, ...]

    def ranked(self, *, descending: bool = True) -> list[tuple[str, float]]:
        """Return candidate sentences paired with scores, ordered by similarity."""
        return sorted(
            zip(self.sentences, self.scores, strict=True),
            key=lambda item: item[1],
            reverse=descending,
        )


def calculate_sentence_similarity(
    source_sentence: str,
    sentences: Sequence[str],
    *,
    model: str = DEFAULT_SENTENCE_SIMILARITY_MODEL,
    provider: str = DEFAULT_INFERENCE_PROVIDER,
    api_key: str | None = None,
) -> SentenceSimilarityResult:
    """Score sentence similarity with the Hugging Face Inference API.

    Args:
        source_sentence: Sentence to compare against each candidate.
        sentences: Candidate sentences to score.
        model: Hugging Face sentence-similarity model identifier.
        provider: Hugging Face inference provider name.
        api_key: Hugging Face API token. Defaults to the ``HF_TOKEN``
            environment variable.

    Returns:
        A frozen result object containing the source sentence, candidates, and
        similarity scores in the same order as ``sentences``.
    """
    if not source_sentence:
        raise ValueError("source_sentence cannot be empty")

    candidate_sentences = tuple(sentences)
    if not candidate_sentences:
        raise ValueError("sentences cannot be empty")
    if any(not sentence for sentence in candidate_sentences):
        raise ValueError("sentences cannot contain empty values")

    token = api_key or os.environ["HF_TOKEN"]

    from huggingface_hub import InferenceClient

    client = InferenceClient(provider=provider, api_key=token)
    scores = client.sentence_similarity(
        {
            "source_sentence": source_sentence,
            "sentences": list(candidate_sentences),
        },
        model=model,
    )

    return SentenceSimilarityResult(
        source_sentence=source_sentence,
        sentences=candidate_sentences,
        scores=tuple(float(score) for score in scores),
    )
