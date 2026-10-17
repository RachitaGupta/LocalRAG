"""Central settings. Override any value with an environment variable of the same name."""
import os
from pathlib import Path


def _env(name: str, default):
    value = os.getenv(name)
    if value is None:
        return default
    return type(default)(value)


ROOT_DIR = Path(__file__).resolve().parent.parent

# Where Chroma persists its data on disk
CHROMA_DIR = Path(_env("CHROMA_DIR", str(ROOT_DIR / "vector_store")))
COLLECTION_NAME = _env("COLLECTION_NAME", "documents")

# Embedding model (any sentence-transformers model works)
EMBED_MODEL = _env("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
# BGE models retrieve better when queries carry this instruction prefix
QUERY_PREFIX = _env(
    "QUERY_PREFIX",
    "Represent this sentence for searching relevant passages: "
    if "bge" in EMBED_MODEL.lower() else "",
)
EMBED_BATCH_SIZE = _env("EMBED_BATCH_SIZE", 32)

# Chunking (characters, roughly 4 chars ~ 1 token)
CHUNK_SIZE = _env("CHUNK_SIZE", 1000)
CHUNK_OVERLAP = _env("CHUNK_OVERLAP", 150)

# OCR
OCR_ENABLED = _env("OCR_ENABLED", 1) == 1
OCR_LANG = _env("OCR_LANG", "eng")          # e.g. "eng+deu"
OCR_MIN_CHARS = _env("OCR_MIN_CHARS", 30)   # PDF pages with less text get OCR'd
OCR_DPI = _env("OCR_DPI", 300)
TESSERACT_CMD = _env("TESSERACT_CMD", "")   # set on Windows if not on PATH

# Excel: how many rows go into one text block before chunking
EXCEL_ROWS_PER_BLOCK = _env("EXCEL_ROWS_PER_BLOCK", 20)

# Retrieval / generation
TOP_K = _env("TOP_K", 5)
OLLAMA_URL = _env("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "llama3.2")
