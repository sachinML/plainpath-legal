"""Strip active HTML from model output before it is shown as Markdown."""

from __future__ import annotations

import re

_SCRIPT = re.compile(r"(?is)<script\b[^>]*>.*?</script>")
_IFRAME = re.compile(r"(?is)<iframe\b[^>]*>.*?</iframe>")
_OBJECT = re.compile(r"(?is)<object\b[^>]*>.*?</object>")
_EMBED = re.compile(r"(?is)<embed\b[^>]*/?>")
_JS_URL = re.compile(r"(?i)javascript:")
_EVENT_ATTR = re.compile(r"(?i)\son\w+\s*=")


def safe_markdown(text: str) -> str:
    """Keep Markdown emphasis; drop script/iframe/js URLs and inline handlers."""
    if not text:
        return ""
    cleaned = _SCRIPT.sub("", text)
    cleaned = _IFRAME.sub("", cleaned)
    cleaned = _OBJECT.sub("", cleaned)
    cleaned = _EMBED.sub("", cleaned)
    cleaned = _JS_URL.sub("", cleaned)
    cleaned = _EVENT_ATTR.sub(" ", cleaned)
    return cleaned
