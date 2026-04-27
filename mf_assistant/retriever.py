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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .build_index import build as build_index
from .config import (
    CLOUD_LIGHT_MODE,
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
        self._keyword_vectorizer = None
        self._keyword_matrix = None
        self._load()

    # ---------- loading ----------
    def _load(self) -> None:
        if not FAISS_INDEX_PATH.exists() or not META_PATH.exists():
            # Build on first use so the app is functional out of the box.
            build_index(verbose=False)
        self._meta = self._read_meta(META_PATH)
        if self._meta:
            # Only load vector index if NOT in Light Mode
            if not CLOUD_LIGHT_MODE:
                try:
                    import faiss  # type: ignore
                    if FAISS_INDEX_PATH.exists():
                        print("DEBUG: FAISS imported and loading index.")
                        self._index = faiss.read_index(str(FAISS_INDEX_PATH))
                    else:
                        print(f"DEBUG: Vector index not found at {FAISS_INDEX_PATH}")
                except Exception as e:
                    print(f"ERROR: Failed to import FAISS or read index: {e}")
                    self._index = None
            else:
                print("DEBUG: CLOUD_LIGHT_MODE active. Skipping FAISS vector index.")
                self._index = None
            
            # Initialize keyword index
            texts = [m.get("text", "") for m in self._meta]
            self._keyword_vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )
            self._keyword_matrix = self._keyword_vectorizer.fit_transform(texts)

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

    def list_schemes(self) -> List[str]:
        """Return distinct scheme names present in the indexed metadata."""
        seen = []
        for m in self._meta:
            name = (m.get("scheme_name") or "").strip()
            if name and name not in seen:
                seen.append(name)
        return sorted(seen)

    def _ensure_model(self):
        """Lazy load the sentence-transformer model if not in Light Mode."""
        if CLOUD_LIGHT_MODE:
            return None
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore
            print(f"DEBUG: Loading embedding model {EMBED_MODEL_NAME}...")
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
        allowed_page_types: Optional[set[str]] = None,
        min_score: float = 0.05,
    ) -> List[Hit]:
        """Return up to ``top_k`` chunks using hybrid (vector + keyword) search."""
        if not query or not self._index or not self._meta:
            return []

        # 1. Vector search - only if NOT in light mode
        v_scores, v_idx = [], []
        model = self._ensure_model()
        if model is not None and self._index is not None:
            qv = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
            k_fetch = min(max(top_k * 2, DEFAULT_OVERFETCH), len(self._meta))
            v_scores, v_idx = self._index.search(qv, k_fetch)
            v_scores = v_scores[0]
            v_idx = v_idx[0]
        else:
            if CLOUD_LIGHT_MODE:
                print("DEBUG: Vector search skipped (Cloud Light Mode)")
            elif not self._index:
                print("DEBUG: Vector search skipped (Index missing)")

        # 2. Keyword search
        q_vec = self._keyword_vectorizer.transform([query])
        k_scores = cosine_similarity(q_vec, self._keyword_matrix).flatten()
        k_idx = k_scores.argsort()[::-1][:k_fetch]
        k_scores_top = k_scores[k_idx]

        # 3. Merge and Re-rank
        merged_hits: Dict[int, float] = {} # meta_index -> final_score
        
        # Normalize scores to 0-1 for merging
        # Vector scores are already cosine (0-1)
        # Keyword scores are also cosine (0-1)
        
        # Weights
        W_VECTOR = 0.6
        W_KEYWORD = 0.4
        
        for s, i in zip(v_scores, v_idx):
            if i >= 0:
                merged_hits[int(i)] = merged_hits.get(int(i), 0) + float(s) * W_VECTOR
        
        for s, i in zip(k_scores_top, k_idx):
            if s > 0:
                merged_hits[int(i)] = merged_hits.get(int(i), 0) + float(s) * W_KEYWORD

        # 4. Filter and Boost
        scheme_q = (scheme_name or "").strip().lower()
        stype_q = (source_type or "").strip().lower()
        
        # Simple scheme detection from query if not provided
        if not scheme_q:
            schemes = self.list_schemes()
            for sname in schemes:
                if sname.lower() in query.lower():
                    scheme_q = sname.lower()
                    break

        final_hits: List[Hit] = []
        # Sort by score descending
        sorted_indices = sorted(merged_hits.items(), key=lambda x: x[1], reverse=True)
        
        for i, score in sorted_indices:
            m = self._meta[i]
            
            # Filters
            if scheme_name and scheme_name.lower() not in (m.get("scheme_name", "") or "").lower():
                continue
            if stype_q and stype_q != (m.get("source_type", "") or "").lower():
                continue
            if allowed_page_types and (m.get("page_type", "") or "").lower() not in allowed_page_types:
                continue
            
            # Boosts
            final_score = score
            m_scheme = (m.get("scheme_name", "") or "").lower()
            if scheme_q and scheme_q in m_scheme:
                final_score += 0.2 # Substantial boost for correct scheme
            
            if final_score < min_score:
                continue

            final_hits.append(
                Hit(
                    score=final_score,
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
            if len(final_hits) >= top_k:
                break
        
        return final_hits


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
    
    # Debug individual searches
    model = r._ensure_model()
    qv = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    v_scores, v_idx = r._index.search(qv, 3)
    
    print("--- Vector Hits ---")
    for s, i in zip(v_scores[0], v_idx[0]):
        if i >= 0:
            print(f"Index: {i:3} | Score: {s:.3f} | Scheme: {r._meta[i].get('scheme_name')}")

    q_vec = r._keyword_vectorizer.transform([query])
    k_scores = cosine_similarity(q_vec, r._keyword_matrix).flatten()
    k_idx = k_scores.argsort()[::-1][:3]
    print("\n--- Keyword Hits (TF-IDF) ---")
    for i in k_idx:
        print(f"Index: {i:3} | Score: {k_scores[i]:.3f} | Scheme: {r._meta[i].get('scheme_name')}")

    hits = r.search(query, top_k=3)
    print("\n--- Final Hybrid Hits (Merged & Boosted) ---")
    if not hits:
        print("(no hits)")
        return
    for rank, h in enumerate(hits, start=1):
        preview = h.text[:300].replace("\n", " ")
        print(f"Rank {rank} | Final Score: {h.score:.3f} | Scheme: {h.scheme_name}")
        print(f"Text: {preview}...\n")


if __name__ == "__main__":
    _cli(sys.argv[1:])
