"""End-to-end orchestration: query → router → facts/retriever → responder.

For ANSWER-classified queries, we consult the structured facts store first
when the question targets a known field on a known scheme. If we have a
matching fact we return it directly (1-sentence, precise). Otherwise we fall
back to vector retrieval over the FAISS index.
"""
from __future__ import annotations

from typing import Optional

from .fact_intent import detect_field, detect_scheme
from .facts_store import get_facts_store
from .responder import (
    Response,
    build_answer_response,
    build_fact_response,
    build_not_found_response,
    build_refuse_response,
    format_response,
)
from .retriever import get_retriever
from .router import classify

DEFAULT_TOP_K = 4


def _try_structured_fact(query: str, scheme_filter: Optional[str]) -> Optional[Response]:
    """If the query asks for a known field on a known scheme, return a fact response."""
    field = detect_field(query)
    if not field:
        return None
    facts = get_facts_store()
    scheme = scheme_filter or detect_scheme(query, facts.schemes())
    if not scheme:
        return None
    rec = facts.get(scheme, field)
    if not rec:
        return None
    return build_fact_response(rec)


def answer_query(query: str, scheme_filter: Optional[str] = None) -> Response:
    """Run the full pipeline for one user query and return a ``Response``."""
    decision = classify(query)

    if decision.decision == "REFUSE":
        return build_refuse_response(reason=decision.refuse_reason or "advice")

    if decision.decision == "NOT_FOUND":
        return build_not_found_response()

    # ANSWER branch: consult structured facts first.
    fact_resp = _try_structured_fact(query, scheme_filter)
    if fact_resp is not None:
        return fact_resp

    # Fallback: vector retrieval + grounded snippet.
    hits = get_retriever().search(query, top_k=DEFAULT_TOP_K, scheme_name=scheme_filter)
    return build_answer_response(query, hits)


def answer_query_text(query: str, scheme_filter: Optional[str] = None) -> str:
    return format_response(answer_query(query, scheme_filter=scheme_filter))
