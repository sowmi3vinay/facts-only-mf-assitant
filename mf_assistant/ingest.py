"""Ingestion pipeline.

Reads ``sources.csv``, downloads each approved URL, parses the content, and
caches raw bytes under ``data/raw/`` so re-builds are fast and offline-friendly.

Run:
    python -m mf_assistant.ingest

TODO: Configure real AMC URLs in sources.csv before running this.
"""
from __future__ import annotations

import csv
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import requests  # type: ignore

from .parser import parse_by_type

ROOT = Path(__file__).resolve().parent
SOURCES_CSV = ROOT / "sources.csv"
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "FactsOnlyMFAssistant/0.1 (+contact: replace-me)"


@dataclass
class SourceRow:
    scheme_id: str
    scheme_name: str
    amc: str
    doc_type: str
    url: str
    last_checked: str

    @property
    def source_id(self) -> str:
        h = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]
        return f"{self.scheme_id}:{self.doc_type}:{h}"

    @property
    def raw_path(self) -> Path:
        h = hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:16]
        suffix = ".pdf" if self.doc_type.lower() in {"pdf", "factsheet", "sid", "kim"} else ".html"
        return RAW_DIR / f"{h}{suffix}"


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
                        scheme_id=r["scheme_id"].strip(),
                        scheme_name=r["scheme_name"].strip(),
                        amc=r["amc"].strip(),
                        doc_type=r["doc_type"].strip(),
                        url=r["url"].strip(),
                        last_checked=r.get("last_checked", "").strip(),
                    )
                )
            except KeyError:
                continue
    return rows


def _strip_comments(lines: Iterable[str]) -> Iterable[str]:
    for line in lines:
        s = line.strip()
        if s.startswith("#"):
            continue
        yield line


def download(row: SourceRow, *, timeout: int = 20, force: bool = False) -> Optional[bytes]:
    """Fetch the URL bytes, cached on disk. Returns None on failure."""
    if row.raw_path.exists() and not force:
        try:
            return row.raw_path.read_bytes()
        except Exception:
            pass
    try:
        resp = requests.get(row.url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if resp.status_code != 200:
            return None
        row.raw_path.write_bytes(resp.content)
        return resp.content
    except Exception:
        return None


def ingest_all(force: bool = False) -> List[dict]:
    """Download and parse every source, returning per-source parsed text records."""
    out: List[dict] = []
    for row in load_sources():
        data = download(row, force=force)
        if not data:
            continue
        text = parse_by_type(data, row.doc_type)
        if not text:
            continue
        out.append(
            {
                "source_id": row.source_id,
                "scheme_id": row.scheme_id,
                "scheme_name": row.scheme_name,
                "amc": row.amc,
                "doc_type": row.doc_type,
                "url": row.url,
                "last_checked": row.last_checked,
                "text": text,
            }
        )
    return out


if __name__ == "__main__":
    records = ingest_all(force=os.environ.get("FORCE", "0") == "1")
    print(f"Ingested {len(records)} sources")
