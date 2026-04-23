"""Shared constants and paths for the MF assistant pipeline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

NORMALIZED_DIR = DATA_DIR / "normalized"
CHUNKS_DIR = DATA_DIR / "chunks"
CHUNKS_JSONL = CHUNKS_DIR / "chunks.jsonl"

INDEX_DIR = DATA_DIR / "index"
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
META_PATH = INDEX_DIR / "meta.jsonl"
INDEX_INFO_PATH = INDEX_DIR / "info.json"

# Embedding model - small, fast, good general semantic quality.
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384

# Retrieval defaults
DEFAULT_TOP_K = 5
DEFAULT_OVERFETCH = 30  # fetch more than top_k so post-filters still leave enough
