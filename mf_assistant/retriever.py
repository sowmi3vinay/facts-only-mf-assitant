"""Retrieval over the persisted TF-IDF index."""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .build_index import CHUNKS_PATH, MATRIX_PATH, VECTORIZER_PATH, build

ROOT = Path(__file__).resolve().parent


@dataclass
class Hit:
    text: str
    source_id: str
    scheme_id: str
    url: str
    last_checked: str
    score: float


class Retriever:
    def __init__(self) -> None:
        self.chunks: List[dict] = []
        self.vectorizer = None
        self.matrix = None
        self._load()

    def _load(self) -> None:
        if not CHUNKS_PATH.exists() or not VECTORIZER_PATH.exists() or not MATRIX_PATH.exists():
            # Build with demo data so the app is usable on first run.
            build(use_demo_if_empty=True)
        try:
            self.chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
        except Exception:
            self.chunks = []
        try:
            with VECTORIZER_PATH.open("rb") as f:
                self.vectorizer = pickle.load(f)
            with MATRIX_PATH.open("rb") as f:
                self.matrix = pickle.load(f)
        except Exception:
            self.vectorizer = None
            self.matrix = None

    def search(self, query: str, top_k: int = 4, min_score: float = 0.08) -> List[Hit]:
        if not query or not self.chunks or self.vectorizer is None or self.matrix is None:
            return []
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self.matrix)[0]
        order = sims.argsort()[::-1][:top_k]
        hits: List[Hit] = []
        for idx in order:
            score = float(sims[idx])
            if score < min_score:
                continue
            c = self.chunks[idx]
            hits.append(
                Hit(
                    text=c["text"],
                    source_id=c["source_id"],
                    scheme_id=c["scheme_id"],
                    url=c["url"],
                    last_checked=c.get("last_checked", ""),
                    score=score,
                )
            )
        return hits


_singleton: Optional[Retriever] = None


def get_retriever() -> Retriever:
    global _singleton
    if _singleton is None:
        _singleton = Retriever()
    return _singleton
