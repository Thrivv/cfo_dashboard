"""Hybrid text chunking utilities for document processing (semantic + backward compatible)."""

from typing import List
import re

# ---------------------------------------------------------------------------
# Basic sentence splitting
# ---------------------------------------------------------------------------

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')

def split_into_sentences(text: str) -> List[str]:
    """Lightweight sentence splitter that handles newlines and punctuation."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    sentences = []
    for p in paragraphs:
        sents = [s.strip() for s in _SENTENCE_END.split(p) if s.strip()]
        sentences.extend(sents)
    return sentences


# ---------------------------------------------------------------------------
# Semantic / Paragraph-based chunking
# ---------------------------------------------------------------------------

def chunk_text_semantic(
    text: str,
    target_words: int = 250,
    overlap_words: int = 50,
    max_words: int = 400,
) -> List[str]:
    """
    Create semantically coherent chunks by merging sentences until ~target_words.
    Keeps numeric tokens and uses small overlap for continuity.
    """
    sentences = split_into_sentences(text)
    sent_words = [s.split() for s in sentences]
    chunks = []

    i = 0
    while i < len(sent_words):
        cur = []
        cur_count = 0
        j = i

        while j < len(sent_words) and cur_count < target_words:
            cur.extend(sent_words[j])
            cur_count += len(sent_words[j])
            j += 1
            if cur_count >= max_words:
                break

        if cur:
            chunks.append(" ".join(cur))

        # Backward overlap step
        if j >= len(sent_words):
            break
        back_count = 0
        k = j - 1
        while k >= 0 and back_count < overlap_words:
            back_count += len(sent_words[k])
            k -= 1
        i = max(k + 1, j)

    return chunks


# ---------------------------------------------------------------------------
# Fixed-size (legacy) chunking
# ---------------------------------------------------------------------------

def chunk_text_fixed(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """Legacy fixed-size chunking for backward compatibility."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Unified API
# ---------------------------------------------------------------------------

def chunk_for_document(text: str, mode: str = "semantic") -> List[str]:
    """Wrapper to choose between semantic or fixed chunking."""
    if mode == "fixed":
        return chunk_text_fixed(text)
    return chunk_text_semantic(text)


# ---------------------------------------------------------------------------
# Backward Compatibility Export
# ---------------------------------------------------------------------------

def chunk_text(text: str, *args, **kwargs) -> List[str]:
    """
    Backward-compatible alias for chunk_text_semantic().
    Allows legacy imports like `from utils.chunker import chunk_text`
    to keep working without code changes.
    """
    return chunk_text_semantic(text, *args, **kwargs)
