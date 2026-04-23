"""Ingestion pipeline for the starter corpus.

Reads ``sources.csv``, downloads each approved URL (HTML or PDF), parses to
clean text, and writes one normalized JSON record per source under
``data/normalized/``. Raw bytes are cached under ``data/raw/`` so re-runs are
fast and offline-friendly. A simple ingestion log is written to
``data/ingestion.log``.

Run:
    PYTHONPATH=. python -m mf_assistant.ingest
    PYTHONPATH=. FORCE=1 python -m mf_assistant.ingest   # re-download
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import requests  # type: ignore

from .normalizer import make_record, now_iso
from .parser import parse_by_type

ROOT = Path(__file__).resolve().parent
SOURCES_CSV = ROOT / "sources.csv"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
LOG_PATH = DATA_DIR / "ingestion.log"

for d in (RAW_DIR, NORMALIZED_DIR):
    d.mkdir(parents=True, exist_ok=True)

USER_AGENT = "FactsOnlyMFAssistant/0.1 (+contact: replace-me)"
REQUEST_TIMEOUT = 30  # seconds

# --- logging setup ---
logger = logging.getLogger("mf_assistant.ingest")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)


@dataclass
class SourceRow:
    source_id: str
    source_name: str
    scheme_name: str
    source_type: str   # "html" | "pdf"
    page_type: str     # "kim" | "scheme_page" | "factsheet_index" | ...
    url: str
    last_updated_from_source: str

    @property
    def raw_path(self) -> Path:
        h = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:16]
        suffix = ".pdf" if self.source_type.lower() == "pdf" else ".html"
        return RAW_DIR / f"{self.source_id}_{h}{suffix}"

    @property
    def normalized_path(self) -> Path:
        return NORMALIZED_DIR / f"{self.source_id}.json"


def load_sources(path: Path = SOURCES_CSV) -> List[SourceRow]:
    rows: List[SourceRow] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(_strip_comments(f))
        for r in reader:
            try:
                rows.append(
                    SourceRow(
                        source_id=r["source_id"].strip(),
                        source_name=r["source_name"].strip(),
                        scheme_name=r["scheme_name"].strip(),
                        source_type=r["source_type"].strip(),
                        page_type=r["page_type"].strip(),
                        url=r["url"].strip(),
                        last_updated_from_source=(r.get("last_updated_from_source") or "").strip(),
                    )
                )
            except KeyError as e:
                logger.warning("Skipping malformed row (missing %s): %r", e, r)
    return rows


def _strip_comments(lines: Iterable[str]) -> Iterable[str]:
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        yield line


def download(row: SourceRow, *, timeout: int = REQUEST_TIMEOUT, force: bool = False) -> Optional[bytes]:
    """Fetch URL bytes, cached on disk. Returns None on failure."""
    if row.raw_path.exists() and not force:
        try:
            return row.raw_path.read_bytes()
        except Exception as e:
            logger.warning("Cache read failed for %s: %s", row.source_id, e)
    try:
        logger.info("GET %s [%s]", row.url, row.source_id)
        resp = requests.get(
            row.url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            allow_redirects=True,
        )
    except requests.Timeout:
        logger.error("Timeout downloading %s", row.source_id)
        return None
    except requests.RequestException as e:
        logger.error("Request failed for %s: %s", row.source_id, e)
        return None

    if resp.status_code != 200:
        logger.error("HTTP %s for %s (%s)", resp.status_code, row.source_id, row.url)
        return None
    try:
        row.raw_path.write_bytes(resp.content)
    except Exception as e:
        logger.warning("Could not cache %s: %s", row.source_id, e)
    return resp.content


def process_row(row: SourceRow, *, force: bool = False) -> Optional[dict]:
    data = download(row, force=force)
    if not data:
        return None
    text = parse_by_type(data, row.source_type)
    if not text:
        logger.warning("Empty text after parsing %s", row.source_id)
        return None
    record = make_record(
        source_id=row.source_id,
        source_type=row.source_type,
        source_name=row.source_name,
        url=row.url,
        scheme_name=row.scheme_name,
        page_type=row.page_type,
        text=text,
        last_updated_from_source=row.last_updated_from_source,
        fetched_at=now_iso(),
    )
    try:
        row.normalized_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.error("Could not write normalized record for %s: %s", row.source_id, e)
    return record


def ingest_all(force: bool = False) -> List[dict]:
    """Download, parse, and normalize every source. Returns list of records."""
    sources = load_sources()
    logger.info("Starting ingestion of %d sources (force=%s)", len(sources), force)
    out: List[dict] = []
    ok = fail = 0
    for row in sources:
        try:
            rec = process_row(row, force=force)
        except Exception as e:
            logger.exception("Unhandled error on %s: %s", row.source_id, e)
            rec = None
        if rec:
            ok += 1
            out.append(rec)
            logger.info("OK   %s (%d chars)", row.source_id, len(rec["text"]))
        else:
            fail += 1
            logger.error("FAIL %s", row.source_id)
    logger.info("Ingestion complete: %d ok, %d failed", ok, fail)
    return out


if __name__ == "__main__":
    records = ingest_all(force=os.environ.get("FORCE", "0") == "1")
    print(f"\nIngested {len(records)} sources. Normalized records in: {NORMALIZED_DIR}")
    for r in records:
        preview = r["text"][:160].replace("\n", " ")
        print(f"- {r['source_id']:24s} {r['page_type']:18s} {len(r['text']):>7d} chars  | {preview}…")
