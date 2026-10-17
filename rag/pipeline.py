"""High-level operations: ingest files, retrieve context, answer questions."""
from __future__ import annotations

import logging
from pathlib import Path

from . import config, store
from .chunking import chunk_sections
from .extract import SUPPORTED_EXT, extract

log = logging.getLogger(__name__)


def iter_files(paths: list[str]):
    for p in map(Path, paths):
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("~$"):
                    yield f
        elif p.is_file():
            yield p
        else:
            log.warning("Not found: %s", p)


def ingest(paths: list[str], force: bool = False) -> dict:
    collection = store.get_collection()
    summary = {"indexed": 0, "skipped": 0, "failed": 0, "chunks": 0}
    try:  # load the embedding model up front so a download problem fails once, clearly
        from .embeddings import embed_documents
        embed_documents(["warm-up"])
    except Exception as exc:
        raise SystemExit(
            f"Could not load embedding model '{config.EMBED_MODEL}': {exc}\n"
            "The first run downloads it from Hugging Face - check your internet/proxy, "
            "or point EMBED_MODEL at a local folder."
        )
    for f in iter_files(paths):
        source = str(f.resolve())
        try:
            digest = store.file_hash(f)
            if not force and store.is_indexed(collection, source, digest):
                log.info("unchanged  %s", f.name)
                summary["skipped"] += 1
                continue
            sections = extract(f)
            for s in sections:
                s["meta"]["source"] = source
            chunks = chunk_sections(sections)
            store.delete_source(collection, source)  # replace old version
            if not chunks:
                log.warning("no text   %s (is Tesseract installed for images/scans?)", f.name)
                summary["failed"] += 1
                continue
            n = store.add_chunks(collection, chunks, digest)
            log.info("indexed    %s  (%d chunks)", f.name, n)
            summary["indexed"] += 1
            summary["chunks"] += n
        except Exception as exc:
            log.error("failed     %s: %s", f.name, exc)
            summary["failed"] += 1
    return summary


def format_citation(meta: dict) -> str:
    loc = []
    for key in ("page", "slide", "sheet", "rows"):
        if key in meta:
            loc.append(f"{key} {meta[key]}")
    return meta.get("filename", "?") + (f" ({', '.join(loc)})" if loc else "")


def build_prompt(question: str, hits: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i}] Source: {format_citation(h['meta'])}\n{h['text']}" for i, h in enumerate(hits, 1)
    )
    return (
        "Answer the question using only the context below. Cite sources like [1], [2]. "
        "If the context does not contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )


def answer(question: str, k: int | None = None) -> dict:
    """Retrieve chunks, then ask a local Ollama model. Falls back to retrieval only."""
    hits = store.search(question, k)
    if not hits:
        return {"answer": "The vector store is empty. Run ingest first.", "hits": []}
    import requests
    try:
        r = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": build_prompt(question, hits), "stream": False},
            timeout=300,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()
    except requests.ConnectionError:
        text = (f"(Ollama is not running at {config.OLLAMA_URL}. Start it with `ollama serve` "
                f"and `ollama pull {config.OLLAMA_MODEL}`. Showing retrieved chunks only.)")
    except Exception as exc:
        text = f"(LLM call failed: {exc}. Showing retrieved chunks only.)"
    return {"answer": text, "hits": hits}
