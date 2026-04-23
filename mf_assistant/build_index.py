"""Build a TF-IDF retrieval index over the chunked corpus.

We use TF-IDF (scikit-learn) as a lightweight, dependency-free embedding
substitute for a small corpus. It avoids API keys and runs fully offline,
which is important for a "facts only" assistant.

Source of truth: normalized JSON records in ``data/normalized/`` produced by
``ingest.py``. Falls back to demo chunks if no normalized records exist yet,
so the UI works on first launch.

Run:
    PYTHONPATH=. python -m mf_assistant.build_index
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List

from .chunker import Chunk, make_chunks

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
NORMALIZED_DIR = DATA_DIR / "normalized"
INDEX_DIR = DATA_DIR / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_PATH = INDEX_DIR / "chunks.json"
VECTORIZER_PATH = INDEX_DIR / "vectorizer.pkl"
MATRIX_PATH = INDEX_DIR / "matrix.pkl"


# --- Placeholder demo chunks so the app works before real ingestion runs. ---
# TODO: Remove or override these once ingest.py has produced normalized records.
DEMO_CHUNKS: List[dict] = [
    {
        "text": (
            "Demo Large Cap Fund - Direct Growth has a total expense ratio (TER) of "
            "0.85% per annum as per the latest factsheet. The scheme's benchmark is "
            "the NIFTY 100 TRI. The riskometer rating is 'Very High'."
        ),
        "source_id": "DEMO_LARGE_CAP_FACTSHEET",
        "scheme_name": "Demo Large Cap Fund - Direct Growth",
        "url": "https://example-amc.com/demo-large-cap/factsheet.pdf",
        "last_updated_from_source": "2026-04-01",
    },
    {
        "text": (
            "Demo Flexi Cap Fund - Direct Growth has a total expense ratio of 0.72% "
            "per annum. Exit load is 1% if redeemed within 12 months, nil thereafter. "
            "The benchmark is NIFTY 500 TRI and the riskometer rating is 'Very High'."
        ),
        "source_id": "DEMO_FLEXI_CAP_FACTSHEET",
        "scheme_name": "Demo Flexi Cap Fund - Direct Growth",
        "url": "https://example-amc.com/demo-flexi-cap/factsheet.pdf",
        "last_updated_from_source": "2026-04-01",
    },
    {
        "text": (
            "Demo ELSS Tax Saver Fund - Direct Growth has a statutory lock-in period "
            "of 3 years (36 months) from the date of allotment of units. There is no "
            "exit load applicable since redemption is not permitted during the lock-in. "
            "Minimum SIP is Rs. 500."
        ),
        "source_id": "DEMO_ELSS_FACTSHEET",
        "scheme_name": "Demo ELSS Tax Saver Fund - Direct Growth",
        "url": "https://example-amc.com/demo-elss/factsheet.pdf",
        "last_updated_from_source": "2026-04-01",
    },
]


def _load_normalized_records() -> list[dict]:
    if not NORMALIZED_DIR.exists():
        return []
    out: list[dict] = []
    for p in sorted(NORMALIZED_DIR.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def _build_chunks_from_records(records: list[dict]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for r in records:
        chunks.extend(
            make_chunks(
                r.get("text", ""),
                source_id=r.get("source_id", ""),
                scheme_id=r.get("scheme_name", ""),
                url=r.get("url", ""),
                last_checked=r.get("last_updated_from_source") or r.get("fetched_at", ""),
            )
        )
    return chunks


def build(use_demo_if_empty: bool = True) -> int:
    """Build the index and persist it to disk. Returns chunk count."""
    records = _load_normalized_records()
    chunks = _build_chunks_from_records(records)

    if not chunks and use_demo_if_empty:
        chunks = [
            Chunk(
                text=c["text"],
                source_id=c["source_id"],
                scheme_id=c["scheme_name"],
                url=c["url"],
                last_checked=c["last_updated_from_source"],
            )
            for c in DEMO_CHUNKS
        ]

    if not chunks:
        CHUNKS_PATH.write_text("[]", encoding="utf-8")
        return 0

    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore

    texts = [c.text for c in chunks]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        sublinear_tf=True,
        stop_words="english",
    )
    matrix = vectorizer.fit_transform(texts)

    CHUNKS_PATH.write_text(
        json.dumps([c.__dict__ for c in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with VECTORIZER_PATH.open("wb") as f:
        pickle.dump(vectorizer, f)
    with MATRIX_PATH.open("wb") as f:
        pickle.dump(matrix, f)

    return len(chunks)


if __name__ == "__main__":
    n = build()
    print(f"Built index with {n} chunks")
