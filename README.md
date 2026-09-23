# PlainPath

**See through legal documents.** Facts stay on the device. Language comes from a live model.

PlainPath is a GenAI companion for people who need to **understand, compare, and navigate** legal papers without pretending the app is a lawyer. It is built for the Hack2skill PromptWars challenge **AI for Legal Assistance & Access**.

> PlainPath provides information and assistance only. It is not a lawyer, it does not create an attorney-client relationship, and it does not replace professional legal advice.

**Public repo:** https://github.com/sachinML/plainpath-legal  
**Live demo:** Deploy from that repo on [Streamlit Community Cloud](https://share.streamlit.io/) (`app.py` on `main`). After you add `GEMINI_API_KEY` (or Groq/OpenAI) as a secret, reboot the app and hard-refresh — the in-app banner must say **Live model**, not mock.

## Why two lanes?

Language models are good at **wording** and bad at unsupervised **arithmetic and lookup**. PlainPath splits the work:

| Lane | What it does | Who computes it |
| --- | --- | --- |
| A — Facts engine | Document type, parties, money (integer cents), dates, days remaining, durations, clause flags, Gap Watch, watchfulness score, obligation sentences, retrieval, next-step routing | Deterministic Python |
| B — Language | Plain-language rewrite, comparison narrative, excerpt-grounded Q&A, rephrased next steps, extra questions for a professional | Live LLM (Gemini, Groq, OpenAI-compatible, or Ollama) |

The model is given JSON facts and is instructed **never to invent amounts, dates, scores, or citations**. If the model is down, Lane A still works and the UI says so honestly.

## Problem statement → feature mapping

| Challenge pillar | Audience / need | Feature | Implementation |
| --- | --- | --- | --- |
| Simplifying complex legal documents | Everyone, especially non-lawyers | Lane B rewrite in plain / everyday / keep-terms style; Flesch reading ease shown for the original | `plainpath/prompts.py`, `plainpath/readability.py`, Simplify tab in `app.py` |
| Comparing contracts, agreements, or policies | Renters comparing a renewal; small businesses comparing vendor paper | Clause alignment plus integer-cent mismatches | `plainpath/compare.py`, Compare tab |
| Highlighting clauses, obligations, risks, inconsistencies | All roles | Clause catalog, obligation ledger, watchfulness score, Gap Watch | `plainpath/clauses.py`, `plainpath/risk.py`, `plainpath/gaps.py` |
| Answering questions based on provided documents | All roles | Local retrieval + model may only use excerpts, cited as `[E1]` | `plainpath/retrieve.py`, Ask tab |
| Understanding options and next steps | Role-specific | Rule router (deadlines, auto-renew, non-compete, access supports) | `plainpath/next_steps.py` |
| Summaries, checklists, actionable outputs | Preparing a visit | Obligation list, papers-to-bring, access checklist | `plainpath/brief.py` |
| Preparing information or questions for a legal professional | Community navigators, caregivers, everyone | Downloadable Lawyer Briefing Pack + drafted questions | Lawyer briefing tab |
| Information, not a replacement for advice | Named on the prompt | Persistent disclaimer; model system prompt forbids advice and outcome predictions | `plainpath/types.py` `DISCLAIMER`, `plainpath/prompts.py` |

### Named roles in the UI

The sidebar **role selector** is not cosmetic. It changes starter questions, Gap Watch, next steps, and the briefing pack:

- Tenant / renter
- Worker / employee
- Consumer
- Small-business owner
- Caregiver / family decision-maker
- Community navigator (helping someone else)

## Accessibility (two levels)

**Domain-level.** Legal information is often unusable if you cannot hire counsel, read dense English, travel to a clinic, or attend without an interpreter. PlainPath adds: plain-language and multilingual explanation; a printable briefing pack; an access checklist (interpreter, large print, extra time, support person, remote meeting); and a Community navigator / Caregiver role for people assisting someone else — including people with disabilities.

**UI-level (WCAG-oriented).**

- Visible keyboard focus outlines on every control (3px; yellow on black in high contrast)
- **High contrast mode** toggle and **Large text mode** toggle, both with visible word labels
- Status is always text (`High risk — Automatic renewal`), never color alone
- No icon-only controls
- Default cream/ink theme aimed at readable contrast

Documented again in `plainpath/a11y.py` and the in-app “How this maps to the challenge” tab.

## Quick start

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m pyflakes plainpath tests app.py
streamlit run app.py
```

Copy `.env.example` to `.env` and set a key, **or** add Streamlit secrets. Never commit secrets.

### Live model (required for a real demo)

Set `LLM_PROVIDER=auto` (default). PlainPath picks the first available:

1. `GEMINI_API_KEY` or `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/) free tier (`gemini-2.5-flash` by default)
2. `GROQ_API_KEY` — Groq OpenAI-compatible API
3. `OPENAI_API_KEY` — OpenAI or any `OPENAI_BASE_URL`
4. Local [Ollama](https://ollama.com) if it is running
5. Mock language mode (facts engine still runs; banner says the language lane is not live)

On Streamlit Community Cloud, put the same names under **App settings → Secrets**, then reboot the app and hard-refresh the browser.

## Tests and hygiene

- Unit tests cover extraction, clause flags, Gap Watch, risk math, compare mismatches, retrieval relevance, next-step routing, config `default_factory` env rereads, prompt grounding, and **LLM graceful degradation** (client pointed at `http://127.0.0.1:1`, no exception to the UI).
- `.gitignore` excludes `.venv/`, `node_modules/`, `__pycache__/`, secrets, IDE folders, zips, and build artifacts.
- Dependencies are declared in `requirements.txt` only (Streamlit, pypdf). `pyflakes` is optional for local lint. No vendored libraries.

## Project layout

```
app.py                 # Streamlit UI
plainpath/             # config, facts engine, LLM clients, prompts, a11y
data/samples/          # fictional lease, renewal, employment, consumer terms
tests/                 # unittest suite
```

## Deploy

1. This GitHub repository must stay **public**, **single branch (`main`)**, and **under 10 MB** (no `.venv`).
2. Open [Streamlit Community Cloud](https://share.streamlit.io/), deploy `app.py` from `main`.
3. Add `GEMINI_API_KEY` (or Groq/OpenAI) as a secret. Reboot. Confirm the in-app banner says **Live model**.

Before every push:

```bash
python -m unittest discover -s tests -v
python -m pyflakes plainpath tests app.py   # optional; pip install pyflakes
git ls-files | grep -E '\.venv/|node_modules/|\.idea/|\.DS_Store'
```

The last command must print nothing.

## License

MIT. Sample documents are fictional and are not legal forms.
