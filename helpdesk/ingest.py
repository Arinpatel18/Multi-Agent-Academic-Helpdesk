"""Build the ChromaDB vector store from the documents in data/documents.

Usage:  python -m helpdesk.ingest [--reset]

Supported formats: .pdf (page-aware), .md/.txt, .xlsx/.csv (row-wise).
Each chunk keeps `source` (file name) and `page` metadata so answers can cite it.
"""
import argparse
import json
import re
import sys

import chromadb
import httpx
import pandas as pd
from pypdf import PdfReader

from . import config


def embed(texts, prefix):
    """Embed a list of strings with the local Ollama embedding model."""
    resp = httpx.post(
        f"{config.OLLAMA_BASE}/api/embed",
        json={"model": config.EMBED_MODEL, "input": [prefix + t for t in texts]},
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def clean(text):
    text = text.replace("​", "").replace("\xa0", " ")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    # Some PDFs extract one word per line; join those into running text.
    if sum(len(l) for l in lines) / len(lines) < 25:
        text = " ".join(lines)
    else:
        text = "\n".join(lines)
    return re.sub(r"[ \t]+", " ", text).strip()


def split(text, size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    """Character window splitter that prefers to break on newlines / sentence ends."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind("\n", start + size // 2, end), text.rfind(". ", start + size // 2, end))
            if cut > start:
                end = cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if len(c) > 40]


def load_document(path):
    """Yield (page, text) pairs for one file."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        for i, page in enumerate(PdfReader(path).pages, start=1):
            yield i, clean(page.extract_text() or "")
    elif suffix in (".md", ".txt"):
        yield None, clean(path.read_text(encoding="utf-8", errors="ignore"))
    elif suffix in (".xlsx", ".xls", ".csv"):
        sheets = pd.read_excel(path, sheet_name=None, header=None) if suffix != ".csv" else {"csv": pd.read_csv(path, header=None)}
        for name, df in sheets.items():
            rows = [" | ".join(str(v) for v in row if pd.notna(v)) for row in df.itertuples(index=False)]
            yield f"sheet '{name}'", "\n".join(r for r in rows if r)


def doc_title(path):
    return re.sub(r"^\d+_", "", path.stem).replace("_", " ")


def build(reset=False):
    files = sorted(p for p in config.DOCS_DIR.iterdir() if p.suffix.lower() in (".pdf", ".md", ".txt", ".xlsx", ".csv"))
    records = []
    for path in files:
        n = 0
        for page, text in load_document(path):
            for j, chunk in enumerate(split(text)):
                records.append({
                    "id": f"{path.stem}::p{page}::c{j}",
                    "text": chunk,
                    "source": path.name,
                    "title": doc_title(path),
                    "page": "" if page is None else str(page),
                })
                n += 1
        print(f"  {path.name:50s} {n:5d} chunks")
    print(f"Total chunks: {len(records)} from {len(files)} documents")

    config.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(config.VECTORSTORE_DIR / "chroma"))
    if reset:
        try:
            client.delete_collection(config.COLLECTION)
        except Exception:
            pass
    col = client.get_or_create_collection(config.COLLECTION, metadata={"hnsw:space": "cosine"})

    batch = 32
    for i in range(0, len(records), batch):
        part = records[i:i + batch]
        col.upsert(
            ids=[r["id"] for r in part],
            documents=[r["text"] for r in part],
            embeddings=embed([r["text"] for r in part], "search_document: "),
            metadatas=[{k: r[k] for k in ("source", "title", "page")} for r in part],
        )
        print(f"\r  embedded {min(i + batch, len(records))}/{len(records)}", end="", file=sys.stderr)
    print(file=sys.stderr)

    with open(config.CHUNKS_FILE, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Vector store ready at {config.VECTORSTORE_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop and rebuild the collection")
    build(ap.parse_args().reset)
