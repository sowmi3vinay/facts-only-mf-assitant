"""End-to-end orchestration: query → router → retriever → responder.

This is the single place the UI calls. Keeps ``app.py`` thin.
"""
from __future__ import annotations

from typing import Optional

from .responder import (
    Response,
    build_answer_response,
    build_not_found_response,
    build_refuse_response,
    format_response,
)
from .retriever import get_retriever
from .router import classify

DEFAULT_TOP_K = 4


def answer_query(query: str, scheme_filter: Optional[str] = None) -> Response:
    """Run the full pipeline for one user query and return a ``Response``.

    The caller decides how to display it (see ``format_response``).
    """
    decision = classify(query)

    if decision.decision == "REFUSE":
        return build_refuse_response(reason=decision.refuse_reason or "advice")

    if decision.decision == "NOT_FOUND":
        return build_not_found_response()

    # decision.decision == "ANSWER" → run retrieval, then ground or downgrade.
    hits = get_retriever().search(query, top_k=DEFAULT_TOP_K, scheme_name=scheme_filter)
    return build_answer_response(query, hits)


def answer_query_text(query: str, scheme_filter: Optional[str] = None) -> str:
    """Convenience: run the pipeline and return the formatted display string."""
    return format_response(answer_query(query, scheme_filter=scheme_filter))
