import os
from pathlib import Path

# --- Cloud Mode Detection ---
# Streamlit Cloud sets specific environment variables. We also check for common cloud paths.
IS_ON_STREAMLIT_CLOUD = (
    os.environ.get("STREAMLIT_SHARING_CLIENT") == "true" or 
    os.environ.get("STREAMLIT_RUNTIME_STATS_GATHER_USAGE_STATS") is not None or
    os.path.exists("/mount/src") or  # Standard Streamlit Cloud mount point
    os.environ.get("HOME") == "/home/adminuser"
)
CLOUD_LIGHT_MODE = os.environ.get("CLOUD_LIGHT_MODE", "1" if IS_ON_STREAMLIT_CLOUD else "0") == "1"

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

# LLM Control
USE_LLM_REWRITE = True
USE_LLM_POLISH = False  # Set to True to allow LLM to polish final answers
