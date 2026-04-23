"""Read/write the structured facts file (``data/facts/facts.jsonl``).

Each line is one fact record:

    {
      "scheme_name": "...",
      "source_id": "...",
      "source_url": "...",
      "field_name": "exit_load",
      "field_value": "1% if redeemed within 1 year",
      "last_updated_from_source": "2025-05-30",
      "evidence_text": "Load Structure  Exit Load: ..."
    }
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .config import DATA_DIR

FACTS_DIR = DATA_DIR / "facts"
FACTS_PATH = FACTS_DIR / "facts.jsonl"


@dataclass
class FactRecord:
    scheme_name: str
    source_id: str
    source_url: str
    field_name: str
    field_value: str
    last_updated_from_source: str
    evidence_text: str


def write_facts(records: List[FactRecord], path: Path = FACTS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    return path


def read_facts(path: Path = FACTS_PATH) -> List[FactRecord]:
    if not path.exists():
        return []
    out: List[FactRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                out.append(FactRecord(**d))
            except Exception:
                continue
    return out


class FactsStore:
    """In-memory lookup keyed by (scheme_name, field_name)."""

    def __init__(self, records: Optional[List[FactRecord]] = None) -> None:
        self._records = records if records is not None else read_facts()
        self._by_key: Dict[tuple, FactRecord] = {}
        for r in self._records:
            self._by_key[(r.scheme_name.strip().lower(), r.field_name)] = r

    def get(self, scheme_name: str, field_name: str) -> Optional[FactRecord]:
        if not scheme_name or not field_name:
            return None
        return self._by_key.get((scheme_name.strip().lower(), field_name))

    def schemes(self) -> List[str]:
        return sorted({r.scheme_name for r in self._records})

    def all(self) -> List[FactRecord]:
        return list(self._records)


_STORE: Optional[FactsStore] = None


def get_facts_store(reload: bool = False) -> FactsStore:
    global _STORE
    if _STORE is None or reload:
        _STORE = FactsStore()
    return _STORE
