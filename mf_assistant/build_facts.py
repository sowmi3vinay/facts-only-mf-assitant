"""Build the structured facts file from normalized scheme documents.

Usage:
    PYTHONPATH=. python -m mf_assistant.build_facts

Reads every JSON in ``data/normalized/``, runs all field extractors over its
text, and writes one ``FactRecord`` per (scheme, field) into
``data/facts/facts.jsonl``. KIM/SID documents are preferred; scheme HTML pages
fill in any field a KIM doesn't cover for the same scheme.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

from .config import DATA_DIR
from .fact_extractor import extract_all
from .facts_store import FACTS_PATH, FactRecord, write_facts

NORMALIZED_DIR = DATA_DIR / "normalized"

# Higher-priority page_types overwrite lower-priority ones for the same field.
_PAGE_TYPE_PRIORITY = {
    "kim": 3,
    "sid": 3,
    "factsheet": 2,
    "scheme_page": 1,
    "factsheet_index": 0,
}


def main(verbose: bool = True) -> Path:
    if not NORMALIZED_DIR.exists():
        raise SystemExit(f"No normalized records found at {NORMALIZED_DIR}")

    # key = (scheme_name, field_name) → (priority, FactRecord)
    chosen: Dict[Tuple[str, str], Tuple[int, FactRecord]] = {}

    for path in sorted(NORMALIZED_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        scheme = (doc.get("scheme_name") or "").strip()
        if not scheme or scheme.lower().startswith("hdfc (multi"):
            continue
        text = doc.get("text") or ""
        if not text:
            continue

        page_type = doc.get("page_type", "")
        priority = _PAGE_TYPE_PRIORITY.get(page_type, 0)

        facts = extract_all(text)
        for fact in facts:
            rec = FactRecord(
                scheme_name=scheme,
                source_id=doc.get("source_id", ""),
                source_url=doc.get("url", ""),
                field_name=fact.field_name,
                field_value=fact.field_value,
                last_updated_from_source=doc.get("last_updated_from_source", ""),
                evidence_text=fact.evidence_text,
            )
            key = (scheme.lower(), fact.field_name)
            existing = chosen.get(key)
            if existing is None or priority > existing[0]:
                chosen[key] = (priority, rec)

    records = [rec for _, rec in chosen.values()]
    out_path = write_facts(records, FACTS_PATH)
    if verbose:
        print(f"Wrote {len(records)} facts → {out_path}")
        for r in records:
            print(f"  {r.scheme_name:32s} | {r.field_name:18s} = {r.field_value}")
    return out_path


if __name__ == "__main__":
    main(verbose=True)
