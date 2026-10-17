"""Local embedding model via sentence-transformers (downloaded once, then cached)."""
from __future__ import annotations

from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.EMBED_MODEL)


def embed_documents(texts: list[str]) -> list[list[float]]:
    vectors = _model().encode(
        texts,
        batch_size=config.EMBED_BATCH_SIZE,
        normalize_embeddings=True,   # cosine similarity == dot product
        show_progress_bar=len(texts) > 64,
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    vector = _model().encode(config.QUERY_PREFIX + text, normalize_embeddings=True)
    return vector.tolist()
