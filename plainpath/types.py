"""Shared data types for the PlainPath facts engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Urgency = Literal["now", "soon", "when_you_can"]
RiskLevel = Literal["high", "medium", "low"]
Literacy = Literal["plain", "everyday", "keep_terms"]
PersonaId = Literal[
    "tenant",
    "worker",
    "consumer",
    "small_business",
    "caregiver",
    "community_navigator",
]

DISCLAIMER = (
    "PlainPath provides information and assistance only. It is not a lawyer, "
    "it does not create an attorney-client relationship, and it does not replace "
    "professional legal advice. Laws vary by place. If a deadline, money, housing, "
    "job, or family decision is on the line, talk to a licensed legal professional "
    "or a legal-aid clinic in your area."
)


@dataclass(frozen=True)
class Party:
    """A named party extracted from the document."""

    role: str
    name: str
    source: str


@dataclass(frozen=True)
class MoneyTerm:
    """A currency amount found in context. Stored in integer cents."""

    amount_cents: int
    label: str
    source: str
    currency: str = "USD"

    @property
    def display(self) -> str:
        """Human-readable amount, computed in code (not by the LLM)."""
        sign = "-" if self.amount_cents < 0 else ""
        cents = abs(self.amount_cents)
        return f"{sign}{self.currency} {cents // 100}.{cents % 100:02d}"


@dataclass(frozen=True)
class DatedItem:
    """A calendar date with surrounding context."""

    value: date
    label: str
    source: str
    days_from_today: int


@dataclass(frozen=True)
class DurationTerm:
    """A duration such as '30 days' or '18 months'."""

    quantity: int
    unit: str
    days_approx: int
    source: str


@dataclass(frozen=True)
class Obligation:
    """Who appears to owe what, based on shall/must language."""

    actor: str
    duty: str
    source: str


@dataclass(frozen=True)
class ClauseHit:
    """A known clause pattern matched in the text."""

    kind: str
    title: str
    level: RiskLevel
    why_it_matters: str
    excerpt: str
    start: int
    end: int


@dataclass(frozen=True)
class Gap:
    """A protection or topic the document does not appear to mention."""

    topic: str
    why_it_matters: str
    suggested_question: str


@dataclass(frozen=True)
class RiskReport:
    """Deterministic risk score derived from clause hits and money terms."""

    score: int
    band: RiskLevel
    summary: str
    drivers: tuple[str, ...]


@dataclass(frozen=True)
class FactSheet:
    """Everything the local engine knows — no LLM involved."""

    document_type: str
    document_type_confidence: str
    parties: tuple[Party, ...]
    money: tuple[MoneyTerm, ...]
    dates: tuple[DatedItem, ...]
    durations: tuple[DurationTerm, ...]
    obligations: tuple[Obligation, ...]
    governing_law: str | None
    word_count: int
    reading_ease: float
    reading_grade: float
    clauses: tuple[ClauseHit, ...]
    gaps: tuple[Gap, ...]
    risk: RiskReport


@dataclass(frozen=True)
class AlignedClause:
    """A clause kind compared across two documents."""

    kind: str
    title: str
    status: Literal["same", "different", "only_a", "only_b"]
    excerpt_a: str | None
    excerpt_b: str | None
    note: str


@dataclass(frozen=True)
class MoneyMismatch:
    """A numeric amount that differs between two documents."""

    label: str
    display_a: str
    display_b: str
    cents_a: int
    cents_b: int
    delta_cents: int


@dataclass(frozen=True)
class CompareReport:
    """Deterministic comparison of two documents."""

    type_a: str
    type_b: str
    aligned: tuple[AlignedClause, ...]
    money_mismatches: tuple[MoneyMismatch, ...]
    only_in_a: tuple[str, ...]
    only_in_b: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedChunk:
    """A document excerpt ranked for a question."""

    chunk_id: str
    text: str
    score: float
    start: int


@dataclass(frozen=True)
class NextStep:
    """A routed next step. Titles/why come from rules, not the LLM."""

    code: str
    title: str
    why: str
    urgency: Urgency
    audience_note: str


@dataclass(frozen=True)
class LawyerBrief:
    """Structured packet a person can take to a legal professional."""

    snapshot_lines: tuple[str, ...]
    risk_lines: tuple[str, ...]
    gap_questions: tuple[str, ...]
    documents_to_bring: tuple[str, ...]
    accessibility_checklist: tuple[str, ...]
    role_questions: tuple[str, ...]


@dataclass
class LLMResult:
    """Outcome of a language-model call that never raises to the UI."""

    text: str
    provider: str
    live: bool
    degraded: bool
    error_kind: str | None = None


@dataclass(frozen=True)
class Persona:
    """A named audience with explicit UI representation."""

    id: PersonaId
    label: str
    blurb: str
    focus: tuple[str, ...]
    starter_questions: tuple[str, ...]


PERSONAS: tuple[Persona, ...] = (
    Persona(
        id="tenant",
        label="Tenant / renter",
        blurb="Leases, deposits, repairs, entry, and staying housed.",
        focus=("rent", "deposit", "landlord", "entry", "eviction", "renewal", "repairs"),
        starter_questions=(
            "When can the landlord enter my home?",
            "What happens if I am late on rent?",
            "How do I get my security deposit back?",
            "Does this lease renew on its own?",
        ),
    ),
    Persona(
        id="worker",
        label="Worker / employee",
        blurb="Job offers, non-competes, pay, and leaving a job.",
        focus=("salary", "non-compete", "termination", "arbitration", "intellectual property"),
        starter_questions=(
            "Can I work elsewhere after I leave?",
            "Is this job at-will, and what does that mean in plain words?",
            "What pay and benefits are actually written down?",
            "Do I have to use private arbitration?",
        ),
    ),
    Persona(
        id="consumer",
        label="Consumer",
        blurb="Subscriptions, warranties, privacy, and store or app terms.",
        focus=("subscription", "refund", "warranty", "privacy", "arbitration", "auto-renew"),
        starter_questions=(
            "How do I cancel, and is there a deadline?",
            "Can the company change these terms without asking me?",
            "What happens to my data?",
            "If something goes wrong, can I go to court?",
        ),
    ),
    Persona(
        id="small_business",
        label="Small-business owner",
        blurb="Vendor contracts, liability caps, and payment terms.",
        focus=("indemnity", "limitation of liability", "payment", "termination", "intellectual property"),
        starter_questions=(
            "Who pays if something goes wrong?",
            "Is there a cap on what I can recover?",
            "When do I have to pay, and what if the other side is late?",
            "Who owns the work product?",
        ),
    ),
    Persona(
        id="caregiver",
        label="Caregiver / family decision-maker",
        blurb="Forms that affect a relative's housing, care, or money.",
        focus=("authority", "consent", "notice", "termination", "privacy", "healthcare"),
        starter_questions=(
            "Who is allowed to make decisions under this paper?",
            "What notices must we receive, and how?",
            "What happens if we need to stop or change the arrangement?",
            "Does this paper talk about medical or financial authority?",
        ),
    ),
    Persona(
        id="community_navigator",
        label="Community navigator",
        blurb="Helping someone else prepare for a clinic, advocate, or lawyer.",
        focus=("deadline", "notice", "documents", "interpreter", "accommodation"),
        starter_questions=(
            "What deadlines should this person not miss?",
            "What papers should they bring to a legal clinic?",
            "What questions should they ask a lawyer first?",
            "What access supports (interpreter, large print, extra time) might help?",
        ),
    ),
)


def persona_by_id(persona_id: str) -> Persona:
    """Return a persona by id, defaulting to tenant."""
    for item in PERSONAS:
        if item.id == persona_id:
            return item
    return PERSONAS[0]


@dataclass
class Analysis:
    """Full local analysis of one document."""

    facts: FactSheet
    next_steps: tuple[NextStep, ...]
    brief: LawyerBrief
    source_name: str = "Document"
    extra: dict = field(default_factory=dict)
