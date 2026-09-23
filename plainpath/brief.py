"""Lawyer Briefing Pack: structured facts a person can take to a professional."""

from __future__ import annotations

from plainpath.readability import ease_label
from plainpath.types import FactSheet, LawyerBrief, NextStep, Persona, PersonaId, PERSONAS


_DOCUMENTS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "lease": (
        "The signed lease and every renewal or addendum",
        "Rent receipts, money-order stubs, or bank records",
        "Photos or written repair requests, if housing conditions matter",
        "Notices from the landlord (entry, late rent, non-renewal, eviction)",
        "A government ID and any housing-subsidy paperwork",
    ),
    "employment": (
        "The offer letter and the signed agreement",
        "Employee handbook pages that were given to you",
        "Pay stubs and a job description",
        "Emails about duties, leave, or exit",
        "Any non-compete, IP, or arbitration add-on",
    ),
    "terms_of_service": (
        "A saved copy or PDF of the terms as they appeared when you agreed",
        "Account emails, invoices, and cancel-attempt screenshots",
        "A timeline of when you signed up and what you paid",
        "Any chat or ticket with the company",
    ),
    "privacy_policy": (
        "The policy text and the date you saved it",
        "Account settings screenshots",
        "A list of what data you think they have",
    ),
    "service_agreement": (
        "The signed agreement, statements of work, and change orders",
        "Invoices and proof of payment",
        "Emails about scope, delays, or defects",
        "A simple timeline of who did what",
    ),
    "other": (
        "The full document, not a screenshot of one page",
        "Every attachment, exhibit, and later email that changed the deal",
        "A timeline of dates, money, and who said what",
        "Photo ID and any prior lawyer letters",
    ),
}

_ACCESS_CHECKLIST: tuple[str, ...] = (
    "Ask for an interpreter if English is not the easiest language for the meeting.",
    "Ask for large print or extra time if reading this paper is tiring or visually hard.",
    "Ask whether a support person or advocate may sit in.",
    "Ask about wheelchair access, remote video, or a quiet room if travel or sensory load is hard.",
    "Bring a paper copy of this briefing pack, not only a phone.",
    "Write down the names of people you meet and the next date they gave you.",
)


def build_brief(
    facts: FactSheet,
    persona: Persona,
    next_steps: tuple[NextStep, ...],
) -> LawyerBrief:
    """Assemble a briefing pack from engine output. No new facts are invented here."""
    snapshot = [
        f"Document type (keyword classifier): {facts.document_type} (confidence {facts.document_type_confidence})",
        f"Word count: {facts.word_count}",
        (
            f"Reading ease: {facts.reading_ease} — {ease_label(facts.reading_ease)}; "
            f"grade estimate {facts.reading_grade}"
        ),
        f"Watchfulness score: {facts.risk.score} / 100 ({facts.risk.band})",
    ]
    if facts.governing_law:
        snapshot.append(f"Governing-law phrase found: {facts.governing_law}")
    if facts.parties:
        snapshot.append(
            "Parties: "
            + "; ".join(f"{party.name} ({party.role})" for party in facts.parties)
        )
    if facts.money:
        snapshot.append(
            "Money terms: "
            + "; ".join(f"{item.label} {item.display}" for item in facts.money[:8])
        )
    if facts.dates:
        snapshot.append(
            "Dates: "
            + "; ".join(
                f"{item.value.isoformat()} ({item.days_from_today:+d} days, {item.label})"
                for item in facts.dates[:8]
            )
        )

    risk_lines = [facts.risk.summary, *facts.risk.drivers]
    gap_questions = tuple(gap.suggested_question for gap in facts.gaps) or (
        "What in this paper is most likely to be misunderstood?",
    )
    docs = _DOCUMENTS_BY_TYPE.get(facts.document_type, _DOCUMENTS_BY_TYPE["other"])
    role_questions = persona.starter_questions + tuple(
        step.audience_note for step in next_steps if step.code == "ask_gap"
    )
    return LawyerBrief(
        snapshot_lines=tuple(snapshot),
        risk_lines=tuple(risk_lines),
        gap_questions=gap_questions,
        documents_to_bring=docs,
        accessibility_checklist=_ACCESS_CHECKLIST,
        role_questions=role_questions,
    )


def brief_to_markdown(
    brief: LawyerBrief,
    *,
    persona_label: str,
    source_name: str,
    disclaimer: str,
) -> str:
    """Render the briefing pack as downloadable Markdown."""
    def bullets(title: str, lines: tuple[str, ...]) -> str:
        body = "\n".join(f"- {line}" for line in lines) or "- (none found)"
        return f"## {title}\n\n{body}\n"

    parts = [
        f"# Lawyer Briefing Pack — {source_name}",
        "",
        f"Prepared for role: **{persona_label}**.",
        "",
        disclaimer,
        "",
        bullets("Snapshot (engine facts)", brief.snapshot_lines),
        bullets("Flags and scores (engine)", brief.risk_lines),
        bullets("Questions about gaps", brief.gap_questions),
        bullets("Questions from this role", brief.role_questions),
        bullets("Papers to bring", brief.documents_to_bring),
        bullets("Access supports to ask for", brief.accessibility_checklist),
        "",
        "_This pack is a study aid. It is not a legal opinion or a filing._",
        "",
    ]
    return "\n".join(parts)


def persona_from_id(persona_id: str) -> Persona:
    """Look up a persona; used by the UI and brief builder."""
    for item in PERSONAS:
        if item.id == persona_id:
            return item
    return PERSONAS[0]


def as_persona_id(raw: str) -> PersonaId:
    """Narrow a string to a known persona id."""
    for item in PERSONAS:
        if item.id == raw:
            return item.id
    return "tenant"
