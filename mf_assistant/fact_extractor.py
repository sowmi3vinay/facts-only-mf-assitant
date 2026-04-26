"""Extract structured facts from normalized scheme documents (KIMs/factsheets).

Each extractor takes the full normalized text of a single document and returns
either ``None`` or an ``ExtractedFact`` containing the field value plus the
short ``evidence_text`` snippet it came from.

We deliberately keep this rule-based (regex + small heuristics) so every
fact is auditable against the source text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


FACT_FIELDS = [
    "expense_ratio",
    "exit_load",
    "minimum_sip",
    "minimum_lumpsum",
    "lock_in_period",
    "benchmark",
    "riskometer",
]


@dataclass
class ExtractedFact:
    field_name: str
    field_value: str
    evidence_text: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean(text: str) -> str:
    """Collapse whitespace runs (incl. newlines) into single spaces."""
    return re.sub(r"\s+", " ", (text or "").strip())


def _shorten(text: str, max_chars: int = 320) -> str:
    text = _clean(text)
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rstrip()
    sp = cut.rfind(" ")
    if sp > max_chars - 60:
        cut = cut[:sp]
    return cut + "…"


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------


def extract_lock_in(text: str) -> Optional[ExtractedFact]:
    # Pattern: "statutory lock in of 3 years"
    m = re.search(r"\block[\s\-]?in[^.\n]{0,40}?(\d+)\s*(year|month)s?\b", text, re.I)
    if m:
        n, unit = m.group(1), m.group(2).lower()
        value = f"{n} {unit}{'s' if int(n) != 1 else ''}"
        if "statutory" in text[max(0, m.start() - 40) : m.end() + 20].lower():
            value = f"{value} (statutory)"
        evidence = _shorten(text[max(0, m.start() - 60) : m.end() + 80], 240)
        return ExtractedFact("lock_in_period", value, evidence)

    # If the doc is a KIM and has no lock-in language, treat as Nil for open-ended schemes.
    if re.search(r"\bopen[\s\-]?ended\b", text, re.I) and "lock" not in text.lower()[:6000]:
        return ExtractedFact(
            "lock_in_period",
            "No lock-in (open-ended scheme)",
            "Open-ended scheme; no statutory lock-in mentioned in KIM.",
        )
    return None


def extract_exit_load(text: str) -> Optional[ExtractedFact]:
    # Find "Load Structure ... Exit Load: <value>"
    m = re.search(r"Load Structure\s*\n?\s*Exit Load\s*[:\-]?\s*(.+?)(?=\n\s*\(i\)|\n\s*\(ii\)|\n\n|\nThe Trustee)",
                  text, re.I | re.S)
    if not m:
        # Fallback: any Exit Load line, stopping at next section headers
        m = re.search(r"Exit Load\s*[:\-]?\s*(.+?)(?=\n\s*\(i\)|\n\n|\nThe Trustee|\bProduct Labelling\b|\bBenchmark\b|$)", text, re.I | re.S)
    if not m:
        return None
    raw = _clean(m.group(1))
    # Common patterns -> short value.
    if raw.lower().startswith("nil") or raw.lower().startswith("no exit load"):
        value = "Nil"
    else:
        # Try to find "1.00% ... within X year(s)/month(s)/day(s)"
        sub = re.search(
            r"(?:an\s+Exit\s+Load\s+of\s+)?(\d+(?:\.\d+)?)\s*%[^.]*?within\s+(\d+)\s*(year|month|day)s?\b",
            raw, re.I,
        )
        if sub:
            pct, n, unit = sub.group(1), sub.group(2), sub.group(3).lower()
            value = f"{pct}% if redeemed within {n} {unit}{'s' if int(n) != 1 else ''}"
        else:
            value = _shorten(raw, 180)
    evidence = _shorten(m.group(0), 320)
    return ExtractedFact("exit_load", value, evidence)


def extract_benchmark(text: str) -> Optional[ExtractedFact]:
    """Pull the Tier I benchmark index name."""
    # Pattern: "<INDEX NAME> (TRI) (as per AMFI Tier I Benchmark)" or similar.
    m = re.search(
        r"([A-Z][A-Z0-9 &/\-\.]+?(?:Index|TRI)[^(\n]{0,40})\s*\(?\s*\(?TRI\)?\s*\)?\s*\(?as per\s+AMFI\s+Tier\s+I\s+Benchmark",
        text, re.I,
    )
    if not m:
        # Looser fallback: any "NIFTY ... (TRI) ... AMFI Tier I" up to 200 chars apart.
        m = re.search(r"((?:NIFTY|BSE|S&P\s+BSE)[^\n]{0,80})", text)
        if not m:
            return None
    value = _clean(m.group(1))
    # Normalize: strip trailing punctuation and collapse "Total Returns Index" notation.
    value = re.sub(r"\s+\(TRI\).*$", " (TRI)", value)
    value = re.sub(r"\s+", " ", value).strip(" .,")
    evidence = _shorten(text[max(0, m.start() - 40) : m.end() + 120], 260)
    return ExtractedFact("benchmark", value, evidence)


def extract_minimum_lumpsum(text: str) -> Optional[ExtractedFact]:
    # Section 11 "Minimum Application Amount" — first Rs.X/- after that header.
    sec = re.search(r"11\.\s*Minimum Application Amount.*?(?=\n\s*\d{1,2}\.\s)", text, re.I | re.S)
    body = sec.group(0) if sec else text
    m = re.search(r"Rs\.?\s*([\d,]+)\s*/?\-", body)
    if not m:
        return None
    amt = m.group(1).replace(",", "")
    value = f"₹{int(amt):,} (purchase / switch-in)"
    evidence = _shorten(body[: max(400, m.end() + 80)], 320)
    return ExtractedFact("minimum_lumpsum", value, evidence)


def extract_minimum_sip(text: str) -> Optional[ExtractedFact]:
    # Look for "SIP" + nearby "Rs. X" amount, or fall back to lumpsum minimum
    # since HDFC equity schemes share the same Rs.100 / Rs.500 minimum.
    sip_block = None
    for m in re.finditer(r"\bSIP\b[^.\n]{0,200}?Rs\.?\s*([\d,]+)", text, re.I):
        sip_block = m
        break
    if sip_block:
        amt = sip_block.group(1).replace(",", "")
        value = f"₹{int(amt):,}"
        evidence = _shorten(
            text[max(0, sip_block.start() - 60) : sip_block.end() + 80], 260
        )
        return ExtractedFact("minimum_sip", value, evidence)
    # Fallback to lumpsum if available.
    lump = extract_minimum_lumpsum(text)
    if lump:
        return ExtractedFact(
            "minimum_sip",
            lump.field_value,
            "Same as minimum application amount: " + lump.evidence_text,
        )
    return None


def extract_expense_ratio(text: str) -> Optional[ExtractedFact]:
    m = re.search(
        r"Maximum Total Expense Ratio under Regulation 52\s*\(6\)\s*:?\s*(.+?)(?=\n\s*\d{1,2}\.\s|\n\n[A-Z])",
        text, re.I | re.S,
    )
    if not m:
        return None
    body = _clean(m.group(1))
    # First slab is the headline.
    first = re.search(
        r"On the first[^%\n]{0,120}?[\-:]\s*(\d+(?:\.\d+)?)\s*%\s*p\.?a\.?",
        body, re.I,
    )
    if first:
        value = (
            f"Up to {first.group(1)}% p.a. on the first ₹500 cr (SEBI Reg. 52(6) "
            "TER cap; see latest factsheet for current actual TER)"
        )
    else:
        value = _shorten(body, 180)
    evidence = _shorten(m.group(0), 320)
    return ExtractedFact("expense_ratio", value, evidence)


def extract_riskometer(text: str) -> Optional[ExtractedFact]:
    # KIM riskometer ratings are usually rendered as images, so the literal
    # word ("Very High" / "High" / "Moderate") is rarely in the OCR'd text.
    # We look for an explicit textual claim if present.
    m = re.search(
        r"Riskometer[^\n]{0,80}?\b(Low|Low to Moderate|Moderate|Moderately High|High|Very High)\b",
        text, re.I,
    )
    if not m:
        return None
    value = m.group(1).title()
    evidence = _shorten(text[max(0, m.start() - 40) : m.end() + 60], 200)
    return ExtractedFact("riskometer", value, evidence)


# ---------------------------------------------------------------------------
# Public entry: extract all known fields from one document
# ---------------------------------------------------------------------------


_EXTRACTORS: Dict[str, Callable[[str], Optional[ExtractedFact]]] = {
    "lock_in_period": extract_lock_in,
    "exit_load": extract_exit_load,
    "benchmark": extract_benchmark,
    "minimum_sip": extract_minimum_sip,
    "minimum_lumpsum": extract_minimum_lumpsum,
    "expense_ratio": extract_expense_ratio,
    "riskometer": extract_riskometer,
}


def extract_all(text: str) -> List[ExtractedFact]:
    out: List[ExtractedFact] = []
    for fn in _EXTRACTORS.values():
        try:
            fact = fn(text)
        except Exception:
            fact = None
        if fact:
            out.append(fact)
    return out
