"""
Chunking: split a document into overlapping, paragraph-aware pieces.

Why chunk at all: embeddings represent one passage as one vector. A whole
manual as a single vector would match everything a little and nothing well.
Chunks of roughly a paragraph or two (``size`` characters) keep each vector
about one topic; the ``overlap`` repeats the tail of the previous chunk so a
sentence cut at a boundary still appears whole in one of them.
"""
from typing import List


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> List[str]:
    """Return chunks of at most ``size`` characters with ``overlap`` carried over."""
    if size <= 0:
        raise ValueError("size must be positive")
    overlap = max(0, min(overlap, size // 2))
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for paragraph in paragraphs:
        # Paragraph longer than a chunk: slice it with overlap.
        if len(paragraph) > size:
            flush()
            start = 0
            while start < len(paragraph):
                end = min(start + size, len(paragraph))
                piece = paragraph[start:end]
                # Prefer to end on a sentence boundary when one is near.
                if end < len(paragraph):
                    cut = max(piece.rfind(". "), piece.rfind("\n"))
                    if cut > size * 0.5:
                        piece = piece[: cut + 1]
                        end = start + len(piece)
                chunks.append(piece.strip())
                if end >= len(paragraph):
                    break
                start = max(end - overlap, start + 1)
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= size:
            current = candidate
        else:
            flush()
            # Start the next chunk with the overlap tail of the previous one.
            tail = chunks[-1][-overlap:] if chunks and overlap else ""
            current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
            if len(current) > size:
                current = paragraph
    flush()
    return [c for c in chunks if c]
