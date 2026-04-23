"""Build a TF-IDF retrieval index over the chunked corpus.

We use TF-IDF (scikit-learn) as a lightweight, dependency-free embedding
substitute for a small corpus. It avoids API keys and runs fully offline,
which is important for a "facts only" assistant.

Run:
    python -m mf_assistant.build_index
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List

from .chunker import Chunk, make_chunks
from .ingest import ingest_all

ROOT = Path(__file__).resolve().parent
INDEX_DIR = ROOT / "data" / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_PATH = INDEX_DIR / "chunks.json"
VECTORIZER_PATH = INDEX_DIR / "vectorizer.pkl"
MATRIX_PATH = INDEX_DIR / "matrix.pkl"


# --- Placeholder demo chunks so the app works before real ingestion runs. ---
# TODO: Remove or override these once ingest.py has produced real chunks.
DEMO_CHUNKS: List[dict] = [
    {
        "text": (
            "Demo Large Cap Fund - Direct Growth has a total expense ratio (TER) of "
            "0.85% per annum as per the latest factsheet. The scheme's benchmark is "
            "the NIFTY 100 TRI. The riskometer rating is 'Very High'."
        ),
        "source_id": "DEMO_LARGE_CAP:factsheet:demo1",
        "scheme_id": "DEMO_LARGE_CAP",
        "url": "https://example-amc.com/demo-large-cap/factsheet.pdf",
        "last_checked": "2026-04-01",
    },
    {
        "text": (
            "Demo Large Cap Fund - Direct Growth has an exit load of 1% if redeemed "
            "or switched out within 365 days from the date of allotment, otherwise nil. "
            "The minimum SIP amount is Rs. 500 with monthly frequency."
        ),
        "source_id": "DEMO_LARGE_CAP:factsheet:demo2",
        "scheme_id": "DEMO_LARGE_CAP",
        "url": "https://example-amc.com/demo-large-cap/factsheet.pdf",
        "last_checked": "2026-04-01",
    },
    {
        "text": (
            "Demo Flexi Cap Fund - Direct Growth has a total expense ratio of 0.72% "
            "per annum. Exit load is 1% if redeemed within 12 months, nil thereafter. "
            "The benchmark is NIFTY 500 TRI and the riskometer rating is 'Very High'."
        ),
        "source_id": "DEMO_FLEXI_CAP:factsheet:demo1",
        "scheme_id": "DEMO_FLEXI_CAP",
        "url": "https://example-amc.com/demo-flexi-cap/factsheet.pdf",
        "last_checked": "2026-04-01",
    },
    {
        "text": (
            "Demo ELSS Tax Saver Fund - Direct Growth has a statutory lock-in period "
            "of 3 years (36 months) from the date of allotment of units. There is no "
            "exit load applicable since redemption is not permitted during the lock-in. "
            "Minimum SIP is Rs. 500."
        ),
        "source_id": "DEMO_ELSS:factsheet:demo1",
        "scheme_id": "DEMO_ELSS",
        "url": "https://example-amc.com/demo-elss/factsheet.pdf",
        "last_checked": "2026-04-01",
    },
    {
        "text": (
            "To download your account statement on Kuvera, go to the Reports section "
            "in the app or web dashboard and select 'Account Statement'. Choose the "
            "date range and tap Download to receive the statement by email as a PDF."
        ),
        "source_id": "KUVERA_HELP:help:statements",
        "scheme_id": "KUVERA_HELP",
        "url": "https://kuvera.in/help/statements",
        "last_checked": "2026-04-01",
    },
    {
        "text": (
            "To download your capital gains statement on Kuvera, open Reports and "
            "select 'Capital Gains'. Choose the financial year and tap Download; the "
            "report is emailed to your registered address as a PDF for tax filing."
        ),
        "source_id": "KUVERA_HELP:help:capital-gains",
        "scheme_id": "KUVERA_HELP",
        "url": "https://kuvera.in/help/capital-gains",
        "last_checked": "2026-04-01",
    },
    {
        "text": (
            "AMFI's Risk-o-meter is a standardised pictorial representation of the "
            "risk associated with a mutual fund scheme. It has six levels: Low, Low to "
            "Moderate, Moderate, Moderately High, High, and Very High."
        ),
        "source_id": "AMFI_RISKO:reference:1",
        "scheme_id": "AMFI_RISKO",
        "url": "https://www.amfiindia.com/investor-corner/investor-center/risk-o-meter.html",
        "last_checked": "2026-04-01",
    },
]


def _build_chunks_from_records(records: list[dict]) -> List[Chunk]:
    chunks: List[Chunk] = []
    for r in records:
        chunks.extend(
            make_chunks(
                r["text"],
                source_id=r["source_id"],
                scheme_id=r["scheme_id"],
                url=r["url"],
                last_checked=r.get("last_checked", ""),
            )
        )
    return chunks


def build(use_demo_if_empty: bool = True) -> int:
    """Build the index and persist it to disk. Returns chunk count."""
    records = ingest_all()
    chunks = _build_chunks_from_records(records)

    if not chunks and use_demo_if_empty:
        chunks = [
            Chunk(
                text=c["text"],
                source_id=c["source_id"],
                scheme_id=c["scheme_id"],
                url=c["url"],
                last_checked=c["last_checked"],
            )
            for c in DEMO_CHUNKS
        ]

    if not chunks:
        # Persist empty state
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
