"""Compose grounded answers from retrieved chunks.

We keep this fully extractive (no LLM) by default so answers are guaranteed to
be grounded in retrieved text. The composer:

- Picks the top hit.
- Trims it to <= 3 sentences.
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


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _take_sentences(text: str, max_sentences: int = 3) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    parts = _SENT_SPLIT.split(text)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return text
    return " ".join(parts[:max_sentences]).strip()


def compose(hits: List[Hit]) -> Answer:
    if not hits:
        return Answer(text=REFUSAL_OUT_OF_SCOPE, url=None, last_updated=None, grounded=False)

    top = hits[0]
    snippet = _take_sentences(top.text, max_sentences=3)
    if not snippet:
        return Answer(text=REFUSAL_OUT_OF_SCOPE, url=None, last_updated=None, grounded=False)

    return Answer(
        text=snippet,
        url=top.url,
        last_updated=top.last_checked or None,
        grounded=True,
    )


def format_for_display(answer: Answer) -> str:
    """Render the final user-facing markdown block."""
    if not answer.grounded:
        return answer.text
    lines = [answer.text]
    if answer.url:
        lines.append(f"\nSource: {answer.url}")
    if answer.last_updated:
        lines.append(f"Last updated from sources: {answer.last_updated}")
    return "\n".join(lines)
