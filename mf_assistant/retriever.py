"""Vector retrieval over the FAISS index.

Loads ``data/index/faiss.index`` plus its aligned metadata file, embeds the
user query with the same SentenceTransformer model used at build time, and
returns the top-k chunks with their metadata.

Optional post-filters: ``scheme_name`` and ``source_type``.

CLI debug:
    PYTHONPATH=. python -m mf_assistant.retriever \
        "What is the lock-in period for HDFC ELSS Tax Saver Fund?"
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .build_index import build as build_index
from .config import (
    DEFAULT_OVERFETCH,
    DEFAULT_TOP_K,
    EMBED_MODEL_NAME,
    FAISS_INDEX_PATH,
    META_PATH,
)

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


@dataclass
class Hit:
    score: float
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

    # ---- Backward-compat shim for the existing UI/responder ----
    @property
    def last_checked(self) -> str:
        return self.last_updated_from_source


class Retriever:
    """Loads the FAISS index + metadata and serves nearest-neighbor queries."""

    def __init__(self) -> None:
        self._model = None
        self._index = None
        self._meta: List[dict] = []
        self._load()

    # ---------- loading ----------
    def _load(self) -> None:
        if not FAISS_INDEX_PATH.exists() or not META_PATH.exists():
            # Build on first use so the app is functional out of the box.
            build_index(verbose=False)
        self._meta = self._read_meta(META_PATH)
        if self._meta:
            import faiss  # type: ignore

            self._index = faiss.read_index(str(FAISS_INDEX_PATH))

    @staticmethod
    def _read_meta(path: Path) -> List[dict]:
        out: List[dict] = []
        if not path.exists():
            return out
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(EMBED_MODEL_NAME)
        return self._model

    # ---------- query ----------
    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        *,
        scheme_name: Optional[str] = None,
        source_type: Optional[str] = None,
        min_score: float = 0.10,
    ) -> List[Hit]:
        """Return up to ``top_k`` chunks most relevant to ``query``.

        Filters:
            scheme_name — case-insensitive substring match on the chunk's scheme.
            source_type — exact match on 'html' or 'pdf'.
        """
        if not query or not self._index or not self._meta:
            return []

        import numpy as np  # noqa: F401

        model = self._ensure_model()
        qv = model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype("float32")

        k = min(max(top_k * 1, DEFAULT_OVERFETCH), len(self._meta))
        scores, idx = self._index.search(qv, k)
        scores = scores[0]
        idx = idx[0]

        scheme_q = (scheme_name or "").strip().lower()
        stype_q = (source_type or "").strip().lower()

        hits: List[Hit] = []
        for s, i in zip(scores, idx):
            if i < 0 or i >= len(self._meta):
                continue
            score = float(s)
            if score < min_score:
                continue
            m = self._meta[i]
            if scheme_q and scheme_q not in (m.get("scheme_name", "") or "").lower():
                continue
            if stype_q and stype_q != (m.get("source_type", "") or "").lower():
                continue
            hits.append(
                Hit(
                    score=score,
                    chunk_id=m.get("chunk_id", ""),
                    doc_id=m.get("doc_id", ""),
                    source_id=m.get("source_id", ""),
                    source_type=m.get("source_type", ""),
                    source_name=m.get("source_name", ""),
                    url=m.get("url", ""),
                    scheme_name=m.get("scheme_name", ""),
                    page_type=m.get("page_type", ""),
                    last_updated_from_source=m.get("last_updated_from_source", "") or "",
                    chunk_index=int(m.get("chunk_index", 0)),
                    text=m.get("text", ""),
                )
            )
            if len(hits) >= top_k:
                break
        return hits


_singleton: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _singleton
    if _singleton is None:
        _singleton = Retriever()
    return _singleton


# ---------- CLI debug ----------

def _cli(argv: list[str]) -> None:
    query = " ".join(argv) if argv else "What is the lock-in period for HDFC ELSS Tax Saver Fund?"
    print(f"Query: {query}\n")
    r = get_retriever()
    hits = r.search(query, top_k=3)
    if not hits:
        print("(no hits)")
        return
    for rank, h in enumerate(hits, start=1):
        preview = h.text[:300].replace("\n", " ")
        print(f"--- Rank {rank}  score={h.score:.3f} ---")
        print(f"source_id   : {h.source_id}")
        print(f"scheme_name : {h.scheme_name}")
        print(f"source_type : {h.source_type}  page_type: {h.page_type}")
        print(f"url         : {h.url}")
        print(f"text[:300]  : {preview}…\n")


if __name__ == "__main__":
    _cli(sys.argv[1:])
