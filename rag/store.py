"""Vector store wrapper around a persistent, local ChromaDB collection."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import config
from .embeddings import embed_documents, embed_query


def _client():
    import chromadb
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def get_collection():
    # We supply our own vectors, so Chroma's default embedder is never used.
    return _client().get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _clean_meta(meta: dict) -> dict:
    """Chroma only accepts str/int/float/bool metadata values."""
    return {k: v if isinstance(v, (str, int, float, bool)) else str(v)
            for k, v in meta.items() if v is not None}


def is_indexed(collection, source: str, digest: str) -> bool:
    hit = collection.get(where={"$and": [{"source": source}, {"file_hash": digest}]}, limit=1)
    return bool(hit["ids"])


def delete_source(collection, source: str) -> None:
    collection.delete(where={"source": source})


def add_chunks(collection, chunks: list[dict], digest: str, batch: int = 256) -> int:
    for start in range(0, len(chunks), batch):
        part = chunks[start:start + batch]
        texts = [c["text"] for c in part]
        metas = [_clean_meta({**c["meta"], "file_hash": digest}) for c in part]
        ids = [f"{digest[:16]}-{start + i}" for i in range(len(part))]
        collection.add(ids=ids, documents=texts, metadatas=metas,
                       embeddings=embed_documents(texts))
    return len(chunks)


def search(query: str, k: int | None = None, where: dict | None = None) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    res = collection.query(
        query_embeddings=[embed_query(query)],
        n_results=min(k or config.TOP_K, collection.count()),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"text": doc, "meta": meta, "score": round(1 - dist, 4)}
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def stats() -> dict:
    collection = get_collection()
    metas = collection.get(include=["metadatas"])["metadatas"]
    files = sorted({m["source"] for m in metas})
    return {"chunks": len(metas), "files": files, "path": str(config.CHROMA_DIR),
            "model": config.EMBED_MODEL}
