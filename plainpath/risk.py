"""Deterministic risk scoring from clause hits and extracted facts."""

from __future__ import annotations

from plainpath.types import ClauseHit, DurationTerm, MoneyTerm, RiskLevel, RiskReport

_LEVEL_WEIGHT: dict[RiskLevel, int] = {"high": 18, "medium": 10, "low": 4}

# Extra weight when a non-compete looks long (math, not an LLM guess).
_LONG_NONCOMPETE_DAYS = 365


def score_risk(
    clauses: tuple[ClauseHit, ...],
    money: tuple[MoneyTerm, ...] = (),
    durations: tuple[DurationTerm, ...] = (),
) -> RiskReport:
    """
    Compute a 0–100 score from weighted clause flags plus a few numeric rules.

    The language model is never asked to invent this number.
    """
    score = 0
    drivers: list[str] = []

    kinds = {hit.kind for hit in clauses}
    for hit in clauses:
        score += _LEVEL_WEIGHT[hit.level]
        drivers.append(f"{hit.level.upper()} · {hit.title}: {hit.why_it_matters}")

    if "arbitration" in kinds and "class_waiver" in kinds:
        score += 8
        drivers.append("HIGH · Arbitration plus a class waiver stacks extra access barriers.")

    if "auto_renewal" in kinds:
        notice = _shortest_day_duration(durations)
        if notice is not None and notice < 15:
            score += 8
            drivers.append(
                f"HIGH · Auto-renewal with a short notice window (~{notice} days) is easy to miss."
            )

    if "non_compete" in kinds:
        longest = _longest_duration_days(durations)
        if longest is not None and longest > _LONG_NONCOMPETE_DAYS:
            score += 10
            drivers.append(
                f"HIGH · A non-compete lasting about {longest} days is longer than one year."
            )

    if "late_fee" in kinds:
        late = _money_with_label(money, "late")
        rent = _money_with_label(money, "rent") or _money_with_label(money, "salary")
        if late and rent and rent.amount_cents > 0:
            pct = (late.amount_cents * 100) // rent.amount_cents
            if pct >= 10:
                score += 8
                drivers.append(
                    f"MEDIUM · Late fee {late.display} is about {pct}% of {rent.label} {rent.display}."
                )

    score = max(0, min(100, score))
    band: RiskLevel
    if score >= 50:
        band = "high"
    elif score >= 25:
        band = "medium"
    else:
        band = "low"

    summary = (
        f"Watchfulness score {score} / 100 ({band}). "
        "This is a document-flag count, not a prediction of a court outcome."
    )
    return RiskReport(score=score, band=band, summary=summary, drivers=tuple(drivers[:12]))


def _shortest_day_duration(durations: tuple[DurationTerm, ...]) -> int | None:
    dayish = [item.days_approx for item in durations if item.unit.lower().startswith("day")]
    if not dayish:
        return None
    return min(dayish)


def _longest_duration_days(durations: tuple[DurationTerm, ...]) -> int | None:
    if not durations:
        return None
    return max(item.days_approx for item in durations)


def _money_with_label(money: tuple[MoneyTerm, ...], needle: str) -> MoneyTerm | None:
    needle_l = needle.lower()
    for item in money:
        if needle_l in item.label.lower():
            return item
    return None
