"""Deterministic text chunking."""


def chunk_text(text: str, *, size: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into bounded overlapping chunks."""
    if size <= overlap:
        raise ValueError("chunk size must exceed overlap")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks
