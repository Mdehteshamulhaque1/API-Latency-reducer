"""
Output checks for model answers.

``grounding_score`` is a cheap lexical check: for every sentence in the
answer, what share of its content words also appear in the retrieved
sources (or the measured facts)? A sentence is "supported" when at least
half of its content words are found. The score is the supported share of
all sentences. It catches answers that drift away from the provided
material; it does not prove correctness, and short numeric sentences can
score low even when right. The score is reported to the caller, never used
to rewrite the answer.
"""
import re
from typing import Iterable, List

INSUFFICIENT_CONTEXT = (
    "I don't have enough information in the available data to answer that."
)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-/.]{2,}")
_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
    "have", "has", "had", "not", "but", "you", "your", "can", "will", "would",
    "should", "could", "about", "into", "than", "then", "them", "they", "there",
    "their", "which", "what", "when", "where", "while", "also", "been", "being",
    "more", "most", "some", "such", "very", "each", "other", "these", "those",
    "because", "however", "therefore", "between", "based", "using", "used",
}


def _content_words(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS]


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


def grounding_score(answer: str, sources: Iterable[str]) -> float:
    """Share of answer sentences whose content words mostly appear in sources."""
    vocabulary = set()
    for source in sources:
        vocabulary.update(_content_words(source))
    sentences = _sentences(answer)
    if not sentences:
        return 0.0
    if not vocabulary:
        return 0.0
    supported = 0
    for sentence in sentences:
        words = _content_words(sentence)
        if not words:
            supported += 1  # nothing to check, e.g. "Yes."
            continue
        hits = sum(1 for w in words if w in vocabulary)
        if hits / len(words) >= 0.5:
            supported += 1
    return round(supported / len(sentences), 3)


def validate_answer(answer: str, max_length: int = 8000) -> str:
    """Normalise a model answer and reject empty or oversized output."""
    cleaned = (answer or "").strip()
    if not cleaned:
        raise ValueError("Model returned an empty answer")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + " …"
    return cleaned
