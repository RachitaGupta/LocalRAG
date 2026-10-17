"""Recursive character chunking with overlap (no external dependencies).

Splits on the most meaningful boundary that fits: paragraphs, then lines,
then sentences, then words, and finally hard character cuts.
"""
from __future__ import annotations

import re

from . import config

SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split(text: str, size: int, separators: list[str]) -> list[str]:
    """Break text into pieces no longer than `size`."""
    if len(text) <= size:
        return [text]
    sep = next((s for s in separators if s == "" or s in text), "")
    if sep == "":
        return [text[i:i + size] for i in range(0, len(text), size)]
    rest = separators[separators.index(sep) + 1:]
    pieces = []
    for part in text.split(sep):
        part = part + sep if sep.strip() in ".?!;," and sep.strip() else part
        if len(part) <= size:
            pieces.append(part)
        else:
            pieces.extend(_split(part, size, rest))
    return pieces


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or config.CHUNK_SIZE
    overlap = config.CHUNK_OVERLAP if overlap is None else overlap
    text = _clean(text)
    if not text:
        return []

    pieces = _split(text, size, SEPARATORS)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        joiner = "\n" if current and not current.endswith((" ", "\n")) else ""
        if len(current) + len(joiner) + len(piece) <= size:
            current += joiner + piece
            continue
        if current.strip():
            chunks.append(current.strip())
        # Start the next chunk with the tail of the previous one (overlap),
        # cut at a word boundary so we don't begin mid-word.
        tail = current[-overlap:] if overlap else ""
        if " " in tail:
            tail = tail[tail.index(" ") + 1:]
        current = (tail + " " + piece) if tail else piece
        if len(current) > size:  # overlap made it too long; drop the overlap
            current = piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_sections(sections: list[dict]) -> list[dict]:
    """Chunk extracted sections, keeping each section's metadata on its chunks."""
    out = []
    for sec in sections:
        for i, chunk in enumerate(chunk_text(sec["text"])):
            out.append({"text": chunk, "meta": {**sec["meta"], "chunk_in_section": i}})
    return out
