"""Text extraction for HTML and PDF sources.

Kept intentionally small. The ingestion pipeline calls these helpers to turn
raw bytes into clean text that the chunker can split.
"""
from __future__ import annotations

import io
import re
from typing import Optional


def extract_html(html: str) -> str:
    """Extract readable text from an HTML string."""
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        # Fallback: very naive tag stripper
        return re.sub(r"<[^>]+>", " ", html or "")
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return _normalize_whitespace(text)


def extract_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    if not pdf_bytes:
        return ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception:
        return ""
    out: list[str] = []
    for page in reader.pages:
        try:
            out.append(page.extract_text() or "")
        except Exception:
            continue
    return _normalize_whitespace("\n".join(out))


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"\u00a0", " ", text or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_by_type(content: bytes, doc_type: Optional[str]) -> str:
    """Dispatch parse by doc_type ('html'|'pdf'|...)."""
    dt = (doc_type or "").lower()
    if dt in {"pdf", "factsheet", "sid", "kim"}:
        return extract_pdf(content)
    return extract_html(content.decode("utf-8", errors="ignore"))
