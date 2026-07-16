"""Pure, deterministic text chunking.

Retrieval v1 indexes one chunk per paper (title + abstract), which almost
always fits a single window; the same function handles section-aware full-text
chunking later without API changes.
"""


def paper_chunk(title: str, abstract: str) -> str:
    """The v1 retrieval unit for a paper."""
    return f"{title.strip()}\n\n{abstract.strip()}".strip()


def chunk_text(text: str, *, max_words: int = 220, overlap_words: int = 40) -> list[str]:
    """Split text into word windows of at most max_words with fixed overlap."""
    if max_words <= 0:
        raise ValueError("max_words must be positive")
    if not 0 <= overlap_words < max_words:
        raise ValueError("overlap_words must be in [0, max_words)")

    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [" ".join(words)]

    step = max_words - overlap_words
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + max_words]))
        if start + max_words >= len(words):
            break
        start += step
    return chunks
