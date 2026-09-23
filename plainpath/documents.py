"""Read uploaded bytes into plain text."""

from __future__ import annotations

import io


def bytes_to_text(filename: str, payload: bytes) -> str:
    """Decode a .txt/.md upload or extract text from a PDF. Never uses eval."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _pdf_to_text(payload)
    return payload.decode("utf-8", errors="replace")


def _pdf_to_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("PDF support requires the pypdf package.") from error
    reader = PdfReader(io.BytesIO(payload))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    joined = "\n\n".join(pages).strip()
    if not joined:
        raise RuntimeError("This PDF did not contain extractable text.")
    return joined
