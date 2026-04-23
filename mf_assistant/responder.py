"""Compose grounded answers from retrieved chunks.

We keep this fully extractive (no LLM) so answers are guaranteed to be
grounded in retrieved text. The composer:

- Picks the top hit.
- Selects the 1-3 sentences from that chunk that best match the user's
  query (by token overlap), preserving original order.
- Appends exactly one source URL.
- Appends a 'Last updated from sources:' line.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .prompts import REFUSAL_OUT_OF_SCOPE
from .retriever import Hit


@dataclass
class Answer:
    text: str
    url: Optional[str]
    last_updated: Optional[str]
    grounded: bool


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "is", "are", "and", "or",
    "what", "which", "how", "do", "does", "i", "my", "your", "this", "that",
    "be", "as", "at", "by", "from", "with", "about", "it", "fund", "scheme",
    "mutual", "funds", "please", "tell", "me", "hdfc",
}


def _normalize(text: str) -> str:
    """Lowercase and treat hyphens/slashes as spaces so tokens like ``lock-in``
    match ``lock in`` in OCR'd PDF text.
    """
    return re.sub(r"[\-/]", " ", (text or "").lower())


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(_normalize(text)) if w not in _STOPWORDS}


def _split_sentences(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def _window_snippet(chunk_text: str, query: str, window_chars: int = 480) -> str:
    """Return a window of ``chunk_text`` centered on the densest cluster of query terms.

    Falls back to the chunk's first ``window_chars`` characters when no query
    term is present in the chunk.
    """
    text = (chunk_text or "").strip()
    if not text:
        return ""
    q_tokens = list(_tokens(query))
    if not q_tokens:
        return _truncate(text, window_chars)

    # Find positions of any query-token occurrence in the *normalized* chunk
    # text (hyphens turned into spaces). Position alignment with the original
    # text is preserved because _normalize only substitutes single chars.
    norm = _normalize(text)
    # token -> list of positions
    token_positions: list[tuple[str, int]] = []
    for tok in q_tokens:
        start = 0
        while True:
            idx = norm.find(tok, start)
            if idx == -1:
                break
            # ensure word boundary
            before_ok = idx == 0 or not norm[idx - 1].isalnum()
            after_pos = idx + len(tok)
            after_ok = after_pos >= len(norm) or not norm[after_pos].isalnum()
            if before_ok and after_ok:
                token_positions.append((tok, idx))
            start = idx + len(tok)

    if not token_positions:
        return _truncate(text, window_chars)

    # For each candidate center (a hit position), count the number of *distinct*
    # query tokens whose positions fall inside the centered window. The center
    # with the most distinct tokens (ties broken by total hits) wins.
    half = window_chars // 2
    best_center = token_positions[0][1]
    best_distinct = -1
    best_total = -1
    for _, center in token_positions:
        lo = center - half
        hi = center + half
        distinct = {t for t, p in token_positions if lo <= p <= hi}
        total = sum(1 for _, p in token_positions if lo <= p <= hi)
        if (len(distinct), total) > (best_distinct, best_total):
            best_distinct = len(distinct)
            best_total = total
            best_center = center

    start = max(0, best_center - half)
    end = min(len(text), start + window_chars)
    start = max(0, end - window_chars)

    snippet = text[start:end].strip()
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    # Round to nearest space to avoid breaking words when possible.
    if prefix:
        sp = snippet.find(" ")
        if 0 < sp < 30:
            snippet = snippet[sp + 1 :]
    if suffix:
        sp = snippet.rfind(" ")
        if sp > len(snippet) - 30:
            snippet = snippet[:sp]
    return f"{prefix}{snippet}{suffix}"


def _truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    sp = cut.rfind(" ")
    if sp > max_chars - 30:
        cut = cut[:sp]
    return cut + "…"


def compose(hits: List[Hit], query: str = "") -> Answer:
    if not hits:
        return Answer(text=REFUSAL_OUT_OF_SCOPE, url=None, last_updated=None, grounded=False)

    top = hits[0]
    snippet = _window_snippet(top.text, query, window_chars=480)
    if not snippet:
        return Answer(text=REFUSAL_OUT_OF_SCOPE, url=None, last_updated=None, grounded=False)

    return Answer(
        text=snippet,
        url=top.url,
        last_updated=top.last_updated_from_source or None,
        grounded=True,
    )


def format_for_display(answer: Answer) -> str:
    if not answer.grounded:
        return answer.text
    lines = [answer.text]
    if answer.url:
        lines.append(f"\nSource: {answer.url}")
    if answer.last_updated:
        lines.append(f"Last updated from sources: {answer.last_updated}")
    return "\n".join(lines)
