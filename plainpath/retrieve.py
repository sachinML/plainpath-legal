"""Lightweight retrieval over the uploaded document. No embeddings, no extra deps."""

from __future__ import annotations

from functools import lru_cache
import re

from plainpath.types import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "by",
    "with",
    "is",
    "are",
    "be",
    "this",
    "that",
    "it",
    "as",
    "at",
    "from",
    "not",
    "if",
}


@lru_cache(maxsize=16)
def chunk_document(text: str, max_chars: int = 900) -> tuple[RetrievedChunk, ...]:
    """Split on blank lines, then pack short paragraphs into bounded chunks."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        cleaned = text.strip()
        if not cleaned:
            return ()
        paragraphs = [cleaned]

    packed: list[tuple[int, str]] = []
    cursor = 0
    buf = ""
    buf_start = 0
    for para in paragraphs:
        start = text.find(para, cursor)
        if start < 0:
            start = cursor
        cursor = start + len(para)
        if buf and len(buf) + 2 + len(para) > max_chars:
            packed.append((buf_start, buf.strip()))
            buf = para
            buf_start = start
        else:
            if not buf:
                buf_start = start
            buf = f"{buf}\n\n{para}" if buf else para
    if buf.strip():
        packed.append((buf_start, buf.strip()))

    chunks: list[RetrievedChunk] = []
    for index, (start, body) in enumerate(packed, start=1):
        chunks.append(
            RetrievedChunk(
                chunk_id=f"E{index}",
                text=body,
                score=0.0,
                start=start,
            )
        )
    return tuple(chunks)


def retrieve(text: str, question: str, *, k: int = 4) -> tuple[RetrievedChunk, ...]:
    """
    Rank chunks by token overlap with the question, with a phrase-boost.

    Returns up to `k` chunks with score > 0, or the first chunk if nothing matches
    so the caller always has grounding text when the document is non-empty.
    """
    chunks = chunk_document(text)
    if not chunks:
        return ()
    q_tokens = _tokens(question)
    q_phrases = _phrases(question)
    ranked: list[RetrievedChunk] = []
    for chunk in chunks:
        score = _score(chunk.text, q_tokens, q_phrases)
        ranked.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                score=score,
                start=chunk.start,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    positive = [item for item in ranked if item.score > 0]
    picked = positive[:k] if positive else ranked[:1]
    return tuple(picked)


def tokenize(text: str) -> tuple[str, ...]:
    """Public tokenizer used by tests."""
    return tuple(_tokens(text))


def _tokens(text: str) -> list[str]:
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOP and len(tok) > 1]


def _phrases(question: str) -> list[str]:
    tokens = _tokens(question)
    phrases = [" ".join(tokens[i : i + 2]) for i in range(len(tokens) - 1)]
    return phrases


def _score(chunk_text: str, q_tokens: list[str], q_phrases: list[str]) -> float:
    lowered = chunk_text.lower()
    chunk_tokens = set(_tokens(chunk_text))
    if not q_tokens:
        return 0.0
    overlap = sum(1 for tok in q_tokens if tok in chunk_tokens)
    phrase_hits = sum(1 for phrase in q_phrases if phrase in lowered)
    return float(overlap) + 2.0 * float(phrase_hits)
