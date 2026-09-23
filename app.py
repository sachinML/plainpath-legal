"""PlainPath Streamlit entry point."""

from __future__ import annotations

from datetime import date

import streamlit as st

from plainpath.a11y import DOMAIN_A11Y_BLURB, UI_A11Y_BLURB, css_bundle
from plainpath.brief import brief_to_markdown
from plainpath.config import get_settings
from plainpath.documents import bytes_to_text
from plainpath.extract import parse_today
from plainpath.llm import build_llm, provider_status
from plainpath.pipeline import (
    analyze_document,
    answer_question,
    compare_texts,
    narrate_compare,
    narrate_lawyer_questions,
    narrate_next_steps,
    narrate_simplify,
)
from plainpath.readability import ease_label
from plainpath.samples import list_samples, load_sample, load_sample_pair
from plainpath.types import DISCLAIMER, PERSONAS, Analysis, Literacy

st.set_page_config(page_title="PlainPath — legal documents in two lanes", layout="wide")


def _literacy(raw: str) -> Literacy:
    if raw.startswith("Plain"):
        return "plain"
    if raw.startswith("Keep"):
        return "keep_terms"
    return "everyday"


def _read_upload(upload) -> str:
    if upload is None:
        return ""
    try:
        return bytes_to_text(upload.name, upload.getvalue())
    except Exception as error:
        st.error(f"Could not read that file: {error}")
        return ""


def _status_words(level: str) -> str:
    mapping = {"high": "High", "medium": "Medium", "low": "Low", "same": "Same",
               "different": "Different", "only_a": "Only in A", "only_b": "Only in B"}
    return mapping.get(level, level)


def _show_llm_result(result) -> None:
    if result.degraded:
        st.warning(result.text)
        return
    st.markdown(result.text)


def main() -> None:
    settings = get_settings()
    if "llm_client" not in st.session_state:
        st.session_state.llm_client = build_llm(settings)
    client = st.session_state.llm_client
    status = provider_status(client)

    with st.sidebar:
        st.header("Who is this for?")
        persona_label = st.selectbox(
            "Your role (changes questions, next steps, and the briefing pack)",
            options=[p.label for p in PERSONAS],
            index=0,
        )
        persona = next(p for p in PERSONAS if p.label == persona_label)
        st.write(persona.blurb)

        literacy_raw = st.selectbox(
            "Reading style",
            options=[
                "Plain words",
                "Everyday English",
                "Keep legal terms, add a gloss",
            ],
        )
        language = st.selectbox(
            "Language for the generated explanation",
            options=["English", "Spanish", "Hindi"],
        )
        as_of_raw = st.text_input(
            "As-of date for deadline math (YYYY-MM-DD)",
            value=date.today().isoformat(),
            help="Dates and 'days remaining' are subtracted in code from this date.",
        )
        as_of = parse_today(as_of_raw, fallback=date.today())

        st.header("Reading supports")
        high_contrast = st.toggle("High contrast mode", value=False)
        large_text = st.toggle("Large text mode", value=False)

        st.header("Sample papers")
        sample_name = st.selectbox("Load a fictional sample into Document A", options=list_samples())
        if st.button("Load sample into Document A", type="primary"):
            st.session_state.doc_a_area = load_sample(sample_name)
            st.session_state.doc_a_name = sample_name
            st.rerun()
        if st.button("Load Oakridge lease pair for compare"):
            a_text, b_text = load_sample_pair()
            st.session_state.doc_a_area = a_text
            st.session_state.doc_b_area = b_text
            st.session_state.doc_a_name = "Oakridge lease (sample A)"
            st.session_state.doc_b_name = "Oakridge renewal (sample B)"
            st.rerun()

        st.header("Language model")
        if status.live:
            st.markdown(f"**Status: Live model** — {status.label}")
        else:
            st.markdown(f"**Status: Not live** — {status.label}")
        st.write(status.detail)
        if st.button("Rebuild model client from current secrets"):
            st.session_state.llm_client = build_llm(get_settings())
            st.rerun()

    st.markdown(css_bundle(high_contrast=high_contrast, large_text=large_text), unsafe_allow_html=True)

    st.title("PlainPath")
    st.subheader("See through legal documents. Facts stay on this device. Language comes from a live model.")
    st.info(DISCLAIMER)

    if status.live:
        st.success(f"Language lane: {status.label}. Facts lane: local engine (always on).")
    else:
        st.warning(f"Language lane: {status.label}. Facts, scores, and flags still run locally.")

    st.markdown(
        "Two lanes: **Lane A (facts)** extracts parties, money, dates, clause flags, "
        "gaps, and a watchfulness score in code. **Lane B (language)** asks a live model "
        "only to explain those facts in your role, reading style, and language. "
        "The model is told not to invent numbers."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Document A")
        upload_a = st.file_uploader(
            "Upload Document A (.txt, .md, or .pdf)",
            type=["txt", "md", "pdf"],
            key="upload_a",
        )
        if upload_a is not None:
            token = (upload_a.name, upload_a.size)
            if st.session_state.get("_upload_a_token") != token:
                loaded = _read_upload(upload_a)
                if loaded:
                    st.session_state.doc_a_area = loaded
                    st.session_state.doc_a_name = upload_a.name
                    st.session_state._upload_a_token = token
        doc_a = st.text_area(
            "Document A text",
            height=160,
            key="doc_a_area",
        )
    with col_b:
        st.markdown("### Document B (optional, for compare)")
        upload_b = st.file_uploader(
            "Upload Document B (.txt, .md, or .pdf)",
            type=["txt", "md", "pdf"],
            key="upload_b",
        )
        if upload_b is not None:
            token = (upload_b.name, upload_b.size)
            if st.session_state.get("_upload_b_token") != token:
                loaded = _read_upload(upload_b)
                if loaded:
                    st.session_state.doc_b_area = loaded
                    st.session_state.doc_b_name = upload_b.name
                    st.session_state._upload_b_token = token
        doc_b = st.text_area(
            "Document B text",
            height=160,
            key="doc_b_area",
        )

    if not doc_a.strip():
        st.markdown("Paste or load a document to begin. Samples live in the sidebar.")
        _footer()
        return

    analysis = analyze_document(
        doc_a,
        today=as_of,
        persona_id=persona.id,
        source_name=st.session_state.get("doc_a_name", "Document A"),
    )
    literacy = _literacy(literacy_raw)

    tabs = st.tabs(
        [
            "Simplify and scan",
            "Compare A and B",
            "Ask the document",
            "Options and next steps",
            "Lawyer briefing pack",
            "How this maps to the challenge",
        ]
    )

    with tabs[0]:
        _tab_simplify(client, analysis, persona.id, literacy, language)
    with tabs[1]:
        _tab_compare(client, doc_a, doc_b, persona.id, literacy, language)
    with tabs[2]:
        _tab_ask(client, doc_a, persona, literacy, language)
    with tabs[3]:
        _tab_steps(client, analysis, persona.id, literacy, language)
    with tabs[4]:
        _tab_brief(client, analysis, persona, literacy, language)
    with tabs[5]:
        _tab_mapping()

    _footer()


def _tab_simplify(client, analysis: Analysis, persona_id: str, literacy: Literacy, language: str) -> None:
    facts = analysis.facts
    left, right = st.columns(2)
    with left:
        st.markdown("### Lane A — facts engine")
        st.markdown(
            f"**Document type:** {facts.document_type} "
            f"(confidence {facts.document_type_confidence}, keyword classifier)"
        )
        st.markdown(
            f"**Reading ease:** {facts.reading_ease} — {ease_label(facts.reading_ease)} "
            f"(grade estimate {facts.reading_grade}). Word count: {facts.word_count}."
        )
        st.markdown(
            f"**Watchfulness score:** {facts.risk.score} / 100 — "
            f"{_status_words(facts.risk.band)} band. {facts.risk.summary}"
        )
        if facts.parties:
            st.markdown("**Parties found**")
            for party in facts.parties:
                st.write(f"- {party.name} ({party.role})")
        if facts.money:
            st.markdown("**Money terms (integer cents, formatted in code)**")
            for item in facts.money:
                st.write(f"- {item.label}: {item.display}")
        if facts.dates:
            st.markdown("**Dates and days from the as-of date**")
            for item in facts.dates:
                when = "in the past" if item.days_from_today < 0 else f"{item.days_from_today} days away"
                st.write(f"- {item.value.isoformat()} — {when} — {item.label}")
        st.markdown("**Clause flags (color is never the only signal)**")
        if facts.clauses:
            for hit in facts.clauses:
                st.write(f"- {_status_words(hit.level)} risk — {hit.title}: {hit.why_it_matters}")
                st.caption(hit.excerpt)
        else:
            st.write("No catalogued clause phrases were matched.")
        st.markdown("**Gap Watch — topics this kind of paper often covers but this text does not**")
        if facts.gaps:
            for gap in facts.gaps:
                st.write(f"- Missing: {gap.topic}. {gap.why_it_matters}")
        else:
            st.write("No catalogued gaps for this document type and role.")
        st.markdown("**Obligation sentences (shall / must)**")
        for ob in facts.obligations[:8]:
            st.write(f"- {ob.actor}: {ob.duty}")
    with right:
        st.markdown("### Lane B — live language")
        if st.button("Generate plain-language explanation", type="primary", key="btn_simplify"):
            with st.spinner("Calling the language model with the facts JSON only..."):
                result = narrate_simplify(
                    client, analysis, persona_id=persona_id, literacy=literacy, language=language
                )
                st.session_state.simplify_result = result
        if "simplify_result" in st.session_state:
            _show_llm_result(st.session_state.simplify_result)
        else:
            st.write("Press the button to rewrite Lane A in your reading style. Numbers come from Lane A.")


def _tab_compare(client, doc_a: str, doc_b: str, persona_id: str, literacy: Literacy, language: str) -> None:
    if not doc_b.strip():
        st.write("Paste a second document (or load the Oakridge pair) to compare clauses and amounts.")
        return
    report = compare_texts(doc_a, doc_b)
    st.markdown(
        f"Classifier: Document A looks like **{report.type_a}**; "
        f"Document B looks like **{report.type_b}**."
    )
    st.markdown("### Amounts that differ (subtracted in cents)")
    if report.money_mismatches:
        for row in report.money_mismatches:
            delta = row.delta_cents / 100.0
            st.write(
                f"- {row.label}: A {row.display_a} vs B {row.display_b} "
                f"(B minus A = {delta:+.2f})"
            )
    else:
        st.write("No labelled amounts were matched across both papers with a different value.")
    st.markdown("### Clause alignment")
    for row in report.aligned:
        st.markdown(f"**{row.title}** — {_status_words(row.status)}. {row.note}")
        cols = st.columns(2)
        with cols[0]:
            st.caption("Document A")
            st.write(row.excerpt_a or "Not found in A.")
        with cols[1]:
            st.caption("Document B")
            st.write(row.excerpt_b or "Not found in B.")
    if st.button("Explain these differences in plain language", type="primary", key="btn_compare"):
        with st.spinner("Calling the language model with the compare JSON only..."):
            st.session_state.compare_result = narrate_compare(
                client, report, persona_id=persona_id, literacy=literacy, language=language
            )
    if "compare_result" in st.session_state:
        _show_llm_result(st.session_state.compare_result)


def _tab_ask(client, doc_a: str, persona, literacy: Literacy, language: str) -> None:
    st.markdown("Ask a question. Retrieval is local keyword ranking; the model may only use the excerpts.")
    suggestion = st.selectbox("Starter question for your role", options=list(persona.starter_questions))
    question = st.text_input("Your question", value=suggestion)
    if st.button("Search the document and answer", type="primary", key="btn_ask"):
        if not question.strip():
            st.error("Type a question first.")
        else:
            with st.spinner("Retrieving excerpts, then calling the model..."):
                chunks, result = answer_question(
                    client,
                    doc_a,
                    question.strip(),
                    persona_id=persona.id,
                    literacy=literacy,
                    language=language,
                )
                st.session_state.qa_chunks = chunks
                st.session_state.qa_result = result
    if "qa_chunks" in st.session_state:
        st.markdown("### Retrieved excerpts (local ranker)")
        for chunk in st.session_state.qa_chunks:
            st.write(f"**{chunk.chunk_id}** — match score {chunk.score:.1f}")
            st.caption(chunk.text[:900])
    if "qa_result" in st.session_state:
        st.markdown("### Model answer")
        _show_llm_result(st.session_state.qa_result)


def _tab_steps(client, analysis: Analysis, persona_id: str, literacy: Literacy, language: str) -> None:
    st.markdown("These options are routed by rules from the fact sheet. The model only rephrases them.")
    for step in analysis.next_steps:
        st.markdown(
            f"**{step.title}** — urgency: {_status_words_urgency(step.urgency)}. Why: {step.why}"
        )
        st.caption(step.audience_note)
    if st.button("Write this plan in my reading style", type="primary", key="btn_steps"):
        with st.spinner("Calling the language model with the steps JSON only..."):
            st.session_state.steps_result = narrate_next_steps(
                client, analysis, persona_id=persona_id, literacy=literacy, language=language
            )
    if "steps_result" in st.session_state:
        _show_llm_result(st.session_state.steps_result)


def _status_words_urgency(value: str) -> str:
    return {"now": "Now", "soon": "Soon", "when_you_can": "When you can"}.get(value, value)


def _tab_brief(client, analysis: Analysis, persona, literacy: Literacy, language: str) -> None:
    brief = analysis.brief
    st.markdown("### Snapshot (engine)")
    for line in brief.snapshot_lines:
        st.write(f"- {line}")
    st.markdown("### Flags")
    for line in brief.risk_lines:
        st.write(f"- {line}")
    st.markdown("### Questions about gaps")
    for line in brief.gap_questions:
        st.write(f"- {line}")
    st.markdown("### Questions from this role")
    for line in brief.role_questions:
        st.write(f"- {line}")
    st.markdown("### Papers to bring")
    for line in brief.documents_to_bring:
        st.write(f"- {line}")
    st.markdown("### Access supports to ask for")
    for line in brief.accessibility_checklist:
        st.write(f"- {line}")
    markdown = brief_to_markdown(
        brief,
        persona_label=persona.label,
        source_name=analysis.source_name,
        disclaimer=DISCLAIMER,
    )
    st.download_button(
        "Download briefing pack as Markdown",
        data=markdown.encode("utf-8"),
        file_name="plainpath-lawyer-briefing.md",
        mime="text/markdown",
    )
    if st.button("Draft extra questions for a legal professional", type="primary", key="btn_brief"):
        with st.spinner("Calling the language model with flags and gaps only..."):
            st.session_state.brief_q = narrate_lawyer_questions(
                client, analysis, persona_id=persona.id, literacy=literacy, language=language
            )
    if "brief_q" in st.session_state:
        _show_llm_result(st.session_state.brief_q)


def _tab_mapping() -> None:
    st.markdown("**Challenge pillar to feature**")
    st.markdown(
        "| Pillar | Feature in this app | Where |\n"
        "| --- | --- | --- |\n"
        "| Simplify complex documents | Lane B rewrite grounded in Lane A facts; Flesch scores in code | Simplify and scan |\n"
        "| Compare contracts or policies | Clause alignment plus integer-cent mismatches | Compare A and B |\n"
        "| Highlight clauses, obligations, risks, inconsistencies | Clause catalog, obligation ledger, watchfulness score, Gap Watch | Simplify and scan |\n"
        "| Answer questions from the document | Local retrieval plus cited excerpts | Ask the document |\n"
        "| Options and next steps | Rule router plus optional rewrite | Options and next steps |\n"
        "| Summaries, checklists, actionable outputs | Obligation list, briefing pack, access checklist | Lawyer briefing pack |\n"
        "| Prepare for a legal professional | Downloadable briefing pack and drafted questions | Lawyer briefing pack |\n"
        "| Information, not a replacement for advice | Persistent disclaimer; model instructions forbid advice | Every page |"
    )
    st.write(DOMAIN_A11Y_BLURB)
    st.write(UI_A11Y_BLURB)


def _footer() -> None:
    st.divider()
    st.caption(DISCLAIMER)
    st.caption("Sample documents are fictional. Do not use them as real contracts.")


if __name__ == "__main__":
    main()
