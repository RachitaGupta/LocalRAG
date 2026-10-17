# Local RAG Starter

A small, fully free and local Retrieval-Augmented Generation project:

```
files ──► extract (+OCR) ──► chunk ──► embed (bge-small) ──► ChromaDB ──► search / ask (Ollama)
```

| Stage | Tool |
|---|---|
| PDF text | PyMuPDF |
| Scanned PDFs, images | Tesseract OCR (`pytesseract`) |
| Word / PowerPoint | `python-docx`, `python-pptx` (incl. tables, slide notes, OCR of embedded images) |
| Excel / CSV | `pandas` + `openpyxl` (row-wise `column: value` text, every sheet) |
| Chunking | Built-in recursive splitter with overlap (`rag/chunking.py`) |
| Embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers (runs on CPU) |
| Vector store | ChromaDB, persisted to `./vector_store` |
| Answers (optional) | Any Ollama model, e.g. `llama3.2` |

Supported files: `.pdf .docx .pptx .xlsx .xlsm .xls .csv .tsv .png .jpg .jpeg .tif .tiff .bmp .webp .gif .txt .md .html .json .xml`

---

## Step-by-step setup

### 1. Install Python and Tesseract

You need Python 3.10 or newer, plus the Tesseract OCR engine (a system program, not a pip package).

| OS | Command |
|---|---|
| macOS | `brew install tesseract` |
| Ubuntu/Debian | `sudo apt install tesseract-ocr` |
| Windows | Install from https://github.com/UB-Mannheim/tesseract/wiki, then set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` |

Extra OCR languages: install e.g. `tesseract-ocr-deu`, then set `OCR_LANG=eng+deu`.

### 2. Create a virtual environment and install dependencies

```bash
cd rag-project
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. (Optional) Generate test files

```bash
python scripts/make_samples.py     # writes one sample of every type to data/samples/
```

### 4. Build the vector store (ingest)

Put your documents in a folder (e.g. `data/`) and run:

```bash
python main.py ingest data/
```

What happens to each file:
1. **Extract**: text is pulled out with the right library for the file type. PDF pages with almost no text are rendered at 300 DPI and OCR'd. Images are OCR'd directly.
2. **Chunk**: text is split into ~1000-character chunks with 150 characters of overlap, preferring paragraph, then line, then sentence boundaries.
3. **Embed**: each chunk becomes a 384-dimension normalized vector. The first run downloads the model (~130 MB) to your Hugging Face cache.
4. **Store**: vectors, text and metadata (file name, page, sheet, slide, rows, file hash) are saved in Chroma at `./vector_store`.

Re-running `ingest` skips unchanged files (SHA-256 hash check) and replaces the chunks of files that changed. Use `--force` to re-index everything.

### 5. Search

```bash
python main.py search "refund policy"
python main.py search "revenue by region" --filetype xlsx -k 3
python main.py stats
```

### 6. (Optional) Get generated answers with Ollama

```bash
# install from https://ollama.com, then:
ollama pull llama3.2
ollama serve                         # if it isn't already running
python main.py ask "How long is the hardware warranty?"
```

Without Ollama, `ask` still shows the retrieved sources.

### 7. Start over

```bash
python main.py reset                 # deletes the collection
```

---

## Configuration

Every setting in `rag/config.py` can be overridden with an environment variable:

| Variable | Default | Notes |
|---|---|---|
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Try `BAAI/bge-base-en-v1.5` (better) or `intfloat/multilingual-e5-base` (multilingual). **Changing the model requires `reset` + re-ingest.** |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Characters (~4 chars per token) |
| `TOP_K` | `5` | Chunks retrieved per query |
| `OCR_ENABLED` | `1` | Set `0` to skip OCR |
| `OCR_LANG` | `eng` | Tesseract language codes |
| `OCR_MIN_CHARS` | `30` | PDF pages with less text than this get OCR'd |
| `EXCEL_ROWS_PER_BLOCK` | `20` | Spreadsheet rows grouped per text block |
| `CHROMA_DIR` | `./vector_store` | Where the store lives |
| `OLLAMA_MODEL` | `llama3.2` | Any model you've pulled |

Example: `EMBED_MODEL=BAAI/bge-base-en-v1.5 CHUNK_SIZE=800 python main.py ingest data/`

## Using it from Python

```python
from rag import pipeline, store

pipeline.ingest(["data/"])
for hit in store.search("warranty", k=3):
    print(hit["score"], pipeline.format_citation(hit["meta"]), hit["text"][:100])
print(pipeline.answer("How long is the warranty?")["answer"])
```

## Project layout

```
rag-project/
├── main.py              # CLI: ingest / search / ask / stats / reset
├── requirements.txt
├── rag/
│   ├── config.py        # settings (env-overridable)
│   ├── extract.py       # per-file-type extraction + OCR
│   ├── chunking.py      # recursive splitter with overlap
│   ├── embeddings.py    # sentence-transformers wrapper
│   ├── store.py         # ChromaDB: add, dedupe, search
│   └── pipeline.py      # ingest + answer orchestration
├── scripts/make_samples.py
├── data/                # put your documents here
└── vector_store/        # created on first ingest
```

## Next steps

- **Better layout and tables**: swap `rag/extract.py` for [Docling](https://github.com/docling-project/docling) on complex PDFs.
- **Better OCR** on messy scans: replace `_ocr_image` with PaddleOCR or RapidOCR.
- **Hybrid search**: add BM25 (`rank-bm25`) and merge it with vector results for exact terms like IDs.
- **Reranking**: re-score the top 20 hits with `BAAI/bge-reranker-base` before keeping the top 5.
- **UI**: wrap `store.search` and `pipeline.answer` in a ~30-line Streamlit app.
