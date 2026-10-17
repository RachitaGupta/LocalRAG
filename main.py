"""Command-line interface.

    python main.py ingest data/            # index a folder (or files)
    python main.py search "refund policy"  # semantic search only
    python main.py ask "What is the refund policy?"   # search + Ollama answer
    python main.py stats                   # what is in the store
    python main.py reset                   # delete the whole collection
"""
import argparse
import logging
import textwrap

from rag import config, pipeline, store


def print_hits(hits):
    for i, h in enumerate(hits, 1):
        print(f"\n[{i}] score={h['score']}  {pipeline.format_citation(h['meta'])}")
        print(textwrap.indent(textwrap.shorten(h["text"], 400, placeholder=" ..."), "    "))


def main():
    p = argparse.ArgumentParser(description="Small local RAG: extract -> OCR -> chunk -> embed -> Chroma")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="index files or folders")
    pi.add_argument("paths", nargs="+")
    pi.add_argument("--force", action="store_true", help="re-index even if unchanged")

    ps = sub.add_parser("search", help="semantic search")
    ps.add_argument("query")
    ps.add_argument("-k", type=int, default=config.TOP_K)
    ps.add_argument("--filetype", help="filter, e.g. pdf, xlsx, png")

    pa = sub.add_parser("ask", help="search + answer with a local LLM (Ollama)")
    pa.add_argument("question")
    pa.add_argument("-k", type=int, default=config.TOP_K)

    sub.add_parser("stats", help="show store contents")
    sub.add_parser("reset", help="delete the collection")

    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "chromadb", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if args.cmd == "ingest":
        print(pipeline.ingest(args.paths, force=args.force))
    elif args.cmd == "search":
        where = {"filetype": args.filetype.lstrip(".")} if args.filetype else None
        print_hits(store.search(args.query, args.k, where))
    elif args.cmd == "ask":
        result = pipeline.answer(args.question, args.k)
        print("\nANSWER:\n" + result["answer"])
        print("\nSOURCES:")
        print_hits(result["hits"])
    elif args.cmd == "stats":
        s = store.stats()
        print(f"Store: {s['path']}\nModel: {s['model']}\nChunks: {s['chunks']}\nFiles ({len(s['files'])}):")
        for f in s["files"]:
            print("  -", f)
    elif args.cmd == "reset":
        store._client().delete_collection(config.COLLECTION_NAME)
        print("Collection deleted.")


if __name__ == "__main__":
    main()
