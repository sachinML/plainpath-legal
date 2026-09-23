"""Read uploaded bytes into plain text."""

from __future__ import annotations

import io

# Caps keep extraction linear-time on a Streamlit rerun and bound memory.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_PDF_PAGES = 25
MAX_DOC_CHARS = 80_000
ALLOWED_SUFFIXES = (".txt", ".md", ".pdf")


def clip_text(text: str, max_chars: int = MAX_DOC_CHARS) -> tuple[str, bool]:
    """Return (text, clipped). Lane A only needs the leading window."""
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def bytes_to_text(
    filename: str,
    payload: bytes,
    *,
    max_bytes: int = MAX_UPLOAD_BYTES,
    max_pdf_pages: int = MAX_PDF_PAGES,
) -> str:
    """Decode a .txt/.md upload or extract text from a PDF. Never uses eval."""
    if len(payload) > max_bytes:
        raise ValueError(
            f"That file is {len(payload)} bytes. PlainPath reads at most {max_bytes} bytes."
        )
    lower = filename.lower()
    if not lower.endswith(ALLOWED_SUFFIXES):
        raise ValueError("Use a .txt, .md, or .pdf file.")
    if lower.endswith(".pdf"):
        return _pdf_to_text(payload, max_pages=max_pdf_pages)
    return payload.decode("utf-8", errors="replace")


def _pdf_to_text(payload: bytes, *, max_pages: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("PDF support requires the pypdf package.") from error
    reader = PdfReader(io.BytesIO(payload))
    pages: list[str] = []
    for page in reader.pages[:max_pages]:
        text = page.extract_text() or ""
        pages.append(text)
    joined = "\n\n".join(pages).strip()
    if not joined:
        raise RuntimeError("This PDF did not contain extractable text.")
    return joined
