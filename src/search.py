"""Semantic search + RAG over a client's meeting history.

This is the V2 "intelligence" layer. Two steps, the classic RAG pattern:
  1. RETRIEVE — embed the question and the past meetings, find the most similar passages
     by cosine similarity (done by hand in numpy so the mechanics are visible, not hidden
     behind a vector DB).
  2. GENERATE — hand those passages to Claude and ask it to answer using only them.

Embeddings are local and free (fastembed on onnxruntime — no torch, no paid API).
Anthropic has no embeddings endpoint, so like voice this retrieval half is non-Claude;
the generation half is the existing Claude `call`.
"""

import re
import numpy as np
from src.storage import load_meetings
from src.llm import call

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding()  # small ONNX model, downloaded once
    return _model


def embed(texts: list[str]) -> np.ndarray:
    return np.array(list(_get_model().embed(texts)), dtype=np.float32)


def _chunk(text: str, max_chars: int = 500) -> list[str]:
    """Split text into searchable passages. Blank-line blocks first (one per
    transcript turn), then pack long blocks into ~max_chars sentence windows."""
    text = (text or "").strip()
    if not text:
        return []
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    chunks: list[str] = []
    for b in blocks:
        if len(b) <= max_chars:
            chunks.append(b)
            continue
        cur = ""
        for s in re.split(r"(?<=[.!?])\s+", b):
            if cur and len(cur) + len(s) + 1 > max_chars:
                chunks.append(cur.strip())
                cur = s
            else:
                cur = f"{cur} {s}".strip()
        if cur:
            chunks.append(cur.strip())
    return chunks


def build_index(client_id: str) -> tuple[list[dict], np.ndarray]:
    """Chunk every meeting's notes and embed them. Returns (chunks, embeddings).
    Each chunk: {text, timestamp}. Expensive part — cache by (client, #meetings)."""
    chunks: list[dict] = []
    for m in load_meetings(client_id):
        ts = m.get("_timestamp", "")
        for piece in _chunk(m.get("notes", "")):
            chunks.append({"text": piece, "timestamp": ts})
    if not chunks:
        return [], np.zeros((0, 0), dtype=np.float32)
    embeddings = embed([c["text"] for c in chunks])
    return chunks, embeddings


def search_index(chunks: list[dict], embeddings: np.ndarray, query: str, top_k: int = 5) -> list[dict]:
    """Cheap per-query step: embed the question, rank chunks by cosine similarity."""
    if not chunks:
        return []
    q = embed([query])[0]
    sims = embeddings @ q / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(q) + 1e-9)
    order = np.argsort(-sims)[:top_k]
    return [{**chunks[i], "score": float(sims[i])} for i in order]


RAG_SYSTEM = """You are a wealth management analyst answering a question about one specific client,
using ONLY the excerpts from their past meeting records provided to you.
- Ground every claim in the excerpts. Cite the meeting date(s) in brackets, e.g. [June 19, 2026].
- If the excerpts don't contain enough to answer, say so plainly — never invent facts.
- For advice-style questions, base recommendations on what the records actually show, and note what
  additional information you'd want. Be concise and specific."""

RAG_USER = """Client meeting excerpts:
{context}

Question: {question}

Answer using only the excerpts above, citing the relevant meeting date(s)."""


def answer_from_context(question: str, hits: list[dict]) -> str:
    """Generation half of RAG: answer the question grounded in the retrieved passages."""
    if not hits:
        return "There are no meeting records to search yet for this client."
    context = "\n\n".join(f"[{h['timestamp']}] {h['text']}" for h in hits)
    return call(prompt=RAG_USER.format(context=context, question=question), system=RAG_SYSTEM)
