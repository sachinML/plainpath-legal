"""Clause-aligned comparison of two documents. Numbers are compared in code."""

from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache

from plainpath.clauses import clause_titles_by_kind, detect_clauses
from plainpath.extract import classify_document, extract_money
from plainpath.types import AlignedClause, ClauseHit, CompareReport, MoneyMismatch, MoneyTerm


@lru_cache(maxsize=16)
def compare_documents(text_a: str, text_b: str) -> CompareReport:
    """Align clause families and flag numeric mismatches between two texts."""
    type_a, _ = classify_document(text_a)
    type_b, _ = classify_document(text_b)
    hits_a = {hit.kind: hit for hit in detect_clauses(text_a)}
    hits_b = {hit.kind: hit for hit in detect_clauses(text_b)}
    titles = clause_titles_by_kind()
    kinds = sorted(set(hits_a) | set(hits_b), key=lambda kind: titles.get(kind, kind))

    aligned: list[AlignedClause] = []
    only_a: list[str] = []
    only_b: list[str] = []
    for kind in kinds:
        title = titles.get(kind, kind)
        left = hits_a.get(kind)
        right = hits_b.get(kind)
        if left and not right:
            only_a.append(title)
            aligned.append(
                AlignedClause(
                    kind=kind,
                    title=title,
                    status="only_a",
                    excerpt_a=left.excerpt,
                    excerpt_b=None,
                    note="Present only in document A.",
                )
            )
            continue
        if right and not left:
            only_b.append(title)
            aligned.append(
                AlignedClause(
                    kind=kind,
                    title=title,
                    status="only_b",
                    excerpt_a=None,
                    excerpt_b=right.excerpt,
                    note="Present only in document B.",
                )
            )
            continue
        if left and right:
            aligned.append(_align_both(kind, title, left, right))

    mismatches = _money_mismatches(extract_money(text_a), extract_money(text_b))
    return CompareReport(
        type_a=type_a,
        type_b=type_b,
        aligned=tuple(aligned),
        money_mismatches=tuple(mismatches),
        only_in_a=tuple(only_a),
        only_in_b=tuple(only_b),
    )


def _align_both(kind: str, title: str, left: ClauseHit, right: ClauseHit) -> AlignedClause:
    ratio = SequenceMatcher(None, left.excerpt.lower(), right.excerpt.lower()).ratio()
    if ratio >= 0.72:
        return AlignedClause(
            kind=kind,
            title=title,
            status="same",
            excerpt_a=left.excerpt,
            excerpt_b=right.excerpt,
            note=f"Similar wording (match {int(ratio * 100)}%).",
        )
    return AlignedClause(
        kind=kind,
        title=title,
        status="different",
        excerpt_a=left.excerpt,
        excerpt_b=right.excerpt,
        note=f"Same topic, different wording (match {int(ratio * 100)}%).",
    )


def _money_mismatches(
    money_a: tuple[MoneyTerm, ...], money_b: tuple[MoneyTerm, ...]
) -> list[MoneyMismatch]:
    """Pair amounts that share a label token and differ in cents."""
    out: list[MoneyMismatch] = []
    used_b: set[int] = set()
    for index_a, term_a in enumerate(money_a):
        best: tuple[int, MoneyTerm] | None = None
        for index_b, term_b in enumerate(money_b):
            if index_b in used_b:
                continue
            if not _labels_related(term_a.label, term_b.label):
                continue
            if best is None:
                best = (index_b, term_b)
                continue
            # Prefer a pair with a different amount when labels match.
            if term_a.amount_cents != term_b.amount_cents:
                best = (index_b, term_b)
        if best is None:
            continue
        index_b, term_b = best
        if term_a.amount_cents == term_b.amount_cents:
            used_b.add(index_b)
            continue
        used_b.add(index_b)
        out.append(
            MoneyMismatch(
                label=term_a.label or term_b.label,
                display_a=term_a.display,
                display_b=term_b.display,
                cents_a=term_a.amount_cents,
                cents_b=term_b.amount_cents,
                delta_cents=term_b.amount_cents - term_a.amount_cents,
            )
        )
        if len(out) >= 12:
            break
    return out


_LABEL_STOP = {
    "of",
    "the",
    "a",
    "an",
    "to",
    "and",
    "or",
    "for",
    "in",
    "on",
    "shall",
    "pay",
    "is",
    "be",
}
_LABEL_GENERIC = {"fee", "amount", "charge", "cost", "payment"}


def _labels_related(left: str, right: str) -> bool:
    tokens_a = set(left.lower().split()) - _LABEL_STOP
    tokens_b = set(right.lower().split()) - _LABEL_STOP
    if not tokens_a or not tokens_b:
        return False
    if tokens_a == tokens_b:
        return True
    distinctive_a = tokens_a - _LABEL_GENERIC
    distinctive_b = tokens_b - _LABEL_GENERIC
    return bool(distinctive_a and distinctive_b and distinctive_a & distinctive_b)
