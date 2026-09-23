"""Accessibility CSS and copy. Injected by the Streamlit shell."""

from __future__ import annotations

DEFAULT_CSS = """
<style>
:root { --plainpath-focus: #0B57D0; }
a:focus, button:focus, input:focus, textarea:focus, select:focus,
[tabindex]:focus, .stButton > button:focus, .stDownloadButton > button:focus,
.stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox div:focus-within {
  outline: 3px solid var(--plainpath-focus) !important;
  outline-offset: 3px !important;
}
.stApp { color: #1A1A1A; }
.status-text { font-weight: 650; }
.skip-link {
  position: absolute;
  left: 0.75rem;
  top: -3rem;
  background: #000000;
  color: #FFFFFF;
  padding: 0.5rem 0.75rem;
  z-index: 10000;
  font-weight: 700;
}
.skip-link:focus { top: 0.5rem; }
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
"""

HIGH_CONTRAST_CSS = """
<style>
:root { --plainpath-focus: #FFD100; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
[data-testid="stSidebar"], [data-testid="stToolbar"] {
  background: #000000 !important;
  color: #FFFFFF !important;
}
.stApp p, .stApp li, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {
  color: #FFFFFF !important;
}
a, a:visited { color: #FFD100 !important; }
.stButton > button, .stDownloadButton > button {
  background: #000000 !important;
  color: #FFFFFF !important;
  border: 2px solid #FFFFFF !important;
}
a:focus, button:focus, input:focus, textarea:focus, select:focus,
[tabindex]:focus, .stButton > button:focus {
  outline: 3px solid #FFD100 !important;
  outline-offset: 3px !important;
}
</style>
"""

LARGE_TEXT_CSS = """
<style>
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] label,
[data-testid="stMarkdownContainer"] {
  font-size: 1.22rem !important;
  line-height: 1.55 !important;
}
[data-testid="stAppViewContainer"] h1 { font-size: 2rem !important; }
[data-testid="stAppViewContainer"] h2 { font-size: 1.6rem !important; }
[data-testid="stAppViewContainer"] h3 { font-size: 1.35rem !important; }
</style>
"""


def css_bundle(*, high_contrast: bool, large_text: bool) -> str:
    """Return the CSS block(s) to inject. Never shown as visible page text."""
    parts = [DEFAULT_CSS]
    if high_contrast:
        parts.append(HIGH_CONTRAST_CSS)
    if large_text:
        parts.append(LARGE_TEXT_CSS)
    return "\n".join(parts)


DOMAIN_A11Y_BLURB = (
    "Domain accessibility: PlainPath is built for people who cannot easily hire a lawyer, "
    "including renters, workers, consumers, family caregivers, and community navigators "
    "helping someone else. It offers plain-language rewrites, a large-print / high-contrast "
    "reading surface, a printable briefing pack, and an access checklist (interpreter, "
    "support person, extra time, remote meeting). It does not replace accessible court "
    "or clinic services — it helps someone prepare to use them."
)

UI_A11Y_BLURB = (
    "Interface accessibility: skip link to the document; visible keyboard focus outlines "
    "on every control; optional high-contrast and large-text modes; status is always text "
    "(for example 'High · Automatic renewal'), never color alone; buttons and toggles have "
    "visible word labels, not icons-only; language of the explanation is announced; default "
    "theme targets readable contrast on cream and ink."
)
