"""Tiny debug runner for the four canonical pipeline cases.

Usage:
    PYTHONPATH=. python -m mf_assistant._debug_queries

Covers:
    1. Lock-in question     → ANSWER (grounded in HDFC ELSS KIM).
    2. Benchmark question   → ANSWER (grounded in HDFC Top 100 KIM).
    3. Exit load question   → ANSWER (grounded in HDFC Flexi Cap KIM).
    4. "Should I invest"    → REFUSE (advice).
Plus an extra noise query that exercises the NOT_FOUND downgrade.
"""
from __future__ import annotations

from .pipeline import answer_query
from .responder import format_response

DEBUG_QUERIES = [
    ("lock-in",   "What is the lock-in period for HDFC ELSS Tax Saver Fund?"),
    ("benchmark", "What is the benchmark of HDFC Top 100 Fund?"),
    ("exit load", "What is the exit load on HDFC Flexi Cap Fund?"),
    ("advice",    "Should I invest in HDFC Mid Cap Fund right now?"),
    ("noise",     "What is the weather in Delhi tomorrow?"),
]


def main() -> None:
    for label, q in DEBUG_QUERIES:
        resp = answer_query(q)
        print(f"=== [{label}]  kind={resp.kind} ===")
        print(f"Q: {q}")
        print(format_response(resp))
        print()


if __name__ == "__main__":
    main()
