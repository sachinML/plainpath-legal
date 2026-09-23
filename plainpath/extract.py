"""Deterministic extraction of parties, money, dates, durations, and obligations."""

from __future__ import annotations

from datetime import date, datetime
import re

from plainpath.readability import count_words, flesch_scores
from plainpath.types import DatedItem, DurationTerm, MoneyTerm, Obligation, Party

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_DOC_TYPE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "lease",
        ("landlord", "tenant", "premises", "rent", "security deposit", "lease term", "dwelling"),
    ),
    (
        "employment",
        ("employee", "employer", "salary", "at-will", "non-compete", "job duties", "wages"),
    ),
    (
        "terms_of_service",
        ("terms of service", "acceptable use", "subscription", "user account", "the service"),
    ),
    (
        "privacy_policy",
        ("personal information", "privacy policy", "data we collect", "cookies", "third parties"),
    ),
    (
        "service_agreement",
        ("statement of work", "services to be provided", "invoices", "independent contractor"),
    ),
)

_MONEY_RE = re.compile(
    r"(?P<label>(?:rent|salary|wage|deposit|fee|penalty|cap|price|compensation|late fee|"
    r"early termination|subscription|monthly|annual)?[^.\n]{0,40}?)"
    r"\$\s?(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

_ISO_DATE_RE = re.compile(r"\b(20\d{2}|19\d{2})-(\d{1,2})-(\d{1,2})\b")
_US_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2}|19\d{2})\b")
_NAMED_DATE_RE = re.compile(
    r"\b("
    r"January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    r")\.?\s+(\d{1,2}),?\s+(20\d{2}|19\d{2})\b",
    re.IGNORECASE,
)

_DURATION_RE = re.compile(
    r"""
    (?:
        (?P<qty_numparen>\d{1,3})\s*\(\s*[a-z\- ]+?\s*\)\s*
      | [a-z\-]+\s*\(\s*(?P<qty_wordparen>\d{1,3})\s*\)\s*
      | (?P<qty_plain>\d{1,3})\s+
    )
    (?P<unit>days?|months?|years?)
    """,
    re.IGNORECASE | re.VERBOSE,
)

_PARTY_ROLE_RE = re.compile(
    r"""(?P<name>[A-Z][^()\n]{1,80}?)\s+\((?:the\s+)?["“']?(?P<role>Landlord|Tenant|Employer|Employee|Company|Customer|Client|Provider|User|Contractor)["”']?\)""",
)

_GOVERNING_LAW_RE = re.compile(
    r"governed by the laws of (?:the State of\s+)?(?P<place>[A-Za-z ,]+?)(?:\.|,|;)",
    re.IGNORECASE,
)

_OBLIGATION_RE = re.compile(
    r"(?P<sent>(?:[A-Z][^.!?\n]{8,220}?)\b(?:shall|must|agrees to)\b[^.!?\n]{8,220}[.!?])",
)

_ROLE_WORDS = (
    "landlord",
    "tenant",
    "employer",
    "employee",
    "company",
    "customer",
    "client",
    "provider",
    "user",
    "contractor",
    "you",
)


def classify_document(text: str) -> tuple[str, str]:
    """Return (document_type, confidence_label) using keyword hits only."""
    lowered = text.lower()
    scored: list[tuple[int, str]] = []
    for doc_type, hints in _DOC_TYPE_HINTS:
        hits = sum(1 for hint in hints if hint in lowered)
        scored.append((hits, doc_type))
    scored.sort(reverse=True)
    best_hits, best_type = scored[0]
    if best_hits >= 3:
        return best_type, "high"
    if best_hits >= 1:
        return best_type, "medium"
    return "other", "low"


def parse_money_to_cents(raw: str) -> int:
    """Parse a dollar amount like '1,450.50' into integer cents."""
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return 0
    if "." in cleaned:
        whole, frac = cleaned.split(".", 1)
        frac = (frac + "00")[:2]
        return int(whole or "0") * 100 + int(frac)
    return int(cleaned) * 100


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def extract_money(text: str) -> tuple[MoneyTerm, ...]:
    """Find dollar amounts and a short label from nearby words."""
    found: list[MoneyTerm] = []
    seen: set[tuple[int, str]] = set()
    for match in _MONEY_RE.finditer(text):
        cents = parse_money_to_cents(match.group("amount"))
        nearby = match.group("label").strip(" :-\n\t")
        label = _clip_label(nearby) or "amount"
        key = (cents, label.lower())
        if key in seen:
            continue
        seen.add(key)
        found.append(
            MoneyTerm(
                amount_cents=cents,
                label=label,
                source=_excerpt(text, match.start(), match.end()),
            )
        )
    return tuple(found[:24])


def extract_dates(text: str, today: date) -> tuple[DatedItem, ...]:
    """Find calendar dates and compute days-from-today in code."""
    items: list[DatedItem] = []
    seen: set[date] = set()

    def add(value: date | None, start: int, end: int, label: str) -> None:
        if value is None or value in seen:
            return
        seen.add(value)
        items.append(
            DatedItem(
                value=value,
                label=label,
                source=_excerpt(text, start, end),
                days_from_today=(value - today).days,
            )
        )

    for match in _ISO_DATE_RE.finditer(text):
        add(
            _safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3))),
            match.start(),
            match.end(),
            _date_label(text, match.start()),
        )
    for match in _US_DATE_RE.finditer(text):
        add(
            _safe_date(int(match.group(3)), int(match.group(1)), int(match.group(2))),
            match.start(),
            match.end(),
            _date_label(text, match.start()),
        )
    for match in _NAMED_DATE_RE.finditer(text):
        month = _MONTHS.get(match.group(1).lower().rstrip("."))
        if month is None:
            continue
        add(
            _safe_date(int(match.group(3)), month, int(match.group(2))),
            match.start(),
            match.end(),
            _date_label(text, match.start()),
        )
    items.sort(key=lambda item: item.value)
    return tuple(items[:20])


def extract_durations(text: str) -> tuple[DurationTerm, ...]:
    """Find day/month/year durations and convert to an approximate day count."""
    found: list[DurationTerm] = []
    seen: set[tuple[int, str]] = set()
    for match in _DURATION_RE.finditer(text):
        qty_raw = match.group("qty_numparen") or match.group("qty_wordparen") or match.group("qty_plain")
        if not qty_raw:
            continue
        quantity = int(qty_raw)
        unit = match.group("unit").lower()
        days = _duration_to_days(quantity, unit)
        key = (quantity, unit.rstrip("s"))
        if key in seen:
            continue
        seen.add(key)
        found.append(
            DurationTerm(
                quantity=quantity,
                unit=unit,
                days_approx=days,
                source=_excerpt(text, match.start(), match.end()),
            )
        )
    return tuple(found[:20])


def extract_parties(text: str) -> tuple[Party, ...]:
    """Find 'Name (the "Role")' party definitions."""
    found: list[Party] = []
    seen: set[tuple[str, str]] = set()
    for match in _PARTY_ROLE_RE.finditer(text):
        name = re.sub(r"\s+", " ", match.group("name")).strip(" ,")
        role = match.group("role").lower()
        key = (role, name.lower())
        if key in seen or len(name) < 3:
            continue
        seen.add(key)
        found.append(Party(role=role, name=name, source=_excerpt(text, match.start(), match.end())))
    return tuple(found[:12])


def extract_governing_law(text: str) -> str | None:
    """Return a governing-law place name if the common phrase is present."""
    match = _GOVERNING_LAW_RE.search(text)
    if not match:
        return None
    place = re.sub(r"\s+", " ", match.group("place")).strip(" ,")
    return place or None


def extract_obligations(text: str) -> tuple[Obligation, ...]:
    """Pull shall/must sentences and guess the actor from nearby role words."""
    found: list[Obligation] = []
    seen: set[str] = set()
    for match in _OBLIGATION_RE.finditer(text):
        sentence = re.sub(r"\s+", " ", match.group("sent")).strip()
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        actor = _guess_actor(sentence)
        duty = sentence
        found.append(Obligation(actor=actor, duty=duty, source=sentence[:240]))
        if len(found) >= 20:
            break
    return tuple(found)


def _duration_to_days(quantity: int, unit: str) -> int:
    stem = unit.lower().rstrip("s")
    if stem == "day":
        return quantity
    if stem == "month":
        return quantity * 30
    if stem == "year":
        return quantity * 365
    return quantity


def _guess_actor(sentence: str) -> str:
    lowered = sentence.lower()
    for role in _ROLE_WORDS:
        if re.search(rf"\b{re.escape(role)}\b", lowered):
            return role
    return "a party"


def _clip_label(raw: str) -> str:
    words = re.findall(r"[A-Za-z]+", raw)
    if not words:
        return ""
    return " ".join(words[-5:]).lower()


def _date_label(text: str, start: int) -> str:
    window = text[max(0, start - 48) : start]
    words = re.findall(r"[A-Za-z]+", window)
    if not words:
        return "date"
    return " ".join(words[-6:]).lower()


def _excerpt(text: str, start: int, end: int, radius: int = 90) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    chunk = re.sub(r"\s+", " ", text[lo:hi]).strip()
    return chunk[:280]


def reading_profile(text: str) -> tuple[int, float, float]:
    """Return (word_count, flesch_ease, grade_level)."""
    ease, grade = flesch_scores(text)
    return count_words(text), ease, grade


def parse_today(raw: str | None, fallback: date | None = None) -> date:
    """Parse an ISO date string for the 'as of' clock used in deadline math."""
    if raw:
        try:
            return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass
    return fallback or date.today()
