"""Build a FAISS vector index from chunks.jsonl.

Reads ``data/chunks/chunks.jsonl``, embeds each chunk with a small
SentenceTransformer model, and writes:

- ``data/index/faiss.index``   — the FAISS vector index (cosine via inner-product on normalized vectors)
- ``data/index/meta.jsonl``    — one JSON line of chunk metadata per vector (aligned by row)
- ``data/index/info.json``     — model name, dim, chunk count, build timestamp

Run:
    PYTHONPATH=. python -m mf_assistant.build_index
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .config import (
    CHUNKS_JSONL,
    EMBED_DIM,
    EMBED_MODEL_NAME,
    FAISS_INDEX_PATH,
    INDEX_DIR,
    INDEX_INFO_PATH,
    META_PATH,
)

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

INDEX_DIR.mkdir(parents=True, exist_ok=True)


def _read_chunks(path: Path = CHUNKS_JSONL) -> List[dict]:
    if not path.exists():
        return []
    chunks: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except Exception:
                continue
    return chunks


def build(verbose: bool = True) -> int:
    """Build and persist the FAISS index. Returns number of vectors."""
    chunks = _read_chunks()
    if not chunks:
        if verbose:
            print(f"No chunks found at {CHUNKS_JSONL}. Run chunker.py first.")
        return 0

    # Lazy imports - heavy
    import numpy as np
    import faiss  # type: ignore
    from sentence_transformers import SentenceTransformer  # type: ignore

    if verbose:
        print(f"Loading model: {EMBED_MODEL_NAME}")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    texts = [c["text"] for c in chunks]
    if verbose:
        print(f"Embedding {len(texts)} chunks…")
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=verbose,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    assert vectors.shape[1] == EMBED_DIM, (
        f"Expected embedding dim {EMBED_DIM}, got {vectors.shape[1]}"
    )

    # Cosine similarity via inner product on L2-normalized vectors.
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(vectors)
    faiss.write_index(index, str(FAISS_INDEX_PATH))

    with META_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    INDEX_INFO_PATH.write_text(
        json.dumps(
            {
                "model": EMBED_MODEL_NAME,
                "dim": EMBED_DIM,
                "count": len(chunks),
                "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if verbose:
        print(f"Built FAISS index with {len(chunks)} vectors → {FAISS_INDEX_PATH}")
    return len(chunks)


if __name__ == "__main__":
    build(verbose=True)
