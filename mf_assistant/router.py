"""Query router: decides whether to answer, refuse for PII, or refuse for advice."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Decision = Literal["answer", "refuse_pii", "refuse_advice", "refuse_scope"]


@dataclass
class RouteResult:
    decision: Decision
    reason: str


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
    if _PAN_RE.search(text):
        return True
    if _AADHAAR_RE.search(text):
        return True
    if _PHONE_RE.search(text):
        return True
    if _EMAIL_RE.search(text):
        return True
    if _OTP_RE.search(text):
        return True
    if _ACCT_RE.search(text):
        return True
    return False


def looks_like_advice(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _ADVICE_KEYWORDS)


def looks_factual(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _FACT_KEYWORDS)


def route(query: str) -> RouteResult:
    """Decide how to handle the user's query.

    Order of checks matters: PII first, then advice/recommendation intent,
    then a soft factual intent check.
    """
    q = (query or "").strip()
    if not q:
        return RouteResult("refuse_scope", "Empty query.")

    if contains_pii(q):
        return RouteResult("refuse_pii", "PII detected in query.")

    if looks_like_advice(q):
        return RouteResult("refuse_advice", "Query asks for advice or recommendation.")

    # If it doesn't match any factual keyword and is very short, still try to answer;
    # the retriever will decide if there's grounded context.
    return RouteResult("answer", "Factual query; route to retrieval.")
