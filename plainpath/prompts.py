"""Prompts that hand the model FACTS JSON and forbid invented numbers."""

from __future__ import annotations

import json
from typing import Any

from plainpath.types import CompareReport, FactSheet, Literacy, NextStep, Persona, RetrievedChunk

_SYSTEM = """You are PlainPath's language lane. You explain legal documents in accessible language.

Hard rules:
- You are not a lawyer. Do not give legal advice, predictions of court outcomes, or "you should sign / not sign" commands.
- Use ONLY the JSON facts, excerpts, or steps provided. If a number, date, party, or clause is not in that JSON, say you do not have it.
- Never invent amounts, dates, routes, scores, or legal citations.
- Pair every caution with words, not only adjectives.
- If the user asked for another language, write in that language but keep names, dates, and amounts exactly as given.
- End with the reminder that a licensed professional should review anything high-stakes.
"""


def literacy_instruction(literacy: Literacy) -> str:
    """How simple the rewrite should be."""
    if literacy == "plain":
        return "Use short sentences and everyday words. Explain a term the first time it appears."
    if literacy == "keep_terms":
        return "Keep legal terms, but add a plain-language gloss in parentheses."
    return "Use clear adult English. Avoid Latin and unexplained jargon."


def simplify_prompt(
    facts: FactSheet,
    persona: Persona,
    literacy: Literacy,
    language: str,
) -> tuple[str, str]:
    """Prompt for a grounded plain-language summary."""
    payload = {
        "persona": {"id": persona.id, "label": persona.label, "focus": list(persona.focus)},
        "literacy": literacy,
        "language": language,
        "document_type": facts.document_type,
        "parties": [{"role": p.role, "name": p.name} for p in facts.parties],
        "money": [{"label": m.label, "display": m.display} for m in facts.money],
        "dates": [
            {
                "date": item.value.isoformat(),
                "days_from_as_of": item.days_from_today,
                "label": item.label,
            }
            for item in facts.dates
        ],
        "durations": [
            {"quantity": d.quantity, "unit": d.unit, "days_approx": d.days_approx}
            for d in facts.durations
        ],
        "governing_law": facts.governing_law,
        "reading_ease": facts.reading_ease,
        "reading_grade": facts.reading_grade,
        "watchfulness_score": facts.risk.score,
        "watchfulness_band": facts.risk.band,
        "clauses": [
            {"title": c.title, "level": c.level, "why": c.why_it_matters, "excerpt": c.excerpt}
            for c in facts.clauses
        ],
        "gaps": [{"topic": g.topic, "question": g.suggested_question} for g in facts.gaps],
        "obligations": [{"actor": o.actor, "duty": o.duty} for o in facts.obligations[:8]],
    }
    user = (
        f"{literacy_instruction(literacy)}\n"
        f"Write for this role: {persona.label}. Language: {language}.\n"
        "Produce: (1) a short what-this-paper-is, (2) who appears to owe what, "
        "(3) flags to notice, (4) what the paper does not appear to say. "
        "Do not add options that are not supported by the JSON.\n\n"
        f"FACTS_JSON:\n{json.dumps(payload, indent=2)}"
    )
    return _SYSTEM, user


def compare_prompt(
    report: CompareReport,
    persona: Persona,
    literacy: Literacy,
    language: str,
) -> tuple[str, str]:
    """Prompt for explaining a comparison that was already computed."""
    payload: dict[str, Any] = {
        "type_a": report.type_a,
        "type_b": report.type_b,
        "aligned": [
            {
                "title": row.title,
                "status": row.status,
                "note": row.note,
                "excerpt_a": row.excerpt_a,
                "excerpt_b": row.excerpt_b,
            }
            for row in report.aligned
        ],
        "money_mismatches": [
            {
                "label": row.label,
                "document_a": row.display_a,
                "document_b": row.display_b,
                "delta_cents": row.delta_cents,
            }
            for row in report.money_mismatches
        ],
        "only_in_a": list(report.only_in_a),
        "only_in_b": list(report.only_in_b),
    }
    user = (
        f"{literacy_instruction(literacy)}\n"
        f"Role: {persona.label}. Language: {language}.\n"
        "Explain the differences. When money differs, repeat the provided displays; "
        "do not recompute. Call out clauses that appear in only one document.\n\n"
        f"COMPARE_JSON:\n{json.dumps(payload, indent=2)}"
    )
    return _SYSTEM, user


def qa_prompt(
    question: str,
    chunks: tuple[RetrievedChunk, ...],
    persona: Persona,
    literacy: Literacy,
    language: str,
) -> tuple[str, str]:
    """Prompt for excerpt-grounded Q&A."""
    payload = {
        "question": question,
        "excerpts": [{"id": c.chunk_id, "score": c.score, "text": c.text} for c in chunks],
    }
    user = (
        f"{literacy_instruction(literacy)}\n"
        f"Role: {persona.label}. Language: {language}.\n"
        "Answer the question using ONLY the excerpts. Cite excerpt ids like [E1]. "
        "If the excerpts do not contain the answer, say the document does not appear "
        "to address it, and suggest one question for a legal professional.\n\n"
        f"QA_JSON:\n{json.dumps(payload, indent=2)}"
    )
    return _SYSTEM, user


def next_steps_prompt(
    steps: tuple[NextStep, ...],
    persona: Persona,
    literacy: Literacy,
    language: str,
) -> tuple[str, str]:
    """Prompt that rephrases routed steps without adding new ones."""
    payload = {
        "steps": [
            {
                "title": s.title,
                "why": s.why,
                "urgency": s.urgency,
                "audience_note": s.audience_note,
            }
            for s in steps
        ]
    }
    user = (
        f"{literacy_instruction(literacy)}\n"
        f"Role: {persona.label}. Language: {language}.\n"
        "Turn these steps into a short numbered plan. Do not add new steps, dates, or amounts.\n\n"
        f"STEPS_JSON:\n{json.dumps(payload, indent=2)}"
    )
    return _SYSTEM, user


def lawyer_questions_prompt(
    facts: FactSheet,
    persona: Persona,
    literacy: Literacy,
    language: str,
) -> tuple[str, str]:
    """Prompt for extra questions a person can take to a professional."""
    payload = {
        "persona": persona.label,
        "document_type": facts.document_type,
        "clauses": [c.title for c in facts.clauses],
        "gaps": [g.topic for g in facts.gaps],
        "money": [f"{m.label} {m.display}" for m in facts.money],
        "starter_questions": list(persona.starter_questions),
    }
    user = (
        f"{literacy_instruction(literacy)}\n"
        f"Language: {language}.\n"
        "Write 6 practical questions this person can ask a licensed legal professional. "
        "Ground each question in the provided flags or gaps. Do not answer the questions.\n\n"
        f"BRIEF_JSON:\n{json.dumps(payload, indent=2)}"
    )
    return _SYSTEM, user
