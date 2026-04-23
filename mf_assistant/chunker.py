"""Word-based chunker over normalized documents.

Reads ``data/normalized/*.json`` (produced by ``ingest.py``) and writes one
``chunks.jsonl`` line per chunk to ``data/chunks/chunks.jsonl``. Each chunk
carries the metadata needed for later retrieval and citation.

Strategy:
- Split text into words.
- Pack words into windows of ~600 words (configurable 500-800).
- Overlap ~100 words between adjacent windows.
- Drop empty or extremely tiny chunks (< MIN_WORDS).

Run:
    PYTHONPATH=. python -m mf_assistant.chunker
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
CHUNKS_DIR = DATA_DIR / "chunks"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_JSONL = CHUNKS_DIR / "chunks.jsonl"

# --- Tunables ---
TARGET_WORDS = 600     # within the requested 500-800 range
OVERLAP_WORDS = 100
MIN_WORDS = 40         # drop "extremely tiny" chunks
MAX_WORDS = 800        # hard cap


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    source_id: str
    source_type: str
    source_name: str
    url: str
    scheme_name: str
    page_type: str
    last_updated_from_source: str
    chunk_index: int
    text: str


# ---------- helpers ----------

_WORD_RE = re.compile(r"\S+")


def _tokenize_words(text: str) -> List[str]:
    """Whitespace-based tokenization that preserves punctuation with words."""
    return _WORD_RE.findall(text or "")


def split_words(
    words: List[str],
    *,
    target: int = TARGET_WORDS,
    overlap: int = OVERLAP_WORDS,
    max_words: int = MAX_WORDS,
    min_words: int = MIN_WORDS,
) -> List[str]:
    """Pack a word list into overlapping chunks; return chunk strings."""
    if not words:
        return []
    target = max(1, min(target, max_words))
    overlap = max(0, min(overlap, target - 1))
    step = target - overlap

    # If the doc is very short but above the min, return as a single chunk.
    if len(words) <= target:
        return [" ".join(words)] if len(words) >= min_words else []

    chunks: List[str] = []
    start = 0
    n = len(words)
    while start < n:
        end = min(start + target, n)
        piece = " ".join(words[start:end])
        if len(words[start:end]) >= min_words:
            chunks.append(piece)
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


# ---------- IO ----------

def load_normalized_docs(path: Path = NORMALIZED_DIR) -> List[dict]:
    docs: List[dict] = []
    if not path.exists():
        return docs
    for p in sorted(path.glob("*.json")):
        try:
            docs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return docs


def make_chunk_records(doc: dict) -> List[ChunkRecord]:
    text = doc.get("text", "") or ""
    words = _tokenize_words(text)
    pieces = split_words(words)

    source_id = doc.get("source_id", "")
    doc_id = source_id  # one normalized doc per source
    out: List[ChunkRecord] = []
    for i, piece in enumerate(pieces):
        out.append(
            ChunkRecord(
                chunk_id=f"{doc_id}::chunk_{i:04d}",
                doc_id=doc_id,
                source_id=source_id,
                source_type=doc.get("source_type", ""),
                source_name=doc.get("source_name", ""),
                url=doc.get("url", ""),
                scheme_name=doc.get("scheme_name", ""),
                page_type=doc.get("page_type", ""),
                last_updated_from_source=doc.get("last_updated_from_source", "") or "",
                chunk_index=i,
                text=piece,
            )
        )
    return out


def write_chunks_jsonl(records: Iterable[ChunkRecord], path: Path = CHUNKS_JSONL) -> int:
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            n += 1
    return n


def build_chunks(verbose: bool = True) -> List[ChunkRecord]:
    docs = load_normalized_docs()
    all_records: List[ChunkRecord] = []
    per_doc: Counter[str] = Counter()
    for d in docs:
        recs = make_chunk_records(d)
        all_records.extend(recs)
        per_doc[d.get("source_id", "<unknown>")] = len(recs)

    n_written = write_chunks_jsonl(all_records)

    if verbose:
        print(f"Loaded {len(docs)} normalized documents")
        print(f"Wrote {n_written} chunks to {CHUNKS_JSONL}")
        print("Chunks per document:")
        for sid, cnt in per_doc.most_common():
            print(f"  {sid:24s} {cnt:>4d}")
        # Sample 1-2 chunks for sanity
        for sample in all_records[:2]:
            preview = sample.text[:300].replace("\n", " ")
            print(
                f"\nSample [{sample.chunk_id}] doc={sample.doc_id} "
                f"page_type={sample.page_type} words≈{len(_tokenize_words(sample.text))}\n"
                f"  {preview}…"
            )
    return all_records


# ---------- legacy adapter (used by build_index.py) ----------

@dataclass
class Chunk:
    text: str
    source_id: str
    scheme_id: str
    url: str
    last_checked: str


def make_chunks(
    text: str,
    *,
    source_id: str,
    scheme_id: str,
    url: str,
    last_checked: str,
    chunk_size: Optional[int] = None,  # kept for backward compat; unused
    overlap: Optional[int] = None,     # kept for backward compat; unused
) -> List[Chunk]:
    """Backward-compatible helper used by ``build_index.py``.

    Uses the same word-based packer so the retrieval index and the new
    ``chunks.jsonl`` stay consistent.
    """
    pieces = split_words(_tokenize_words(text))
    return [
        Chunk(text=p, source_id=source_id, scheme_id=scheme_id, url=url, last_checked=last_checked)
        for p in pieces
    ]


if __name__ == "__main__":
    build_chunks(verbose=True)
