"""Normalize parsed source text into a uniform record schema.

Each ingested source becomes one normalized record:

    {
      "source_id": str,
      "source_type": "html" | "pdf",
      "source_name": str,
      "url": str,
      "scheme_name": str,
      "page_type": str,           # e.g. "kim", "scheme_page", "factsheet_index"
      "fetched_at": ISO8601 str,
      "last_updated_from_source": str,  # may be empty when source has no date
      "text": str,
    }
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_text(text: str) -> str:
    text = (text or "").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def make_record(
    *,
    source_id: str,
    source_type: str,
    source_name: str,
    url: str,
    scheme_name: str,
    page_type: str,
    text: str,
    last_updated_from_source: str = "",
    fetched_at: Optional[str] = None,
) -> dict:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "source_name": source_name,
        "url": url,
        "scheme_name": scheme_name,
        "page_type": page_type,
        "fetched_at": fetched_at or now_iso(),
        "last_updated_from_source": last_updated_from_source or "",
        "text": clean_text(text),
    }
