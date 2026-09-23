"""Rule-based next-step router. The LLM only rephrases these steps."""

from __future__ import annotations

from plainpath.types import FactSheet, NextStep, PersonaId


def route_next_steps(facts: FactSheet, persona_id: PersonaId) -> tuple[NextStep, ...]:
    """Choose next steps from extracted facts, clause kinds, gaps, and persona."""
    steps: list[NextStep] = []
    kinds = {hit.kind for hit in facts.clauses}

    steps.append(
        NextStep(
            code="not_advice",
            title="Treat this as information, not a decision",
            why="PlainPath cannot apply the law of your city or state to your facts.",
            urgency="now",
            audience_note="Everyone sees this reminder.",
        )
    )

    upcoming = [item for item in facts.dates if 0 <= item.days_from_today <= 21]
    overdue = [item for item in facts.dates if item.days_from_today < 0]
    if upcoming:
        soonest = min(upcoming, key=lambda item: item.days_from_today)
        steps.append(
            NextStep(
                code="calendar",
                title=f"Put {soonest.value.isoformat()} on a calendar ({soonest.days_from_today} days from the as-of date)",
                why=f"The engine found a date near: {soonest.label or 'a dated term'}.",
                urgency="now" if soonest.days_from_today <= 7 else "soon",
                audience_note="Deadlines are computed from dates in the text, not guessed.",
            )
        )
    if overdue:
        steps.append(
            NextStep(
                code="past_date",
                title="A date in this paper is already in the past",
                why="Check whether that date was a start date, a notice date, or a missed window.",
                urgency="now",
                audience_note="Past dates need a human to interpret; the engine only subtracts calendars.",
            )
        )

    if "auto_renewal" in kinds:
        steps.append(
            NextStep(
                code="cancel_window",
                title="Find the last day you can say you do not want a renewal",
                why="Automatic renewal language is in this document.",
                urgency="soon",
                audience_note="Ask a clinic or lawyer before relying on a self-help cancel if money or housing is at stake.",
            )
        )

    if facts.risk.band == "high":
        steps.append(
            NextStep(
                code="lawyer_before_sign",
                title="Show this paper to a legal professional before you sign, ignore, or pay a penalty",
                why=f"Watchfulness score is {facts.risk.score} / 100 (high).",
                urgency="now",
                audience_note=_aid_note(persona_id),
            )
        )
    elif facts.risk.band == "medium":
        steps.append(
            NextStep(
                code="lawyer_questions",
                title="Prepare questions for a legal professional or clinic",
                why=f"Watchfulness score is {facts.risk.score} / 100 (medium).",
                urgency="soon",
                audience_note=_aid_note(persona_id),
            )
        )

    if any(hit.kind in {"late_fee", "early_termination_fee", "deposit"} for hit in facts.clauses):
        steps.append(
            NextStep(
                code="money_records",
                title="Gather payment records, notices, and messages",
                why="Fees or held money appear in the document.",
                urgency="soon",
                audience_note="Bank records, receipts, and dated emails help a lawyer faster than a summary alone.",
            )
        )

    if "non_compete" in kinds:
        steps.append(
            NextStep(
                code="noncompete",
                title="Do not assume a non-compete is enforceable or unenforceable",
                why="Non-compete language was flagged. Rules differ widely by place and job type.",
                urgency="now",
                audience_note="Workers: ask before quitting, starting a new job, or signing.",
            )
        )

    if persona_id in {"community_navigator", "caregiver"}:
        steps.append(
            NextStep(
                code="access_supports",
                title="Ask about interpreter, large-print, extra time, and a support person",
                why="Courts, clinics, and agencies often must consider access needs when asked.",
                urgency="soon",
                audience_note="Write the request, keep a copy, and bring the large-print briefing pack.",
            )
        )

    if facts.gaps:
        first_gap = facts.gaps[0]
        steps.append(
            NextStep(
                code="ask_gap",
                title=f"Ask about a missing topic: {first_gap.topic}",
                why=first_gap.why_it_matters,
                urgency="when_you_can",
                audience_note=first_gap.suggested_question,
            )
        )

    steps.append(
        NextStep(
            code="bring_pack",
            title="Take the Lawyer Briefing Pack to a clinic or licensed professional",
            why="The pack lists facts the engine found, flags, gaps, and questions — not a legal opinion.",
            urgency="when_you_can",
            audience_note="Legal aid, law-school clinics, and bar-referral services are starting points in many areas.",
        )
    )
    return tuple(_dedupe(steps))


def _aid_note(persona_id: PersonaId) -> str:
    if persona_id == "tenant":
        return "Housing counselors and tenant hotlines exist in many cities; they are not a substitute for legal advice."
    if persona_id == "worker":
        return "Employment-law clinics and labor agencies can explain options; they need the written contract."
    if persona_id == "consumer":
        return "Consumer-protection agencies and legal aid may review unfair-terms questions."
    if persona_id == "small_business":
        return "Small-business legal clinics and bar referral services can review vendor paper."
    if persona_id == "caregiver":
        return "Ask whether a legal clinic can include the person who has legal authority to decide."
    return "Help the person book an interpreter and bring paper copies, not only a phone screenshot."


def _dedupe(steps: list[NextStep]) -> list[NextStep]:
    seen: set[str] = set()
    out: list[NextStep] = []
    for step in steps:
        if step.code in seen:
            continue
        seen.add(step.code)
        out.append(step)
    return out
