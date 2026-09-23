"""Orchestrate local facts first, then optional language generation."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from plainpath.brief import as_persona_id, build_brief, persona_from_id
from plainpath.clauses import detect_clauses
from plainpath.compare import compare_documents
from plainpath.extract import (
    classify_document,
    extract_dates,
    extract_durations,
    extract_governing_law,
    extract_money,
    extract_obligations,
    extract_parties,
    reading_profile,
)
from plainpath.gaps import find_gaps
from plainpath.llm import LLMClient
from plainpath.next_steps import route_next_steps
from plainpath.prompts import (
    compare_prompt,
    lawyer_questions_prompt,
    next_steps_prompt,
    qa_prompt,
    simplify_prompt,
)
from plainpath.retrieve import retrieve
from plainpath.risk import score_risk
from plainpath.types import (
    Analysis,
    CompareReport,
    FactSheet,
    LLMResult,
    Literacy,
    RetrievedChunk,
)


def build_fact_sheet(text: str, *, today: date, persona_id: str) -> FactSheet:
    """Run the entire local engine. No network."""
    doc_type, confidence = classify_document(text)
    parties = extract_parties(text)
    money = extract_money(text)
    dates = extract_dates(text, today)
    durations = extract_durations(text)
    obligations = extract_obligations(text)
    governing_law = extract_governing_law(text)
    words, ease, grade = reading_profile(text)
    clauses = detect_clauses(text)
    gaps = find_gaps(text, doc_type, persona_id)
    risk = score_risk(clauses, money, durations)
    return FactSheet(
        document_type=doc_type,
        document_type_confidence=confidence,
        parties=parties,
        money=money,
        dates=dates,
        durations=durations,
        obligations=obligations,
        governing_law=governing_law,
        word_count=words,
        reading_ease=ease,
        reading_grade=grade,
        clauses=clauses,
        gaps=gaps,
        risk=risk,
    )


@lru_cache(maxsize=32)
def analyze_document(
    text: str,
    *,
    today: date,
    persona_id: str,
    source_name: str = "Document",
) -> Analysis:
    """Facts + routed next steps + briefing pack. Cached per (text, as-of, role)."""
    pid = as_persona_id(persona_id)
    facts = build_fact_sheet(text, today=today, persona_id=pid)
    steps = route_next_steps(facts, pid)
    persona = persona_from_id(pid)
    brief = build_brief(facts, persona, steps)
    return Analysis(facts=facts, next_steps=steps, brief=brief, source_name=source_name)


def narrate_simplify(
    client: LLMClient,
    analysis: Analysis,
    *,
    persona_id: str,
    literacy: Literacy,
    language: str,
) -> LLMResult:
    """Language-lane summary grounded in the fact sheet."""
    persona = persona_from_id(persona_id)
    system, user = simplify_prompt(analysis.facts, persona, literacy, language)
    return client.complete(system=system, user=user)


def narrate_compare(
    client: LLMClient,
    report: CompareReport,
    *,
    persona_id: str,
    literacy: Literacy,
    language: str,
) -> LLMResult:
    """Explain a comparison that was already computed."""
    persona = persona_from_id(persona_id)
    system, user = compare_prompt(report, persona, literacy, language)
    return client.complete(system=system, user=user)


def answer_question(
    client: LLMClient,
    document_text: str,
    question: str,
    *,
    persona_id: str,
    literacy: Literacy,
    language: str,
    k: int = 4,
) -> tuple[tuple[RetrievedChunk, ...], LLMResult]:
    """Retrieve excerpts in code, then ask the model to speak only from those excerpts."""
    chunks = retrieve(document_text, question, k=k)
    persona = persona_from_id(persona_id)
    system, user = qa_prompt(question, chunks, persona, literacy, language)
    return chunks, client.complete(system=system, user=user)


def narrate_next_steps(
    client: LLMClient,
    analysis: Analysis,
    *,
    persona_id: str,
    literacy: Literacy,
    language: str,
) -> LLMResult:
    """Rephrase routed steps."""
    persona = persona_from_id(persona_id)
    system, user = next_steps_prompt(analysis.next_steps, persona, literacy, language)
    return client.complete(system=system, user=user)


def narrate_lawyer_questions(
    client: LLMClient,
    analysis: Analysis,
    *,
    persona_id: str,
    literacy: Literacy,
    language: str,
) -> LLMResult:
    """Generate extra questions for a professional, grounded in flags/gaps."""
    persona = persona_from_id(persona_id)
    system, user = lawyer_questions_prompt(analysis.facts, persona, literacy, language)
    return client.complete(system=system, user=user)


@lru_cache(maxsize=16)
def compare_texts(text_a: str, text_b: str) -> CompareReport:
    """Public compare entry point. Cached per document pair."""
    return compare_documents(text_a, text_b)
