"""Compose grounded answers from retrieved chunks.

Fully extractive: we never invent text. The pipeline is:

1. ``router.classify(query)`` returns ANSWER | REFUSE | NOT_FOUND.
2. For ANSWER, we run retrieval, then either:
   - synthesize a grounded snippet (≤ 3 sentences) from the top hit, OR
   - downgrade to NOT_FOUND if the retrieved context is insufficient.
3. For REFUSE, we return a polite facts-only refusal with one official
   educational source link.
4. For NOT_FOUND (either from the router or the responder downgrade), we say
   we couldn't verify the answer from indexed official sources.

Output for grounded factual answers is exactly:

    Answer: <snippet>
    Source: <url>
    Last updated from sources: <date>
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .facts_store import FactRecord
from .llm_client import generate_answer
from .prompts import (
    EDUCATIONAL_SOURCE_URL,
    NOT_FOUND_MESSAGE,
    REFUSAL_ADVICE,
    REFUSAL_PII,
)
from .retriever import Hit


# Human-readable label per structured field for the answer sentence.
_FIELD_LABELS = {
    "lock_in_period": "Lock-in period",
    "exit_load": "Exit load",
    "benchmark": "Benchmark",
    "minimum_sip": "Minimum SIP",
    "minimum_lumpsum": "Minimum lumpsum / application amount",
    "expense_ratio": "Expense ratio",
    "riskometer": "Riskometer",
}


def build_fact_response(fact: FactRecord) -> "Response":
    """Format a structured fact as a 1-sentence grounded answer (deterministic)."""
    label = _FIELD_LABELS.get(fact.field_name, fact.field_name)
    text = f"{label} for {fact.scheme_name}: {fact.field_value}."
    return Response(
        kind="answer",
        text=text,
        url=fact.source_url or None,
        last_updated=fact.last_updated_from_source or None,
    )


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class Response:
    """Final response object returned to the UI layer."""

    kind: str  # "answer" | "refuse" | "not_found"
    text: str  # The body text (snippet for answers, message for the rest).
    url: Optional[str] = None
    last_updated: Optional[str] = None


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Flag to enable/disable LLM polishing. Set to False for 100% deterministic output.
from .config import USE_LLM_POLISH
USE_LLM = USE_LLM_POLISH

# Below this cosine similarity, treat the top retrieval as too weak to ground
# a factual answer. all-MiniLM-L6-v2 cosine scores on this corpus are roughly
# 0.55-0.78 for clearly relevant queries and < 0.30 for noise.
MIN_SCORE_FOR_ANSWER = 0.35

# Max sentences (after sentence splitting) returned in an answer body.
MAX_SENTENCES = 3

# Max characters in the snippet window (a soft cap before sentence trimming).
WINDOW_CHARS = 480


# ---------------------------------------------------------------------------
# Tokenizer / window picker
# ---------------------------------------------------------------------------


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "is", "are", "and", "or",
    "what", "which", "how", "do", "does", "i", "my", "your", "this", "that",
    "be", "as", "at", "by", "from", "with", "about", "it", "fund", "scheme",
    "mutual", "funds", "please", "tell", "me", "hdfc",
}


def _normalize(text: str) -> str:
    return re.sub(r"[\-/]", " ", (text or "").lower())


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(_normalize(text)) if w not in _STOPWORDS}


def _split_sentences(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    return [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    sp = cut.rfind(" ")
    if sp > max_chars - 30:
        cut = cut[:sp]
    return cut + "…"


def _cap_sentences(text: str, max_sentences: int) -> str:
    sents = _split_sentences(text)
    if len(sents) <= max_sentences:
        return text.strip()
    return " ".join(sents[:max_sentences]).strip()


def _window_snippet(chunk_text: str, query: str, window_chars: int = WINDOW_CHARS) -> str:
    """Window of ``chunk_text`` centered on the densest cluster of query terms."""
    text = (chunk_text or "").strip()
    if not text:
        return ""
    q_tokens = list(_tokens(query))
    if not q_tokens:
        return _truncate(text, window_chars)

    norm = _normalize(text)
    token_positions: list[tuple[str, int]] = []
    for tok in q_tokens:
        start = 0
        while True:
            idx = norm.find(tok, start)
            if idx == -1:
                break
            before_ok = idx == 0 or not norm[idx - 1].isalnum()
            after_pos = idx + len(tok)
            after_ok = after_pos >= len(norm) or not norm[after_pos].isalnum()
            if before_ok and after_ok:
                token_positions.append((tok, idx))
            start = idx + len(tok)

    if not token_positions:
        return _truncate(text, window_chars)

    half = window_chars // 2
    best_center = token_positions[0][1]
    best_distinct = -1
    best_total = -1
    for _, center in token_positions:
        lo, hi = center - half, center + half
        distinct = {t for t, p in token_positions if lo <= p <= hi}
        total = sum(1 for _, p in token_positions if lo <= p <= hi)
        if (len(distinct), total) > (best_distinct, best_total):
            best_distinct, best_total, best_center = len(distinct), total, center

    start = max(0, best_center - half)
    end = min(len(text), start + window_chars)
    start = max(0, end - window_chars)

    snippet = text[start:end].strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    if prefix:
        sp = snippet.find(" ")
        if 0 < sp < 30:
            snippet = snippet[sp + 1 :]
    if suffix:
        sp = snippet.rfind(" ")
        if sp > len(snippet) - 30:
            snippet = snippet[:sp]

    # Clean up common PDF headers
    snippet = re.sub(r"^(?:\d+\s+)?HDFC.*?Fund\s*(?:-\s*KIM)?\s*", "", snippet, flags=re.IGNORECASE)
    snippet = re.sub(r"^KEY INFORMATION MEMORANDUM\s*", "", snippet, flags=re.IGNORECASE)
    snippet = re.sub(r"^HDFC.*?Fund\s*", "", snippet, flags=re.IGNORECASE)
    snippet = re.sub(r"\s+", " ", snippet).strip()

    return f"{prefix}{snippet}{suffix}"


# ---------------------------------------------------------------------------
# Public API: builders for each branch
# ---------------------------------------------------------------------------


def _is_grounded(top: Hit, query: str) -> bool:
    """Heuristic: top hit is strong enough to answer.

    Two conditions:
      1. cosine score above MIN_SCORE_FOR_ANSWER, AND
      2. at least one non-stopword query token actually appears in the chunk
         (so we never quote a chunk that has no lexical link to the question).
    """
    if top.score < MIN_SCORE_FOR_ANSWER:
        return False
    q = _tokens(query)
    if not q:
        return True  # Pure semantic match; trust the score.
    chunk_norm = _normalize(top.text)
    return any(re.search(rf"\b{re.escape(t)}\b", chunk_norm) for t in q)


def build_answer_response(query: str, hits: List[Hit]) -> Response:
    """Build a response from retrieved chunks. Uses extractive snippets (deterministic)."""
    if not hits:
        return build_not_found_response()
    
    top = hits[0]
    if top.score < MIN_SCORE_FOR_ANSWER:
        return build_not_found_response()

    # Try LLM synthesis only if enabled
    if USE_LLM:
        llm_output = generate_answer(query, top.text, top.url, top.last_updated_from_source)
        if llm_output:
            match = re.search(r"Answer:\s*(.*?)(?:\n|$)", llm_output, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                # Double-check for typical hallucination phrases
                forbidden = ["subject to change", "verify with latest factsheet", "consult your advisor"]
                if not any(f in text.lower() for f in forbidden):
                    return Response(
                        kind="answer",
                        text=text,
                        url=top.url or None,
                        last_updated=top.last_updated_from_source or None,
                    )

    # Deterministic fallback: extractive snippet
    snippet = _window_snippet(top.text, query)
    text = _cap_sentences(snippet, MAX_SENTENCES)

    return Response(
        kind="answer",
        text=text,
        url=top.url or None,
        last_updated=top.last_updated_from_source or None,
    )


def build_howto_response(query: str, hits: List[Hit]) -> Response:
    """Build a HOW_TO response. Uses minimal safe instructions (deterministic)."""
    if not hits:
        return build_not_found_response()
    top = hits[0]
    
    # Try LLM synthesis only if enabled
    if USE_LLM:
        llm_output = generate_answer(query, top.text, top.url, top.last_updated_from_source)
        if llm_output:
            match = re.search(r"Answer:\s*(.*?)(?:\n|$)", llm_output, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                # Double-check grounding
                forbidden = ["subject to change", "consult an advisor"]
                if not any(f in text.lower() for f in forbidden):
                    return Response(
                        kind="howto",
                        text=text,
                        url=top.url or None,
                        last_updated=top.last_updated_from_source or None,
                    )

    # Deterministic safe template
    text = "You can refer to the official source for instructions."
    return Response(
        kind="howto",
        text=text,
        url=top.url or None,
        last_updated=top.last_updated_from_source or None,
    )


def build_refuse_response(reason: str = "advice") -> Response:
    """Build a polite facts-only refusal."""
    msg = REFUSAL_PII if reason == "pii" else REFUSAL_ADVICE
    return Response(kind="refuse", text=msg, url=EDUCATIONAL_SOURCE_URL)


def build_not_found_response() -> Response:
    return Response(kind="not_found", text=NOT_FOUND_MESSAGE)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_response(resp: Response) -> str:
    """Render the Response into the user-facing string in the spec format."""
    if resp.kind in ("answer", "howto", "refuse"):
        lines = [f"Answer: {resp.text}" if resp.kind != "refuse" else resp.text]
        if resp.url:
            lines.append(f"Source: {resp.url}")
        # Always include Last updated from sources if we have a URL/answer
        date_str = resp.last_updated if resp.last_updated else "Not stated on source page"
        lines.append(f"Last updated from sources: {date_str}")
        return "\n".join(lines)

    # not_found
    return resp.text


# ---------------------------------------------------------------------------
# Backward-compat shims for older code paths
# ---------------------------------------------------------------------------


@dataclass
class Answer:
    text: str
    url: Optional[str]
    last_updated: Optional[str]
    grounded: bool


def compose(hits: List[Hit], query: str = "") -> Answer:
    """Older API used by earlier UI snapshots."""
    resp = build_answer_response(query, hits)
    return Answer(
        text=resp.text,
        url=resp.url,
        last_updated=resp.last_updated,
        grounded=(resp.kind == "answer"),
    )


def format_for_display(answer: Answer) -> str:
    if not answer.grounded:
        return answer.text
    lines = [f"Answer: {answer.text}"]
    if answer.url:
        lines.append(f"Source: {answer.url}")
    if answer.last_updated:
        lines.append(f"Last updated from sources: {answer.last_updated}")
    return "\n".join(lines)
