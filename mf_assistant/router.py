"""Query router.

Classifies a user query into one of three buckets:

- ``ANSWER``    — proceed to retrieval and grounded response.
- ``REFUSE``    — investment-advice / recommendation / PII; respond with a polite refusal.
- ``NOT_FOUND`` — empty query or otherwise unanswerable up front.

The retriever/responder layer may *also* downgrade an ``ANSWER`` decision to
``NOT_FOUND`` later if the retrieved context is insufficient to ground a
factual answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# Public decision labels.
Decision = Literal["ANSWER", "REFUSE", "NOT_FOUND"]

# Internal sub-reason for refusals (helps the responder pick the right canned text).
RefuseReason = Literal["pii", "advice", "scope", ""]


@dataclass
class RouteResult:
    decision: Decision
    refuse_reason: RefuseReason = ""
    detail: str = ""

    # ---- Backward-compat shim for older callers that read ``.decision`` as
    #      one of {"answer","refuse_pii","refuse_advice","refuse_scope"}. ----
    @property
    def legacy_decision(self) -> str:
        if self.decision == "ANSWER":
            return "answer"
        if self.decision == "REFUSE" and self.refuse_reason == "pii":
            return "refuse_pii"
        if self.decision == "REFUSE" and self.refuse_reason == "advice":
            return "refuse_advice"
        return "refuse_scope"


# --- PII patterns (do not log matches; we only flag presence) ---
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_OTP_RE = re.compile(r"\b(otp|one[\s-]?time[\s-]?password)\b", re.IGNORECASE)
_ACCT_RE = re.compile(r"\b(account\s*(no|number)|a/?c\s*no)\b", re.IGNORECASE)

# --- Advice / out-of-scope intent keywords ---
_ADVICE_KEYWORDS = [
    "should i", "shall i", "recommend", "recommendation", "best fund",
    "which fund is better", "which is better", "better than", "buy", "sell",
    "invest in", "good investment", "bad investment", "portfolio allocation",
    "asset allocation", "predict", "prediction", "forecast", "future return",
    "expected return", "will it give", "how much will i earn", "compare returns",
    "performance comparison", "outperform", "alpha", "suitable for me", "suit me",
]

# --- Allowed factual intents (used as a soft hint, not a hard gate) ---
_FACT_KEYWORDS = [
    "expense ratio", "exit load", "minimum sip", "min sip", "lock-in", "lock in",
    "lockin", "benchmark", "riskometer", "risk-o-meter", "statement",
    "capital gains", "nav", "fund manager", "category", "scheme code",
    "isin", "aum", "inception", "plan", "direct", "regular",
]


def contains_pii(text: str) -> bool:
    """Return True if the text appears to contain PII we refuse to handle."""
    if not text:
        return False
    return bool(
        _PAN_RE.search(text)
        or _AADHAAR_RE.search(text)
        or _PHONE_RE.search(text)
        or _EMAIL_RE.search(text)
        or _OTP_RE.search(text)
        or _ACCT_RE.search(text)
    )


def looks_like_advice(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _ADVICE_KEYWORDS)


def looks_factual(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _FACT_KEYWORDS)


def classify(query: str) -> RouteResult:
    """Classify the query into ANSWER / REFUSE / NOT_FOUND.

    Order of checks: PII → advice/recommendation → empty → ANSWER.
    """
    q = (query or "").strip()
    if not q:
        return RouteResult("NOT_FOUND", "", "Empty query.")

    if contains_pii(q):
        return RouteResult("REFUSE", "pii", "PII detected in query.")

    if looks_like_advice(q):
        return RouteResult("REFUSE", "advice", "Query asks for advice or recommendation.")

    return RouteResult("ANSWER", "", "Factual query; route to retrieval.")


# Backward-compat alias for older callers.
def route(query: str) -> RouteResult:
    return classify(query)
