"""Detect which structured fact (if any) a user query is asking about, and which
indexed scheme it refers to.

This is intentionally rule-based and conservative: if we're not sure, we
return ``None`` for the field and let the retrieval path handle the question.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# Field name -> ordered list of phrase patterns (lowercase, regex).
_FIELD_PATTERNS = {
    "lock_in_period": [r"\block[\s\-]?in\b", r"\blockin\b"],
    "exit_load":      [r"\bexit\s*load\b"],
    "benchmark":      [r"\bbenchmark\b", r"\bindex\b"],
    "minimum_sip":    [r"\bminimum\s+sip\b", r"\bmin\s+sip\b", r"\bsip\s+amount\b",
                       r"\bminimum\s+investment\s+for\s+sip\b"],
    "minimum_lumpsum":[r"\bminimum\s+(lumpsum|lump\s*sum|investment|application|amount)\b"],
    "expense_ratio":  [r"\bexp[a-z]*se\s*ratio\b", r"\bexpsense\b", r"\bratio\b", r"\bter\b"],
    "riskometer":     [r"\briskometer\b", r"\brisk[\s\-]?o[\s\-]?meter\b",
                       r"\brisk\s+(level|rating|category)\b"],
}


def detect_field(query: str) -> Optional[str]:
    q = (query or "").lower()
    if not q:
        return None
    for field, patterns in _FIELD_PATTERNS.items():
        for p in patterns:
            if re.search(p, q):
                return field
    return None


def detect_scheme(query: str, known_schemes: List[str]) -> Optional[str]:
    """Pick the most specific known scheme name mentioned in the query.

    Strategy: tokenize the query and each scheme name, score by the count of
    distinctive scheme tokens present in the query (e.g. "elss", "midcap",
    "flexi", "top", "small"). Return the highest-scoring scheme if score > 0.
    """
    if not query or not known_schemes:
        return None
    q = re.sub(r"[\-/]", " ", query.lower())

    # Token-level matching of the *distinctive* parts of each scheme name.
    common = {"hdfc", "fund", "direct", "the", "of", "a", "an", "growth", "plan", "scheme"}
    best: Tuple[int, Optional[str]] = (0, None)
    for s in known_schemes:
        s_norm = re.sub(r"[\-/]", " ", s.lower())
        toks = [t for t in re.findall(r"[a-z0-9]+", s_norm) if t not in common]
        # collapse common synonyms
        score = 0
        for t in toks:
            if re.search(rf"\b{re.escape(t)}\b", q):
                score += 1
        # Also match "midcap" / "smallcap" etc. spelled as one word
        for t in toks:
            if t in {"mid", "small", "large"}:
                if re.search(rf"\b{t}\s*cap\b", q):
                    score += 1
        if score > best[0]:
            best = (score, s)
    return best[1]
