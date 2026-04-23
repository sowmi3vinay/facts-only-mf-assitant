"""Simple text chunker with character-based windows and overlap."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class Chunk:
    text: str
    source_id: str
    scheme_id: str
    url: str
    last_checked: str


def split_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    """Split text into overlapping windows of approximately ``chunk_size`` chars.

    A simple but effective baseline for small corpora. We break on paragraph or
    sentence boundaries when possible to keep chunks readable.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    # Prefer to break on double newlines, then single newlines, then spaces.
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            # Try to back off to a clean boundary
            window = text[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                idx = window.rfind(sep)
                if idx != -1 and idx > int(chunk_size * 0.5):
                    end = start + idx + len(sep)
                    break
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def make_chunks(
    text: str,
    *,
    source_id: str,
    scheme_id: str,
    url: str,
    last_checked: str,
    chunk_size: int = 800,
    overlap: int = 120,
) -> List[Chunk]:
    return [
        Chunk(text=t, source_id=source_id, scheme_id=scheme_id, url=url, last_checked=last_checked)
        for t in split_text(text, chunk_size=chunk_size, overlap=overlap)
    ]
