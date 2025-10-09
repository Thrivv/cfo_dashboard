"""Text chunking utilities for document processing."""

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chunks text using a sliding window approach."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks
