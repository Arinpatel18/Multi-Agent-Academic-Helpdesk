"""Hybrid retrieval: dense (ChromaDB + nomic-embed-text) fused with BM25 via reciprocal rank fusion.

BM25 matters here because many questions hinge on exact tokens (course codes,
"75%", "CGPA") that dense embeddings of small models blur.
"""
import json
import math
import re
from collections import Counter
from functools import lru_cache

import chromadb

from . import config
from .ingest import embed

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_STOP = set("a an the of to in on for and or is are be by with as at from that this it its what which how many much do does i my me we our you your can".split())
# Words that appear in nearly every document; small models like to pad queries with them,
# which drowns the useful terms. They are removed from the query before dense and BM25 search.
_NOISE = re.compile(r"\b(iit\s*jodhpur|iitj|iit|jodhpur|academic\s+regulations?|rules\s*(and|&)\s*regulations|"
                    r"regulations?|according to|as per|the institute)\b", re.I)


def clean_query(query):
    q = re.sub(r"\s+", " ", _NOISE.sub(" ", query)).strip()
    return q or query


def tokenize(text):
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(d)) for d in docs]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg = sum(self.len) / max(len(self.len), 1)
        df = Counter(t for tf in self.tf for t in tf)
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def top(self, query, k):
        q = tokenize(query)
        scores = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            if s:
                scores.append((s, i))
        return [i for _, i in sorted(scores, reverse=True)[:k]]


@lru_cache(maxsize=1)
def _index():
    if not config.CHUNKS_FILE.exists():
        raise RuntimeError("Vector store not built. Run: python -m helpdesk.ingest --reset")
    chunks = [json.loads(l) for l in open(config.CHUNKS_FILE, encoding="utf-8")]
    client = chromadb.PersistentClient(path=str(config.VECTORSTORE_DIR / "chroma"))
    col = client.get_collection(config.COLLECTION)
    return chunks, {c["id"]: i for i, c in enumerate(chunks)}, BM25([c["title"] + " " + c["text"] for c in chunks]), col


def search(query, k=config.TOP_K, pool=20):
    chunks, pos, bm25, col = _index()
    query = clean_query(query)
    dense = col.query(query_embeddings=embed([query], "search_query: "), n_results=pool)["ids"][0]
    sparse = bm25.top(query, pool)
    fused = Counter()
    for rank, cid in enumerate(dense):
        fused[pos[cid]] += 1 / (60 + rank)
    for rank, i in enumerate(sparse):
        fused[i] += 1 / (60 + rank)
    return [dict(chunks[i], score=round(s, 4)) for i, s in fused.most_common(k)]


def citation(chunk):
    return f"{chunk['source']}, page {chunk['page']}" if chunk["page"] and chunk["page"].isdigit() else chunk["source"]
