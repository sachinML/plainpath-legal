"""Keyword/phrase clause detector. Flags are computed here, never guessed by the LLM."""

from __future__ import annotations

from dataclasses import dataclass
import re

from plainpath.types import ClauseHit, RiskLevel


@dataclass(frozen=True)
class ClausePattern:
    """A searchable clause family."""

    kind: str
    title: str
    level: RiskLevel
    why_it_matters: str
    phrases: tuple[str, ...]


CLAUSE_PATTERNS: tuple[ClausePattern, ...] = (
    ClausePattern(
        kind="auto_renewal",
        title="Automatic renewal",
        level="high",
        why_it_matters="The deal may continue unless you cancel in a specific window.",
        phrases=(
            "automatically renew",
            "automatic renewal",
            "auto-renew",
            "shall renew unless",
            "renews for successive",
        ),
    ),
    ClausePattern(
        kind="unilateral_change",
        title="Company can change terms",
        level="high",
        why_it_matters="The other side may change the rules after you agree.",
        phrases=(
            "we may modify these terms",
            "may update these terms",
            "reserve the right to modify",
            "unilateral",
            "at any time without notice",
            "in its sole discretion",
        ),
    ),
    ClausePattern(
        kind="arbitration",
        title="Binding arbitration",
        level="high",
        why_it_matters="Disputes may have to go to private arbitration instead of court.",
        phrases=(
            "binding arbitration",
            "arbitration",
            "arbitrator",
            "dispute resolution body",
        ),
    ),
    ClausePattern(
        kind="class_waiver",
        title="Class or collective action waiver",
        level="high",
        why_it_matters="You may have to bring claims alone, not as a group.",
        phrases=(
            "class action waiver",
            "waive any right to participate in a class",
            "class or collective action",
            "no class actions",
        ),
    ),
    ClausePattern(
        kind="limitation_of_liability",
        title="Limitation of liability",
        level="medium",
        why_it_matters="The other side may cap what they would ever have to pay you.",
        phrases=(
            "limitation of liability",
            "shall not be liable",
            "in no event shall",
            "liability shall not exceed",
            "maximum liability",
        ),
    ),
    ClausePattern(
        kind="indemnity",
        title="Indemnity / hold harmless",
        level="high",
        why_it_matters="You may have to cover the other side's losses and legal costs.",
        phrases=("indemnify", "indemnification", "hold harmless", "defend and hold"),
    ),
    ClausePattern(
        kind="early_termination_fee",
        title="Early termination fee",
        level="medium",
        why_it_matters="Leaving early may cost a stated penalty.",
        phrases=(
            "early termination fee",
            "early termination penalty",
            "liquidated damages",
            "if tenant vacates before",
        ),
    ),
    ClausePattern(
        kind="late_fee",
        title="Late fee",
        level="medium",
        why_it_matters="Missing a due date can add extra charges.",
        phrases=("late fee", "late charge", "overdue", "past due"),
    ),
    ClausePattern(
        kind="entry",
        title="Right of entry",
        level="medium",
        why_it_matters="Someone may be allowed to enter a home or space, with or without notice.",
        phrases=(
            "right to enter",
            "may enter the premises",
            "access the premises",
            "inspect the premises",
        ),
    ),
    ClausePattern(
        kind="non_compete",
        title="Non-compete / non-solicit",
        level="high",
        why_it_matters="You may be limited in where you can work or whom you can contact later.",
        phrases=(
            "non-compete",
            "noncompete",
            "covenant not to compete",
            "shall not solicit",
            "non-solicitation",
        ),
    ),
    ClausePattern(
        kind="at_will",
        title="At-will employment",
        level="medium",
        why_it_matters="The job may be ended by either side at any time, as written here.",
        phrases=("at-will", "at will employment", "either party may terminate employment"),
    ),
    ClausePattern(
        kind="ip_assignment",
        title="Intellectual property assignment",
        level="medium",
        why_it_matters="Work you create may belong to the other party.",
        phrases=(
            "hereby assigns",
            "intellectual property",
            "work made for hire",
            "inventions",
        ),
    ),
    ClausePattern(
        kind="warranty_disclaimer",
        title="Warranty disclaimer",
        level="medium",
        why_it_matters="The document may say goods or services are provided 'as is'.",
        phrases=("as is", "without warranty", "disclaims all warranties", "no warranty"),
    ),
    ClausePattern(
        kind="auto_payment",
        title="Automatic charges",
        level="medium",
        why_it_matters="A card or account may be billed without a new approval each time.",
        phrases=(
            "automatically charge",
            "recurring billing",
            "recurring payment",
            "saved payment method",
        ),
    ),
    ClausePattern(
        kind="data_sharing",
        title="Data sharing",
        level="medium",
        why_it_matters="Information about you may be shared with affiliates or partners.",
        phrases=(
            "share your information",
            "share personal information",
            "affiliates and partners",
            "sell your data",
            "third-party advertisers",
        ),
    ),
    ClausePattern(
        kind="notice_period",
        title="Notice period",
        level="low",
        why_it_matters="You may have a short window to give or receive written notice.",
        phrases=("written notice", "days' notice", "days notice", "prior written notice"),
    ),
    ClausePattern(
        kind="deposit",
        title="Deposit or prepaid amount",
        level="low",
        why_it_matters="Money may be held and returned only if stated conditions are met.",
        phrases=("security deposit", "damage deposit", "prepaid", "retainer"),
    ),
    ClausePattern(
        kind="governing_law",
        title="Governing law / venue",
        level="low",
        why_it_matters="Disputes may be limited to a specific place's courts or rules.",
        phrases=("governing law", "governed by the laws", "exclusive venue", "jurisdiction"),
    ),
    ClausePattern(
        kind="confession_of_judgment",
        title="Confession of judgment",
        level="high",
        why_it_matters="You may be giving up the chance to defend yourself in court first.",
        phrases=("confession of judgment", "confess judgment", "cognovit"),
    ),
    ClausePattern(
        kind="waiver_of_jury",
        title="Jury trial waiver",
        level="medium",
        why_it_matters="A jury may not hear the dispute.",
        phrases=("waive the right to a jury", "jury trial waiver", "waives any right to trial by jury"),
    ),
)


def detect_clauses(text: str) -> tuple[ClauseHit, ...]:
    """Return unique clause hits with excerpts and character offsets."""
    lowered = text.lower()
    hits: list[ClauseHit] = []
    seen_kinds: set[str] = set()
    for pattern in CLAUSE_PATTERNS:
        start = _first_phrase_index(lowered, pattern.phrases)
        if start is None:
            continue
        if _is_negated(lowered, start):
            continue
        if pattern.kind in seen_kinds:
            continue
        seen_kinds.add(pattern.kind)
        excerpt = _window(text, start)
        hits.append(
            ClauseHit(
                kind=pattern.kind,
                title=pattern.title,
                level=pattern.level,
                why_it_matters=pattern.why_it_matters,
                excerpt=excerpt,
                start=start,
                end=min(len(text), start + len(excerpt)),
            )
        )
    return tuple(hits)


def clause_titles_by_kind() -> dict[str, str]:
    """Map clause kind → display title."""
    return {pattern.kind: pattern.title for pattern in CLAUSE_PATTERNS}


_NEGATION_RE = re.compile(r"\b(do not|does not|did not|will not|shall not|cannot|n['’]t)\b")


def _is_negated(lowered: str, start: int, window: int = 28) -> bool:
    """Skip a hit when the matching phrase is locally denied (e.g. 'does not automatically renew')."""
    prefix = lowered[max(0, start - window) : start]
    return bool(_NEGATION_RE.search(prefix))


def _first_phrase_index(lowered: str, phrases: tuple[str, ...]) -> int | None:
    best: int | None = None
    for phrase in phrases:
        idx = lowered.find(phrase.lower())
        if idx < 0:
            continue
        if best is None or idx < best:
            best = idx
    return best


def _window(text: str, start: int, radius: int = 140) -> str:
    lo = max(0, start - 40)
    hi = min(len(text), start + radius)
    chunk = text[lo:hi]
    return re.sub(r"\s+", " ", chunk).strip()
